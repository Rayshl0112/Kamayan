# Third-party attribution and distribution notes

Reviewed for this local evaluation on 10 October 2026. This file records the evidence and packaging decision; it does not grant rights to third-party materials.

## GestureBridge source and pretrained models

**Authors:** Yizheng Lin and Shufeng Chen. **Source:** [GestureBridge](https://github.com/yl6079/GestureBridge). **Inspected commit:** `4eadbcd157f5c62208e2c49dc37cea01cf670177`.

The inspected checkout has no top-level LICENSE file, and the GitHub repository metadata reports no recognized repository license. Its README cites training-data licenses but does not provide a general reuse or redistribution grant for its own source or pretrained weights. The local integration imports its inference modules from the separate research checkout; no upstream code or weights are included in the application's distributable source.

Treat GestureBridge source and weights as local evaluation materials only. Obtain the authors' explicit permission, or replace the implementation and models with assets carrying clear rights, before distributing them with a public or commercial application. A public repository is not itself an open-source license. [GitHub's licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) explains the distinction.

The verified local ensemble comprises Conv1D-Small, GRU-Small, and three BigConv1D weights with WLASL-100 labels. Model status exposes the actually loaded configuration. Attributions are retained even though research materials are excluded from packaging.

## WLASL and derived landmarks

**Citation:** Dongxu Li, Cristian Rodriguez, Xin Yu, and Hongdong Li. “Word-level Deep Sign Language Recognition from Video: A New Large-scale Dataset and Methods Comparison.” WACV 2020, pages 1459–1469.

The [official WLASL repository](https://github.com/dxli94/WLASL) identifies the dataset's [C-UDA agreement](https://github.com/dxli94/WLASL/blob/master/start_kit/C-UDA-1.0.pdf) and states that its data is for academic/computational use, with commercial usage prohibited. Raw clips and derived data must not be treated as generally unrestricted media.

The [C-UDA text](https://github.com/microsoft/Computational-Use-of-Data-Agreement/blob/master/C-UDA-1.0.md) distinguishes computational data from results and says that qualifying trained models can be results. This distinction does **not** supply a missing license from the GestureBridge model authors, nor does it override WLASL's posted conditions. No claim of unrestricted commercial model use is made.

GestureBridge's README attributes its pre-extracted landmark training set to [Kaggle: chinhde/wlasl-300-landmarks](https://www.kaggle.com/datasets/chinhde/wlasl-300-landmarks) and reports an MIT license for that derivative dataset. This statement has not been used as proof that original video rights or GestureBridge weight rights are unrestricted. The app uses pretrained inference weights, not a newly distributed landmark training set.

Local test-video provenance and reference labels belong in the model validation report. Do not distribute downloaded test clips. For a public demonstration, prefer a self-recorded signer with consent or an explicitly licensed authorized video. YouTube access does not confer a download or redistribution license.

## Runtime libraries

These independently developed packages provide the local web UI, API, landmark detector, and numerical runtime. Their installed packages retain their upstream license files. Keep the relevant notices with any distribution of those dependencies.

| Component | Attribution / source | License identified by upstream package |
| --- | --- | --- |
| React and React DOM | [Meta / React contributors](https://github.com/facebook/react) | MIT |
| Vite | [Vite contributors](https://github.com/vitejs/vite) | MIT |
| Lucide React icons | [Lucide contributors](https://github.com/lucide-icons/lucide) | ISC |
| NumPy | [NumPy developers](https://github.com/numpy/numpy) | BSD-3-Clause; bundled notices also apply |
| OpenCV | [OpenCV contributors](https://github.com/opencv/opencv) | Apache-2.0 for the current OpenCV core; bundled notices also apply |
| MediaPipe | [Google / MediaPipe contributors](https://github.com/google-ai-edge/mediapipe) | Apache-2.0; check task-model terms separately |
| FastAPI | [Sebastián Ramírez / FastAPI contributors](https://github.com/fastapi/fastapi) | MIT |
| Uvicorn | [Encode / Uvicorn contributors](https://github.com/encode/uvicorn) | BSD-3-Clause |
| Python multipart | [python-multipart contributors](https://github.com/Kludex/python-multipart) | Apache-2.0 |
| HTTPX | [Encode / HTTPX contributors](https://github.com/encode/httpx) | BSD-3-Clause |
| Pytest | [Pytest developers](https://github.com/pytest-dev/pytest) | MIT |
| Psutil | [Giampaolo Rodola / psutil contributors](https://github.com/giampaolo/psutil) | BSD-3-Clause |

The local `hand_landmarker.task` is obtained through the GestureBridge evaluation checkout. Its redistribution permission has not been independently cleared here; keep it out of an application bundle pending asset-specific verification.

Windows SAPI and desktop voices are installed operating-system components, used locally under their existing terms. No Windows voice files or Apple font files are redistributed. The UI requests system fonts already installed on the device.

## Packaging decision

The application code, startup scripts, and documentation are separate from `research/`, sample videos, model weights, detector assets, and generated speech recordings. `.gitignore` excludes research/model/video assets. This is a technical packaging measure, not a substitute for permission.

**Public model redistribution and commercial-use readiness remain unverified.** Do not present the local evaluation build as a cleared commercial distribution. Model authors' permission and the planned submission's applicable terms must be resolved before shipping the research assets.
