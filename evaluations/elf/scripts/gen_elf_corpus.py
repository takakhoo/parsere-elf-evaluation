#!/usr/bin/env python3
"""
Generate minimal ELF64 corpus files for ParseRE's ELF evaluation.

Each generated file is a valid ELF64 that libelf can parse.
The files differ in controlled structural ways so that ParseRE's
pairwise trace differencing can identify which code handles which
ELF production (program headers, section headers, symbol tables, etc.).

Layout (all variants use the same fixed offsets):
  [0:64]      ELF header (Elf64_Ehdr)
  [64:176]    Program header table (2 × Elf64_Phdr = 112 bytes)
  [176:240]   .shstrtab data (64 bytes, section-name string table)
  [240:360]   .strtab data (120 bytes, symbol-name string table)
  [360:600]   .symtab data (240 bytes = 10 × Elf64_Sym)
  [600:664]   .text data (64 bytes, placeholder code)
  [664:1048]  Section header table (6 × Elf64_Shdr = 384 bytes)

Total: 1048 bytes per file.
"""

import struct
import os

# ELF constants
ELFMAG = b'\x7fELF'
ELFCLASS64 = 2
ELFDATA2LSB = 1
EV_CURRENT = 1
ELFOSABI_NONE = 0
ET_EXEC = 2
EM_X86_64 = 62
EM_386 = 3

PT_NULL = 0
PT_LOAD = 1
PT_DYNAMIC = 2
PT_INTERP = 3
PT_NOTE = 4

PF_X = 1
PF_W = 2
PF_R = 4

SHT_NULL = 0
SHT_PROGBITS = 1
SHT_SYMTAB = 2
SHT_STRTAB = 3
SHT_DYNSYM = 11

SHF_ALLOC = 2
SHF_EXECINSTR = 4

STB_GLOBAL = 1
STT_FUNC = 2

# Fixed layout offsets
EHDR_SIZE = 64
PHDR_ENTRY_SIZE = 56
SHDR_ENTRY_SIZE = 64
SYM_ENTRY_SIZE = 24

PHDR_OFFSET = 64
PHDR_COUNT = 2
PHDR_TABLE_SIZE = PHDR_COUNT * PHDR_ENTRY_SIZE  # 112

SHSTRTAB_OFFSET = PHDR_OFFSET + PHDR_TABLE_SIZE  # 176
SHSTRTAB_SIZE = 64

STRTAB_OFFSET = SHSTRTAB_OFFSET + SHSTRTAB_SIZE  # 240
STRTAB_SIZE = 120

SYMTAB_OFFSET = STRTAB_OFFSET + STRTAB_SIZE  # 360
SYMTAB_SIZE = 240  # 10 symbols

TEXT_OFFSET = SYMTAB_OFFSET + SYMTAB_SIZE  # 600
TEXT_SIZE = 64

SHDR_OFFSET = TEXT_OFFSET + TEXT_SIZE  # 664
SHDR_COUNT = 6  # null + shstrtab + strtab + symtab + text + extra
SHDR_TABLE_SIZE = SHDR_COUNT * SHDR_ENTRY_SIZE  # 384

TOTAL_SIZE = SHDR_OFFSET + SHDR_TABLE_SIZE  # 1048


def make_ehdr(e_machine=EM_X86_64, e_phnum=2, e_shnum=6, e_shstrndx=1):
    """Build a 64-byte ELF64 header."""
    e_ident = (
        ELFMAG
        + bytes([ELFCLASS64, ELFDATA2LSB, EV_CURRENT, ELFOSABI_NONE])
        + b'\x00' * 8  # padding
    )
    return struct.pack(
        '<16sHHIQQQIHHHHHH',
        e_ident,
        ET_EXEC,           # e_type
        e_machine,         # e_machine
        EV_CURRENT,        # e_version
        0x400000,          # e_entry (fake)
        PHDR_OFFSET,       # e_phoff
        SHDR_OFFSET,       # e_shoff
        0,                 # e_flags
        EHDR_SIZE,         # e_ehsize
        PHDR_ENTRY_SIZE,   # e_phentsize
        e_phnum,           # e_phnum
        SHDR_ENTRY_SIZE,   # e_shentsize
        e_shnum,           # e_shnum
        e_shstrndx,        # e_shstrndx
    )


def make_phdr(p_type, p_offset=0, p_vaddr=0x400000, p_filesz=0, p_memsz=0,
              p_flags=PF_R, p_align=0x1000):
    """Build a 56-byte Elf64_Phdr."""
    return struct.pack(
        '<IIQQQQQQ',
        p_type,   # p_type
        p_flags,  # p_flags
        p_offset, # p_offset
        p_vaddr,  # p_vaddr
        p_vaddr,  # p_paddr (same as vaddr)
        p_filesz, # p_filesz
        p_memsz,  # p_memsz
        p_align,  # p_align
    )


