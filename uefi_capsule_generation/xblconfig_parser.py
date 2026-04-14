#!/usr/bin/env python3
# Copyright (c) Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause-Clear

import argparse
import hashlib
import io
import os
import struct
from dataclasses import dataclass
from typing import List, Tuple

from elftools.elf.elffile import ELFFile

# =========================================================
# Helpers
# =========================================================


def align_up(x: int, a: int) -> int:
    r = x % a
    return x if r == 0 else x + (a - r)


# =========================================================
# Metadata v2 parsing (Program Header blob)
# ---------------------------------------------------------
# Header (12 bytes):
#   xcfg_type[4] (ASCII), major[1], minor[1], entries[2] (LE), meta_size[4] (LE)
#
# Item v2 (repeated 'entries' times):
#   attributes[4] (LE)
#   offset_from_meta_start[4] (LE)
#   item_size[4] (LE)       <-- bytes 8..11 of item, offset +8 from item_start
#   chipinfo[8] (LE)
#   platforminfo[8] (LE)
#   config_name_len[4] (LE)
#   config_name[config_name_len] (UTF-8)
#   PAD so THIS ITEM'S TOTAL SIZE is a multiple of 8
# =========================================================


@dataclass
class MetaHeader:
    xcfg_type: str
    major: int
    minor: int
    entries: int
    meta_size: int


@dataclass
class MetaItemV2:
    attributes: int
    offset_from_meta_start: int
    item_size: int
    chipinfo: int
    platforminfo: int
    config_name_len: int
    config_name: str
    start_off: int  # byte offset of this item's start inside the meta blob
    end_off: int  # byte offset just past this item (after padding)


def parse_meta_header(blob: bytes, off: int = 0) -> Tuple[MetaHeader, int]:
    if off + 12 > len(blob):
        raise ValueError("Metadata header truncated")
    xcfg_type = blob[off : off + 4].decode("ascii", errors="replace")
    major = blob[off + 4]
    minor = blob[off + 5]
    entries = int.from_bytes(blob[off + 6 : off + 8], "little")
    meta_size = int.from_bytes(blob[off + 8 : off + 12], "little")
    return MetaHeader(xcfg_type, major, minor, entries, meta_size), off + 12


def parse_meta_items_v2(
    blob: bytes, off: int, count: int
) -> Tuple[List[MetaItemV2], int]:
    items: List[MetaItemV2] = []
    cur = off
    for idx in range(count):
        item_start = cur

        # fixed 32 bytes
        if cur + 32 > len(blob):
            raise ValueError(f"Metadata v2 item {idx} truncated (fixed part)")
        attributes = int.from_bytes(blob[cur + 0 : cur + 4], "little")
        ofs_from_meta_start = int.from_bytes(blob[cur + 4 : cur + 8], "little")
        item_size = int.from_bytes(blob[cur + 8 : cur + 12], "little")
        chipinfo = int.from_bytes(blob[cur + 12 : cur + 20], "little")
        platforminfo = int.from_bytes(blob[cur + 20 : cur + 28], "little")
        name_len = int.from_bytes(blob[cur + 28 : cur + 32], "little")
        cur += 32

        # variable-length name
        if cur + name_len > len(blob):
            raise ValueError(
                f"Metadata v2 item {idx} name truncated (need {name_len} at 0x{cur:x}, buf=0x{len(blob):x})"
            )
        config_name = blob[cur : cur + name_len].decode("utf-8", errors="replace")
        cur += name_len

        # pad so THIS item's total size is a multiple of 8
        item_len_now = cur - item_start
        padded_len = align_up(item_len_now, 8)
        cur = item_start + padded_len

        items.append(
            MetaItemV2(
                attributes=attributes,
                offset_from_meta_start=ofs_from_meta_start,
                item_size=item_size,
                chipinfo=chipinfo,
                platforminfo=platforminfo,
                config_name_len=name_len,
                config_name=config_name,
                start_off=item_start,
                end_off=cur,
            )
        )
    return items, cur


# =========================================================
# ELF helpers
# =========================================================


def load_elf(elf_path: str) -> Tuple[bytearray, ELFFile, List]:
    """Read the ELF once, and create an ELFFile bound to an in-memory stream."""
    with open(elf_path, "rb") as f:
        file_bytes = f.read()
    data = bytearray(file_bytes)
    elf_stream = io.BytesIO(file_bytes)  # prevents 'seek of closed file'
    elf = ELFFile(elf_stream)
    segments = list(elf.iter_segments())
    return data, elf, segments


