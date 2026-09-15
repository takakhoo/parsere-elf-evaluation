import itertools
import functools
import multiprocessing
import multiprocessing.pool
import subprocess
import uuid
import os
import copy
import re

from collections import defaultdict
from dataclasses import dataclass
from argparse import ArgumentParser, Namespace
from pathlib import Path
from subprocess import CompletedProcess
from typing import Iterable, Callable, Self, TypeGuard, Any
from re import Pattern

import networkx
import tqdm

try:
    from cxxfilt import demangle  # type: ignore
except ModuleNotFoundError:

    def demangle(s: str) -> str:
        return s


import elftools.elf.constants

from elftools.elf.segments import Segment
from elftools.elf.elffile import ELFFile
from networkx import DiGraph
from pydot import Dot

type ttuple[T] = tuple[T, ...]


def eager_pmap[U, T](
    f: Callable[[U], T],
    s: Iterable[U],
    nproc: int = max(1, multiprocessing.cpu_count()),
) -> list[T]:
    with multiprocessing.pool.ThreadPool(nproc) as pool:
        return list(pool.map(f, s))


_COLORS: ttuple[str] = (
    "#ff0000",
    "#ff7f00",
    "#999900",
    "#00ff00",
    "#00aa20",
    "#0000ff",
    "#4b0082",
    "#8f00ff",
    "#d18bc0",
    "#B92DDC",
)
_color_index: int = 0


@functools.cache
def color_from_label(label: str) -> str:
    """
    Produces a unique-ish color from a string.
    """
    global _color_index
    result: str = _COLORS[_color_index % len(_COLORS)]
    _color_index += 1
    return result


@dataclass(frozen=True)
class BasicBlock:
    start: int
    end: int


@dataclass(frozen=True)
class TraceResult:
    trace: ttuple[BasicBlock]
    exit_status: int

    @functools.cache
    def bb_trace(self: Self) -> ttuple[BasicBlock]:
        return self.trace

    @functools.cache
    def bb_map(self: Self) -> frozenset[BasicBlock]:
        return frozenset(self.trace)

    @functools.cache
    def edge_trace(self: Self) -> ttuple[tuple[BasicBlock, BasicBlock]]:
        return tuple(itertools.pairwise(self.trace))

    @functools.cache
    def edge_map(self: Self) -> frozenset[tuple[BasicBlock, BasicBlock]]:
        return frozenset(self.edge_trace())


QEMU_TRACE_BB_PAT: Pattern = re.compile(
    b"-+\nIN: .*\n(?P<start_addr>0x[0-9a-f]*):  (?P<first_bytes>(?:[0-9a-f]{2} )*).*\n(?:(?:0x.*\n)*(?P<end_addr>0x[0-9a-f]*):  (?P<second_bytes>(?:[0-9a-f]{2} )*).*\n)?\n"
)


@dataclass(frozen=True)
class QEMUTracer:
    qemu: Path
    target: Path

    def __post_init__(self: Self) -> None:
        assert self.qemu.is_file() and self.target.is_file()

    @functools.cache
    def get_executable_segment(self: Self) -> Segment:
        # Assumes there is one executable mapping in the ELF
        exec_segments: ttuple[Segment] = tuple(
            s
            for s in ELFFile.load_from_path(self.target).iter_segments()
            if s["p_type"] == "PT_LOAD"
            and s["p_flags"] & elftools.elf.constants.P_FLAGS.PF_X
        )
        assert len(exec_segments) == 1
        return exec_segments[0]

    @functools.cache
    def get_executable_range(self: Self) -> range:
        # Assumes there is one executable mapping in the ELF
        exec_segment: Segment = self.get_executable_segment()
        base_addr: int = self.get_executable_segment()["p_vaddr"]
        return range(base_addr, base_addr + exec_segment["p_memsz"])

    def trace(self: Self, data: bytes) -> TraceResult:
        tempfile: str = f"/tmp/{uuid.uuid4()}"
        completed_process: CompletedProcess
        completed_process = subprocess.run(
            [str(self.qemu), "-D", tempfile, "-d", "in_asm", str(self.target)],
            input=data,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            check=False,
        )
        trace: list[BasicBlock] = []
        with open(tempfile, "rb") as f:
            for m in re.finditer(QEMU_TRACE_BB_PAT, f.read()):
                end_addr: int = int(
                    m["end_addr"] if m["end_addr"] is not None else m["start_addr"], 16
                )
                trace.append(BasicBlock(int(m["start_addr"], 16), end_addr))
        os.remove(tempfile)
        return TraceResult(
            tuple(bb for bb in trace if bb.start in self.get_executable_range()),
            completed_process.returncode,
        )


