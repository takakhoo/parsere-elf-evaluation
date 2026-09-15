# references/

This document maps the closest related work to the corresponding framing in the paper draft. Bibliographic entries are maintained in `paper/references.bib`.

## The closest cousins

**Tenet** (Markus Gaasedelen, 2021): [github.com/gaasedelen/tenet](https://github.com/gaasedelen/tenet)

IDA Pro plugin that highlights basic blocks differing between two execution traces. Two-input differential analysis, no input-side labels. We position ParseRE as the N-to-many generalization with grammar attribution.

**Lighthouse** (Markus Gaasedelen, 2017): [github.com/gaasedelen/lighthouse](https://github.com/gaasedelen/lighthouse)

Coverage exploration in IDA. Same author, same niche, less differential. Cited in the same paragraph as Tenet.

## The "annotate the input" line

**PolyFile / PolyTracker** (Trail of Bits): [github.com/trailofbits/polyfile](https://github.com/trailofbits/polyfile), [github.com/trailofbits/polytracker](https://github.com/trailofbits/polytracker)

PolyFile parses a file and identifies the byte ranges associated with its structures. PolyTracker tracks data flow through a program at the LLVM IR level and produces a graph mapping input bytes to operations.

PolyTracker relies on LLVM instrumentation and offers richer byte-level data flow. ParseRE instead observes a runnable binary through QEMU, avoiding compiler instrumentation while providing coarser control-flow evidence.

## Grammar recovery (the inverse problem)

These tools answer "what does this binary eat?" given only the binary. ParseRE answers "given that this binary eats X, where is X handled?" The two problems are sequential rather than competing. The paper hammers this distinction in Section V-C.

- **Tupni** (Microsoft Research, CCS 2008): dynamic analysis to infer input formats
- **Polyglot** (CMU, CCS 2007): protocol message format inference
- **AUTOGRAM** (Höschele and Zeller, ASE 2016): grammar inference from observed input-output behavior, source-code dependent
- **Gopinath et al.** (2020): mining input grammars from dynamic control flow
- **Prospex** (2009): protocol state machine recovery from network traces

## Differential testing

- **HTTP Garden**: potentially relevant prior work on differential parser behavior. Evaluate whether it materially supports the final related-work argument before adding it.
- **T-Reqs** (Jabiyev et al., CCS 2021): differential testing of HTTP parsers
- **ParDiff** (Zheng et al., 2024): static differential analysis of protocol parsers. Complementary to ParseRE: ParDiff finds disagreement, ParseRE localizes it.

## Useful tool papers for style reference

- **angr SoK** (Shoshitaishvili et al., S&P 2016): the model for how to write a binary analysis tool paper. They name architectural modules but never name methods or filepaths.
- **KLEE** (Cadar et al., OSDI 2008): the canonical symbolic execution paper.
- **BAP** (Brumley et al., CAV 2011): binary analysis platform line.

For language hierarchy, the introduction cites **Chomsky 1956**.

## How ParseRE positions

The draft separates grammar recovery, which infers an accepted format, from label transfer, which maps a known input structure onto program locations. The related-work section organizes prior work around that distinction.