def parse_metadata_from_ph(
    elf: ELFFile, meta_ph_index: int
) -> Tuple[MetaHeader, List[MetaItemV2], bytes, int]:
    """Return (header, items, meta_blob, meta_file_offset)."""
    segments = list(elf.iter_segments())
    if not segments or meta_ph_index >= len(segments):
        raise IndexError(f"Program header #{meta_ph_index} not found")

    meta_seg = segments[meta_ph_index]
    meta_blob = meta_seg.data()
    # file offset of the metadata segment (needed for absolute writes if ever used)
    ph = elf._get_segment_header(meta_ph_index)
    meta_file_off = ph["p_offset"]

    hdr, off = parse_meta_header(meta_blob, 0)
    items, _ = parse_meta_items_v2(meta_blob, off, hdr.entries)
    return hdr, items, meta_blob, meta_file_off


# =========================================================
# Helpers for patching ELF program / section headers
# =========================================================


def _ph_file_offset_field(is_64: bool) -> Tuple[int, int]:
    """Return (field_offset_in_phdr, field_size) for p_offset."""
    # ELF32: p_offset at byte 4, 4 bytes
    # ELF64: p_offset at byte 8, 8 bytes
    if is_64:
        return 8, 8
    return 4, 4


def _ph_filesz_field(is_64: bool) -> Tuple[int, int]:
    """Return (field_offset_in_phdr, field_size) for p_filesz."""
    # ELF32 Phdr layout: type(4) offset(4) vaddr(4) paddr(4) filesz(4) memsz(4) flags(4) align(4)
    # ELF64 Phdr layout: type(4) flags(4) offset(8) vaddr(8) paddr(8) filesz(8) memsz(8) align(8)
    if is_64:
        return 0x20, 8
    return 0x10, 4


def _ph_memsz_field(is_64: bool) -> Tuple[int, int]:
    if is_64:
        return 0x28, 8
    return 0x14, 4


def _sh_offset_field(is_64: bool) -> Tuple[int, int]:
    """Return (field_offset_in_shdr, field_size) for sh_offset."""
    # ELF32: sh_offset at 16, 4 bytes
    # ELF64: sh_offset at 24, 8 bytes
    if is_64:
        return 24, 8
    return 16, 4


def _pack(endian: str, size: int, value: int) -> bytes:
    fmt = endian + {4: "I", 8: "Q"}[size]
    return struct.pack(fmt, value)


def _write_ph_field(
    data: bytearray,
    elf: ELFFile,
    seg_idx: int,
    field_off: int,
    field_size: int,
    value: int,
) -> None:
    endian = "<" if elf.little_endian else ">"
    phoff = elf.header["e_phoff"]
    phentsz = elf.header["e_phentsize"]
    pos = phoff + seg_idx * phentsz + field_off
    data[pos : pos + field_size] = _pack(endian, field_size, value)


def _write_sh_field(
    data: bytearray,
    elf: ELFFile,
    sec_idx: int,
    field_off: int,
    field_size: int,
    value: int,
) -> None:
    endian = "<" if elf.little_endian else ">"
    shoff = elf.header["e_shoff"]
    shentsz = elf.header["e_shentsize"]
    pos = shoff + sec_idx * shentsz + field_off
    data[pos : pos + field_size] = _pack(endian, field_size, value)


# =========================================================
# Dump logic based on metadata -> PH index (i + 2)
# =========================================================


def safe_filename(path: str) -> str:
    """Sanitize filename minimally: drop path components and disallow empty names."""
    name = os.path.basename(path)
    if not name:
        name = "unnamed"
    return name


