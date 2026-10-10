"""Local continuous ASL inference, using Meta's published SignHiera/SONAR.

Run in the isolated Ubuntu runtime. No reference text enters inference.
Original upstream preprocessing and weights are retained; the adapters below
only keep loading within this laptop's RAM/VRAM budget.
"""
from __future__ import annotations
import argparse
import gc
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'research/sonar-assets'
os.environ.setdefault('TORCH_HOME',str(ASSETS/'torch-cache'))
os.environ.setdefault('HF_HOME',str(ASSETS/'hf-cache'))
sys.path.insert(0,str(ROOT/'research/ssvp_slt/src'))


class SentenceRecognizer:
    def __init__(self):
        import torch
        import ctypes.util
        import soundfile
        original_find_library=ctypes.util.find_library
        ctypes.util.find_library=lambda name: str(soundfile._full_path) if name=='sndfile' else original_find_library(name)
        if not torch.cuda.is_available():
            raise RuntimeError('The sentence model requires the available local GPU for this configuration.')
        self.torch=torch
        self.device=torch.device('cuda')
        torch.set_num_threads(4)
        # torch.load with an mmap avoids allocating another complete CPU copy
        # of the authors' 3 GB state dictionary. Paths are fixed local assets.
        original_load=torch.load
        def mapped_load(source,*args,**kwargs):
            if hasattr(source,'name') and isinstance(source.name,str):
                source=source.name
            if isinstance(source,(str,Path)):
                kwargs.setdefault('mmap',True)
                kwargs['map_location']='cpu'
            return original_load(source,*args,**kwargs)
        torch.load=mapped_load
        from ssvp_slt.modeling import sign_hiera,sonar
        from ssvp_slt.modeling.sign_t5 import SignT5Config
        from ssvp_slt.util.video import Preprocessor

        self.loads=[]
        def load_weights(model,checkpoint_path,model_key='model'):
            checkpoint=mapped_load(str(checkpoint_path))
            state=next(checkpoint[key] for key in (model_key,'model','model_state') if key in checkpoint)
            remapped={key.replace('feature_proj','feature_projection.feature_proj') if 'feature_proj' in key and 'feature_projection' not in key else key:value for key,value in state.items()}
            mismatch=[key for key,value in remapped.items() if key in model.state_dict() and model.state_dict()[key].shape!=value.shape]
            if mismatch:
                raise RuntimeError(f'Incompatible trained weights: {mismatch[:3]}')
            missing,extra=model.load_state_dict(remapped,strict=False)
            missing=[key for key in missing if key not in sign_hiera.SIGNHIERA_EXPECTED_MISSING]
            extra=[key for key in extra if not key.startswith(sign_hiera.SIGNHIERA_EXPECTED_EXTRA)]
            if missing or extra:
                raise RuntimeError(f'Incomplete checkpoint mapping: {missing[:3]}, {extra[:3]}')
            self.loads.append({'artifact':Path(checkpoint_path).name,'loaded_tensors':len(remapped),'missing_keys':missing,'unexpected_keys':extra})
            del checkpoint,state,remapped
            gc.collect()
        sign_hiera.load_model=load_weights
        sonar.load_model=load_weights
        def create_encoder(config,device=None,dtype=None):
            config=SignT5Config.from_pretrained(str(ASSETS/'t5-config'),decoder_start_token_id=0,dropout_rate=0)
            previous=torch.get_default_dtype()
            try:
                torch.set_default_dtype(dtype or torch.float16)
                with torch.device(device or self.device):
                    model=sonar.SignT5SonarEncoder(config)
            finally:
                torch.set_default_dtype(previous)
            return model
        sonar.create_sonar_signt5_encoder_model=create_encoder
        class MeasuredPreprocessor(Preprocessor):
            face_fraction=0.0
            def detect_faces(self,frames):
                boxes,maximum=super().detect_faces(frames)
                self.face_fraction=sum(bool(box) for box in boxes)/max(1,len(boxes))
                return boxes,maximum
        config=SimpleNamespace(up_exp=1.,down_exp=3.,left_exp=1.5,right_exp=1.5,iou_threshold=.2,num_ratio_threshold=.5,hog_detector=True,detector_path=None,detection_sampling_rate=16,detection_downsample=True,num_frames=128,feature_extraction_stride=64,sampling_rate=2,target_fps=25,target_size=224,mean=(.45,.45,.45),std=(.225,.225,.225),debug=False,verbose=True)
        self.preprocessor=MeasuredPreprocessor(config,device=self.device)
        self.extractor=sign_hiera.FeatureExtractor(SimpleNamespace(pretrained_model_path=str(ASSETS/'dm_70h_ub_signhiera.pth'),model_name='hiera_base_128x224',max_batch_size=1,fp16=True,verbose=True),device=self.device)
        self.extractor.model.half()
        self.translator=sonar.SonarTranslator(SimpleNamespace(pretrained_model_path=str(ASSETS/'dm_70h_ub_sonar_encoder.pth'),base_model_name=str(ASSETS/'t5-config'),verbose=True),device=self.device,dtype=torch.float16)
        self.ready=True

    def translate(self,path):
        began=time.perf_counter()
        self.torch.cuda.reset_peak_memory_stats()
        inputs=self.preprocessor(Path(path))
        if self.preprocessor.face_fraction<.3:
            return {'text':None,'uncertain':True,'reason':'No clear signer was found.','model':'SignHiera + SONAR ASL-to-English','device':'RTX 2060','processing_ms':round((time.perf_counter()-began)*1000,2)}
        with self.torch.inference_mode():
            features=self.extractor(**inputs).to(dtype=self.torch.float16)
            result=self.translator(features,tgt_langs=['eng_Latn'])
        return {'text':result['translations'][0],'uncertain':False,'model':'SignHiera + SONAR ASL-to-English','device':self.torch.cuda.get_device_name(0),'processing_ms':round((time.perf_counter()-began)*1000,2),'feature_shape':list(features.shape),'face_detection_fraction':self.preprocessor.face_fraction,'gpu_peak_mb':round(self.torch.cuda.max_memory_allocated()/1024**2,2),'trained_weights':self.loads,'experimental':True}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--video',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    engine=SentenceRecognizer()
    result=engine.translate(args.video)
    Path(args.output).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)

if __name__=='__main__':
    main()
