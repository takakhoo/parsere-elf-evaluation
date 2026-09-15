# evaluations/url/

This directory contains a committed run of the upstream `URI_PARSE_TREE_TEMPLATE` against curl. The template is unchanged in this snapshot.

## Target

[curl](https://github.com/curl/curl), commit `462244447e8ba3a53b1ba9f0ba7baa52d8777daa`. Built from source with `--without-shared` and most optional features disabled, linked statically through `libcurl.a`.

Entry point: `curl_url_set(handle, CURLUPART_URL, input, 0)`.

## Headline numbers

| Metric | Value |
|--------|------:|
| Template instantiations | 1,458 |
| Ordered comparisons | 2,124,306 |
| CFG nodes after cleanup | 522 |
| CFG edges | 558 |
| Production-labeled basic blocks | 191 (36.6% of graph) |
| Ambiguous (`None`) blocks | 21 |
| Output entries | 212 |
| Labels used | 10 productions + `None` |

## Label distribution

| Production | Labeled BBs | % |
|-----------|------------:|---:|
| host | 91 | 43.1% |
| port | 31 | 14.7% |
| segment | 30 | 14.2% |
| userinfo@ | 25 | 11.8% |
| None (ambiguous) | 21 | 10.0% |
| ?query | 3 | 1.4% |
| :port | 3 | 1.4% |
| #fragment | 3 | 1.4% |
| query | 2 | 0.9% |
| fragment | 2 | 0.9% |
| path-abempty | 1 | 0.5% |

`host` dominates because curl's URL parser does extensive host validation: IPv4 vs IPv6, IDNA, bracket handling, length checks.

The duplicate-looking labels (`port` vs `:port`, `query` vs `?query`, etc.) come from the template's leaf naming. The colon/question/hash prefix indicates that the delimiter character is included in the label. These labels should remain separate unless the evaluation protocol explicitly defines a merge.

## The static linking lesson

The first URL run produced no parser labels because the harness used the system `libcurl.so`. The current tracer retains only translation blocks whose addresses fall inside the target executable's single executable `PT_LOAD` segment. Curl's parser code therefore lived outside the retained range and was discarded.

The fix was to rebuild curl with `--without-shared` and link its static archive into the harness. This places curl's parser code inside the target executable segment. The harness can still depend dynamically on system libraries; the important constraint is that the parser code under analysis must fall inside the address range retained by the tracer.

The Dockerfile bakes this in. The whole curl build is in there.

This lesson is in the paper now (Section IV-C). It's also why the ELF harness uses `-static` full static linking.

## TP/FP/FN status

The committed files contain 191 production-labeled blocks and 21 ambiguous blocks. A complete manual TP/FP/FN review is not present, so accuracy remains unverified.

## Running

```bash
mkdir -p output
docker run --platform linux/amd64 --rm -v "$PWD/output:/output" parsere-runner url
```

The committed Apple Silicon run took roughly eight minutes because of the 2,124,306 ordered comparisons. Most of the time was spent computing differences rather than invoking QEMU.
