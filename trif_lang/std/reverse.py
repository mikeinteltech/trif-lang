"""Small helpers for reverse engineering workflows."""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class ExecutableInfo:
    path: str
    format: str
    sections: List[Dict[str, Any]]


def inspectExecutable(path: str) -> ExecutableInfo:
    data = Path(path).read_bytes()
    if data.startswith(b"\x7fELF"):
        return ExecutableInfo(path, "ELF", _parse_elf_sections(data))
    if data.startswith(b"MZ"):
        return ExecutableInfo(path, "PE", _parse_pe_sections(data))
    return ExecutableInfo(path, "unknown", [])


def hexdump(data: bytes, width: int = 16) -> str:
    lines: List[str] = []
    for offset in range(0, len(data), width):
        chunk = data[offset : offset + width]
        hex_bytes = " ".join(f"{byte:02X}" for byte in chunk)
        ascii_repr = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{offset:08X}  {hex_bytes:<{width * 3}}  {ascii_repr}")
    return "\n".join(lines)


def _parse_elf_sections(data: bytes) -> List[Dict[str, Any]]:
    is_64 = data[4] == 2
    if is_64:
        e_shoff = struct.unpack_from("<Q", data, 40)[0]
        e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", data, 58)
        header_fmt = "<IIQQQQIIQQ"
    else:
        e_shoff = struct.unpack_from("<I", data, 32)[0]
        e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", data, 46)
        header_fmt = "<IIIIIIIIII"

    sections: List[Dict[str, Any]] = []
    str_hdr_offset = e_shoff + e_shentsize * e_shstrndx
    if is_64:
        _, _, _, _, _, _, _, _, str_offset, str_size = struct.unpack_from(header_fmt, data, str_hdr_offset)
    else:
        _, _, _, _, _, _, _, _, str_offset, str_size = struct.unpack_from(header_fmt, data, str_hdr_offset)
    str_table = data[str_offset : str_offset + str_size]

    for index in range(e_shnum):
        offset = e_shoff + e_shentsize * index
        header = struct.unpack_from(header_fmt, data, offset)
        name_offset = header[0]
        section_offset = header[4 if is_64 else 4]
        section_size = header[5 if is_64 else 5]
        name = _read_c_string(str_table, name_offset)
        sections.append({"name": name, "offset": section_offset, "size": section_size})
    return sections


def _parse_pe_sections(data: bytes) -> List[Dict[str, Any]]:
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    num_sections = struct.unpack_from("<H", data, pe_offset + 6)[0]
    section_table = pe_offset + 24 + struct.unpack_from("<H", data, pe_offset + 20)[0]
    sections: List[Dict[str, Any]] = []
    entry_size = 40
    for i in range(num_sections):
        entry = section_table + entry_size * i
        name = data[entry : entry + 8].split(b"\0", 1)[0].decode("ascii", errors="ignore")
        virtual_size, virtual_address, size_of_raw, pointer_to_raw = struct.unpack_from("<IIII", data, entry + 8)
        sections.append(
            {
                "name": name,
                "virtualSize": virtual_size,
                "virtualAddress": virtual_address,
                "rawSize": size_of_raw,
                "rawOffset": pointer_to_raw,
            }
        )
    return sections


def _read_c_string(blob: bytes, offset: int) -> str:
    end = blob.find(b"\0", offset)
    if end == -1:
        end = len(blob)
    return blob[offset:end].decode("utf-8", errors="ignore")


__all__ = ["ExecutableInfo", "inspectExecutable", "hexdump"]
