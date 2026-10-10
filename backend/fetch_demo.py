"""One-time download/crop of the exact licensed reference demo; no ASL model."""
import hashlib
import json
import subprocess
from pathlib import Path
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
SOURCE='https://imatge-upc.github.io/slt_how2sign_wicv2023/assets/example_1_slt.mp4'
SOURCE_SHA='acf850d51339c7424581292348a9a5627c8e891d65ceb26fdea4be8dd62358a9'

def main():
    directory=ROOT/'research/samples'
    directory.mkdir(parents=True,exist_ok=True)
    output=directory/'how2sign-sentence.mp4'
    if not output.is_file():
        from imageio_ffmpeg import get_ffmpeg_exe
        with urlopen(SOURCE,timeout=45) as response:
            content=response.read(20*1024*1024+1)
        if hashlib.sha256(content).hexdigest()!=SOURCE_SHA:
            raise RuntimeError('The source demo has changed. Review its reference translation before using it.')
        original=directory/'sentence-source.mp4'
        original.write_bytes(content)
        try:
            subprocess.run([get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y','-i',str(original),'-vf','crop=1280:580:0:0','-c:v','libx264','-preset','veryfast','-crf','19','-an','-movflags','+faststart',str(output)],check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        finally:
            original.unlink(missing_ok=True)
    entries=[{'id':'how2sign-sentence','kind':'sentence','name':'Continuous ASL sentence','path':output.name,'source_url':SOURCE,'source_page':'https://imatge-upc.github.io/slt_how2sign_wicv2023/','license':'How2Sign research sample, CC BY-NC 4.0.','changes':'Bottom reference text cropped; original frame timing preserved; audio removed.'}]
    (directory/'sentence_manifest.json').write_text(json.dumps(entries,indent=2),encoding='utf-8')
    print('Static sentence sample ready. No AI models downloaded or loaded.')

if __name__=='__main__':
    main()
