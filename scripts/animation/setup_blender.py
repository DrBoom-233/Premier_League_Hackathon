"""Download a checksum-pinned official Windows x64 portable Blender into .tools."""
import hashlib
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
NAME = "blender-4.5.9-windows-x64"
SHA256 = "41da973b9bf95bb312cbeff4d1982feb13259b43c821686b9bafea4dfe5477cf"


def main():
    tools = ROOT / ".tools"
    tools.mkdir(exist_ok=True)
    target = tools / NAME / "blender.exe"
    if target.exists():
        print(f"Already present: {target}")
        return
    archive = tools / f"{NAME}.zip"
    if not archive.exists():
        print("Downloading official Blender portable (~399 MB)...", flush=True)
        urllib.request.urlretrieve(f"https://download.blender.org/release/Blender4.5/{NAME}.zip", archive)
    with archive.open("rb") as source:
        actual = hashlib.file_digest(source, "sha256").hexdigest()
    if actual != SHA256:
        raise SystemExit("Blender archive checksum mismatch; remove the ZIP and retry.")
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.namelist():
            if not (tools / member).resolve().is_relative_to(tools.resolve()):
                raise SystemExit("Unsafe archive path")
        zipped.extractall(tools)
    print(f"Verified and extracted: {target}")


if __name__ == "__main__":
    main()
