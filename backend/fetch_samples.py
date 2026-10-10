"""Obtain private evaluation clips without redistributing or interpreting them.

Run only for an authorized academic/computational evaluation. These clips are
separate from the application's source, and this utility is never called by a
recognition request. It does not download from YouTube or process captions.
"""
from __future__ import annotations
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "research" / "samples"
INDEX = "https://raw.githubusercontent.com/dxli94/WLASL/master/start_kit/WLASL_v0.3.json"
IDS = {"17713", "12320", "27209", "69494"}
CONTROL_URL = "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4"


def download(url: str, destination: Path) -> None:
    if destination.exists():
        return
    if "youtube.com" in url.lower() or "youtu.be" in url.lower():
        raise ValueError("Only direct, authorized evaluation sources are accepted.")
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": url})
    with urlopen(request, timeout=30) as response:
        data = response.read(20 * 1024 * 1024 + 1)
    if not 8192 <= len(data) <= 20 * 1024 * 1024 or b"ftyp" not in data[:32]:
        raise ValueError("The source did not return a bounded MP4 file.")
    destination.write_bytes(data)


def main() -> int:
    SAMPLES.mkdir(parents=True, exist_ok=True)
    existing_manifest = SAMPLES / "manifest.json"
    if existing_manifest.exists():
        existing = json.loads(existing_manifest.read_text(encoding="utf-8"))
        if IDS <= {entry["id"] for entry in existing} and all((SAMPLES / entry["path"]).exists() for entry in existing):
            download(CONTROL_URL, SAMPLES / "no-sign.mp4")
            print("All four evaluation clips and the no-sign control are available locally.")
            return 0
    with urlopen(INDEX, timeout=30) as response:
        entries = json.load(response)
    manifest = []
    for entry in entries:
        for instance in entry["instances"]:
            clip_id = str(instance["video_id"])
            if clip_id not in IDS:
                continue
            if instance["split"] != "test" or not instance["url"].endswith(".mp4"):
                raise ValueError(f"Official metadata no longer identifies {clip_id} as a direct test clip.")
            destination = SAMPLES / f"{clip_id}.mp4"
            download(instance["url"], destination)
            manifest.append({"id": clip_id, "expected_gloss": entry["gloss"], "path": destination.name, "source_url": instance["url"], "source": instance["source"], "split": "test", "frame_start": instance["frame_start"], "frame_end": instance["frame_end"], "license": "WLASL C-UDA; private computational evaluation policy, no redistribution"})
            print(f"Fetched {clip_id}; independent reference {entry['gloss']}.")
    if len(manifest) != len(IDS):
        raise ValueError("The official metadata no longer contains every expected evaluation clip.")
    existing_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    download(CONTROL_URL, SAMPLES / "no-sign.mp4")
    print("Evaluation media remains private in research/samples; never publish it with the app.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
