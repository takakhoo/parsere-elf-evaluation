# evaluations/json/

This directory contains a committed run of the upstream `JSON_PARSE_TREE_TEMPLATE` against json-c. The template is unchanged in this snapshot.

## Target

[json-c](https://github.com/json-c/json-c), commit `89485680314df3b4dfb2aaed14f89d212d57c119`. Built with cmake, linked statically through `libjson-c.a`.

Entry point: `json_tokener_parse(input)`.

## Headline numbers

| Metric | Value |
|--------|------:|
| Template instantiations | 27 |
| Ordered comparisons | 702 |
| CFG nodes after cleanup | 464 |
| CFG edges | 400 |
| Production-labeled basic blocks | 295 (63.6% of graph) |
| Productions used | 6 |

## Label distribution

| Production | Labeled BBs | % of labels |
|-----------|------------:|------------:|
| number    | 110 | 37.4% |
| object-element | 77 | 26.2% |
| string    | 39 | 13.3% |
| array     | 36 | 12.2% |
| boolean   | 24 | 8.2% |
| nan       | 9  | 3.1% |

`number` dominates because C-level numeric parsing is heavy: sign handling, decimal point, exponent, overflow checks, `strtod` wrappers. Each step is a separate basic block.

`nan` is tiny because it's a three-character string comparison.

## TP/FP/FN status

The committed `parsere.out` and `out.svg` files are raw outputs. A complete manual TP/FP/FN review is not present in this repository, so per-block accuracy remains unverified and is marked as a `TODO` in the paper draft.

## Running

```bash
mkdir -p output
docker run --platform linux/amd64 --rm -v "$PWD/output:/output" parsere-runner json
```

About 30 seconds end-to-end.
