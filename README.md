# icurses

Terminal-library source study.

## Source

[`libr_cons/`](libr_cons/) contains the complete, unmodified radare2 console
source directory: 65 tracked console files, plus public headers and upstream
license material (77 upstream files total). The snapshot is pinned to radare2
commit `596397d15faaa4decd7367a79e1b8f1a5cc28451`.

- [Provenance, layout, and build boundary](libr_cons/UPSTREAM.md)
- [Per-file source manifest and checksums](libr_cons/SOURCE_MANIFEST.json)
- [Reproducible importer](%5F/import_libr_cons.py)
- [Original investigation and discussion links](https://github.com/isomorphisms/icurses/issues/1)

The imported console subtree reproduces upstream Git tree
`391ee63d66cc398b51ca9182ee06c65a278dfb3d` exactly. This is source for inspection,
not a standalone build or a demonstrated ncurses replacement. Nothing has been
pruned or translated yet.
