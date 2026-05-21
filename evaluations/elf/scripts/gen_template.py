#!/usr/bin/env python3
"""
Generate the ELF_PARSE_TREE_TEMPLATE Python code for ParseRE's main.py.

Outputs a .py file that defines the template using pre-computed ELF bytes.
The template splits each ELF into 3 children:
  - elf_header (64 bytes, always the same)
  - program_header (112 bytes, 4 alternatives)
  - section_header (872 bytes, 5 alternatives including shdrs)

Cartesian product: 1 × 4 × 5 = 20 instantiations.
"""

import gen_elf_corpus as g


def bytes_to_literal(data: bytes) -> str:
    """Convert bytes to a Python bytes literal."""
    return repr(data)


def main():
    # Build the header (always the same)
    ehdr = g.make_ehdr()

    # Build phdr alternatives
    phdr_variants = {
        'PT_LOAD + PT_NOTE': g.build_elf(phdr_types=(g.PT_LOAD, g.PT_NOTE))[64:176],
        'PT_LOAD + PT_INTERP': g.build_elf(phdr_types=(g.PT_LOAD, g.PT_INTERP))[64:176],
        'PT_LOAD + PT_DYNAMIC': g.build_elf(phdr_types=(g.PT_LOAD, g.PT_DYNAMIC))[64:176],
        'PT_LOAD + PT_NULL': g.build_elf(phdr_types=(g.PT_LOAD, g.PT_NULL))[64:176],
    }

    # Build section alternatives (includes section data + section headers)
    section_variants = {
        'full (symtab + strtab + text)': g.build_elf(has_symtab=True, has_strtab=True, has_text=True)[176:],
        'no symtab': g.build_elf(has_symtab=False, has_strtab=True, has_text=True)[176:],
        'no strtab': g.build_elf(has_symtab=True, has_strtab=False, has_text=True)[176:],
        'no symtab or strtab': g.build_elf(has_symtab=False, has_strtab=False, has_text=True)[176:],
        'no text': g.build_elf(has_symtab=True, has_strtab=True, has_text=False)[176:],
    }

    # Write the template file
    with open('elf_template.py', 'w') as f:
        f.write('"""ELF_PARSE_TREE_TEMPLATE for ParseRE — auto-generated."""\n\n')

        # Write byte constants
        f.write(f'_EHDR = {bytes_to_literal(ehdr)}\n\n')

        for i, (name, data) in enumerate(phdr_variants.items()):
            f.write(f'# {name}\n')
            f.write(f'_PHDR_{i} = {bytes_to_literal(data)}\n\n')

        for i, (name, data) in enumerate(section_variants.items()):
            f.write(f'# {name}\n')
            f.write(f'_SECT_{i} = {bytes_to_literal(data)}\n\n')

        # Write the template definition
        f.write('''
# Import ParseTreeTemplate from main module
# (This file is meant to be imported by a patched main.py)

def make_elf_template(ParseTreeTemplate):
    """Build the ELF template using the ParseTreeTemplate class."""
    return ParseTreeTemplate(
        "ELF",
        frozenset((
            (
                ParseTreeTemplate("elf_header", frozenset((
                    _EHDR,
                ))),
                ParseTreeTemplate("program_header", frozenset((
''')
        for i in range(len(phdr_variants)):
            f.write(f'                    _PHDR_{i},\n')
        f.write('''                ))),
                ParseTreeTemplate("section_header", frozenset((
''')
        for i in range(len(section_variants)):
            f.write(f'                    _SECT_{i},\n')
        f.write('''                ))),
            ),
        )),
    )
''')

    print('Generated elf_template.py')
    print(f'  Header: {len(ehdr)} bytes (1 variant)')
    print(f'  Program headers: {len(list(phdr_variants.values())[0])} bytes ({len(phdr_variants)} variants)')
    print(f'  Sections: {len(list(section_variants.values())[0])} bytes ({len(section_variants)} variants)')
    print(f'  Instantiations: 1 × {len(phdr_variants)} × {len(section_variants)} = {len(phdr_variants) * len(section_variants)}')


if __name__ == '__main__':
    main()
