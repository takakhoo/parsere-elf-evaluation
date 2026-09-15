# evaluations/hpack/

This directory is a design note for a planned HPACK evaluation. It contains no implementation, harness, raw output, or measured result.

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

## Expected artifact layout

Drop them into:

- `evaluations/hpack/harness/hpack_harness.c` or another documented harness path
- `evaluations/hpack/output/parsere.out`, `out.dot`, `out.svg`
- Add a `case "hpack":` in `parsere/main.py` switch
- Update the corresponding pending row in `paper/sections/evaluation.tex`

## A suggestion

ELF requires a Python generator because of interdependent offsets. HPACK is stream-oriented rather than layout-driven, so a first implementation may be able to express byte alternatives directly in an `HPACK_PARSE_TREE_TEMPLATE`; that design remains to be validated.
