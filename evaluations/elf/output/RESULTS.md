# ELF Evaluation Results

**Date**: May 21, 2026
**Run by**: Taka (via Docker: `parsere-runner` image)
**Environment**: Docker `python:3.13-bookworm` on macOS ARM with `linux/amd64` emulation

---

## Setup

**Harness**: `elf_harness.c` -> reads ELF from stdin via libelf (`elf_memory`), walks ehdr, phdrs, shdrs, symtab
**Library**: libelf from elfutils (Debian bookworm `libelf-dev` package)
**Compilation**: `gcc -Wl,-z,now -no-pie -g -O0 -fno-inline -static` with `-lelf -lz`
**Template**: 3 children: elf_header (1 variant), program_header (4 variants), section_header (5 variants)
**Static linking**: Fully static binary (`-static` flag), keeping libelf code inside the executable address range retained by the current tracer

---

## Results

| Metric | Value |
|--------|-------|
| Template instantiations | 20 |
| Pairwise comparisons | 380 |
| Trace-derived graph nodes | 358 |
| Consecutive-record edges | 354 |
| **Labeled basic blocks** | **68** (19.0% of graph) |
| Ambiguous (None) blocks | 202 |
| Productions used | 1 (`section_header` only) |

### Label Distribution

| Production | BBs | % of labeled |
|-----------|-----|-------------|
| section_header | 68 | 100% |

### Why Only One Production?

**elf_header (0 labels)**: Only 1 variant in the template (the ELF header is identical across all 20 instantiations). With no variation, `difference()` never returns this production.

**program_header (0 labels)**: 4 variants exist (PT_LOAD+PT_NOTE, PT_LOAD+PT_INTERP, PT_LOAD+PT_DYNAMIC, PT_LOAD+PT_NULL), but libelf's `gelf_getphdr()` reads all program header types through the exact same code path. The `p_type` field is just an integer stored in the struct -- libelf doesn't dispatch to type-specific parsing code. So the QEMU traces for different phdr types are identical at the basic-block level, producing no differential edges.

**section_header (68 labels)**: 5 variants that change `sh_type` (SHT_SYMTAB vs SHT_NULL), `sh_size` (0 vs non-zero), and data content (populated vs zeroed symbol/string tables). These trigger genuinely different code paths:
- `shdr.sh_type == SHT_SYMTAB` branch in harness -> symbol table iteration
- `elf_getdata()` returns different data for populated vs empty sections  
- `elf_strptr()` behavior differs with real vs empty string tables
- `gelf_getsym()` loop runs different iteration counts

### Comparison with Other Evaluations

| Format | Library | Instantiations | Graph Nodes | Record-Pair Edges | Labeled BBs | % Labeled | Productions |
|--------|---------|---------------|-----------|-----------|-------------|-----------|-------------|
| URI | Curl | 1,458 | 522 | 558 | 191 | 36.6% | 10 |
| JSON | json-c | 27 | 464 | 400 | 295 | 63.6% | 6 |
| **ELF** | **libelf** | **20** | **358** | **354** | **68** | **19.0%** | **1** |

### Key Observations

1. **This ELF parser uses uniform record readers**: In this run, `gelf_getphdr()` reads and unpacks the same 56-byte record regardless of the program-header type field, unlike the production-specific branches exercised by the committed JSON and URI harnesses.

2. **Labels come from consumer code rather than reader code in this run**: The 68 `section_header` labels are mostly in `__libelf_set_rawdata_wrlock` and the harness's symbol-table iteration loop. This code processes the parsed data conditionally rather than merely reading raw bytes. More binary parsers must be evaluated before treating this as a format-wide distinction.

3. **Lower coverage in this binary-format case**: The 19.0% labeling rate is below the committed JSON (63.6%) and URI (36.6%) results. This supports a hypothesis that the fixed-layout ELF parser uses less production-specific branching than the two text parsers, but broader evaluation is needed before generalizing to binary formats as a class.

4. **High ambiguity rate (74.8% None)**: Most of the reachable code in libelf is shared across all section types -- memory allocation (`__calloc`), data conversion, error checking. This shared code can't be attributed to any single production.

5. **The result is consistent with the template and harness design**: The section-header variants exercise conditional handling, while the program-header type variants follow the same retained `gelf_getphdr()` path. The absence of `program_header` labels is therefore expected for this corpus and harness.

---

## Labeled Function Breakdown

From addr2line output in the dot file, the 68 section_header blocks map to these libelf functions:

- `__libelf_set_rawdata_wrlock` -- section data setup (majority of labels)
- `elf_begin.o` functions -- initial ELF structure parsing
- Harness code (`walk_section_headers`) -- conditional symtab/strtab iteration

---

## Reproduction

From the repository root:

```bash
docker build --platform linux/amd64 -t parsere-runner -f docker/Dockerfile .
mkdir -p reproduced/elf
docker run --platform linux/amd64 --rm \
  -v "$PWD/reproduced/elf:/output" \
  parsere-runner elf
```

Output: `out.dot`, `out.svg`, `parsere.out` in the mounted `/output` directory.
