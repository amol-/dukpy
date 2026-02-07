#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
from pathlib import Path
import shutil
import urllib.parse
import urllib.request
import zipfile

VERSION = "v0.11.0"
URL_TEMPLATE = "https://github.com/quickjs-ng/quickjs/releases/download/{version}/quickjs-amalgam.zip"


def main() -> None:
    parser = argparse.ArgumentParser(description="Update QuickJS-NG vendored sources.")
    parser.add_argument("--version", default=VERSION, help="QuickJS-NG release tag")
    parser.add_argument("--url", help="Explicit quickjs-amalgam.zip URL to download")
    args = parser.parse_args()

    version = args.version if args.version.startswith("v") else f"v{args.version}"
    url = args.url or URL_TEMPLATE.format(version=version)
    if args.url:
        parts = [part for part in urllib.parse.urlparse(url).path.split("/") if part]
        if len(parts) >= 2 and parts[-1] == "quickjs-amalgam.zip":
            version = parts[-2]
        else:
            parser.error("Unable to infer version from URL; pass --version.")

    quickjs_dir = Path(__file__).resolve().parents[1] / "src" / "quickjs"
    shutil.rmtree(quickjs_dir, ignore_errors=True)
    quickjs_dir.mkdir(parents=True)

    with (
        urllib.request.urlopen(url) as response,
        zipfile.ZipFile(io.BytesIO(response.read())) as archive,
    ):
        names = [name for name in archive.namelist() if name.endswith((".c", ".h"))]
        if not any(name.endswith(".c") for name in names):
            raise SystemExit("No .c files found in the amalgamated zip.")
        if not any(name.endswith(".h") for name in names):
            raise SystemExit("No .h files found in the amalgamated zip.")
        for name in names:
            (quickjs_dir / Path(name).name).write_bytes(archive.read(name))

    (quickjs_dir / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    print(
        f"Updated {quickjs_dir} with: {', '.join(sorted(Path(name).name for name in names))}"
    )
    print(f"Recorded version: {version}")


if __name__ == "__main__":
    main()
