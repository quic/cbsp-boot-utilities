#!/usr/bin/env python3
# Copyright (c) Qualcomm Innovation Center, Inc. All rights reserved.
# SPDX-License-Identifier: BSD-3-Clause-Clear

import re
import struct
import sys

import libfdt


def encode_value(value: str) -> bytes:
    """
    Encode a value for FDT:
    - @file:<path>  -> binary split into 32-bit big-endian words
    - @list:<path>  -> text file with hex/decimal ints, each -> 32-bit word
    - single integer -> 4-byte big-endian
    - list of integers -> array of 4-byte big-endian
    - otherwise -> UTF-8 string
    """
    value = value.strip()

    # Binary from file -> 32-bit words
    if value.startswith("@file:"):
        file_path = value[6:]
        with open(file_path, "rb") as f:
            data = f.read()
        if len(data) % 4 != 0:
            data += b"\x00" * (4 - (len(data) % 4))
        return b"".join(
            struct.pack(">I", struct.unpack(">I", data[i : i + 4])[0])
            for i in range(0, len(data), 4)
        )

    # Integer list from file
    if value.startswith("@list:"):
        file_path = value[6:]
        with open(file_path, "r") as f:
            text = f.read()
        # Split on whitespace or commas
        parts = re.split(r"[\s,]+", text.strip())
        return b"".join(struct.pack(">I", int(p, 16)) for p in parts if p)

    # Single integer
    int_pattern = re.compile(r"^-?(0x[0-9a-fA-F]+|\d+)$")
    int_list_pattern = re.compile(
        r"^(-?(0x[0-9a-fA-F]+|\d+)[ ,]+)+(-?(0x[0-9a-fA-F]+|\d+))$"
    )

    if int_pattern.match(value):
        return struct.pack(">I", int(value, 0))
    elif int_list_pattern.match(value + " "):
        parts = re.split(r"[ ,]+", value.strip())
        return b"".join(struct.pack(">I", int(p, 0)) for p in parts if p)
    else:
        # Default: UTF-8 string
        return value.encode("utf-8")


def set_dtb_property(
    dtb_path: str,
    node_path: str,
    prop_name: str,
    value: str,
    out_path: str,
    extra_space: int = 1024,
):
    """
    Set or add a property in a DTB, automatically resizing if needed.
    """
    # Load DTB from file
    with open(dtb_path, "rb") as f:
        dtb_data = f.read()

    fdt_obj = libfdt.Fdt(dtb_data)

    try:
        node_off = fdt_obj.path_offset(node_path)
    except libfdt.FdtException:
        raise ValueError(f"Node path '{node_path}' not found in DTB")

    value_bytes = encode_value(value)

    try:
        fdt_obj.setprop(node_off, prop_name, value_bytes)
    except libfdt.FdtException as e:
        # Handle not enough space error
        if hasattr(e, "err") and e.err == -libfdt.FDT_ERR_NOSPACE:
            print("[!] Not enough space, resizing DTB...")
            # Resize DTB buffer to fit new property
            fdt_obj.resize(
                len(fdt_obj.as_bytearray()) + max(len(value_bytes), extra_space)
            )
            # Retry setting the property
            fdt_obj.setprop(node_off, prop_name, value_bytes)
        else:
            raise

    # Save updated DTB
    with open(out_path, "wb") as f:
        f.write(fdt_obj.as_bytearray())

    print(f"[+] Updated '{prop_name}' at '{node_path}', written to {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 6:
        print(
            f"Usage: {sys.argv[0]} <input.dtb> <node_path> <property> <value|@file:path|@list:path> <output.dtb>"
        )
        sys.exit(1)

    input_dtb, node_path, prop_name, value, output_dtb = sys.argv[1:]
    set_dtb_property(input_dtb, node_path, prop_name, value, output_dtb)