def make_shdr(sh_name=0, sh_type=SHT_NULL, sh_flags=0, sh_addr=0,
              sh_offset=0, sh_size=0, sh_link=0, sh_info=0,
              sh_addralign=1, sh_entsize=0):
    """Build a 64-byte Elf64_Shdr."""
    return struct.pack(
        '<IIQQQQIIQQ',
        sh_name,       # sh_name
        sh_type,       # sh_type
        sh_flags,      # sh_flags
        sh_addr,       # sh_addr
        sh_offset,     # sh_offset
        sh_size,       # sh_size
        sh_link,       # sh_link
        sh_info,       # sh_info
        sh_addralign,  # sh_addralign
        sh_entsize,    # sh_entsize
    )


def make_sym(st_name=0, st_info=0, st_other=0, st_shndx=0,
             st_value=0, st_size=0):
    """Build a 24-byte Elf64_Sym."""
    return struct.pack(
        '<IBBHQQ',
        st_name,  # st_name
        st_info,  # st_info
        st_other, # st_other
        st_shndx, # st_shndx
        st_value, # st_value
        st_size,  # st_size
    )


def build_shstrtab():
    """Build the section-name string table."""
    # Format: null-terminated strings, preceded by a null byte at index 0
    names = b'\x00.shstrtab\x00.strtab\x00.symtab\x00.text\x00'
    return names.ljust(SHSTRTAB_SIZE, b'\x00')


def name_offset(name):
    """Get the offset of a section name in our .shstrtab."""
    tab = b'\x00.shstrtab\x00.strtab\x00.symtab\x00.text\x00'
    return tab.index(name.encode())


def build_strtab(symbols=None):
    """Build the symbol-name string table."""
    if symbols is None:
        symbols = ['', 'main', 'printf', '_start', 'data_val',
                   'helper', 'init', 'fini', 'loop', 'exit']
    data = b'\x00'
    offsets = [0]
    for s in symbols[1:]:
        offsets.append(len(data))
        data += s.encode() + b'\x00'
    return data.ljust(STRTAB_SIZE, b'\x00'), offsets


def build_symtab(strtab_offsets, shndx=4):
    """Build the symbol table (10 entries)."""
    syms = b''
    # Entry 0: null symbol (required)
    syms += make_sym()
    # Entries 1-9: real symbols
    for i in range(1, 10):
        st_name = strtab_offsets[min(i, len(strtab_offsets) - 1)]
        st_info = (STB_GLOBAL << 4) | STT_FUNC
        syms += make_sym(
            st_name=st_name,
            st_info=st_info,
            st_shndx=shndx,
            st_value=0x400000 + i * 0x10,
            st_size=0x10,
        )
    return syms.ljust(SYMTAB_SIZE, b'\x00')


def build_elf(phdr_types=(PT_LOAD, PT_NOTE),
              has_symtab=True,
              has_strtab=True,
              has_text=True,
              e_machine=EM_X86_64,
              e_phnum=2,
              e_shnum=6):
    """
    Build a complete 1048-byte ELF64 file.
    Returns raw bytes.
    """
    # 1. ELF header
    ehdr = make_ehdr(e_machine=e_machine, e_phnum=e_phnum,
                     e_shnum=e_shnum, e_shstrndx=1)
    assert len(ehdr) == EHDR_SIZE

    # 2. Program headers
    phdrs = b''
    for i, pt in enumerate(phdr_types):
        if pt == PT_LOAD:
            phdrs += make_phdr(PT_LOAD, p_offset=0, p_filesz=TOTAL_SIZE,
                               p_memsz=TOTAL_SIZE, p_flags=PF_R | PF_X)
        elif pt == PT_NOTE:
            phdrs += make_phdr(PT_NOTE, p_offset=TEXT_OFFSET,
                               p_filesz=TEXT_SIZE, p_memsz=TEXT_SIZE,
                               p_flags=PF_R, p_align=4)
        elif pt == PT_INTERP:
            phdrs += make_phdr(PT_INTERP, p_offset=TEXT_OFFSET,
                               p_filesz=16, p_memsz=16,
                               p_flags=PF_R, p_align=1)
        elif pt == PT_DYNAMIC:
            phdrs += make_phdr(PT_DYNAMIC, p_offset=TEXT_OFFSET,
                               p_filesz=TEXT_SIZE, p_memsz=TEXT_SIZE,
                               p_flags=PF_R | PF_W, p_align=8)
        elif pt == PT_NULL:
            phdrs += make_phdr(PT_NULL)
        else:
            phdrs += make_phdr(pt)
    phdrs = phdrs.ljust(PHDR_TABLE_SIZE, b'\x00')
    assert len(phdrs) == PHDR_TABLE_SIZE

    # 3. Section data
    shstrtab = build_shstrtab()
    assert len(shstrtab) == SHSTRTAB_SIZE

    strtab_data, strtab_offsets = build_strtab()
    if not has_strtab:
        strtab_data = b'\x00' * STRTAB_SIZE
        strtab_offsets = [0] * 10
    assert len(strtab_data) == STRTAB_SIZE

    symtab_data = build_symtab(strtab_offsets)
    if not has_symtab:
        symtab_data = b'\x00' * SYMTAB_SIZE
    assert len(symtab_data) == SYMTAB_SIZE

    text_data = b'\xcc' * TEXT_SIZE if has_text else b'\x00' * TEXT_SIZE
    assert len(text_data) == TEXT_SIZE

    # 4. Section header table
    shdrs = b''
    # Entry 0: null (required)
    shdrs += make_shdr()
    # Entry 1: .shstrtab
    shdrs += make_shdr(
        sh_name=name_offset('.shstrtab'),
        sh_type=SHT_STRTAB,
        sh_offset=SHSTRTAB_OFFSET,
        sh_size=SHSTRTAB_SIZE,
    )
    # Entry 2: .strtab
    shdrs += make_shdr(
        sh_name=name_offset('.strtab'),
        sh_type=SHT_STRTAB if has_strtab else SHT_NULL,
        sh_offset=STRTAB_OFFSET,
        sh_size=STRTAB_SIZE if has_strtab else 0,
    )
    # Entry 3: .symtab (linked to .strtab at index 2)
    shdrs += make_shdr(
        sh_name=name_offset('.symtab'),
        sh_type=SHT_SYMTAB if has_symtab else SHT_NULL,
        sh_offset=SYMTAB_OFFSET,
        sh_size=SYMTAB_SIZE if has_symtab else 0,
        sh_link=2,  # link to .strtab
        sh_info=1,  # first non-local symbol index
        sh_entsize=SYM_ENTRY_SIZE,
    )
    # Entry 4: .text
    shdrs += make_shdr(
        sh_name=name_offset('.text'),
        sh_type=SHT_PROGBITS if has_text else SHT_NULL,
        sh_flags=SHF_ALLOC | SHF_EXECINSTR,
        sh_addr=0x400000,
        sh_offset=TEXT_OFFSET,
        sh_size=TEXT_SIZE if has_text else 0,
    )
    # Entry 5: padding (null)
    shdrs += make_shdr()

    assert len(shdrs) == SHDR_TABLE_SIZE

    # Assemble
    elf = ehdr + phdrs + shstrtab + strtab_data + symtab_data + text_data + shdrs
    assert len(elf) == TOTAL_SIZE, f"Expected {TOTAL_SIZE}, got {len(elf)}"
    return elf