def is_frozenset_bytes(x: Any) -> TypeGuard[frozenset[bytes]]:
    return isinstance(x, frozenset) and all(isinstance(b, bytes) for b in x)


@dataclass(frozen=True)
class StringTree:
    data: str
    children: ttuple["StringTree"]


@dataclass(frozen=True)
class ParseTree:
    name: str
    children_or_data: ttuple["ParseTree"] | bytes

    @functools.cache
    def to_bytes(self: Self) -> bytes:
        if isinstance(self.children_or_data, bytes):
            return self.children_or_data
        return b"".join(c.to_bytes() for c in self.children_or_data)

    @functools.cache
    def to_rule_tree(self: Self) -> StringTree:
        return StringTree(
            self.name,
            tuple()
            if isinstance(self.children_or_data, bytes)
            else tuple(c.to_rule_tree() for c in self.children_or_data),
        )

    @functools.cache
    def difference(self: Self, other: Self) -> frozenset[StringTree]:
        if (
            isinstance(self.children_or_data, bytes)
            and isinstance(other.children_or_data, bytes)
            and self.name == other.name
            and (
                not self.children_or_data
                or self.children_or_data == other.children_or_data
            )
        ):
            # Exact match of leaves or nothing to report
            return frozenset()
        if (
            isinstance(self.children_or_data, tuple)
            and isinstance(other.children_or_data, tuple)
            and self.name == other.name
        ):
            # Names match for internal nodes
            if len(self.children_or_data) == len(other.children_or_data) and tuple(
                c.name for c in self.children_or_data
            ) == tuple(c.name for c in other.children_or_data):
                # Child names match
                return frozenset().union(
                    *(
                        c1.difference(c2)
                        for c1, c2 in zip(self.children_or_data, other.children_or_data)
                    )
                )
            if other.children_or_data:
                # Child names don't match.
                # Just grab all the children name trees and call it a day
                return frozenset().union(
                    *(
                        map(
                            lambda c: frozenset((c.to_rule_tree(),)),
                            self.children_or_data,
                        )
                    )
                )
        return frozenset(
            (self.to_rule_tree(),),
        )


@dataclass(frozen=True)
class ParseTreeTemplate:
    name: str
    children_or_data_options: frozenset[ttuple["ParseTreeTemplate"]] | frozenset[bytes]

    @functools.cache
    def instantiate(
        self: Self,
    ) -> frozenset[ParseTree]:
        if is_frozenset_bytes(self.children_or_data_options):
            data_options: frozenset[bytes] = self.children_or_data_options
            return frozenset(ParseTree(self.name, b) for b in data_options)
        if is_frozenset_ttuple_ptt(self.children_or_data_options):
            children_options: frozenset[ttuple["ParseTreeTemplate"]] = (
                self.children_or_data_options
            )
            result: set[ParseTree] = set()
            for children in children_options:
                recursive_results: ttuple[frozenset[ParseTree]] = tuple(
                    c.instantiate() for c in children
                )
                for selection in itertools.product(*recursive_results):
                    result.add(ParseTree(self.name, selection))
            return frozenset(result)
        assert False


def is_frozenset_ttuple_ptt(x: Any) -> TypeGuard[frozenset[ttuple[ParseTreeTemplate]]]:
    return isinstance(x, frozenset) and all(
        isinstance(t, tuple) and all(isinstance(i, ParseTreeTemplate) for i in t)
        for t in x
    )


