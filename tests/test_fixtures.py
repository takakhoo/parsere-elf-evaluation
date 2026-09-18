import io
import itertools
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from elftools.elf.elffile import ELFFile
from elftools.common.exceptions import ELFError
from parsere.main import ELF_PARSE_TREE_TEMPLATE, BasicBlock, QEMUTracer, parse_translation_log
from evaluations.elf.scripts import gen_elf_corpus as g


class FixtureTests(unittest.TestCase):
    def test_twenty_inputs_match_generator(self):
        template={tree.to_bytes() for tree in ELF_PARSE_TREE_TEMPLATE.instantiate()}
        generated={g.build_elf(phdr_types=(g.PT_LOAD,p), **s) for p,s in itertools.product(
            [g.PT_NOTE,g.PT_INTERP,g.PT_DYNAMIC,g.PT_NULL],
            [{},{'has_symtab':False},{'has_strtab':False},{'has_symtab':False,'has_strtab':False},{'has_text':False}])}
        self.assertEqual(template,generated)
        self.assertEqual(len(template),20)
        invalid=0
        for data in template:
            self.assertEqual(len(data),1048)
            elf=ELFFile(io.BytesIO(data))
            self.assertEqual(elf.num_segments(),2)
            self.assertEqual(elf.num_sections(),6)
            try:
                list(elf.iter_sections())
            except ELFError as error:
                self.assertIn('expected SHT_STRTAB',str(error))
                invalid+=1
        self.assertEqual(invalid,4)

    def test_translation_records(self):
        data=b'----------------\nIN: main\n0x00400100:  90  nop\n0x00400101:  c3  ret\n\n----------------\nIN: helper\n0x00400200:  c3  ret\n\n'
        self.assertEqual(parse_translation_log(data),[BasicBlock(0x400100,0x400101),BasicBlock(0x400200,0x400200)])
        self.assertEqual(parse_translation_log(b'not a trace'),[])

    def test_timeout_cleans_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable=Path(tmp)/'fixture';executable.touch()
            tracer=QEMUTracer(executable,executable,timeout=.1)
            logs=[]
            def fail(args,**kwargs):
                logs.append(Path(args[2]));logs[-1].write_bytes(b'partial')
                self.assertEqual(kwargs['timeout'],.1)
                raise subprocess.TimeoutExpired(args,.1)
            with patch('parsere.main.subprocess.run',side_effect=fail):
                with self.assertRaises(subprocess.TimeoutExpired): tracer.trace(b'benign')
            self.assertFalse(logs[0].parent.exists())


if __name__=='__main__': unittest.main()
