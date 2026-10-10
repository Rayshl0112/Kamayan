"""User-authorized static captions for the exact research sentence video.

This is a reference-caption demo, not AI inference. A file hash prevents these
captions from being attached to unrelated uploaded signing videos.
"""
import hashlib
from pathlib import Path

SAMPLE_SHA256='5e0c26d841c943e86cf0c4168c40493f8d98466919a4780dee0f8c2bfbbff76c'
SENTENCE="And that's a great vital point technique for women's self defense."
FILIPINO='At iyan ay isang mahusay na teknik na nakatuon sa sensitibong bahagi ng katawan para sa pagtatanggol sa sarili ng kababaihan.'
DURATION=3.8705333333333334
CAPTIONS=[
    {'start':0.0,'end':1.05,'text':"And that's a great",'text_fil':'At iyan ay isang mahusay na'},
    {'start':1.05,'end':2.15,'text':"And that's a great vital point technique",'text_fil':'At iyan ay isang mahusay na teknik na nakatuon sa sensitibong bahagi ng katawan'},
    {'start':2.15,'end':DURATION,'text':SENTENCE,'text_fil':FILIPINO},
]

def demo_events(path:Path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        while chunk:=stream.read(1024*1024):
            digest.update(chunk)
    canonical=Path(__file__).resolve().parents[1]/'research/samples/how2sign-sentence.mp4'
    expected=hashlib.sha256(canonical.read_bytes()).hexdigest() if canonical.is_file() else SAMPLE_SHA256
    if digest.hexdigest()!=expected:
        yield {'type':'error','message':'This demo contains captions for the sentence sample only. Choose “Try a sentence video” to play it.'}
        return
    yield {'type':'metadata','duration':DURATION,'total':len(CAPTIONS),'model':'Exact sample reference captions','mode':'demo','full_text':SENTENCE,'full_text_fil':FILIPINO,'scope':'Static reference captions for this exact sample. No AI inference.'}
    for index,caption in enumerate(CAPTIONS):
        yield {'type':'prediction','index':index,'total':len(CAPTIONS),'text':caption['text'],'text_fil':caption['text_fil'],'uncertain':False,'mode':'demo','segment':{'start':caption['start'],'end':caption['end']}}
    yield {'type':'complete','total':len(CAPTIONS),'mode':'demo','sentence_translation':False,'static_reference':True}
