/*
 * ParseRE ELF evaluation harness.
 *
 * Reads an ELF file from stdin, walks its structure using libelf's public API.
 * Exits 0 on success, 1 on any parse failure.
 *
 * Order of operations is fixed so ParseRE's CFG correlates against a predictable
 * traversal pattern:
 *   1. read ELF header                  → ELF_HEADER production
 *   2. iterate program headers          → PROGRAM_HEADER production
 *   3. iterate section headers          → SECTION_HEADER production
 *   4. read names via .shstrtab         → STRING_TABLE production
 *   5. iterate symbols + look up names  → SYMBOL_TABLE production
 */

#include <fcntl.h>
#include <gelf.h>
#include <libelf.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#define DIE(msg) do { fprintf(stderr, "harness: %s\n", (msg)); return 1; } while (0)

static int walk_program_headers(Elf *e, size_t phnum) {
    GElf_Phdr phdr;
    for (size_t i = 0; i < phnum; i++) {
        if (gelf_getphdr(e, (int)i, &phdr) != &phdr) return 1;
        /* Touch every phdr field so ParseRE sees uniform basic-block coverage. */
        volatile uint64_t sink = phdr.p_type ^ phdr.p_offset ^ phdr.p_vaddr
                                ^ phdr.p_paddr ^ phdr.p_filesz ^ phdr.p_memsz
                                ^ phdr.p_flags ^ phdr.p_align;
        (void)sink;
    }
    return 0;
}

static int walk_section_headers(Elf *e, size_t shstrndx) {
    Elf_Scn *scn = NULL;
    while ((scn = elf_nextscn(e, scn)) != NULL) {
        GElf_Shdr shdr;
        if (gelf_getshdr(scn, &shdr) != &shdr) return 1;

        const char *name = elf_strptr(e, shstrndx, shdr.sh_name);
        if (name == NULL) {
            /* Some sections may have no name. Not an error. */
            continue;
        }

        /* Symbol-table walk for .symtab / .dynsym. */
        if (shdr.sh_type == SHT_SYMTAB || shdr.sh_type == SHT_DYNSYM) {
            Elf_Data *data = elf_getdata(scn, NULL);
            if (data == NULL) continue;

            size_t nsyms = shdr.sh_size / shdr.sh_entsize;
            for (size_t i = 0; i < nsyms; i++) {
                GElf_Sym sym;
                if (gelf_getsym(data, (int)i, &sym) != &sym) return 1;

                /* Look up symbol name via the linked string table. */
                const char *symname = elf_strptr(e, shdr.sh_link, sym.st_name);
                (void)symname;
            }
        }
    }
    return 0;
}

int main(void) {
    /* Slurp all stdin. We use a generous fixed cap to avoid dynamic allocation
       complicating the CFG; corpus inputs are intentionally small. */
    static unsigned char buf[1 << 20];
    size_t total = 0;
    ssize_t n;
    while ((n = read(0, buf + total, sizeof(buf) - total)) > 0) {
        total += (size_t)n;
        if (total == sizeof(buf)) break;
    }
    if (n < 0) DIE("read failed");
    if (total == 0) DIE("empty input");

    if (elf_version(EV_CURRENT) == EV_NONE) DIE("elf_version");

    Elf *e = elf_memory((char *)buf, total);
    if (e == NULL) DIE("elf_memory");

    if (elf_kind(e) != ELF_K_ELF) { elf_end(e); return 1; }

    /* (1) ELF header. */
    GElf_Ehdr ehdr;
    if (gelf_getehdr(e, &ehdr) != &ehdr) { elf_end(e); return 1; }

    /* (2) Program headers. */
    size_t phnum = 0;
    if (elf_getphdrnum(e, &phnum) != 0) { elf_end(e); return 1; }
    if (phnum > 0 && walk_program_headers(e, phnum) != 0) { elf_end(e); return 1; }

    /* (3+4+5) Section headers, string-table lookups, symbol-table walk. */
    size_t shstrndx = 0;
    if (elf_getshdrstrndx(e, &shstrndx) != 0) { elf_end(e); return 1; }

    if (walk_section_headers(e, shstrndx) != 0) { elf_end(e); return 1; }

    elf_end(e);
    return 0;
}
