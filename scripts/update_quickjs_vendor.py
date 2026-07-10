#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
import zipfile

VERSION = "v0.11.0"
URL_TEMPLATE = (
    "https://github.com/quickjs-ng/quickjs/releases/download/"
    "{version}/quickjs-amalgam.zip"
)
ARCHIVE_SHA256_BY_VERSION = {
    "v0.11.0": "c06c2122eed258444ad3d94470c6d645653b308e10002d3e43a774ba4d24953d",
}
VENDORING_METADATA = "VENDORING.json"
MANIFEST_QUICKJS_RULE = "recursive-include src/quickjs *.c *.h VERSION VENDORING.json"
MANIFEST_SCRIPT_RULE = "include scripts/update_quickjs_vendor.py"
MANIFEST_PATCH_RULE = "recursive-include scripts/quickjs_patches *.patch"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Update QuickJS-NG vendored sources.")
    parser.add_argument(
        "--version",
        help=f"QuickJS-NG release tag; defaults to {VERSION} without --url",
    )
    parser.add_argument("--url", help="Explicit quickjs-amalgam.zip URL to download")
    parser.add_argument("--sha256", help="Expected SHA256 of quickjs-amalgam.zip")
    args = parser.parse_args(argv)

    version = _normalized_version(args.version or VERSION)
    url = args.url or URL_TEMPLATE.format(version=version)
    if args.url:
        inferred_version = _version_from_release_url(url)
        if inferred_version:
            version = inferred_version
        elif args.version:
            version = _normalized_version(args.version)
        else:
            parser.error("Unable to infer version from URL; pass --version.")

    expected_sha256 = args.sha256 or ARCHIVE_SHA256_BY_VERSION.get(version)
    if not expected_sha256:
        parser.error(f"No recorded SHA256 for {version}; pass --sha256.")

    repo_root = Path(__file__).resolve().parents[1]
    names, archive_sha256 = update_vendor(repo_root, version, url, expected_sha256)
    print(
        "Updated {0} with: {1}".format(repo_root / "src" / "quickjs", ", ".join(names))
    )
    print(f"Recorded version: {version}")
    print(f"Verified archive sha256: {archive_sha256}")


def update_vendor(
    repo_root: Path, version: str, url: str, expected_sha256: str
) -> tuple[list[str], str]:
    repo_root = Path(repo_root)
    archive_bytes = _download(url)
    archive_sha256 = hashlib.sha256(archive_bytes).hexdigest()
    if archive_sha256.lower() != expected_sha256.lower():
        raise SystemExit(
            "Archive SHA256 mismatch for {0}: expected {1}, got {2}".format(
                url, expected_sha256, archive_sha256
            )
        )

    quickjs_dir = repo_root / "src" / "quickjs"
    quickjs_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".quickjs-staging-", dir=quickjs_dir.parent
    ) as staging_parent:
        staging_quickjs_dir = Path(staging_parent) / "quickjs"
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            names = _extract_amalgam(archive, staging_quickjs_dir)

        patches = _apply_local_patches(repo_root, staging_quickjs_dir)
        (staging_quickjs_dir / "VERSION").write_text(f"{version}\n", encoding="utf-8")
        (staging_quickjs_dir / VENDORING_METADATA).write_text(
            json.dumps(
                {
                    "archive_sha256": archive_sha256,
                    "files": names,
                    "patches": patches,
                    "upstream": {
                        "name": "quickjs-ng",
                        "url": url,
                        "version": version,
                    },
                    "workflow": "scripts/update_quickjs_vendor.py",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        _replace_quickjs_dir(quickjs_dir, staging_quickjs_dir)

    _update_manifest(repo_root, include_patch_rule=bool(patches))
    return names, archive_sha256


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url) as response:
        return response.read()


def _normalized_version(version: str) -> str:
    return version if version.startswith("v") else f"v{version}"


def _version_from_release_url(url: str) -> str | None:
    parts = [part for part in urllib.parse.urlparse(url).path.split("/") if part]
    if len(parts) >= 2 and parts[-1] == "quickjs-amalgam.zip":
        return parts[-2]
    return None


def _extract_amalgam(archive: zipfile.ZipFile, quickjs_dir: Path) -> list[str]:
    members: dict[str, str] = {}
    for name in archive.namelist():
        path = Path(name)
        if path.name and path.suffix in {".c", ".h"}:
            if path.name in members:
                raise SystemExit(f"Duplicate vendored filename in archive: {path.name}")
            members[path.name] = name

    names = sorted(members)
    if not any(name.endswith(".c") for name in names):
        raise SystemExit("No .c files found in the amalgamated zip.")
    if not any(name.endswith(".h") for name in names):
        raise SystemExit("No .h files found in the amalgamated zip.")

    quickjs_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        (quickjs_dir / name).write_bytes(archive.read(members[name]))
    return names


def _replace_quickjs_dir(quickjs_dir: Path, replacement_dir: Path) -> None:
    backup_dir = None
    if quickjs_dir.exists():
        backup_dir = Path(
            tempfile.mkdtemp(prefix=".quickjs-backup-", dir=quickjs_dir.parent)
        )
        shutil.rmtree(backup_dir)
        quickjs_dir.rename(backup_dir)

    try:
        replacement_dir.rename(quickjs_dir)
    except Exception:
        if quickjs_dir.exists():
            shutil.rmtree(quickjs_dir)
        if backup_dir and backup_dir.exists():
            backup_dir.rename(quickjs_dir)
        raise

    if backup_dir and backup_dir.exists():
        shutil.rmtree(backup_dir)


def _apply_local_patches(repo_root: Path, quickjs_dir: Path) -> list[dict[str, str]]:
    patches_dir = repo_root / "scripts" / "quickjs_patches"
    if not patches_dir.exists():
        return []

    patches = []
    for patch_path in sorted(patches_dir.glob("*.patch")):
        subprocess.run(["git", "apply", str(patch_path)], cwd=quickjs_dir, check=True)
        patches.append(
            {
                "path": patch_path.relative_to(repo_root).as_posix(),
                "sha256": hashlib.sha256(patch_path.read_bytes()).hexdigest(),
            }
        )
    return patches


def _update_manifest(repo_root: Path, include_patch_rule: bool) -> None:
    manifest = repo_root / "MANIFEST.in"
    if not manifest.exists():
        return

    lines = manifest.read_text(encoding="utf-8").splitlines()
    updated_lines = []
    quickjs_rule_added = False
    for line in lines:
        if line.startswith("recursive-include src/quickjs "):
            if not quickjs_rule_added:
                updated_lines.append(MANIFEST_QUICKJS_RULE)
                quickjs_rule_added = True
        else:
            updated_lines.append(line)

    if not quickjs_rule_added:
        updated_lines.append(MANIFEST_QUICKJS_RULE)
    if MANIFEST_SCRIPT_RULE not in updated_lines:
        updated_lines.append(MANIFEST_SCRIPT_RULE)
    if include_patch_rule and MANIFEST_PATCH_RULE not in updated_lines:
        updated_lines.append(MANIFEST_PATCH_RULE)

    new_content = "\n".join(updated_lines) + "\n"
    if manifest.read_text(encoding="utf-8") != new_content:
        manifest.write_text(new_content, encoding="utf-8")


if __name__ == "__main__":
    main()