def dump_from_meta(elf_path: str, out_dir: str, meta_ph_index: int) -> None:
    data, elf, segments = load_elf(elf_path)

    # Parse metadata v2 from PH#meta_ph_index
    hdr, items, _, _ = parse_metadata_from_ph(elf, meta_ph_index)

    os.makedirs(out_dir, exist_ok=True)

    print(
        f"Metadata (PH#{meta_ph_index}) xcfg_type='{hdr.xcfg_type}' "
        f"v{hdr.major}.{hdr.minor} entries={hdr.entries} meta_size={hdr.meta_size}"
    )
    print("Dumping items -> program headers starting at index 2 (i -> PH i+2):\n")

    for idx, it in enumerate(items):
        name = it.config_name

        ph_index = idx + 2
        if ph_index >= len(segments):
            print(
                f"  [i] WARN config_item[{idx}] name='{name}': "
                f"PH#{ph_index} doesn't exist (ELF has {len(segments)} segments)"
            )
            continue

        seg = segments[ph_index]
        seg_bytes = seg.data()
        to_write = min(len(seg_bytes), it.item_size)

        if to_write < it.item_size:
            print(
                f"  [i] WARN config_item[{idx}] name='{name}': "
                f"item_size={it.item_size} > segment_size={len(seg_bytes)}; clipping to {to_write}"
            )

        out_name = safe_filename(name)
        # If duplicate names appear, suffix with index to avoid overwrite
        out_path = os.path.join(out_dir, out_name)
        if os.path.exists(out_path):
            base, ext = os.path.splitext(out_name)
            out_path = os.path.join(out_dir, f"{base}__{idx}{ext}")

        with open(out_path, "wb") as out:
            out.write(seg_bytes[:to_write])

        print(
            f"  [+] config_item[{idx}] -> PH#{ph_index:>2} -> '{out_path}' ({to_write} bytes)"
        )

    print("\nDone.")


# =========================================================
# Replace logic: swap payload in a given program header,
# update metadata item_size, and update the SHA-384 hash.
# =========================================================


def replace_ph(
    elf_path: str,
    target_ph_index: int,
    new_file: str,
    output_file: str,
    meta_ph_index: int,
) -> None:
    """Replace the payload in program header *target_ph_index* with the
    contents of *new_file*, then patch:
      - ELF program-header p_filesz / p_memsz
      - ELF section-header sh_offset for any sections displaced by a grow
      - Metadata item_size for the corresponding config entry
      - SHA-384 hash table entry (binary search-and-replace)
    """
    data, elf, segments = load_elf(elf_path)

    if target_ph_index >= len(segments):
        raise IndexError(
            f"Target program header #{target_ph_index} not found "
            f"(ELF has {len(segments)} segments)"
        )

    # ----------------------------------------------------------
    # Load payloads
    # ----------------------------------------------------------
    old_seg = segments[target_ph_index]
    old_data = old_seg.data()
    old_size = old_seg["p_filesz"]
    seg_offset = old_seg["p_offset"]

    with open(new_file, "rb") as f:
        new_data = f.read()
    new_size = len(new_data)

    old_hash = hashlib.sha384(old_data[:old_size]).digest()
    new_hash = hashlib.sha384(new_data).digest()

    print(
        f"[i] Replacing PH#{target_ph_index}: old size={old_size}, new size={new_size}"
    )
    print(f"[i] Old SHA-384: {old_hash.hex()}")
    print(f"[i] New SHA-384: {new_hash.hex()}")

    is_64 = elf.elfclass == 64

    grow_size = new_size - old_size

    # ----------------------------------------------------------
    # Splice new payload into the raw ELF bytes
    # ----------------------------------------------------------
    if grow_size <= 0:
        # In-place replacement (shrink or same size)
        data[seg_offset : seg_offset + new_size] = new_data
        if grow_size < 0:
            # Zero-fill the freed tail so stale bytes don't confuse readers
            data[seg_offset + new_size : seg_offset + old_size] = b"\x00" * (-grow_size)
    else:
        # Segment grows: splice bytes and fix up all later offsets
        tail = bytes(data[seg_offset + old_size :])
        data[seg_offset : seg_offset + new_size] = new_data
        new_tail_start = seg_offset + new_size
        data[new_tail_start : new_tail_start + len(tail)] = tail
        data.extend(b"\x00" * grow_size)

        off_field, off_field_sz = _ph_file_offset_field(is_64)

        # Shift p_offset for every program header whose content lies after ours
        for i, seg in enumerate(segments):
            if seg["p_offset"] > seg_offset:
                new_off = seg["p_offset"] + grow_size
                _write_ph_field(data, elf, i, off_field, off_field_sz, new_off)

        # Shift sh_offset for every section header whose content lies after ours
        sh_off_field, sh_off_field_sz = _sh_offset_field(is_64)
        for i, sec in enumerate(elf.iter_sections()):
            if sec["sh_offset"] > seg_offset:
                new_off = sec["sh_offset"] + grow_size
                _write_sh_field(data, elf, i, sh_off_field, sh_off_field_sz, new_off)

    # ----------------------------------------------------------
    # Update p_filesz and p_memsz of the target program header
    # ----------------------------------------------------------
    filesz_field, filesz_field_sz = _ph_filesz_field(is_64)
    memsz_field, memsz_field_sz = _ph_memsz_field(is_64)
    _write_ph_field(data, elf, target_ph_index, filesz_field, filesz_field_sz, new_size)
    _write_ph_field(data, elf, target_ph_index, memsz_field, memsz_field_sz, new_size)

    # ----------------------------------------------------------
    # Update item_size in the metadata blob
    #
    # Config items in the META structure map to program headers as:
    #   meta_item[i]  <->  PH#(i + 2)
    # So for target_ph_index we need meta_item index = target_ph_index - 2.
    # ----------------------------------------------------------
    meta_item_index = target_ph_index - 2
    if meta_item_index >= 0:
        try:
            _, items, meta_blob, meta_file_off = parse_metadata_from_ph(
                elf, meta_ph_index
            )

            if meta_item_index < len(items):
                it = items[meta_item_index]
                # item_size is the third uint32 in the fixed part (offset +8 from item start)
                abs_field_off = meta_file_off + it.start_off + 8
                data[abs_field_off : abs_field_off + 4] = struct.pack("<I", new_size)
                print(
                    f"[i] Updated metadata item[{meta_item_index}] ('{it.config_name}') "
                    f"item_size: {it.item_size} -> {new_size} "
                    f"(at file offset 0x{abs_field_off:x})"
                )
            else:
                print(
                    f"[!] meta_item_index={meta_item_index} out of range "
                    f"(metadata has {len(items)} items); item_size not updated"
                )
        except Exception as exc:
            print(f"[!] Could not update metadata item_size: {exc}")
    else:
        print(
            f"[i] PH#{target_ph_index} has no corresponding metadata item (index < 2); "
            f"item_size not updated"
        )

    # ----------------------------------------------------------
    # Replace SHA-384 hash (binary search in the whole file)
    # ----------------------------------------------------------
    pos = bytes(data).find(old_hash)
    if pos != -1:
        print(
            f"[i] Found old SHA-384 at file offset 0x{pos:x}; replacing with new hash"
        )
        data[pos : pos + len(new_hash)] = new_hash
    else:
        print("[!] Old SHA-384 hash not found in ELF binary; hash table not updated")

    # ----------------------------------------------------------
    # Write output
    # ----------------------------------------------------------
    with open(output_file, "wb") as out:
        out.write(data)
    print(f"[+] Written patched ELF to '{output_file}'")


