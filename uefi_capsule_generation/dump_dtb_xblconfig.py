#!/usr/bin/env python3
# Copyright (c) Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause-Clear

import argparse
import hashlib
import magic
import struct
import sys

from elftools.elf.elffile import ELFFile

# used by libmagic for DTB file detection
DTB_MAGICS = { 0xd00dfeed, 0xedfe0dd0, 0xedfe0dd0, 0xedfe0dd0 }

def is_device_tree_blob(data: bytes) -> bool:
    if len(data) < 4:
        return False
    magic = int.from_bytes(data[:4], byteorder="big")
    return magic in DTB_MAGICS

def parse_elf(filename, dump_dtb=False):
    with open(filename, 'rb') as f:
        elf = ELFFile(f)

        print("ELF Header:")
        print(f"  Class: {elf.elfclass}-bit")
        print(f"  Data encoding: {elf.little_endian and 'Little endian' or 'Big endian'}")
        print(f"  Entry point: 0x{elf.header.e_entry:x}")
        print(f"  Number of sections: {elf.num_sections()}")
        print(f"  Number of program headers: {elf.num_segments()}")
        print()

        print("Program Headers:")
        for i, segment in enumerate(elf.iter_segments()):
            print(f"  Segment #{i}")
            print(f"    Type: {segment['p_type']}")
            print(f"    File Offset: 0x{segment['p_offset']:x}")
            print(f"    Virtual Address: 0x{segment['p_vaddr']:x}")
            print(f"    File Size: {segment['p_filesz']} bytes")
            print(f"    Memory Size: {segment['p_memsz']} bytes")

            if segment['p_filesz'] > 0:
                data = segment.data()
                if data:
                    try:
                        m = magic.Magic(mime=False)
                        filetype = m.from_buffer(data)
                        print(f"    Detected content type: {filetype}")

                        if dump_dtb and is_device_tree_blob(data):
                            outname = f"{filename}.segment{i}.dtb"
                            with open(outname, "wb") as out:
                                out.write(data)
                            print(f"    >>> Extracted Device Tree Blob to {outname}")
                    except Exception as e:
                        print(f"    [!] Could not detect file type: {e}")
            print()

def replace_dtb(filename, segment_index, new_dtb_file, output_file):
    with open(filename, "rb") as f:
        orig_data = bytearray(f.read())
        elf = ELFFile(f)
        segments = list(elf.iter_segments())
        segment = segments[segment_index]

        phoff   = elf.header['e_phoff']
        phentsz = elf.header['e_phentsize']
        shoff   = elf.header['e_shoff']
        is_64   = elf.elfclass == 64
        endian  = "<" if elf.little_endian else ">"

        # Load old and new DTB
        old_dtb = segment.data()
        with open(new_dtb_file, "rb") as nf:
            new_dtb = nf.read()

        offset = segment['p_offset']
        old_size = segment['p_filesz']
        new_size = len(new_dtb)
        grow_size = new_size - old_size

        print(f"[i] Replacing segment #{segment_index}: old size {old_size}, new size {new_size}")

        # Compute SHA-384 hashes
        old_hash = hashlib.sha384(old_dtb).digest()
        new_hash = hashlib.sha384(new_dtb).digest()
        print(f"[i] Old DTB SHA-384: {old_hash.hex()}")
        print(f"[i] New DTB SHA-384: {new_hash.hex()}")

        # Replace DTB in file
        if grow_size <= 0:
            orig_data[offset:offset+new_size] = new_dtb
            if new_size < old_size:
                orig_data[offset+new_size:offset+old_size] = b"\x00" * (old_size-new_size)
        else:
            # Grow file safely
            tail = orig_data[offset+old_size:]
            orig_data[offset:offset+new_size] = new_dtb
            orig_data[offset+new_size:] = tail
            orig_data.extend(b"\x00" * grow_size)

            # Fix offsets in later program headers
            for i, seg in enumerate(segments):
                if seg['p_offset'] > offset:
                    ph_offset = phoff + i * phentsz
                    if is_64:
                        orig_data[ph_offset + 0x08:ph_offset + 0x10] = struct.pack(endian + "Q", 
                                                                                   seg['p_offset'] +
                                                                                   grow_size)
                    else:
                        orig_data[ph_offset + 0x04:ph_offset + 0x08] = struct.pack(endian+"I", 
                                                                                   seg['p_offset'] +
                                                                                   grow_size)

            # Fix offsets in later section headers
            for i, sec in enumerate(elf.iter_sections()):
                if sec['sh_offset'] > offset:
                    sh_offset = shoff + i * elf.header['e_shentsize']
                    if is_64:
                        orig_data[sh_offset+0x18:sh_offset+0x20] = struct.pack(endian+"Q",
                                                                               sec['sh_offset'] +
                                                                               grow_size)
                    else:
                        orig_data[sh_offset+0x10:sh_offset+0x14] = struct.pack(endian+"I",
                                                                               sec['sh_offset'] +
                                                                               grow_size)

        # Update p_filesz & p_memsz
        ph_offset = phoff + segment_index * phentsz
        if is_64:
            orig_data[ph_offset+0x20:ph_offset+0x28] = struct.pack(endian+"Q", new_size)
            orig_data[ph_offset+0x28:ph_offset+0x30] = struct.pack(endian+"Q", new_size)
        else:
            orig_data[ph_offset+0x10:ph_offset+0x14] = struct.pack(endian+"I", new_size)
            orig_data[ph_offset+0x14:ph_offset+0x18] = struct.pack(endian+"I", new_size)

        # Replace old hash with new hash. We really don't care about where exactly it's stored,
        # we just look for the old value in binary form and replace it
        pos = bytes(orig_data).find(old_hash)
        if pos != -1:
            print(f"[i] Found old DTB hash at offset 0x{pos:x}, replacing with new hash")
            orig_data[pos:pos+len(new_hash)] = new_hash
        else:
            print("[!] Old DTB hash not found in ELF binary")

        # Replace old dtb size. Same search approach as we do for the hash
        old_size_le = struct.pack("<I", old_size)
        new_size_le = struct.pack("<I", new_size)

        replaced = 0
        i = 0
        while True:
            pos = bytes(orig_data).find(old_size_le, i)
            if pos == -1:
                break
            orig_data[pos:pos+4] = new_size_le
            print(f"[i] Replaced old DTB size (LE) at 0x{pos:x}")
            replaced += 1
            i = pos + 4

        if replaced == 0:
            print("[!] No stored DTB size value found")
        else:
            print(f"[+] Updated {replaced} DTB size occurrence(s)")

    with open(output_file, "wb") as out:
        out.write(orig_data)

    print(f"[+] Replaced DTB in segment #{segment_index}, written new ELF: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ELF parser with DTB replace")
    parser.add_argument("elf_file", help="Path to ELF binary")
    parser.add_argument("--dump-dtb", action="store_true",
                        help="Extract DTB blobs from program headers into separate files")
    parser.add_argument("--replace-dtb", nargs=3, metavar=("SEG_INDEX", "NEW_DTB", "OUTPUT_ELF"),
                        help="Replace DTB in segment SEG_INDEX with NEW_DTB, save to OUTPUT_ELF")
    args = parser.parse_args()

    if args.replace_dtb:
        seg_index, new_dtb, output_elf = args.replace_dtb
        replace_dtb(args.elf_file, int(seg_index), new_dtb, output_elf)
    else:
        parse_elf(args.elf_file, dump_dtb=args.dump_dtb)
