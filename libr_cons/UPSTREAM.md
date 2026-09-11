# libr_cons: upstream source snapshot

This is an unmodified source import for reading and comparison, not a standalone
ncurses replacement and not a build or runtime acceptance result.

## Provenance

- Upstream: https://github.com/radareorg/radare2
- Exact commit: `596397d15faaa4decd7367a79e1b8f1a5cc28451`
- Console tree: `391ee63d66cc398b51ca9182ee06c65a278dfb3d`
- Source: https://github.com/radareorg/radare2/tree/596397d15faaa4decd7367a79e1b8f1a5cc28451/libr/cons
- Historical lead: [pancake's 26 May 2011 message](https://lists.suckless.org/dev/1105/8111.html)
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

There are **65 console-subtree files** and **77 upstream
files in total**, occupying **615660 bytes**. `SOURCE_MANIFEST.json`
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
