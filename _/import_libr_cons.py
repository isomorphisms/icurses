#!/usr/bin/env python3
"""Copy a pinned radare2 console source snapshot; never build upstream code."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tempfile

UPSTREAM = "https://github.com/radareorg/radare2.git"
COMMIT = "596397d15faaa4decd7367a79e1b8f1a5cc28451"
DISCUSSION = "https://lists.suckless.org/dev/1105/8111.html"


def git(repository: Path, *arguments: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repository), *arguments])


def destination_path(source: str) -> str | None:
    if source.startswith("libr/cons/"):
        return source.removeprefix("libr/cons/")
    if source in {"libr/include/r_cons.h", "libr/include/r_line.h"} or source.startswith("libr/include/r_cons/"):
        return "include/" + source.removeprefix("libr/include/")
    if source in {"COPYING.md", "doc/licenses.md"} or source.startswith("doc/licenses/"):
        return "_/upstream/" + source
    return None


def import_source(repository: Path, commit: str, destination: Path) -> dict:
    if destination.exists() or destination.is_symlink():
        raise RuntimeError(f"Refusing to replace existing source: {destination}")
    records = []
    seen = set()
    reserved = {"UPSTREAM.md", "SOURCE_MANIFEST.json"}
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Stage the entire copy before publishing the directory.
    with tempfile.TemporaryDirectory(prefix=".libr-cons-", dir=destination.parent) as temporary:
        stage = Path(temporary) / "source"
        stage.mkdir()
        for entry in git(repository, "ls-tree", "-r", "-z", commit).split(b"\0"):
            if not entry:
                continue
            metadata, raw_path = entry.split(b"\t", 1)
            mode, kind, blob = metadata.decode("ascii").split()
            source = raw_path.decode("utf-8")
            relative = destination_path(source)
            if relative is None:
                continue
            path = PurePosixPath(relative)
            if path.is_absolute() or ".." in path.parts or relative in reserved or relative in seen:
                raise RuntimeError(f"Unsafe or colliding destination: {relative}")
            # Do not silently omit links, submodules, or unknown file kinds.
            if kind != "blob" or mode not in {"100644", "100755"}:
                raise RuntimeError(f"Unsupported upstream file type: {source} ({mode} {kind})")
            content = git(repository, "cat-file", "blob", blob)
            actual_blob = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
            if actual_blob != blob:
                raise RuntimeError(f"Upstream blob verification failed: {source}")
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            target.chmod(0o755 if mode == "100755" else 0o644)
            if target.read_bytes() != content:
                raise RuntimeError(f"Copied bytes differ: {relative}")
            seen.add(relative)
            records.append({"path": relative, "upstream_path": source, "mode": mode,
                            "git_blob_sha1": blob, "sha256": hashlib.sha256(content).hexdigest(),
                            "bytes": len(content)})
        required = {"cons.c", "input.c", "include/r_cons.h", "_/upstream/COPYING.md"}
        if not required <= seen:
            raise RuntimeError(f"Required files missing: {sorted(required - seen)}")
        console = [item for item in records if item["upstream_path"].startswith("libr/cons/")]
        manifest = {"upstream": UPSTREAM, "commit": commit,
                    "console_tree": git(repository, "rev-parse", f"{commit}:libr/cons").decode().strip(),
                    "console_files": len(console), "imported_files": len(records),
                    "imported_bytes": sum(item["bytes"] for item in records),
                    "files": sorted(records, key=lambda item: item["path"])}
        (stage / "SOURCE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        documentation = f"""# libr_cons: upstream source snapshot

This is an unmodified source import for reading and comparison, not a standalone
ncurses replacement and not a build or runtime acceptance result.

## Provenance

- Upstream: https://github.com/radareorg/radare2
- Exact commit: `{commit}`
- Console tree: `{manifest['console_tree']}`
- Source: https://github.com/radareorg/radare2/tree/{commit}/libr/cons
- Historical lead: [pancake's 26 May 2011 message]({DISCUSSION})
- Tracking: https://github.com/isomorphisms/icurses/issues/1

This is the snapshot selected for the September 2026 import, **not** the 2011
version discussed in that message. No code has been pruned or rewritten.

## What is here

The complete tracked `libr/cons/` subtree is copied directly into this directory,
including C sources, internal headers, themes/data, scripts, and build files.
Console public headers from `libr/include/` are under `include/`. Upstream's
`COPYING.md`, `doc/licenses.md`, and `doc/licenses/` are retained under
`_/upstream/`; individual source-file copyright and license notices are intact.
The accompanying license collection is contextual, not a claim that every license
in it applies to this library. Consult each source file before reusing it.

There are **{len(console)} console-subtree files** and **{len(records)} upstream
files in total**, occupying **{manifest['imported_bytes']} bytes**. `SOURCE_MANIFEST.json`
records every imported path, original path, executable mode, Git blob ID, and
SHA-256 checksum. Only this document and the manifest are locally generated.

## Build boundary

The upstream Meson definition links this library against `r_util`; the public
header also refers to radare2 support headers and SDB. Those dependencies and the
parent build configuration have not been imported wholesale. The retained build
files therefore still describe a component of radare2, not an independent build
inside icurses. To build unchanged code, use the full radare2 tree at the pinned
commit. No source build or terminal interaction test was run for this import.
No phone, tablet, Linux, Windows, or other platform acceptance is claimed.

## Reproduce and verify

From the repository root, `python3 _/import_libr_cons.py` reproduces the import
only when `libr_cons/` does not already exist. It fetches the exact commit without
its history, selects all tracked console files without extension filtering, and
verifies their bytes against Git blob IDs. It refuses to overwrite existing work.
It never executes upstream scripts or compiles imported C code.

For a local checksum check, from this directory run:

```sh
python3 - <<'PYTHON'
import hashlib, json
from pathlib import Path
manifest = json.loads(Path('SOURCE_MANIFEST.json').read_text())
for item in manifest['files']:
    path = Path(item['path'])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], path
    assert bool(path.stat().st_mode & 0o111) == (item['mode'] == '100755'), path
print('Verified', len(manifest['files']), 'upstream files')
PYTHON
```

Import integrity is separate from compilation and platform acceptance.
"""
        (stage / "UPSTREAM.md").write_text(documentation, encoding="utf-8")
        # os.rename fails rather than replacing a populated destination directory.
        if destination.exists() or destination.is_symlink():
            raise RuntimeError("Destination appeared while importing; refusing replacement")
        os.rename(stage, destination)
    return manifest


def main() -> None:
    destination = Path(__file__).resolve().parents[1] / "libr_cons"
    if destination.exists() or destination.is_symlink():
        raise SystemExit("libr_cons already exists; refusing to overwrite it")
    with tempfile.TemporaryDirectory(prefix="radare2-source-") as temporary:
        repository = Path(temporary)
        git(repository, "init", "--quiet")
        git(repository, "fetch", "--quiet", "--depth=1", UPSTREAM, COMMIT)
        if git(repository, "rev-parse", "FETCH_HEAD").decode().strip() != COMMIT:
            raise RuntimeError("Fetched commit does not match the pin")
        manifest = import_source(repository, COMMIT, destination)
    print(json.dumps({key: value for key, value in manifest.items() if key != "files"}, indent=2))


if __name__ == "__main__":
    main()