def generate_corpus(outdir):
    """Generate the ELF corpus files."""
    os.makedirs(outdir, exist_ok=True)

    variants = {
        # Vary program header types (labels: program_header code)
        'full':        build_elf(phdr_types=(PT_LOAD, PT_NOTE),
                                 has_symtab=True, has_strtab=True),
        'phdr_interp': build_elf(phdr_types=(PT_LOAD, PT_INTERP),
                                 has_symtab=True, has_strtab=True),
        'phdr_dyn':    build_elf(phdr_types=(PT_LOAD, PT_DYNAMIC),
                                 has_symtab=True, has_strtab=True),
        'phdr_null':   build_elf(phdr_types=(PT_LOAD, PT_NULL),
                                 has_symtab=True, has_strtab=True),

        # Vary section contents (labels: section handling code)
        'no_symtab':   build_elf(phdr_types=(PT_LOAD, PT_NOTE),
                                 has_symtab=False, has_strtab=True),
        'no_strtab':   build_elf(phdr_types=(PT_LOAD, PT_NOTE),
                                 has_symtab=True, has_strtab=False),
        'no_sym_str':  build_elf(phdr_types=(PT_LOAD, PT_NOTE),
                                 has_symtab=False, has_strtab=False),
        'no_text':     build_elf(phdr_types=(PT_LOAD, PT_NOTE),
                                 has_symtab=True, has_strtab=True, has_text=False),
    }

    for name, data in variants.items():
        path = os.path.join(outdir, f'{name}.elf')
        with open(path, 'wb') as f:
            f.write(data)
        print(f'  {name}.elf  ({len(data)} bytes)')

    return variants


def generate_template_snippet(variants):
    """
    Print a Python code snippet that defines ELF_PARSE_TREE_TEMPLATE
    for pasting into main.py.
    """
    print("\n# === ELF TEMPLATE SNIPPET (paste into main.py) ===\n")
    print("# Auto-generated by gen_elf_corpus.py")
    print("# Each variant is a complete 1048-byte ELF64 file.")
    print("# The template structure enables ParseRE to isolate")
    print("# program-header vs section-header handling code.\n")

    # For the template to work with ParseRE's difference() algorithm,
    # we need children that vary independently.
    # Approach: split each ELF into a fixed prefix (ehdr) and varying parts.

    print("# The ELF header is always the same (64 bytes).")
    print("# Program headers vary (112 bytes).")
    print("# Section region varies (data + shdrs, 872 bytes).")
    print("#")
    print("# This gives 2 label dimensions: program_header and section_header.")
    print("# gen_template.py combines 1 header × 4 phdr regions × 5 section")
    print("# regions to produce 20 template instantiations.")


if __name__ == '__main__':
    import sys
    outdir = sys.argv[1] if len(sys.argv) > 1 else 'corpus'
    print(f'Generating ELF corpus in {outdir}/')
    variants = generate_corpus(outdir)
    print(f'\nGenerated {len(variants)} ELF variants, each {TOTAL_SIZE} bytes.')
    generate_template_snippet(variants)
