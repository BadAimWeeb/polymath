import os
import zlib

def extract_damaged_zip_buf(damaged_zip_buf, destination_path):
    file_data = damaged_zip_buf

    # Function to find the End of Central Directory (EOCD)
    def find_eocd(data):
        # Try the simplest case first: no comment, EOCD is at the last 22 bytes
        if len(data) >= 22 and data[-22:-18] == b'PK\x05\x06':
            return len(data) - 22
            
        # Search the last ~64KB for the EOCD signature
        search_start = max(0, len(data) - 65536 - 22)
            
        for i in range(len(data) - 4, search_start, -1):
            if data[i:i+4] == b'PK\x05\x06':
                # Verify this is a valid EOCD
                if i + 20 <= len(data):
                    cd_offset = int.from_bytes(data[i+16:i+20], byteorder='little')
                    if cd_offset < len(data) and data[cd_offset:cd_offset+4] == b'PK\x01\x02':
                        return i
            
        raise ValueError("Could not find EOCD in the ZIP file")
    
    end_of_central_dir = find_eocd(file_data)
    central_dir_len = int.from_bytes(file_data[end_of_central_dir+12:end_of_central_dir+16], byteorder='little')
    central_dir_pointer = int.from_bytes(file_data[end_of_central_dir+16:end_of_central_dir+20], byteorder='little')
    
    pointer = end_of_central_dir - central_dir_len
    shdiff = central_dir_pointer - pointer

    while pointer < end_of_central_dir:
        # Read the central directory file header
        if file_data[pointer:pointer+4] != b'PK\x01\x02':
            break
        
        # Read the central directory file header fields
        pointer += 10 # Skip version made by, version needed to extract, general purpose bit flag
        compression_method = int.from_bytes(file_data[pointer:pointer+2], byteorder='little')
        pointer += 10 # Skip last mod file time, last mod file date, crc32
        compressed_size = int.from_bytes(file_data[pointer:pointer+4], byteorder='little')
        pointer += 8 # Skip uncompressed size
        filename_length = int.from_bytes(file_data[pointer:pointer+2], byteorder='little')
        extra_field_length = int.from_bytes(file_data[pointer+2:pointer+4], byteorder='little')
        file_comment_length = int.from_bytes(file_data[pointer+4:pointer+6], byteorder='little')
        pointer += 14 # Skip disk number start, internal file attributes, external file attributes
        file_pointer = int.from_bytes(file_data[pointer:pointer+4], byteorder='little')
        pointer += 4
        file_name = file_data[pointer:pointer+filename_length].decode('utf-8', errors='replace')
        pointer += filename_length
        pointer += extra_field_length + file_comment_length

        # Read data from the original ZIP file
        file_pointer -= shdiff
        file_pointer += 26
        lfh_filename_len = int.from_bytes(file_data[file_pointer:file_pointer + 2], byteorder='little')
        lfh_extra_field_len = int.from_bytes(file_data[file_pointer + 2:file_pointer + 4], byteorder='little')
        file_pointer += 4 + lfh_filename_len + lfh_extra_field_len

        f = file_data[file_pointer:file_pointer + compressed_size]
        if compression_method == 0:
            # No compression
            pass
        elif compression_method == 8:
            # Decompress the data using zlib
            f = zlib.decompress(f, -15)
        else:
            print("unknown compression method " + str(compression_method))

        # Create directory structure and write file
        output_path = os.path.join(destination_path, file_name)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'wb') as out_file:
            out_file.write(f)


def extract_damaged_zip(damaged_zip_path, destination_path):
    """
    Extract files from a damaged zip file.
    
    Args:
        damaged_zip_path (str): Path to the damaged zip file
        destination_path (str): Directory to extract files to
    """
    with open(damaged_zip_path, 'rb') as f:
        file_data = f.read()
    
    return extract_damaged_zip_buf(file_data, destination_path)
