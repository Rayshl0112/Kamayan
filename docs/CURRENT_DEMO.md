# Current static sentence demo

The current app follows the user's change of plan: uploaded sample video, static reference English, static authored Filipino, floating captions, and offline playback of the complete English sentence. Webcam recording is a placeholder. No ASL model loads at app startup or during caption playback.

The English sentence is the exact reference displayed in the original researchers' example:

> And that's a great vital point technique for women's self defense.

The authored Filipino translation is:

> At iyan ay isang mahusay na teknik na nakatuon sa sensitibong bahagi ng katawan para sa pagtatanggol sa sarili ng kababaihan.

Caption timings are manually authored, and the text builds cumulatively. They are not estimated sign boundaries or live AI translation. The play button speaks the complete English reference sentence, including when playback is near the beginning.

Source: [Tarrés et al., CVPR WiCV 2023](https://imatge-upc.github.io/slt_how2sign_wicv2023/), using [How2Sign](https://how2sign.github.io/). How2Sign research material is CC BY-NC 4.0. The bottom 140 pixels were cropped to remove the publication's burned-in reference/model comparisons. Original frame sequence and timing are preserved; audio is removed. Filipino text was authored for this app, not supplied by the dataset authors.

Observed verification: 11 demo/speech tests and 6 subtests passed. Five browser checks passed with outside network requests blocked: minimal upload page, webcam placeholder, caption timing/seeking, English right/Filipino left, complete-sentence local WAV playback, and responsive layout. Production build passed. Backend process memory was approximately 50 MB in this recorded run. AI jobs had stopped, and no GPU compute process was reported.

Run `start.ps1` to open the local studio. Run `test.ps1` for the lightweight demo checks; it does not load the former ASL research models. Earlier AI evidence in the repository records experiments, not the current app behavior.
