# Kamayan: 60–90 second demo

For the private evaluation demo, use `research/samples/12320.mp4`, the downloaded WLASL test clip whose independent reference label is computer. The genuine five-model result recorded for this clip is computer at a model score of 87.91%. Keep the reference separate from inference; let the current model output appear live. For a public demonstration or recording, use a rights-cleared self-recorded computer sign instead of redistributing the research clip. Before presenting, start Kamayan, verify the model-status panel, and check the local voice.

**0–12 seconds — the problem and product**

“This is Kamayan: Every Sign Connects. It recognizes an isolated American Sign Language word from video and lets someone build a transcript and hear it spoken. Processing stays on this laptop.”

**12–35 seconds — real recognition**

Upload the computer sample, preview the signer, and select the whole isolated-word clip. For a longer video, mark one complete sign.

“This clip contains one sign. The model panel shows the actual pretrained five-model ensemble running locally on the CPU.”

Click **Recognize Sign** and let the actual result appear.

“These are the model's top suggestions. Computer was correctly recognized in our recorded test. This score is a model score, not an accuracy guarantee, so I review before confirming.”

If the live result is wrong or uncertain, say: “I will reject this result and review the sign.” Never substitute a predetermined prediction.

**35–60 seconds — transcript and local speech**

Confirm an appropriate label, edit the transcript if useful, and click the play button below it.

“The confirmed word appears on the right. I can edit, undo, copy, or save the text. The play button beneath it uses an installed Windows voice, with adjustable speed and WAV download.”

**60–80 seconds — offline operation and limits**

Show the saved browser and model verification evidence if useful. The recorded tests denied external browser HTTP requests and Python socket connections; they did not physically switch off Wi-Fi.

“The complete workflow passed with external network requests blocked. It recognizes 100 supported isolated words, not complete ASL sentences. Help and student test clips also produced wrong suggestions, so human review matters.”

End on the transcript and the actual model-status panel. For a public demo, use your own authorized signing clip. The GestureBridge checkout and WLASL-related evaluation assets have unresolved or restricted redistribution rights; consult `docs/THIRD_PARTY.md` before packaging them.
