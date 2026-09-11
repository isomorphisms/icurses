# libr_cons reading notes

Recorded 11 September 2026. Related: [icurses issue #1](https://github.com/isomorphisms/icurses/issues/1).

These are observations about the code already present in `libr_cons/`, with possible connections to icurses. They are not an import selection, a replacement design, or a decision to adopt radare2's console API.

## Which code this describes

The imported radare2 snapshot is commit `596397d15faaa4decd7367a79e1b8f1a5cc28451`, not the 2011 version mentioned in the suckless discussion. This reading used icurses commit `6aba1b8eb04347601c6601ce5d132e0c0ea37e0c`. Source links below are pinned to that icurses revision; [the import provenance](../libr_cons/UPSTREAM.md) explains the upstream layout and build boundary.

The inspected portions cover input, terminal state, output, canvas layout, palette definitions, the public header, and build metadata. This is a source reading, not a complete audit. Nothing was compiled or exercised on a terminal, phone, tablet, or Windows console.

## Waiting is more interesting than a read-character wrapper

In [`input.c`](https://github.com/isomorphisms/icurses/blob/6aba1b8eb04347601c6601ce5d132e0c0ea37e0c/libr_cons/input.c), `r_cons_readchar` first consumes any queued bytes in `InputState`. On the ordinary Unix path it then enables raw mode, waits with `pselect`, and reads one byte from `STDIN_FILENO`. The wait temporarily permits `SIGWINCH`; the adjacent comment explains the intended avoidance of a resize-signal race. A resize flag can lead to the `event_resize` callback.

`r_cons_readchar_timeout` has a separate Unix path: it calls `select` on descriptor 0, then calls `r_cons_readchar` when that descriptor is ready. It returns `-1` otherwise. This is not a structured distinction between timeout, interruption, and failure. Also, because this wrapper waits before delegating to the reader, queued input and readiness of the operating-system source deserve separate attention in any later experiment.

The Windows helper, `readchar_w32`, instead obtains a console `HANDLE`, optionally waits with `WaitForSingleObject`, and reads through `ReadFile` or `ReadConsoleInput`. It handles key, mouse, and window-size records rather than assuming every input event starts as a Unix byte stream.

**Possible relevance:** this is a concrete comparison of descriptor-based and handle/event-record-based input. The routines inspected do not accept an application's set of terminal, pipe, socket, and timer sources. They therefore provide material for thinking about the issue #1 waiting problem, not evidence that the problem is already solved here.

The surrounding `r_cons_sleep_begin` and `r_cons_sleep_end` hooks are also worth noticing. Their implementations in [`cons.c`](https://github.com/isomorphisms/icurses/blob/6aba1b8eb04347601c6601ce5d132e0c0ea37e0c/libr_cons/cons.c#L1711-L1724) invoke caller callbacks and critical-section machinery. These are hooks around blocking work, not an event-registration interface.

## Input decoding already contains interface policy

[`input.c`](https://github.com/isomorphisms/icurses/blob/6aba1b8eb04347601c6601ce5d132e0c0ea37e0c/libr_cons/input.c#L17-L300) contains mouse-protocol parsing, coordinate capture, drag state, and navigation-key conversion. `r_cons_mouse_wheel_key` turns wheel directions into `k`, `j`, `h`, and `l`. Drag handling can queue repeated navigation characters. `r_cons_arrow_to_hjkl` also maps arrows and several Emacs-style bindings into that vocabulary.

This is more than recognizing what the terminal sent: it also chooses what a particular interface should do with it. The parsing routines can themselves read further characters, so they are not already a separate incremental decoder that merely consumes supplied bytes.

**Possible relevance:** useful examples of terminal sequences and mouse behavior, while keeping a distinction between a key or pointer event and the application's decision to scroll, move, select, or quit. A future reader view need not inherit radare2's command characters just to understand the same input.

## Terminal ownership and temporary state

At the start of [`cons.c`](https://github.com/isomorphisms/icurses/blob/6aba1b8eb04347601c6601ce5d132e0c0ea37e0c/libr_cons/cons.c#L1-L85), `RConsTerminal` holds a console list, a foreground console, a lock, and platform terminal state. There is a shared `Gterminal`, plus machinery for identifying the current console. Explicit `RCons *` arguments therefore do not imply that every console owns an independent physical terminal.

[`r_cons_set_raw`](https://github.com/isomorphisms/icurses/blob/6aba1b8eb04347601c6601ce5d132e0c0ea37e0c/libr_cons/cons.c#L1450-L1500) selects stored terminal modes, applies them with `tcsetattr` or Windows-specific handling, and changes the foreground console under a lock. Nearby context code supports cloned output contexts, child consoles, and nested push/pop operations.

**Possible relevance:** the distinction between the physical terminal, a console using it, and a temporary output context. This makes ownership and restoration visible as separate concerns. The presence of these routines is not a guarantee that every error, signal, or nested interaction restores state correctly; that was not tested.

## Buffered output and screen presentation

[`r_cons_printf_list`](https://github.com/isomorphisms/icurses/blob/6aba1b8eb04347601c6601ce5d132e0c0ea37e0c/libr_cons/cons.c#L1500-L1605) appends formatted output to a context buffer. `r_cons_gotoxy` either emits a cursor-position escape sequence into that output or delegates to Windows handling.

In [`visual.c`](https://github.com/isomorphisms/icurses/blob/6aba1b8eb04347601c6601ce5d132e0c0ea37e0c/libr_cons/visual.c), `r_cons_visual_write` considers screen rows and columns, display width, wrapping or clipping, and clearing unused screen space. `r_cons_visual_flush` adds highlighting, chooses a platform output path, resets the buffer, and can display a frame-rate indicator. `r_cons_visual_readln` temporarily changes cursor/raw-mode state around line input.

**Possible relevance:** several distinct operations are visible here: accumulating output, fitting it to a viewport, emitting it, and temporarily switching interaction modes. For icurses or an IB view, these are useful boundaries to study without making viewport width, clipping, or highlighting part of the underlying document's meaning.

The color-capability helper in [`cons.c`](https://github.com/isomorphisms/icurses/blob/6aba1b8eb04347601c6601ce5d132e0c0ea37e0c/libr_cons/cons.c#L201-L240) uses `TERM`/`COLORTERM` heuristics; its comment explicitly distinguishes that approach from full terminfo/termcap detection. Its compactness should not be mistaken for proof of equivalent terminal coverage.

## The canvas separates bytes, columns, and styling—but not completely

[`canvas.c`](https://github.com/isomorphisms/icurses/blob/6aba1b8eb04347601c6601ce5d132e0c0ea37e0c/libr_cons/canvas.c#L1-L250) keeps per-row byte buffers, tracks their lengths and capacities, and stores styling positions in a hash table. Styling strings are interned in a string pool. The write path recognizes ANSI sequences separately from the text being placed and translates between byte lengths and display widths.

The local `rune_display_width` routine is a small range-based rule returning one or two columns. In that routine, a combining mark such as U+0301 falls through to one column; the routine also takes a single code point rather than a grapheme sequence. This is a direct observation of the helper, not a measured claim about every rendering path in radare2.

[`r_cons_canvas_new` and `r_cons_canvas_write`](https://github.com/isomorphisms/icurses/blob/6aba1b8eb04347601c6601ce5d132e0c0ea37e0c/libr_cons/canvas.c#L296-L430) also show that the canvas retains a console pointer and can enter console break-handling scopes. It is not merely a standalone rectangular array.

**Possible relevance:** a useful example for keeping byte offsets, text positions, screen columns, and attributes distinct. It also supplies concrete questions about clipping and character width. It should not be treated as a complete Unicode layout solution or an already-isolated renderer.

## The dependencies and vocabulary are visible in the source

[`meson.build`](https://github.com/isomorphisms/icurses/blob/6aba1b8eb04347601c6601ce5d132e0c0ea37e0c/libr_cons/meson.build) declares `r_util` as a dependency and uses parent-project build variables. Its source list includes line editing, a pager, filtering, canvas drawing, and even `2048.c`, alongside terminal handling. The directory is broader than a minimal screen/input layer.

[`include/r_cons.h`](https://github.com/isomorphisms/icurses/blob/6aba1b8eb04347601c6601ce5d132e0c0ea37e0c/libr_cons/include/r_cons.h#L1-L140) brings in radare2 types, thread support, numerous utility headers, and SDB headers. The inspected implementations use those facilities for locks, lists, stacks, string handling, attributes, and callbacks. A dependency in a header does not establish that every individual routine needs the whole dependency graph; that graph was not traced here.

[`pal.c`](https://github.com/isomorphisms/icurses/blob/6aba1b8eb04347601c6601ce5d132e0c0ea37e0c/libr_cons/pal.c#L1-L125) provides an especially clear example of application vocabulary inside the console layer: palette roles include `jmp`, `cjmp`, `call`, `reg`, `graph.traced`, and `var.addr`, alongside generic colors and widget roles.

**Possible relevance:** distinguish mechanisms such as color representation or attribute storage from radare2's meanings for those colors. These are concrete places to look more closely later, not a declaration that a file is either reusable or irretrievably coupled.

## License notices and the limits of this note

The inspected C-file headers identify LGPL licensing. The retained upstream [`COPYING.md`](../libr_cons/_/upstream/COPYING.md) describes most of radare2 as LGPLv3 and notes that dependencies and plugins can have other licenses. This is a record of the source notices, not a completed per-file licensing or redistribution assessment. The [import provenance](../libr_cons/UPSTREAM.md) also explains why the retained license collection should not be read as saying every included license applies to this library.

The useful result of this reading is a set of concrete examples: waiting on different kinds of input source, distinguishing events from key bindings, owning terminal state, buffering and presenting output, and handling text positions separately from terminal columns. No new source import, extraction, build integration, API commitment, ncurses-compatibility result, or platform acceptance follows from these observations.
