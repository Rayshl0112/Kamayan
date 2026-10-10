"""Real local video/model/API checks; no mocked prediction payloads."""
from __future__ import annotations
import json
import shutil
import socket
import tempfile
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.runtime import ROOT, LocalRecognizer, VideoError, inspect_video, validate_sequence

SAMPLES = ROOT / "research/samples"

@pytest.fixture
def tmp_path():
    # The host's old pytest-of-ASUS directory has restrictive ACLs. Allocate
    # each test under this authorized workspace and clean only that directory.
    with tempfile.TemporaryDirectory(prefix="kamayan-test-", dir=ROOT / "research") as directory:
        path = Path(directory).resolve()
        assert ROOT.resolve() in path.parents
        yield path

@pytest.fixture(scope="module")
def runtime():
    engine = LocalRecognizer()
    status = engine.load()
    assert status["ready"], status["error"]
    yield engine
    engine.close()

@pytest.fixture(scope="module")
def client(runtime):
    import backend.app as api
    original = api.recognizer
    api.recognizer = runtime
    with TestClient(api.app) as session:
        yield session
    api.recognizer = original

def test_real_model_files_shapes_labels_and_five_heads(runtime):
    assert runtime.model.input_shape == (30, 63)
    assert len(runtime.model.labels) == 100
    assert runtime.model.labels[0] == "drink"
    assert runtime.model.labels[1] == "computer"
    assert len(runtime.members) == 5
    assert len(runtime.artifacts) == 5
    assert all(artifact["bytes"] > 200_000 and len(artifact["sha256"]) == 64 for artifact in runtime.artifacts)

def test_shape_and_finite_validation():
    validate_sequence(np.zeros((30, 63), dtype=np.float32))
    with pytest.raises(ValueError, match="30, 63"):
        validate_sequence(np.zeros((30, 126)))
    with pytest.raises(ValueError, match="non-finite"):
        validate_sequence(np.full((30, 63), np.nan))

def test_exact_upstream_normalization_and_order(runtime):
    from extract_wlasl_landmarks import _normalize_landmarks, sample_frame_indices
    points = np.arange(63, dtype=np.float32).reshape(21, 3)
    relative = points - points[0]
    expected = (relative / np.linalg.norm(relative[:, :2], axis=1).max()).reshape(-1)
    assert np.allclose(_normalize_landmarks(points), expected)
    assert np.allclose(_normalize_landmarks(points + 100), expected)
    assert np.allclose(_normalize_landmarks(np.zeros((21, 3))), 0)
    indices = sample_frame_indices(102, 30, fs=1, fe=-1)
    assert len(indices) == 30 and indices[0] == 0 and indices[-1] == 101
    assert np.all(np.diff(indices) >= 0)

def test_real_video_decode():
    info = inspect_video(SAMPLES / "12320.mp4")
    assert info["frames"] == 102
    assert 3.3 < info["duration"] < 3.5
    assert info["format"] == "mp4"

def test_reject_corrupt_container(tmp_path):
    corrupt = tmp_path / "corrupt.mp4"
    corrupt.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 200)
    with pytest.raises(VideoError):
        inspect_video(corrupt)
    text = tmp_path / "text.mp4"
    text.write_text("This is not a video")
    with pytest.raises(VideoError, match="not an MP4"):
        inspect_video(text)

def test_real_heldout_samples_change_predictions(runtime):
    manifest = json.loads((SAMPLES / "manifest.json").read_text())
    observed = []
    for entry in manifest:
        result = runtime.recognize(SAMPLES / entry["path"])
        assert result["input_shape"] == [30, 63]
        assert result["hand_detection_rate"] > 0
        assert len(result["top_predictions"]) == 3
        assert all(item["label"] in runtime.model.labels and 0 <= item["score"] <= 1 for item in result["top_predictions"])
        observed.append(result["top_predictions"])
        if entry["id"] == "12320":
            assert result["label"] == "computer"
        if entry["id"] == "17713":
            assert result["uncertain"] and result["label"] is None
    assert len(observed) >= 3
    assert len({json.dumps(predictions) for predictions in observed}) == len(observed)

def test_no_sign_control_abstains(runtime):
    assert (SAMPLES / "no-sign.mp4").exists(), "Fetch the CC0 MDN flower video for the no-sign control."
    result = runtime.recognize(SAMPLES / "no-sign.mp4")
    assert result["hand_detection_rate"] == 0
    assert result["uncertain"] and result["label"] is None

def test_video_inference_with_network_connection_prohibited(runtime, monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("Inference attempted a network connection")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    renamed = tmp_path / "unrelated-filename.mp4"
    shutil.copyfile(SAMPLES / "12320.mp4", renamed)
    result = runtime.recognize(renamed)
    assert result["label"] == "computer"
    assert result["device"] == "CPU"

def test_segments_validate_and_run(runtime):
    with pytest.raises(VideoError, match="valid start and end"):
        runtime.recognize(SAMPLES / "12320.mp4", 3, 2)
    result = runtime.recognize(SAMPLES / "12320.mp4", 0.5, 2.5)
    assert result["segment"] == {"start": 0.5, "end": 2.5}
    assert result["sampled_frames"] == 30

def test_api_health_status_vocabulary_and_samples(client):
    assert client.get("/health").json()["model_ready"]
    assert len(client.get("/vocabulary").json()["labels"]) == 100
    assert client.get("/model-status").json()["ready"]
    assert len(client.get("/samples").json()["samples"]) >= 3
    assert client.get("/samples/12320").status_code == 200
    assert client.get("/samples/not-a-sample").status_code == 404

def test_api_actual_video_and_temp_cleanup(client):
    before = set(Path(tempfile.gettempdir()).glob("kamayan-*.mp4"))
    with (SAMPLES / "12320.mp4").open("rb") as file:
        response = client.post("/recognize-video", files={"file": ("clip.mp4", file, "video/mp4")})
    assert response.status_code == 200, response.text
    assert response.json()["label"] == "computer"
    assert set(Path(tempfile.gettempdir()).glob("kamayan-*.mp4")) == before
    assert client.get("/performance").json()["last_result"]["label"] == "computer"

def test_api_rejects_bad_files_and_bad_segments(client):
    assert client.post("/recognize-video", files={"file": ("file.txt", b"hello", "text/plain")}).status_code == 400
    assert client.post("/recognize-video", files={"file": ("bad.mp4", b"not video", "video/mp4")}).status_code == 400
    with (SAMPLES / "12320.mp4").open("rb") as file:
        response = client.post("/recognize-segment", files={"file": ("clip.mp4", file, "video/mp4")}, data={"start": "5", "end": "6"})
    assert response.status_code == 400
