"""Local adapter for separately obtained GestureBridge research assets.

This application does not vendor upstream inference source or model weights.
The original source is imported from a private evaluation checkout so its exact
trained preprocessing and inference remain together. No network is used here.
"""
from __future__ import annotations

import hashlib
import os
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESEARCH = ROOT / "research" / "GestureBridge"
LICENSE_NOTE = "Private local evaluation only. GestureBridge has no repository license grant; WLASL is computational/noncommercial. Do not redistribute these research assets."


class VideoError(ValueError):
    """The upload cannot be decoded safely or needs a shorter selection."""


def inspect_video(path: Path) -> dict:
    """Validate actual container and decodable video before feature extraction."""
    with path.open("rb") as stream:
        header = stream.read(64)
    is_mp4 = b"ftyp" in header[:32]
    is_webm = header.startswith(b"\x1a\x45\xdf\xa3")
    if not is_mp4 and not is_webm:
        raise VideoError("This file is not an MP4 or WebM video.")
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise VideoError("The video could not be opened. Export an MP4 with H.264 video.")
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if not np.isfinite(fps) or not 0.5 <= fps <= 240:
            raise VideoError("The video has missing or invalid timing information.")
        if frames < 2 or frames > fps * 600:
            # MediaRecorder WebM often omits the duration/frame count. Decode
            # its frames without retaining them to recover bounded timing.
            frames = 0
            while frames <= fps * 600:
                ok, _ = cap.read()
                if not ok:
                    break
                frames += 1
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        if frames < 2:
            raise VideoError('The video does not contain enough decodable frames.')
        duration = frames / fps
        if duration > 600:
            raise VideoError("Please use a video shorter than ten minutes.")
        if min(width, height) < 16 or max(width, height) > 3840:
            raise VideoError("Use a video between 16 pixels and 3840 pixels per side.")
        ok, frame = cap.read()
        if not ok or frame is None:
            raise VideoError("The video container opens, but its frames are corrupted.")
        return {"duration": duration, "fps": fps, "frames": frames, "width": width, "height": height, "format": "mp4" if is_mp4 else "webm"}
    finally:
        cap.release()


def validate_sequence(sequence: np.ndarray) -> None:
    if sequence.shape != (30, 63):
        raise ValueError(f"Expected a (30, 63) landmark sequence; got {sequence.shape}.")
    if not np.isfinite(sequence).all():
        raise ValueError("Landmark sequence contains non-finite values.")


