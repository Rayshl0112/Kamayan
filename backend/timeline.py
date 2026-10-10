"""Experimental video-time word proposals, using the real local word model.

Motion boundaries are editing proposals, not linguistic sign boundaries. This
does not turn an isolated WLASL classifier into a sentence translation model.
No source captions, audio, reference translations or filenames are used.
"""
from __future__ import annotations
import time
from pathlib import Path
import cv2
import numpy as np
from backend.runtime import VideoError, inspect_video


def propose_segments(path: Path, info: dict) -> list[tuple[float, float]]:
    duration = info['duration']
    if duration <= 4.5:
        return [(0.0, duration)]
    cap = cv2.VideoCapture(str(path))
    observations = []
    previous = None
    step = max(1, round(info['fps'] / 6))
    index = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if index % step == 0:
                gray = cv2.cvtColor(cv2.resize(frame, (256, 144)), cv2.COLOR_BGR2GRAY)
                # Analyze the signing area; overlays at the bottom are excluded.
                gray = gray[10:115, 45:211]
                score = 0.0 if previous is None else float(np.mean(cv2.absdiff(gray, previous)))
                observations.append((index / info['fps'], score))
                previous = gray
            index += 1
    finally:
        cap.release()
    scores = np.asarray([score for _, score in observations], dtype=np.float32)
    threshold = max(0.8, float(np.percentile(scores, 25)))
    segments = []
    start = 0.0
    for position in range(2, len(observations) - 1):
        timestamp = observations[position][0]
        span = timestamp - start
        quiet = all(observations[i][1] <= threshold for i in (position - 1, position))
        if span >= 1.1 and ((quiet and span >= 1.5) or span >= 3.8):
            segments.append((round(start, 3), round(timestamp, 3)))
            start = timestamp
    if duration - start >= 0.5:
        segments.append((round(start, 3), duration))
    elif segments:
        segments[-1] = (segments[-1][0], duration)
    return segments or [(0.0, duration)]


def timeline_events(recognizer, path: Path):
    began = time.perf_counter()
    info = inspect_video(path)
    if info['duration'] > 120:
        raise VideoError('For automatic caption proposals, upload a clip up to two minutes long.')
    segments = propose_segments(path, info)
    yield {'type':'metadata', 'duration':info['duration'], 'total':len(segments), 'model':recognizer.name, 'scope':'Experimental isolated-word proposals. Full sentence translation is unavailable.'}
    for index, (start, end) in enumerate(segments):
        yield {'type':'progress', 'index':index, 'total':len(segments), 'start':start, 'end':end}
        result = recognizer.recognize(path, start, end)
        yield {'type':'prediction', 'index':index, 'total':len(segments), **result}
    yield {'type':'complete', 'total':len(segments), 'processing_ms':round((time.perf_counter()-began)*1000, 2), 'sentence_translation':False}
