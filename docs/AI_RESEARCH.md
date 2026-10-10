# kamayan.

**Every Sign Connects.**

Kamayan is a local ASL **isolated-word recognition** studio for Windows. Upload a short signing video, select one sign, review real pretrained-model suggestions, confirm a word, and hear your editable transcript using a local Windows voice.

The interface uses a light mint palette, a large video workspace, a transcript panel on the right, and Apple system-font preferences with Segoe UI on Windows. System fonts are used without downloading or redistributing Apple's font files.

## Start on Windows

Prerequisites: Python 3.11 or 3.12, Node.js 20 or later, Git for Windows, and an installed Windows SAPI voice. This machine's bundled Python 3.12 is supported. Setup downloads dependencies and the local evaluation assets once; inference and speech run on your computer afterward.

From the project folder in PowerShell:

```powershell
.\setup.ps1 -EvaluationSamples
.\test.ps1
.\start.ps1
```

If PowerShell blocks local scripts, run these scoped commands instead:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1 -EvaluationSamples
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\test.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
```

To choose an existing Python installation:

```powershell
.\setup.ps1 -PythonPath 'C:\path\to\python.exe'
```

The studio opens at <http://127.0.0.1:5173>; the recognition service listens at <http://127.0.0.1:8765>. Both bind to loopback. Use `start.ps1 -NoBrowser` if you prefer to open the studio yourself. Startup prints the two process IDs and writes service logs to `.runtime/`. To close this launch, pass those two IDs to `Stop-Process -Id <backend-id>,<studio-id>`.

`-EvaluationSamples` is optional for everyday app use, but required before the full real-video test suite. It obtains four direct-source WLASL test clips for private academic/computational evaluation and a CC0 no-sign control, and stores them separately under `research/samples`. It never downloads from YouTube. Read the third-party notes before using this evaluation option; do not package these recordings with a public build. Omit the option and upload your own authorized recording if you do not need these tests.

Do not use `npm run preview` by itself: the application needs the local recognition service and the Vite API proxy. `start.ps1` starts the required pair.

## Use the studio

1. Upload a local MP4 or WebM obtained through authorized means. Choose a clearly visible signer and a single word from the supported vocabulary.
2. Play or seek the video. Mark a start and end around one complete sign.
3. Choose **Recognize Sign**, or analyze the whole clip when it contains one isolated sign.
4. Review the top suggestions. Confirm only a label you believe is correct, or reject an uncertain result.
5. Edit the transcript, add or remove words, undo, clear, copy, or download its text.
6. Use the play button beneath the transcript to hear a local Windows voice. Stop playback, adjust the speed, or download WAV audio.

The vocabulary and model panel come from the loaded local assets. Scores are model scores, not measured translation accuracy. A sequence of confirmed labels is a gloss transcript; the app does not automatically invent English grammar or translate ASL sentences.

YouTube clips must first be saved through an authorized method and uploaded locally. Kamayan does not download YouTube videos or use audio, captions, filenames, or overlay text to predict signs.

## Local model and rights

The verified local model is [GestureBridge's](https://github.com/yl6079/GestureBridge) WLASL-100 five-model ensemble, using pretrained NumPy inference and `(30, 63)` hand-landmark sequences. The actual model status shows loaded members, input shape, and CPU device; a single Conv1D model and the five-model ensemble are different configurations.

The upstream checkout is stored under `research/GestureBridge` for local evaluation. Setup pins commit `4eadbcd157f5c62208e2c49dc37cea01cf670177` when creating a new checkout. The application imports the upstream inference implementation from that location, preserving its preprocessing and label order.

**Do not redistribute the research checkout, pretrained weights, or downloaded signing videos with this application.** GestureBridge reuse permissions and WLASL restrictions require separate treatment. Read [third-party notes](docs/THIRD_PARTY.md) before a public submission or any commercial use. `.gitignore` excludes these local evaluation assets; that exclusion is not a grant of permission.

CPU inference avoids full PyTorch and TensorFlow installations. The Python dependencies are listed in `backend/requirements.txt`; frontend dependencies are recorded in `package-lock.json` after setup. Model files and the hand detector must already exist locally before offline inference can run.

## Offline use and verification

Once online setup has completed, this command checks the existing environment without installing or downloading anything:

```powershell
.\setup.ps1 -Offline -EvaluationSamples
```

Then start Kamayan and upload an already-local video. Recognition processes footage on this computer; speech uses `Windows SAPI / System.Speech` and installed desktop voices. Fonts, scripts, and icons are bundled or drawn locally. The app does not use hosted AI, cloud TTS, or runtime CDNs.

The complete browser workflow has been tested with external HTTP requests denied: a downloaded computer-sign MP4 plays, yields a genuine model prediction, adds a confirmed word to the right-side transcript, and plays locally synthesized speech. Focused speech checks verified advancing audio playback, stop, WAV download, and fresh synthesis after changing speed. Model loading and inference also passed with Python socket connections disabled. The laptop's Wi-Fi was not physically switched off for those recorded checks.

Observed checks: 19 backend tests and 6 subtests, 4 transcript tests, 9 browser workflow checks, 5 focused browser speech checks, and a successful production build. See [observed validation and limits](docs/VALIDATION.md), [browser workflow evidence](evidence/browser-verification.json), [speech browser evidence](evidence/speech-browser-verification.json), and the [demo script](DEMO.md). Correct computer recognition was demonstrated, but help and student clips also produced wrong high-scoring labels. These observations are functionality checks, not a measured accuracy benchmark.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Required weights or hand detector are missing | Run online setup again, or inspect the asset path printed in the error. Do not substitute unrelated weights. |
| A localhost port is in use | Open the existing Kamayan launch, or close the service using that port and rerun `start.ps1`. |
| Recognition service does not start | Inspect `.runtime/backend.stderr.log`, then run `test.ps1 -SkipFrontend`. |
| A clip is uncertain | Select a shorter complete supported sign, improve visibility, and review the top suggestions. A classifier always has a highest score; that does not make the word correct. |
| Speech is unavailable | Install or enable a Windows desktop SAPI voice. The app does not switch to a cloud voice. |
| Webcam permission is denied | Use the file-upload workflow, or enable camera access for localhost in the browser. |

See `docs/VALIDATION.md` for the current supported scope and observed failures.
