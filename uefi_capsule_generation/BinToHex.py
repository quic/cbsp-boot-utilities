import sys

def bin_to_hex(input_file, output_file, add_prefix=False):
    try:
        with open(input_file, 'rb') as f:
            binary_data = f.read()
    except FileNotFoundError:
        print(f"Error: The file {input_file} was not found.")
        return

    # Calculate the size of the binary file and create the 32-bit header
    file_size = len(binary_data)
    header = f'{file_size:08x}'

    hex_chunks = [header]
    for i in range(0, len(binary_data), 4):
        chunk = binary_data[i:i+4]
        hex_chunk = ''.join(f'{byte:02x}' for byte in chunk)
        hex_chunks.append(hex_chunk.zfill(8))  # Ensure each chunk is 8 hex digits

    if add_prefix:
        hex_chunks = [f"0x{chunk}" for chunk in hex_chunks]

    try:
        with open(output_file, 'w') as f:
            f.write(' '.join(hex_chunks))
    except IOError:
        print(f"Error: Could not write to file {output_file}.")
        return

    print(f"Conversion successful! Hex data with header written to {output_file}")


if __name__ == "__main__":
    args = sys.argv[1:]
    add_prefix = False

    if "-x" in args:
        add_prefix = True
        args.remove("-x")

    if len(args) != 2:
        print("Usage: python bin_to_hex.py [-x] <input_file> <output_file>")
    else:
        input_file, output_file = args
        bin_to_hex(input_file, output_file, add_prefix)