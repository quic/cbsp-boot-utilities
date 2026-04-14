def bin_to_hex(input_file, output_file):
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

    try:
        with open(output_file, 'w') as f:
            f.write(' '.join(hex_chunks))
    except IOError:
        print(f"Error: Could not write to file {output_file}.")
        return

    print(f"Conversion successful! Hex data with header written to {output_file}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python bin_to_hex.py <input_file> <output_file>")
    else:
        bin_to_hex(sys.argv[1], sys.argv[2])