JSON_PARSE_TREE_TEMPLATE: ParseTreeTemplate = ParseTreeTemplate(
    "JSON",
    frozenset(
        (
            (
                ParseTreeTemplate(
                    "object",
                    frozenset(
                        (
                            (
                                ParseTreeTemplate("open-{", frozenset((b"{",))),
                                ParseTreeTemplate(
                                    "object-element",
                                    frozenset(
                                        (
                                            (
                                                ParseTreeTemplate(
                                                    "string",
                                                    frozenset(
                                                        (
                                                            b'"key"',
                                                            b'""',
                                                        ),
                                                    ),
                                                ),
                                                ParseTreeTemplate(
                                                    "key-value-separator-:",
                                                    frozenset(
                                                        (b":",),
                                                    ),
                                                ),
                                                ParseTreeTemplate(
                                                    "value",
                                                    frozenset(
                                                        (
                                                            (
                                                                ParseTreeTemplate(
                                                                    "number",
                                                                    frozenset(
                                                                        (
                                                                            b"1",
                                                                            b"2e77",
                                                                            b"-1000",
                                                                            b"0.4",
                                                                        ),
                                                                    ),
                                                                ),
                                                            ),
                                                            (
                                                                ParseTreeTemplate(
                                                                    "string",
                                                                    frozenset(
                                                                        (
                                                                            b'"a"',
                                                                            b'""',
                                                                            b'"abciouehfiushfiushdfiuhdf"',
                                                                        ),
                                                                    ),
                                                                ),
                                                            ),
                                                            (
                                                                ParseTreeTemplate(
                                                                    "boolean",
                                                                    frozenset(
                                                                        (
                                                                            b"true",
                                                                            b"false",
                                                                        )
                                                                    ),
                                                                ),
                                                            ),
                                                            (
                                                                ParseTreeTemplate(
                                                                    "null",
                                                                    frozenset(
                                                                        (b"null",)
                                                                    ),
                                                                ),
                                                            ),
                                                            (
                                                                ParseTreeTemplate(
                                                                    "nan",
                                                                    frozenset(
                                                                        (b"nan",)
                                                                    ),
                                                                ),
                                                            ),
                                                            (
                                                                ParseTreeTemplate(
                                                                    "inf",
                                                                    frozenset(
                                                                        (b"inf",)
                                                                    ),
                                                                ),
                                                            ),
                                                            (
                                                                ParseTreeTemplate(
                                                                    "array",
                                                                    frozenset(
                                                                        (
                                                                            (
                                                                                ParseTreeTemplate(
                                                                                    "array-open-[",
                                                                                    frozenset(
                                                                                        (
                                                                                            b"[",
                                                                                        )
                                                                                    ),
                                                                                ),
                                                                                ParseTreeTemplate(
                                                                                    "array-close-]",
                                                                                    frozenset(
                                                                                        (
                                                                                            b"]",
                                                                                        )
                                                                                    ),
                                                                                ),
                                                                            ),
                                                                        ),
                                                                    ),
                                                                ),
                                                            ),
                                                        ),
                                                    ),
                                                ),
                                            ),
                                            tuple(),
                                        ),
                                    ),
                                ),
                                ParseTreeTemplate("close-}", frozenset((b"}",))),
                            ),
                        ),
                    ),
                ),
            ),
        )
    ),
)


