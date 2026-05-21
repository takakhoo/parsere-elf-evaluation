# harnesses/

Ben,

Three C harnesses, one per format. They all read bytes from stdin, hand them to the parser library under test, and exit 0 on success or 1 on parse failure.

| Harness | Lines | Library | Entry point |
|---------|------:|---------|------------|
| `json_c_harness.c`   |  25 | json-c | `json_tokener_parse(input)` |
| `curl_url_harness.c` |  30 | libcurl | `curl_url_set(handle, CURLUPART_URL, input, 0)` |
| `elf_harness.c`      | 108 | libelf | `elf_memory(buf, total)` + walk phdrs, shdrs, symtab |

## Why the ELF harness is so much longer

The ELF harness has to call libelf's structure walkers explicitly to exercise the production-specific code paths. Libelf exposes parsing as many small calls (one per program header via `gelf_getphdr`, one per section header via `elf_nextscn` + `gelf_getshdr`, one per symbol via `gelf_getsym`) rather than a single top-level `parse()` entry point. The harness has to call all of them.

The interesting bit is the symbol-table branch:

```c
if (shdr.sh_type == SHT_SYMTAB || shdr.sh_type == SHT_DYNSYM) {
    Elf_Data *data = elf_getdata(scn, NULL);
    // walk symbol entries
}
```

This is what makes the `section_header` label fire 68 times. Corpus members with a real symtab take this branch and execute `elf_getdata`, `gelf_getsym`, `elf_strptr`. Corpus members where the symtab is empty skip the branch. Different traces, different edge sets, attribution works.

## Compilation

Everything compiles inside the Docker image:

```
gcc -Wl,-z,now -no-pie -g -O0 -fno-inline [-static]
```

The flags that matter:

- **`-O0 -fno-inline`**: Without this, the compiler collapses distinct parser functions into shared inlined code. We saw this kill the JSON labeling on a first try with `-O2`. All the productions inlined into `json_tokener_parse`'s entry block and the label distribution flattened.
- **`-no-pie`**: Stable addresses so `addr2line` resolves cleanly against the binary on disk.
- **`-Wl,-z,now`**: Eager symbol resolution. Otherwise PLT/GOT lazy-binding pollutes the first trace.
- **`-g`**: Debug symbols for `addr2line` attribution in `out.dot`.
- **`-static`**: Full static linking. ELF harness only, but in principle we should do this for all of them. See the static linking lesson in the main README.

## Adding a new format

Two pieces:

1. Write `<name>_harness.c` that reads stdin, calls the parser, returns 0/1.
2. Add the build to the Dockerfile, add a case to `run.sh`, define `<NAME>_PARSE_TREE_TEMPLATE` in `parsere/main.py`, add a `case "<name>":` to the format switch.

The template is the hard part for binary formats with interdependent fields. For text formats you write byte alternatives directly. For binary formats you generate them with a Python script like `evaluations/elf/scripts/gen_elf_corpus.py` does it.

Taka
