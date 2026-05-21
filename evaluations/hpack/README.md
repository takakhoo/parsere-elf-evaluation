# HPACK Evaluation (Placeholder)

This is Ben's evaluation, not Taka's. The folder exists so the cross-format comparison in the paper has a place to point to.

## What HPACK is

HPACK is the header compression format for HTTP/2, defined in RFC 7541. It encodes header fields as variable-length integers and optionally Huffman-compressed strings, with a dynamic table for previously-sent headers. It is fully binary, uses context-sensitive encoding (integer bit widths depend on the header type byte), and involves a fixed Huffman table baked into the specification.

For ParseRE this is a stress test: it has the offset-driven structural properties of ELF but with much more conditional encoding logic than ELF's mostly-uniform record readers.

## Expected target

`libnghttp2`, specifically the HPACK decoder. Entry point would be something like `nghttp2_hd_inflate_hd`.

## Expected grammar productions

- `indexed_header`: a single byte referencing the static or dynamic table
- `literal_header_name_index`: indexed name plus literal value
- `literal_header_both_strings`: both name and value as literals
- `huffman_string`: a Huffman-compressed string
- `raw_string`: a non-compressed string
- `variable_length_int`: the integer encoding used throughout HPACK

## Status

Not started. Ben said he was working on this during the May 19 session.

Once Ben has results, drop the harness into `harnesses/`, the template into `parsere/main.py`, and the run output into `evaluations/hpack/output/`.

## Note for Ben

If you want to follow the pattern Taka used for ELF, look at how the ELF template is structured. It is byte-baked because the format has interdependent offsets. For HPACK the byte-level approach should be even easier because HPACK is a stream, not a layout-driven format. You can probably write the template directly in `main.py` without a Python corpus generator.
