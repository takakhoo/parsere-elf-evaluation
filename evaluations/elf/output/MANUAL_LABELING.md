# ELF Manual Label Verification

**Evaluator**: Taka Khoo
**Date**: May 21, 2026
**Total labeled blocks**: 68 (all `section_header`)

## Function-level breakdown

| Function | BBs | Assessment | Notes |
|----------|-----|------------|-------|
| `__libelf_set_rawdata_wrlock` | 26 | **TP** | Sets up raw data for sections. Different section types (SHT_SYMTAB vs SHT_NULL vs SHT_STRTAB) have different data sizes and properties, which triggers different code paths in this function. |
| `elf_getdata` | 11 | **TP** | Retrieves section data. Sections with data (symtab, strtab, text) versus empty or null sections take different paths through data retrieval. |
| `walk_section_headers` (harness) | 9 | **TP** | The harness's conditional logic: `if (shdr.sh_type == SHT_SYMTAB)` branch, the `gelf_getsym` iteration loop, and `elf_strptr` name lookups. Directly implements section-type-conditional processing. |
| `__libelf_set_data_list_rdlock` | 7 | **TP** | Sets up the data list for a section. Varies based on whether the section has actual data content. Called during section traversal. |
| `gelf_getsym` | 5 | **TP** | Symbol table entry reader. Only runs for SHT_SYMTAB sections. Clearly section_header-dependent: it literally reads symbol entries from symtab sections. |
| `__gelf_getehdr_rdlock` | 5 | **FP** | ELF header reader. This function reads the ELF header rather than section headers. It appears here because it is called during section iteration as part of libelf's internal validation (checking ehdr before accessing shdrs). The label "section_header" is technically incorrect; this code processes the ELF header. |
| `elf_strptr` | 3 | **TP** | String table pointer resolution. Only exercised when sections have valid string data. Correctly attributed to section processing. |
| `elf_nextscn` | 1 | **TP** | Section iterator. While it runs for all section types, the specific blocks labeled here are in the section-count-dependent path. |
| `__libelf_seterrno` | 1 | **Marginal TP** | Error number setter. Called when section processing encounters specific conditions. The correlation with section_header is incidental but the label is not wrong. |

## Summary

| Category | Count | % |
|----------|-------|---|
| True Positive | 62 | 91.2% |
| False Positive | 5 | 7.4% |
| Marginal TP | 1 | 1.5% |
| **Total** | **68** | **100%** |

**Accuracy**: 91.2% (62/68) strict; 92.6% (63/68) if marginal TPs are counted.

## False Positive Analysis

The 5 FP blocks all sit in `__gelf_getehdr_rdlock`. This function reads the ELF header, but it is called internally by libelf as a validation step during section traversal: `elf_nextscn` and `gelf_getshdr` re-validate the ELF header before accessing section data. The trace difference arises because some section configurations cause this validation to take different branches (for example, checking `e_shnum` against the actual number of populated sections).

This is a reasonable FP. The code *is* reached through section processing, but it *implements* ELF header validation rather than section header parsing. An analyst using ParseRE would benefit from knowing this is section-related code, even though the precise label is wrong.

## False Negatives

Assessing FN requires checking unlabeled blocks that should have been labeled. Key unlabeled functions in the graph:

- `gelf_getphdr` and `elf64_getphdr`: correctly unlabeled (phdr reading is uniform across types)
- `elf_begin` and `file_read_elf`: correctly unlabeled (runs identically for all inputs)
- `__calloc` and `_int_free`: correctly unlabeled (memory management, shared)

No obvious false negatives identified. The unlabeled blocks are genuinely shared code.

**FN count: 0** (no missed section-handling blocks that should have been labeled)
