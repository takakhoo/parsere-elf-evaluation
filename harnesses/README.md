# Target Harnesses

Three C harnesses, one per format. Each one reads bytes from stdin, hands them to the parser library under test, and exits 0 on success or 1 on parse failure.

## Files

| Harness | Lines | Library | Entry point |
|---------|-------|---------|------------|
| `json_c_harness.c` | ~25 | json-c | `json_tokener_parse(input)` |
| `curl_url_harness.c` | ~30 | libcurl | `curl_url_set(handle, CURLUPART_URL, input, ...)` |
| `elf_harness.c` | ~108 | libelf | `elf_memory(buf, total)` + walk phdrs, shdrs, symtab |

The ELF harness is longer than the other two because libelf is structured as many small calls (one per phdr, one per shdr, one per symtab entry) rather than a single top-level `parse()` entry point.

## Why these specific signatures

ParseRE attributes labels to the basic blocks that *change* between inputs that differ in exactly one grammar production. The harness has to actually execute the production-specific code paths for that attribution to work. So:

- The JSON harness has to traverse the parsed tree well enough that integer parsing, string parsing, etc. are reached.
- The URL harness has to fully validate the URL (curl does this in `curl_url_set` itself).
- The ELF harness has to walk *every* structure mentioned by the grammar template: program headers, section headers, the symbol table. Without the per-structure walks, the labeled differences collapse onto the top-level `elf_begin` call and we get one block labeled and nothing else.

In the ELF case, the symtab iteration loop in `walk_section_headers()` is critical. The `if (shdr.sh_type == SHT_SYMTAB || shdr.sh_type == SHT_DYNSYM)` branch is what makes the section_header label produce 68 distinct blocks rather than a handful.

## Compilation

All three are compiled inside the Docker image using:

```
gcc -Wl,-z,now -no-pie -g -O0 -fno-inline
```

plus `-static` for the ELF harness. The flags matter:

- `-O0 -fno-inline`: prevents the compiler from collapsing distinct parser functions into shared inlined code. Without this, all the JSON productions inline into `json_tokener_parse`'s entry block and the label distribution flattens.
- `-no-pie`: keeps addresses stable so addr2line resolves cleanly against the binary on disk.
- `-Wl,-z,now`: eager symbol resolution. Otherwise PLT/GOT lazy-binding pollutes the first trace.
- `-g`: debug symbols for addr2line attribution in `out.dot`.
- `-static`: full static linking. We learned this the hard way on the URL evaluation. Dynamic linking causes the dynamic-linker startup to dominate every trace, and ParseRE's useless-edges filter wipes the entire graph.

The full Dockerfile in [`../docker/Dockerfile`](../docker/Dockerfile) shows the per-harness build commands.

## Adding a new format

Two pieces:

1. Write a harness `<name>_harness.c` that reads stdin, calls the parser, returns 0/1.
2. Add the harness build to the Dockerfile, add a case to `run.sh`, define a `<NAME>_PARSE_TREE_TEMPLATE` in `parsere/main.py`, and add a `case "<name>":` to the format switch.

The template is the hard part. For text formats, you write byte-level alternatives directly. For binary formats with interdependent fields (offsets must match content positions), generate the template alternatives from a Python script the way `evaluations/elf/scripts/gen_elf_corpus.py` does it.
