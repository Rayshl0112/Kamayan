# **[Visit our website](https://kamayan-na.onrender.com/)**

# kamayan.

Every Sign Connects.

The current app is a lightweight **static sentence-caption demo**, following the user's change of plan. It displays the supplied sentence video's exact reference English on the right and an authored Filipino translation on the left. Both build into complete sentences as the video plays. **Play translated text** reads the full English sentence with an offline Windows voice.

No ASL model loads at startup or during playback. Webcam recording is a visible placeholder. These are prewritten, timed captions; this version does not automatically translate arbitrary signing videos.



## Start

The app is already configured on this machine. Run `start.ps1` and open [Kamayan](http://127.0.0.1:5173). Select **Try a sentence video**, or upload a copy of that exact sample. Play, pause, and seek to see the caption text change. The speech button is separate from the video's play button.

For setup on a new checkout:

```powershell
.\setup.ps1 -EvaluationSamples
.\start.ps1
```

Setup installs only the lightweight demo dependencies and obtains the licensed reference sample. It does not install or download an ASL model. Use `setup.ps1 -Offline` to check an existing environment without downloads.

## Verification

```powershell
.\test.ps1
```

The default test script verifies static captions and local speech without loading AI models. The recorded checks passed: 11 demo/speech tests, 6 subtests, five browser checks, and production build. Browser checks verify English/Filipino timing, right/left overlay placement, full-sentence local WAV playback, webcam placeholder behavior, and mobile layout. The demo backend used about 50 MB of process memory in the observed run.

See [current demo details](docs/CURRENT_DEMO.md) and `evidence/demo-verification.json`. Earlier AI experiments are preserved in [research notes](docs/AI_RESEARCH.md); they are inactive in the current app.

## Sample credit

The sentence video and English reference come from [Tarrés et al., CVPR WiCV 2023](https://imatge-upc.github.io/slt_how2sign_wicv2023/), using [How2Sign](https://how2sign.github.io/) research material under CC BY-NC 4.0. The bottom reference/model comparison was cropped out and audio removed. Original frame sequence and timing remain intact. Filipino text was authored for this app. See [third-party notes](docs/THIRD_PARTY.md) before publishing or commercial use.
