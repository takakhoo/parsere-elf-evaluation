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
**Static linking**: Fully static binary (`-static` flag) to avoid dynamic-linker trace pollution

---

## Results

| Metric | Value |
|--------|-------|
| Template instantiations | 20 |
| Pairwise comparisons | 380 |
| CFG nodes (after cleanup) | 358 |
| CFG edges | 354 |
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

| Format | Library | Instantiations | CFG Nodes | CFG Edges | Labeled BBs | % Labeled | Productions |
|--------|---------|---------------|-----------|-----------|-------------|-----------|-------------|
| URI | Curl | 1,458 | 522 | 558 | 211 | 40.4% | 11 |
| JSON | json-c | 27 | 464 | 400 | 294 | 63.4% | 6 |
| **ELF** | **libelf** | **20** | **358** | **354** | **68** | **19.0%** | **1** |

### Key Observations

1. **Binary formats have uniform record readers**: Unlike text formats where syntactically distinct productions (numbers, strings, arrays in JSON; host, port, path in URLs) trigger completely different parsing code, binary formats like ELF have uniform struct-reading operations. `gelf_getphdr()` always reads 56 bytes and unpacks them identically regardless of the phdr type field.

2. **Labels come from *consumer* code, not *reader* code**: The 68 section_header labels are mostly in `__libelf_set_rawdata_wrlock` and the harness's symbol-table iteration loop -- code that *processes* the parsed data conditionally, not code that *reads* the raw bytes. This highlights a fundamental difference between text and binary format parsing.

3. **Lower coverage expected for binary formats**: The 19.0% labeling rate vs 63.4% (JSON) and 40.4% (URL) reflects the structural simplicity of binary format parsing. Fixed-offset binary formats need much less conditional parsing logic than variable-length text formats.

4. **High ambiguity rate (74.8% None)**: Most of the reachable code in libelf is shared across all section types -- memory allocation (`__calloc`), data conversion, error checking. This shared code can't be attributed to any single production.

5. **The result validates ParseRE's design**: ParseRE correctly identifies that section_header handling is the only structurally-varying part of the ELF parsing code. The absence of program_header labels is not a failure -- it accurately reflects that libelf's phdr reading code is type-agnostic.

---

## Labeled Function Breakdown

From addr2line output in the dot file, the 68 section_header blocks map to these libelf functions:

- `__libelf_set_rawdata_wrlock` -- section data setup (majority of labels)
- `elf_begin.o` functions -- initial ELF structure parsing
- Harness code (`walk_section_headers`) -- conditional symtab/strtab iteration

---

## Reproduction

```bash
cd tools/docker-runner
docker build --platform linux/amd64 -t parsere-runner -f Dockerfile .
docker run --platform linux/amd64 --rm -v "$PWD/output:/output" parsere-runner elf
```

Output: `out.dot`, `out.svg`, `parsere.out` in the mounted `/output` directory.
