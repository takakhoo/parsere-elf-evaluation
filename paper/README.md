# paper/

Ben,

This is the ACSAC submission. Drop the whole folder into Overleaf and set `main.tex` as the root.

```
paper/
├── main.tex          top-level, \input{}s every section
├── IEEEtran.cls      IEEE conference class (don't touch)
├── references.bib    bibliography, 14 entries, all real
├── figures/          TikZ source for the four new figures + their compiled PDFs
└── sections/
    ├── introduction.tex
    ├── background.tex
    ├── design.tex
    ├── implementation.tex
    ├── evaluation.tex
    ├── related-work.tex
    └── future-work.tex
```

## Compiling locally

I use tectonic because it pulls packages on demand and avoids the full TeX Live install:

```bash
brew install tectonic
cd paper
tectonic main.tex
# main.pdf shows up next to main.tex
```

If you prefer the traditional toolchain:

```bash
cd paper
latexmk -pdf main.tex
```

## Where you (and Rishav) need to fill in

I marked every open question with an italic inline tag. Grep for them:

```bash
grep -rn '\\textit{\[BEN:\|\\textit{\[RISHAV:' sections/
```

As of this commit:
- 4 `[BEN:]` markers (HPACK results, QEMU version pinning, public repo URL, HTTP Garden citation policy)
- 2 `[RISHAV:]` markers (URI per-block TP/FP/FN, JSON per-block TP/FP/FN)

When you fill one in, just delete the `\textit{[...]}` wrapper and put the real content.

## New figures (vs. the prior draft)

Four PDFs in `figures/`:

1. **`motivating.pdf`**. Two URIs that differ only in their path subtree, used in the intro (Figure 1). Shows the idea visually before the formal design section.
2. **`pipeline.pdf`**. Replaces the broken TikZ figure where one arrow went into an ellipse. Linear two-row layout, color-coded by data vs operation vs output.
3. **`elf-layout.pdf`**. The 1048-byte ELF corpus layout with the three template children annotated. Goes in Section IV-E next to the ELF discussion.
4. **`elf-cfg-fragment.pdf`**. 12 of the 68 labeled `section_header` blocks, with real addresses from `out.dot`. Shows how the labels group by function (harness vs libelf internals).

All four are hand-tuned TikZ. If you want to regenerate them:

```bash
cd paper/figures
tectonic motivating.tex pipeline.tex elf-layout.tex elf-cfg-fragment.tex
```

## Style rules I'm following

- IEEE conference, `compsoc` option (ACSAC requires this).
- Anonymous author block for dual-blind. Real names come at camera-ready.
- 11-page body cap. Current draft is 8 pages, room to grow.
- Ethics section and LLM Usage Statement included (ACSAC mandatory).
- No em-dashes. Searched and confirmed clean.
- No "X is Y, not Z" structures. Same.

Taka
