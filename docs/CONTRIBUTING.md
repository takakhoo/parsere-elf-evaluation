# Contributing notes

Ben, this is for if I bring in Rishav or anyone else mid-stream.

## What this repo is for

A working snapshot of the ParseRE paper while we finish the ACSAC 2026 submission. After submission this becomes a reproducibility artifact and eventually a PR back to `kenballus/parsere`.

## Branch policy

`main` only for now. If we end up doing parallel work close to deadline we can branch.

## Commit policy

Imperative mood, lowercase first word, no trailing period. Examples:

```
add ELF template byte literals to main.py
fix zero-division in uniquify step when rule has empty edge set
update Dockerfile to use python:3.13-bookworm base
```

**No co-author trailers in any commit, ever.** This is Taka's repo and Taka's commits.

## Where things go

| Adding | Folder |
|--------|--------|
| New evaluation | `evaluations/<format>/` with README, corpus or script, output |
| New harness | `harnesses/<format>_harness.c`, then update Dockerfile |
| Related work | `references/` or `paper/sections/related-work.tex` |
| Paper section | `paper/sections/<name>.tex`, then `\input` from `main.tex` |
| Images and screenshots | `images/`, reference from READMEs with relative paths |

## Don't commit

- Personal scratch directories
- Debug logs from QEMU
- Half-finished paper drafts that contradict the merged version
- Anything outside this repo
- Secrets (we have none)

## Build before pushing

If you edited `paper/`, build locally first to catch LaTeX errors:

```bash
cd paper
tectonic main.tex
```

If you don't have tectonic, drop the `paper/` folder into Overleaf and let it compile there.

Taka