# =========================================================
# CLI
# =========================================================


def main():
    ap = argparse.ArgumentParser(
        description="Inspect and patch an XBLConfig ELF binary"
    )
    ap.add_argument("elf_file", help="Path to the XBLConfig ELF binary")
    ap.add_argument(
        "--meta-ph",
        type=int,
        default=1,
        help="Program header index that contains the XBLConfig metadata blob "
        "(default: 1)",
    )

    sub = ap.add_subparsers(dest="command")

    # ---- dump (default behaviour) ----
    p_dump = sub.add_parser("dump", help="Dump all config items to individual files")
    p_dump.add_argument(
        "--out-dir",
        default=".",
        help="Directory to write dumped files (default: current directory)",
    )

    # ---- replace ----
    p_replace = sub.add_parser(
        "replace", help="Replace the payload in a program header"
    )
    p_replace.add_argument(
        "ph_index",
        type=int,
        help="Index of the program header whose payload to replace",
    )
    p_replace.add_argument("new_file", help="Path to the new payload file")
    p_replace.add_argument("output_elf", help="Path for the patched output ELF")

    args = ap.parse_args()

    if args.command == "replace":
        replace_ph(
            elf_path=args.elf_file,
            target_ph_index=args.ph_index,
            new_file=args.new_file,
            output_file=args.output_elf,
            meta_ph_index=args.meta_ph,
        )
    else:
        # default: dump
        out_dir = getattr(args, "out_dir", ".")
        dump_from_meta(args.elf_file, out_dir, args.meta_ph)


if __name__ == "__main__":
    main()
