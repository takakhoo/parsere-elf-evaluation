# evaluations/url/

Ben,

Real run of your URI template against curl. Used your `URI_PARSE_TREE_TEMPLATE` as-is. This is the evaluation that taught me about static linking the hard way.

## Target

[curl](https://github.com/curl/curl), commit `462244447e8ba3a53b1ba9f0ba7baa52d8777daa`. Built from source with `--without-shared` and most optional features disabled, linked statically through `libcurl.a`.

Entry point: `curl_url_set(handle, CURLUPART_URL, input, 0)`.

## Headline numbers

| Metric | Value |
|--------|------:|
| Template instantiations | 1,458 |
| Pairwise comparisons | 2,125,764 |
| CFG nodes after cleanup | 522 |
| CFG edges | 558 |
| Labeled basic blocks | 211 (40.4% of graph) |
| Productions used | 11 (including "None") |

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

The duplicate-looking labels (`port` vs `:port`, `query` vs `?query`, etc.) come from your template's leaf naming. The colon/question/hash prefix indicates the delimiter character was included in the label. Template-design quirk; the underlying attribution works fine.

## The static linking lesson

First run produced zero labeled blocks. Confusing because the JSON eval had worked fine.

Spent maybe an hour comparing the two before I realized: the JSON harness linked against `libjson-c.a` (static `.a` produced by the cmake build), but the URL harness was using `-lcurl` against the system `libcurl.so`. Dynamic linking adds an enormous startup phase before `main()` runs: ld.so resolves every imported symbol, traverses the DT_NEEDED list, runs the .init array. All of that runs on every input regardless of what input it is.

ParseRE's useless-edges filter looks for edges that appear in every trace, on the reasonable assumption that edges that always fire aren't informative about which input feature is being processed. The dynamic linker code is exactly that. ParseRE wiped the entire graph.

Fix: rebuild curl from source with `--without-shared`, link the harness against the static archive. The dynamic linker startup is still there (we still rely on libc dynamically) but it's no longer in front of the parser code.

The Dockerfile bakes this in. The whole curl build is in there.

This lesson is in the paper now (Section IV-C). It's also why the ELF harness uses `-static` full static linking.

## TP/FP/FN status

Waiting on Rishav, same as JSON.

## Running

```bash
mkdir -p output
docker run --platform linux/amd64 --rm -v "$PWD/output:/output" parsere-runner url
```

About 8 minutes end-to-end on my M1 because of the 2.1M pairwise comparisons. Most of the time is the diff computation, not QEMU tracing.

Taka