class LocalRecognizer:
    def __init__(self, research_path: Path | None = None, mode: str | None = None):
        self.research_path = research_path or Path(os.getenv("KAMAYAN_MODEL_ROOT", str(DEFAULT_RESEARCH)))
        self.mode = mode or os.getenv("KAMAYAN_MODEL_MODE", "ensemble")
        self.model = None
        self.cropper = None
        self.extract_clip = None
        self.ready = False
        self.error = None
        self.name = "Unavailable"
        self.threshold = 0.48
        self.load_ms = 0.0
        self.members = []
        self.artifacts = []
        self.last_result = None
        self.lock = threading.Lock()

    def load(self):
        if self.ready:
            return self.status()
        self.artifacts = []
        started = time.perf_counter()
        try:
            source = self.research_path / "src"
            scripts = self.research_path / "scripts"
            assets = self.research_path / "artifacts" / "wlasl100"
            labels_path = assets / "labels.txt"
            required = [assets / "conv1d_small.npz", labels_path, self.research_path / "artifacts" / "mediapipe" / "hand_landmarker.task"]
            for file in required:
                if not file.is_file():
                    raise FileNotFoundError(f"Missing local research asset: {file.name}. Run setup.ps1.")
            for path in (source, scripts):
                if str(path) not in sys.path:
                    sys.path.insert(0, str(path))
            from gesturebridge.pipelines.hand_crop import HandCropper
            from gesturebridge.pipelines.word_classifier import WordClassifier
            from gesturebridge.pipelines.word_ensemble import GRUClassifier, MultiEnsembleWordClassifier
            from gesturebridge.pipelines.word_bigconv1d import BigConv1DClassifier
            from extract_wlasl_landmarks import extract_clip

            labels = [label.strip() for label in labels_path.read_text(encoding="utf-8").splitlines() if label.strip()]
            if len(labels) != 100 or len(set(labels)) != 100:
                raise ValueError("The WLASL-100 label file must have exactly 100 distinct labels.")
            model_files = [assets / "conv1d_small.npz"]
            ensemble_files = [assets / "gru_small.npz"] + [assets / f"bigconv1d_s{seed}.npz" for seed in (42, 43, 1337)]
            full_ensemble = self.mode != "single" and all(path.is_file() for path in ensemble_files)
            if full_ensemble:
                model_files.extend(ensemble_files)
            # Upstream uses allow_pickle=True; verify every archive entry without
            # pickle before its loader sees the file. No downloaded code is run
            # during an inference request, and no model is downloaded at startup.
            for file in model_files:
                with np.load(file, allow_pickle=False) as weights:
                    for key in weights.files:
                        array = weights[key]
                        if array.dtype.hasobject:
                            raise ValueError(f"Unsafe object array in {file.name}.")
                        if array.dtype.kind in "fci" and not np.isfinite(array).all():
                            raise ValueError(f"Non-finite weights in {file.name}.")
                    shape = tuple(int(value) for value in weights["__input_shape__"])
                    if shape != (30, 63):
                        raise ValueError(f"Incompatible model shape in {file.name}: {shape}")
                self.artifacts.append({"name": file.name, "bytes": file.stat().st_size, "sha256": hashlib.sha256(file.read_bytes()).hexdigest()})
            conv = WordClassifier(assets / "conv1d_small.npz", labels_path)
            if full_ensemble:
                gru = GRUClassifier(assets / "gru_small.npz", labels_path)
                big = [BigConv1DClassifier(assets / f"bigconv1d_s{seed}.npz", labels_path) for seed in (42, 43, 1337)]
                models = [(conv, 0.15), (gru, 0.15)] + [(member, 0.7 / 3) for member in big]
                for member, _ in models:
                    if member.labels != labels:
                        raise ValueError("Ensemble label ordering is inconsistent.")
                self.model = MultiEnsembleWordClassifier(models)
                self.members = [path.name for path in model_files]
                self.name = "GestureBridge WLASL-100 · five-model ensemble"
                calibration = assets / "calibration.npz"
                if calibration.is_file():
                    with np.load(calibration, allow_pickle=False) as data:
                        for key in ("global_threshold", "threshold"):
                            if key in data:
                                self.threshold = float(np.asarray(data[key]).reshape(-1)[0])
                                break
            else:
                self.model = conv
                self.members = ["conv1d_small.npz"]
                self.name = "GestureBridge WLASL-100 · Conv1D-Small"
                self.threshold = 0.70
            self.cropper = HandCropper(output_size=224, padding_ratio=0.25, min_confidence=0.3, model_path=self.research_path / "artifacts" / "mediapipe" / "hand_landmarker.task")
            self.extract_clip = extract_clip
            self.ready = True
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            self.ready = False
        self.load_ms = round((time.perf_counter() - started) * 1000, 2)
        return self.status()

    def status(self):
        return {"ready": self.ready, "model": self.name, "device": "CPU", "labels_count": len(self.model.labels) if self.model else 0, "input_shape": [30, 63], "threshold": self.threshold, "members": self.members, "load_ms": self.load_ms, "artifacts": self.artifacts, "offline": True, "license_note": LICENSE_NOTE, "error": self.error, "scope": "Isolated ASL words. Review each prediction; unsupported signs can still receive high scores."}

    def recognize(self, path: Path, start: float = 0.0, end: float | None = None):
        if not self.ready:
            raise RuntimeError(self.error or "The local recognition model is unavailable.")
        began = time.perf_counter()
        info = inspect_video(path)
        end = info["duration"] if end is None else end
        if not np.isfinite(start) or not np.isfinite(end) or start < 0 or end <= start or end > info["duration"] + 0.05:
            raise VideoError("Select a valid start and end time inside this video.")
        if end - start > 30:
            raise VideoError("Choose one sign, at most 30 seconds. Use the segment controls for longer videos.")
        if end - start < 0.2:
            raise VideoError("Choose a segment at least 0.2 seconds long.")
        fs = int(round(start * info["fps"])) + 1
        fe = min(info["frames"], int(round(end * info["fps"])))
        with self.lock:
            landmark_start = time.perf_counter()
            sequence, detect = self.extract_clip(self.cropper, path, 30, fs=fs, fe=fe)
            landmark_ms = (time.perf_counter() - landmark_start) * 1000
            validate_sequence(sequence)
            inference_start = time.perf_counter()
            predictions = self.model.predict(sequence, top_k=3)
            inference_ms = (time.perf_counter() - inference_start) * 1000
        hand_rate = float(detect.mean())
        score = float(predictions[0][1])
        uncertain = hand_rate < 0.3 or score < self.threshold
        reason = "Hands were not visible in enough sampled frames." if hand_rate < 0.3 else "The model is uncertain. Review the suggestions or record the sign again." if uncertain else None
        result = {"status": "completed", "model": self.name, "label": None if uncertain else predictions[0][0], "top_predictions": [{"label": label, "score": float(prob)} for label, prob in predictions], "model_score": score, "uncertain": uncertain, "reason": reason, "processing_ms": round((time.perf_counter() - began) * 1000, 2), "landmark_ms": round(landmark_ms, 2), "inference_ms": round(inference_ms, 2), "hand_detection_rate": hand_rate, "sampled_frames": 30, "detected_frames": int(detect.sum()), "input_shape": list(sequence.shape), "device": "CPU", "segment": {"start": start, "end": end}, "video": info}
        try:
            import psutil
            result["process_ram_mb"] = round(psutil.Process().memory_info().rss / 1024 ** 2, 2)
        except ImportError:
            pass
        self.last_result = result
        return result

    def close(self):
        if self.cropper is not None:
            self.cropper.close()
            self.cropper = None
        self.ready = False
