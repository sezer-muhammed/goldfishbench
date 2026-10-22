"""Verify every file bound by the public release manifest, without network access."""
import hashlib
import json
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / "release-manifest.json").read_text())
    for item in manifest["files"]:
        name = PurePosixPath(item["path"])
        if name.is_absolute() or ".." in name.parts:
            raise ValueError("Manifest path leaves the release directory")
        path = ROOT / name
        if not path.is_file() or path.stat().st_size != item["bytes"]:
            raise ValueError(f"Released file missing or changed: {name}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Released file checksum differs: {name}")
    print(json.dumps({"status": "PASS_RELEASE_CHECKSUMS", "files": len(manifest["files"]),
                      "version": manifest["version"], "new_model_calls": 0}))


if __name__ == "__main__":
    main()
