import json
from pathlib import Path
import cv2
import numpy as np
from backend.runtime import inspect_video
from backend.timeline import propose_segments
from backend.test_runtime import client, runtime, tmp_path


def test_real_sentence_stream_uses_video_model_and_labels_uncertainty(client):
    path=Path(__file__).resolve().parents[1]/'research/samples/how2sign-sentence.mp4'
    with path.open('rb') as stream:
        response=client.post('/recognize-timeline',files={'file':('unrelated-name.mp4',stream,'video/mp4')})
    assert response.status_code==200
    events=[json.loads(line) for line in response.text.splitlines()]
    assert events[0]['type']=='metadata'
    assert 3.8 < events[0]['duration'] < 4
    prediction=next(event for event in events if event['type']=='prediction')
    assert prediction['input_shape']==[30,63]
    assert prediction['detected_frames']>0
    assert len(prediction['top_predictions'])==3
    assert prediction['uncertain'] is True
    assert events[-1]['sentence_translation'] is False


def test_timeline_rejects_invalid_format_without_false_captions(client):
    response=client.post('/recognize-timeline',files={'file':('video.mp4',b'invalid','video/mp4')})
    assert [json.loads(line)['type'] for line in response.text.splitlines()]==['error']


def test_multiple_proposed_windows_cover_actual_video_time(tmp_path):
    path=tmp_path/'long.mp4'
    writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'mp4v'),20,(160,120))
    assert writer.isOpened()
    for index in range(140):
        frame=np.zeros((120,160,3),dtype=np.uint8)
        cv2.rectangle(frame,(index%100,30),(index%100+25,70),(190,210,190),-1)
        writer.write(frame)
    writer.release()
    info=inspect_video(path)
    intervals=propose_segments(path,info)
    assert len(intervals)>=2
    assert intervals[0][0]==0
    assert abs(intervals[-1][1]-7)<.01
    assert all(start<end and end-start<=4.5 for start,end in intervals)
    assert all(abs(intervals[index][1]-intervals[index+1][0])<.01 for index in range(len(intervals)-1))
