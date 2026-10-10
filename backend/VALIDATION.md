# Local model validation — 10 October 2026

Kamayan runs real local pretrained isolated-word ASL inference. It is not a general sentence translator. The backend imports the original GestureBridge preprocessing and NumPy inference from the separate, ignored `research/GestureBridge` checkout. No upstream source or weights are included in application distribution assets.

## Actual model and preprocessing

The active model is the five-model GestureBridge WLASL-100 ensemble: Conv1D-Small, GRU-Small, and BigConv1D seeds 42, 43, and 1337. All five files physically exist and are loaded. `/model-status` exposes their sizes and SHA-256 hashes. Archives are checked with `allow_pickle=False` before the upstream loader uses them. There are 100 ordered vocabulary labels and an input shape of `(30, 63)`.

The exact upstream extractor samples 30 ordered, evenly spaced frame indices inside the chosen selection. MediaPipe runs in IMAGE mode with one hand, confidence 0.3. It uses the first hand's 21 original-image landmarks: x and y in pixels, z as relative MediaPipe depth. Landmarks are translated to the wrist, divided by the maximum 2D Euclidean distance from the wrist, and flattened into 63 float32 features. Missing detections repeat the last detected feature vector, or use zeros before the first detection. The detector's original cropping and small-crop rejection behavior is preserved.

Ensemble probabilities follow the original formula: `0.15 × Conv1D + 0.15 × GRU + (0.7/3) × each BigConv1D`. The loaded calibration threshold is approximately 0.48. Detection below 30% or a top score below that threshold gives an uncertain result with no accepted label. A high score can still be wrong; the user must review and confirm a word before adding it to the transcript.

## Genuine video observations

The videos came from direct source URLs in the official WLASL v0.3 metadata. All four are designated `test` in that metadata; this is not a signer-disjoint evaluation. The reference gloss is metadata for evaluation and never enters inference. Only decoded pixels enter the model.

| Clip ID | Reference | Actual ensemble top prediction | Model score | Outcome |
| --- | --- | --- | --- | --- |
| 12320 | computer | computer | 87.91% | Correct on this clip |
| 17713 | drink | drink | 29.25% | Correct suggestion; marked uncertain |
| 27209 | help | computer | 58.01% | Wrong; help is third at 12.66% |
| 69494 | student | walk | 73.44% | Wrong, despite a high score |
| no-sign | No signer (CC0 flower video) | walk | 32.99% | Rejected: 0/30 frames have a hand; accepted label is null |

These four clips are a small functionality check, not a valid accuracy benchmark. Two top labels match the references, and two do not. This evidence does not reproduce or establish the upstream's benchmark claim.

The initial single-model smoke test was also genuine. From `research/GestureBridge`, run:

```powershell
& ..\..\.venv\Scripts\python.exe -X utf8 scripts/predict_word_clip.py ../samples/27209.mp4
```

It detected hands in 24/30 frames and returned `room` at 98.2% for the reference `help` video. The command exited 0. The UTF-8 option fixes a Windows terminal encoding error in the upstream progress bars; no model output was changed.

On the first four-clip ensemble run, classifier inference took 17–24 ms on CPU; total video processing took approximately 1.7–3.1 seconds and process RSS was approximately 154–167 MB. Under concurrent work, later runs took up to 9.5 seconds per clip. Timings vary with host load. Model loading took approximately 1.4 seconds. Exact run outputs, hashes, installed versions, and the no-sign control results are saved in `research/report.json` by `research/evaluate.py`.

## Runtime checks

```powershell
& .venv\Scripts\python.exe -X utf8 research/evaluate.py
& .venv\Scripts\python.exe -X utf8 -m pytest backend -v
```

Tests use the actual local weights and real sample videos. They cover model files, hashes, label order, input shape and finite values, exact normalization and sequence order, decoding, corrupt file rejection, different predictions across four videos, genuine successful computer recognition, low-score abstention, no-sign abstention, valid and invalid selections, actual HTTP recognition, model status, vocabulary, samples, upload cleanup, and locally installed SAPI speech.

`evaluate.py` prohibits Python socket connections for the complete model-loading and inference run. This proves inference works with network connections blocked for that process. It does not claim the machine's Wi-Fi was physically disabled. The offline speech helper uses installed Windows System.Speech voices; it does not use browser or cloud speech synthesis.

## Rights and practical limitations

GestureBridge has no detected repository license grant. Keep its checkout, weights, and raw evaluation clips private and separate; do not publish them with the application. WLASL's README says academic/computational use and no commercial use. The C-UDA agreement separately treats qualifying trained models as Results without restrictions on Results; this does not grant permission for the authors' independent code or model distribution. See `docs/THIRD_PARTY.md` for source links and details.

Unsupported words and non-sign hand motion can receive high model scores. The model observes one hand, lacks facial and full-body grammar, and recognizes an isolated supported word per selection. A transcript is a user-reviewed series of glosses, not generated English grammar. Use manual segment selection for longer videos. Recognition performance on new signers is not established.
