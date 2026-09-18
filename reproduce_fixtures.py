"""Inventory generated benign ELF inputs; never executes them."""
from pathlib import Path
import hashlib
import io
import json
import struct
from elftools.elf.elffile import ELFFile
from elftools.common.exceptions import ELFError
from parsere.main import ELF_PARSE_TREE_TEMPLATE


def run():
    rows=[]
    for tree in sorted(ELF_PARSE_TREE_TEMPLATE.instantiate(),key=lambda t:t.to_bytes()):
        data=tree.to_bytes();elf=ELFFile(io.BytesIO(data))
        try:
            sections=[{'name':s.name,'type':s['sh_type'],'bytes':s['sh_size']} for s in elf.iter_sections()]
            error=None
        except ELFError as exc:
            sections=[];error=str(exc)
        rows.append({'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),
                     'program_type_codes':[struct.unpack_from('<I',data,elf['e_phoff']+i*elf['e_phentsize'])[0] for i in range(elf.num_segments())],
                     'sections':sections,'section_validation_error':error})
    result={'inputs':len(rows),'ordered_comparisons':len(rows)*(len(rows)-1),
            'section_validation_failures':sum(r['section_validation_error'] is not None for r in rows),
            'note':'Headers parse; four no_strtab variants retain a symtab linked to SHT_NULL. They are not fully valid ELF files or executable programs. This does not measure trace-label accuracy.', 'records':rows}
    out=Path(__file__).resolve().parent/'results/fixtures.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(f'{len(rows)} inputs, {len(rows)*(len(rows)-1)} comparisons; wrote {out}')


if __name__=='__main__': run()
