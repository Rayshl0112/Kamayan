import json
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import app
from backend.demo import CAPTIONS,DURATION,FILIPINO,SENTENCE,demo_events

ROOT=Path(__file__).resolve().parents[1]

def test_demo_caption_sentence_and_filipino_cover_video():
    assert CAPTIONS[0]['start']==0
    assert CAPTIONS[-1]['end']==DURATION
    assert CAPTIONS[-1]['text']==SENTENCE
    assert CAPTIONS[-1]['text_fil']==FILIPINO
    for previous,next_caption in zip(CAPTIONS,CAPTIONS[1:]):
        assert previous['end']==next_caption['start']
        assert next_caption['text'].startswith(previous['text'])

def test_exact_sample_stream_and_no_ai_loaded():
    with TestClient(app) as client:
        status=client.get('/model-status').json()
        assert status['mode']=='demo'
        assert status['device']=='No AI inference'
        path=ROOT/'research/samples/how2sign-sentence.mp4'
        response=client.post('/recognize-timeline',files={'file':('uploaded.mp4',path.read_bytes(),'video/mp4')})
        assert response.status_code==200
        events=[json.loads(line) for line in response.text.splitlines()]
        assert events[0]['full_text']==SENTENCE
        assert events[0]['full_text_fil']==FILIPINO
        assert events[-1]['static_reference'] is True
        assert events[-1]['sentence_translation'] is False
        assert [event['text'] for event in events if event['type']=='prediction']==[caption['text'] for caption in CAPTIONS]
        assert not any(name in sys.modules for name in ('torch','mediapipe','cv2'))

def test_unrelated_upload_gets_no_invented_sentence():
    with TestClient(app) as client:
        response=client.post('/recognize-timeline',files={'file':('different.mp4',b'different footage','video/mp4')})
        events=[json.loads(line) for line in response.text.splitlines()]
        assert len(events)==1 and events[0]['type']=='error'
        assert 'text' not in events[0]

def test_speech_of_exact_complete_reference_sentence():
    with TestClient(app) as client:
        response=client.post('/speech',json={'text':SENTENCE,'rate':1})
        assert response.status_code==200
        assert response.content[:4]==b'RIFF'
        assert len(response.content)>10000
