# evaluations/hpack/

Ben,

This folder is a placeholder for your HPACK evaluation. The cross-format table in the paper points here.

## What HPACK is (for context)

HPACK is the header compression format for HTTP/2, defined in RFC 7541. Variable-length integers, optionally Huffman-compressed strings, dynamic table for previously-sent headers. Fully binary, context-sensitive encoding (integer bit widths depend on the header type byte), fixed Huffman table baked into the specification.

For ParseRE this should be a stress test: offset-driven binary like ELF, but with much more conditional encoding logic.

## Expected target

`libnghttp2`, specifically the HPACK decoder. Entry point would be `nghttp2_hd_inflate_hd` or similar.

## Expected productions

- `indexed_header`: one byte referencing the static or dynamic table
- `literal_header_name_index`: indexed name plus literal value
- `literal_header_both_strings`: both name and value as literals
- `huffman_string`: Huffman-compressed string
- `raw_string`: non-compressed string
- `variable_length_int`: the integer encoding used throughout

## When you have results

Drop them into:

- `evaluations/hpack/harness/hpack_harness.c` (or wherever you put the source)
- `evaluations/hpack/output/parsere.out`, `out.dot`, `out.svg`
- Add a `case "hpack":` in `parsere/main.py` switch
- Add a row to `paper/sections/evaluation.tex` Table 3
- I'll fill in the `\textit{[BEN:]}` markers in `paper/sections/evaluation.tex` Section IV-D

## A suggestion

For ELF I needed a Python generator because of the interdependent offsets. For HPACK you probably won't. HPACK is a stream rather than a layout-driven format, so you can write the byte alternatives directly into the `HPACK_PARSE_TREE_TEMPLATE` definition in `main.py`.

Taka