URI_PARSE_TREE_TEMPLATE: ParseTreeTemplate = ParseTreeTemplate(
    "URI",
    frozenset(
        (
            (
                ParseTreeTemplate(
                    "scheme",
                    frozenset(
                        (
                            b"a",
                            b"scheme_abcdefghikjlmnopqrstuvwxyz",
                        )
                    ),
                ),
                ParseTreeTemplate(
                    "post-scheme-:",
                    frozenset(
                        (b":",),
                    ),
                ),
                ParseTreeTemplate(
                    "hier-part",
                    frozenset(
                        (
                            (
                                ParseTreeTemplate(
                                    "pre-authority-//",
                                    frozenset(
                                        (b"//",),
                                    ),
                                ),
                                ParseTreeTemplate(
                                    "authority",
                                    frozenset(
                                        (
                                            (
                                                ParseTreeTemplate(
                                                    "userinfo@",
                                                    frozenset(
                                                        (
                                                            (
                                                                ParseTreeTemplate(
                                                                    "userinfo",
                                                                    frozenset(
                                                                        (
                                                                            b"user_abcdefghikjlmnopqrstuvwxyz",
                                                                            b"",
                                                                        )
                                                                    ),
                                                                ),
                                                                ParseTreeTemplate(
                                                                    "post-userinfo-@",
                                                                    frozenset(
                                                                        (b"@",),
                                                                    ),
                                                                ),
                                                            ),
                                                            tuple(),
                                                        )
                                                    ),
                                                ),
                                                ParseTreeTemplate(
                                                    "host",
                                                    frozenset(
                                                        (
                                                            b"host_abcdefghikjlmnopqrstuvwxyz",
                                                            b"1.2.3.4",
                                                            b"[::1]",
                                                        )
                                                    ),
                                                ),
                                                ParseTreeTemplate(
                                                    ":port",
                                                    frozenset(
                                                        (
                                                            (
                                                                ParseTreeTemplate(
                                                                    "pre-port-:",
                                                                    frozenset(
                                                                        (b":",),
                                                                    ),
                                                                ),
                                                                ParseTreeTemplate(
                                                                    "port",
                                                                    frozenset(
                                                                        (
                                                                            b"12340",
                                                                            b"",
                                                                        )
                                                                    ),
                                                                ),
                                                            ),
                                                            tuple(),
                                                        ),
                                                    ),
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                                ParseTreeTemplate(
                                    "path-abempty",
                                    frozenset(
                                        (
                                            (
                                                ParseTreeTemplate(
                                                    "pre-segment-/",
                                                    frozenset(
                                                        (b"/",),
                                                    ),
                                                ),
                                                ParseTreeTemplate(
                                                    "segment",
                                                    frozenset(
                                                        (
                                                            b"segment_abcdefghikjlmnopqrstuvwxyz",
                                                            b"",
                                                        )
                                                    ),
                                                ),
                                            ),
                                            tuple(),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
                ParseTreeTemplate(
                    "?query",
                    frozenset(
                        (
                            (
                                ParseTreeTemplate(
                                    "pre-query-?",
                                    frozenset(
                                        (b"?",),
                                    ),
                                ),
                                ParseTreeTemplate(
                                    "query",
                                    frozenset(
                                        (
                                            b"abc=6&xyz=7",
                                            b"",
                                        ),
                                    ),
                                ),
                            ),
                            tuple(),
                        )
                    ),
                ),
                ParseTreeTemplate(
                    "#fragment",
                    frozenset(
                        (
                            (
                                ParseTreeTemplate(
                                    "pre-fragment-#",
                                    frozenset(
                                        (b"#",),
                                    ),
                                ),
                                ParseTreeTemplate(
                                    "fragment",
                                    frozenset(
                                        (b"fragment_abcdefghikjlmnopqrstuvwxyz", b"")
                                    ),
                                ),
                            ),
                            tuple(),
                        )
                    ),
                ),
            ),
        ),
    ),
)


ELF_PARSE_TREE_TEMPLATE: ParseTreeTemplate = ParseTreeTemplate(
    "ELF",
    frozenset(
        (
            (
                ParseTreeTemplate("elf_header", frozenset((
                    b'\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00>\x00\x01\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x98\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00@\x008\x00\x02\x00@\x00\x06\x00\x01\x00',
                ))),
                ParseTreeTemplate("program_header", frozenset((
                    b'\x01\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x18\x04\x00\x00\x00\x00\x00\x00\x18\x04\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x04\x00\x00\x00X\x02\x00\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00',
                    b'\x01\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x18\x04\x00\x00\x00\x00\x00\x00\x18\x04\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00\x04\x00\x00\x00X\x02\x00\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00',
                    b'\x01\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x18\x04\x00\x00\x00\x00\x00\x00\x18\x04\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x06\x00\x00\x00X\x02\x00\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x08\x00\x00\x00\x00\x00\x00\x00',
                    b'\x01\x00\x00\x00\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x18\x04\x00\x00\x00\x00\x00\x00\x18\x04\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00',
                ))),
                ParseTreeTemplate("section_header", frozenset((
                    b'\x00.shstrtab\x00.strtab\x00.symtab\x00.text\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00main\x00printf\x00_start\x00data_val\x00helper\x00init\x00fini\x00loop\x00exit\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x12\x00\x04\x00\x10\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x06\x00\x00\x00\x12\x00\x04\x00 \x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\r\x00\x00\x00\x12\x00\x04\x000\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x14\x00\x00\x00\x12\x00\x04\x00@\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x1d\x00\x00\x00\x12\x00\x04\x00P\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00$\x00\x00\x00\x12\x00\x04\x00`\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00)\x00\x00\x00\x12\x00\x04\x00p\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00.\x00\x00\x00\x12\x00\x04\x00\x80\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x003\x00\x00\x00\x12\x00\x04\x00\x90\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xb0\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0b\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf0\x00\x00\x00\x00\x00\x00\x00x\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x13\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00h\x01\x00\x00\x00\x00\x00\x00\xf0\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x18\x00\x00\x00\x00\x00\x00\x00\x1b\x00\x00\x00\x01\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00X\x02\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                    b'\x00.shstrtab\x00.strtab\x00.symtab\x00.text\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00main\x00printf\x00_start\x00data_val\x00helper\x00init\x00fini\x00loop\x00exit\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xb0\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0b\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf0\x00\x00\x00\x00\x00\x00\x00x\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x13\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00h\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x18\x00\x00\x00\x00\x00\x00\x00\x1b\x00\x00\x00\x01\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00X\x02\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                    b'\x00.shstrtab\x00.strtab\x00.symtab\x00.text\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x12\x00\x04\x00\x10\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x12\x00\x04\x00 \x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x12\x00\x04\x000\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x12\x00\x04\x00@\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x12\x00\x04\x00P\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x12\x00\x04\x00`\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x12\x00\x04\x00p\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x12\x00\x04\x00\x80\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x12\x00\x04\x00\x90\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xb0\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0b\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x13\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00h\x01\x00\x00\x00\x00\x00\x00\xf0\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x18\x00\x00\x00\x00\x00\x00\x00\x1b\x00\x00\x00\x01\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00X\x02\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                    b'\x00.shstrtab\x00.strtab\x00.symtab\x00.text\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\xcc\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xb0\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0b\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x13\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00h\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x18\x00\x00\x00\x00\x00\x00\x00\x1b\x00\x00\x00\x01\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00X\x02\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                    b'\x00.shstrtab\x00.strtab\x00.symtab\x00.text\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00main\x00printf\x00_start\x00data_val\x00helper\x00init\x00fini\x00loop\x00exit\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x12\x00\x04\x00\x10\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x06\x00\x00\x00\x12\x00\x04\x00 \x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\r\x00\x00\x00\x12\x00\x04\x000\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x14\x00\x00\x00\x12\x00\x04\x00@\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x1d\x00\x00\x00\x12\x00\x04\x00P\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00$\x00\x00\x00\x12\x00\x04\x00`\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00)\x00\x00\x00\x12\x00\x04\x00p\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00.\x00\x00\x00\x12\x00\x04\x00\x80\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x003\x00\x00\x00\x12\x00\x04\x00\x90\x00@\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xb0\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0b\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf0\x00\x00\x00\x00\x00\x00\x00x\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x13\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00h\x01\x00\x00\x00\x00\x00\x00\xf0\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x18\x00\x00\x00\x00\x00\x00\x00\x1b\x00\x00\x00\x00\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00X\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
                ))),
            ),
        )
    ),
)


def run(
    target_path: Path,
    ptt: ParseTreeTemplate,
    qemu_path: Path,
    addr2line_path: Path | None = None,
) -> DiGraph:
    pts: ttuple[ParseTree] = tuple(ptt.instantiate())
    pt_diffs: dict[tuple[ParseTree, ParseTree], frozenset[StringTree]] = {
        (pt1, pt2): pt1.difference(pt2)
        for pt1, pt2 in tqdm.tqdm(
            itertools.permutations(pts, 2),
            total=len(pts) * (len(pts) - 1),
            desc="Computing parse tree diffs",
        )
    }

    tracer: QEMUTracer = QEMUTracer(
        qemu_path,
        target_path,
    )
    print("running target...")
    traces: dict[ParseTree, TraceResult] = dict(
        zip(
            pts,
            eager_pmap(
                tracer.trace,
                map(ParseTree.to_bytes, pts),
            ),
        )
    )

    g: DiGraph[BasicBlock] = DiGraph(
        itertools.chain(
            *(
                tr.edge_map()
                for tr in tqdm.tqdm(
                    traces.values(),
                    desc="building graph",
                )
                if tr.exit_status == 0
            ),
        )
    )

    rule_to_edges: defaultdict[str, set[tuple[BasicBlock, BasicBlock]]] = defaultdict(
        set
    )
    for (first, second), diff in (
        (k, next(iter(v)))
        for k, v in tqdm.tqdm(pt_diffs.items(), desc="associating rules to edges")
        if len(v) == 1
    ):
        if traces[first].exit_status == traces[second].exit_status == 0:
            rule_to_edges[diff.data].update(
                traces[first].edge_map() - traces[second].edge_map()
            )

    rule_to_somewhat_unique_edges: defaultdict[
        str, set[tuple[BasicBlock, BasicBlock]]
    ] = copy.deepcopy(rule_to_edges)
    for (r1, e1), (r2, e2) in tqdm.tqdm(
        itertools.permutations(rule_to_edges.items(), 2), desc="uniquifying (step 1)"
    ):
        if r1 == r2:
            continue
        if len(e1) > 0 and len(e1) < len(e2) and len(e1 - e2) / len(e1) < 0.1:
            rule_to_somewhat_unique_edges[r2] -= e1

    rule_to_unique_edges: dict[str, set[tuple[BasicBlock, BasicBlock]]] = {}
    for rule, edges in tqdm.tqdm(
        rule_to_somewhat_unique_edges.items(), desc="uniquifying (step 2)"
    ):
        rule_to_unique_edges[rule] = edges.difference(
            *(
                rule_to_somewhat_unique_edges[r]
                for r in rule_to_somewhat_unique_edges
                if r != rule
            )
        )

    for rule, unique_edges in tqdm.tqdm(
        rule_to_unique_edges.items(), desc="coloring nodes"
    ):
        g.add_edges_from(
            (*e, {"color": color_from_label(rule), "xlabel": rule})
            for e in unique_edges
        )

    bbs: ttuple[BasicBlock] = tuple(g.nodes())
    if addr2line_path:
        fns_and_lines: ttuple[tuple[str, str]] = tuple(
            itertools.chain(
                *tqdm.tqdm(
                    (
                        itertools.batched(
                            subprocess.run(
                                args=[
                                    addr2line_path,
                                    "--functions",
                                    "--exe",
                                    target_path,
                                    *node_group,
                                ],
                                stdout=subprocess.PIPE,
                                check=True,
                            )
                            .stdout.strip()
                            .decode("ascii")
                            .split("\n"),
                            2,
                        )
                        for node_group in itertools.batched(
                            map(lambda bb: hex(bb.start), bbs),
                            60000,  # 60000 determined by experiment
                        )
                    ),
                    desc="addr2lining",
                ),
            )
        )

        for bb, (fn, line) in zip(
            bbs, tqdm.tqdm(fns_and_lines, "cleaning up node labels")
        ):
            if fn.startswith("_Z"):
                fn = demangle(fn)
            while True:
                depth: int = 0
                open_idx: int = -1
                for i, c in enumerate(fn):
                    if c == "<":
                        if depth == 0:
                            open_idx = i
                        depth += 1
                    if c == ">":
                        depth -= 1
                        if depth == 0:
                            fn = fn[:open_idx] + fn[i + 1 :]
                            break
                else:
                    break
            if "/" in line:
                line = line[line.rfind("/") + 1 :]
            g.nodes()[bb]["label"] = f"{hex(bb.start)} {line} {fn}"
            g.nodes()[bb]["shape"] = "box"

    for node in g.nodes():
        color: str | None = None
        for edge_attrs in (
            g.edges[e] for e in itertools.chain(g.in_edges(node), g.out_edges(node))
        ):
            if "color" not in edge_attrs:
                break
            if color is None:
                color = edge_attrs["color"]
            else:
                if edge_attrs["color"] != color:
                    break
        else:
            g.nodes()[node]["color"] = color
            g.nodes()[node]["style"] = "bold"

    empty_trace: TraceResult = tracer.trace(b"")
    g.remove_edges_from(
        tqdm.tqdm(tracer.trace(b"").edge_map(), desc="removing useless edges")
    )
    g.remove_nodes_from(
        tqdm.tqdm(
            list(filter(lambda n: g.degree(n) == 0, bbs)),
            desc="removing useless nodes",
        )
    )

    print("propagating colors...")
    nodes_to_color: set[BasicBlock] = set(g.nodes())
    while nodes_to_color:
        node_to_color: BasicBlock = nodes_to_color.pop()
        colors: frozenset[str | None] = frozenset(
            g.edges()[e].get("color") for e in g.out_edges(node_to_color)
        )
        labels: frozenset[str | None] = frozenset(
            g.edges()[e].get("xlabel") for e in g.out_edges(node_to_color)
        )

        if len(labels) == 1 and len(colors) == 1:
            new_color: str | None = next(iter(colors))
            new_label: str | None = next(iter(labels))
            if new_color is not None:
                g.nodes()[node_to_color]["color"] = new_color
                g.nodes()[node_to_color]["parsere_label"] = new_label
                for e in g.in_edges(node_to_color):
                    if g.edges()[e].get("color") is None:
                        g.edges()[e]["color"] = new_color
                        nodes_to_color.add(e[0])

    return g


def main() -> None:
    arg_parser: ArgumentParser = ArgumentParser("ParseRE")
    arg_parser.add_argument(
        "--qemu-path",
        type=Path,
        default="/usr/bin/qemu-x86_64",
        help="Path to QEMU executor for target",
    )
    arg_parser.add_argument(
        "--target-path", required=True, type=Path, help="Path to the target binary"
    )
    arg_parser.add_argument(
        "--format", required=True, help="Input format for target program."
    )
    arg_parser.add_argument(
        "--addr2line-path",
        type=Path,
        help="Path to addr2line binary for target. Not required for the tool to work. For evaluation purposes only.",
    )

    args: Namespace = arg_parser.parse_args()

    ptt: ParseTreeTemplate
    match args.format.lower():
        case "json":
            ptt = JSON_PARSE_TREE_TEMPLATE
        case "uri" | "url":
            ptt = URI_PARSE_TREE_TEMPLATE
        case "elf":
            ptt = ELF_PARSE_TREE_TEMPLATE
        case _:
            raise ValueError("Invalid format argument.")

    g: DiGraph = run(args.target_path, ptt, args.qemu_path, args.addr2line_path)

    print("writing dot...")
    g_as_dot: Dot = networkx.drawing.nx_pydot.to_pydot(g)
    g_as_dot.write_raw("out.dot")  # type: ignore
    print("converting to svg...")
    subprocess.run(["dot", "-Tsvg", "out.dot", "-o", "out.svg"], check=True)

    print("writing parsere.out...")
    with open("parsere.out", "w") as f:
        f.write(
            "\n".join(
                f"{hex(n.start)} {hex(n.end)} {g.nodes()[n]['parsere_label']}"
                for n in g.nodes()
                if "parsere_label" in g.nodes()[n]
            )
        )


if __name__ == "__main__":
    main()
