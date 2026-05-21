# references/

Ben,

Quick map of the related work and where each piece lives. The paper's actual citations are in `paper/references.bib`.

## The closest cousins

**Tenet** (Markus Gaasedelen, 2021): [github.com/gaasedelen/tenet](https://github.com/gaasedelen/tenet)

IDA Pro plugin that highlights basic blocks differing between two execution traces. Two-input differential analysis, no input-side labels. We position ParseRE as the N-to-many generalization with grammar attribution.

**Lighthouse** (Markus Gaasedelen, 2017): [github.com/gaasedelen/lighthouse](https://github.com/gaasedelen/lighthouse)

Coverage exploration in IDA. Same author, same niche, less differential. Cited in the same paragraph as Tenet.

## The "annotate the input" line

**PolyFile / PolyTracker** (Trail of Bits): [github.com/trailofbits/polyfile](https://github.com/trailofbits/polyfile), [github.com/trailofbits/polytracker](https://github.com/trailofbits/polytracker)

PolyFile parses a file and tells you which byte ranges are which structures. PolyTracker tracks data flow through a program at the LLVM IR level and produces a graph mapping input bytes to operations.

The methodological line we walk away from: PolyTracker needs LLVM instrumentation, which requires source code. ParseRE works on the binary alone, which is the actual reverse-engineering scenario.

## Grammar recovery (the inverse problem)

These tools answer "what does this binary eat?" given only the binary. ParseRE answers "given that this binary eats X, where is X handled?" The two problems are sequential rather than competing. The paper hammers this distinction in Section V-C.

- **Tupni** (Microsoft Research, CCS 2008): dynamic analysis to infer input formats
- **Polyglot** (CMU, CCS 2007): protocol message format inference
- **AUTOGRAM** (Höschele and Zeller, ASE 2016): grammar inference from observed input-output behavior, source-code dependent
- **Gopinath et al.** (2020): mining input grammars from dynamic control flow
- **Prospex** (2009): protocol state machine recovery from network traces

## Differential testing

- **HTTP Garden** (your other paper): the elephant in the room. Not citing for dual-blind reasons, but ready to add for camera-ready. [BEN: confirm policy]
- **T-Reqs** (Jabiyev et al., CCS 2021): differential testing of HTTP parsers
- **ParDiff** (Zheng et al., 2024): static differential analysis of protocol parsers. Complementary to ParseRE: ParDiff finds disagreement, ParseRE localizes it.

## Useful tool papers for style reference

- **angr SoK** (Shoshitaishvili et al., S&P 2016): the model for how to write a binary analysis tool paper. They name architectural modules but never name methods or filepaths.
- **KLEE** (Cadar et al., OSDI 2008): the canonical symbolic execution paper.
- **BAP** (Brumley et al., CAV 2011): binary analysis platform line.

For language hierarchy: **Chomsky 1956** (the original paper) is the citation we use in the intro.

## How ParseRE positions

From our May 19 conversation, your framing was:

> "It's crucial that reviewers not confuse these two related but not the same problems."

The two problems being grammar recovery (existing work) versus label transfer (ours). The related-work section in the paper has three subsections matching the three lines of prior work, and explicitly positions us against each.

Taka
