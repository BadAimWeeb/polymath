import os
import zipfile
import random
import struct

def create_valid_zip_from_directory(input_dir, output_zip):
    """
    Creates a valid ZIP file from the contents of a directory.
    Central directory is assumed to be used.
    
    Args:
        input_dir (str): Path to the directory to be zipped
        output_zip (str): Path where the ZIP file will be saved
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Check if input directory exists
    if not os.path.isdir(input_dir):
        print(f"Error: Directory '{input_dir}' does not exist")
        return False
    
    try:
        # Create a new ZIP file
        with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Walk through all files and subdirectories
            for root, dirs, files in os.walk(input_dir):
                # for dir in dirs:
                #     zipf.mkdir(os.path.relpath(os.path.join(root, dir), input_dir))
                for file in files:
                    # Calculate the file's path relative to input_dir
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, input_dir)
                    # Add the file to the ZIP
                    zipf.write(file_path, arcname)
        
        print(f"Successfully created ZIP file: {output_zip}")
        return True
    
    except Exception as e:
        print(f"Error creating ZIP file: {e}")
        return False

def mangle_zip_file(zip_file_path, output_zip_path, comment=None):
    """
    Mangles/damages a ZIP file by using various bytecode techniques.
    Input is assumed to be a valid ZIP file created by create_valid_zip_from_directory.

    Args:
        zip_file_path (str): Path to the original ZIP file
        output_zip_path (str): Path where the mangled ZIP file will be saved
        comment (str): Optional comment to add to the ZIP file

    Returns:
        bool: True if successful, False otherwise
    """
    # Check if input ZIP file exists
    if not os.path.isfile(zip_file_path):
        print(f"Error: File '{zip_file_path}' does not exist")
        return False
    
    try:
        # Open the original ZIP file
        with open(zip_file_path, 'rb') as original_zip:
            data = bytearray(original_zip.read())
        
        # There are multiple tricks that should be applied here:
        # 1. Ditch all header data in the local file header including file name (zero out everything, keep only the actual data)
        # 2. Central directory file should have uncompressed size of the largest signed 32-bit integer
        # 3. Central directory file should have zeroed CRC32
        # 4. Central directory file should have disk number 65534, and end of central directory should have disk number 65535
        # 5. End of central directory header should have a central directory disk number 0, and have no central directory record at all
        # 6. Add a comment to the ZIP file if provided
        # 7. Add an extra fake local file header bytes (50 4B 03 04) at the beginning

        # We need the original data first, read it using EOCD
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

        # Find the EOCD and get central directory position
        end_of_central_dir = find_eocd(data)
        central_dir_start = int.from_bytes(data[end_of_central_dir+16:end_of_central_dir+20], byteorder='little')

        print(f"End of Central Directory at: {end_of_central_dir}")
        print(f"Central Directory starts at: {central_dir_start}")

        # Read all the central directory entries
        central_dir_entries = []
        i = central_dir_start
        while i < end_of_central_dir:
            # Read the central directory file header signature
            if data[i:i+4] != b'PK\x01\x02':
                break
            
            # Read the central directory file header fields
            i += 10 # Skip version made by, version needed to extract, general purpose bit flag
            compression_method = int.from_bytes(data[i:i+2], byteorder='little')
            i += 10 # Skip last mod file time, last mod file date, crc32
            compressed_size = int.from_bytes(data[i:i+4], byteorder='little')
            i += 8 # Skip uncompressed size
            filename_length = int.from_bytes(data[i:i+2], byteorder='little')
            extra_field_length = int.from_bytes(data[i+2:i+4], byteorder='little')
            file_comment_length = int.from_bytes(data[i+4:i+6], byteorder='little')
            i += 14 # Skip disk number start, internal file attributes, external file attributes
            file_pointer = int.from_bytes(data[i:i+4], byteorder='little')
            i += 4
            file_name = data[i:i+filename_length].decode('utf-8', errors='replace')
            i += filename_length
            i += extra_field_length + file_comment_length
            
            central_dir_entries.append({
                'compression_method': compression_method,
                'compressed_size': compressed_size,
                'file_pointer': file_pointer,
                'new_file_pointer': -1,
                'file_name': file_name
            })
        
        # Shuffle the central directory entries randomly
        random.shuffle(central_dir_entries)

        # Now, we base on the shuffled entries, and rebuild mangled ZIP file
        mangled_data = bytearray([0x50, 0x4B, 0x03, 0x04])  # ZIP local file header signature
        mangled_data_start = len(mangled_data)

        header_offset = 0

        null_header = b'PK\x03\x04' + (b'\x00' * 26)  # Local file header signature + zeroed header (26 bytes)
        null_header_len = len(null_header)
        for entry in central_dir_entries:
            # Read data from the original ZIP file
            original_file_pointer = entry['file_pointer']
            original_file_pointer += 26
            lfh_filename_len = int.from_bytes(data[original_file_pointer:original_file_pointer + 2], byteorder='little')
            lfh_extra_field_len = int.from_bytes(data[original_file_pointer + 2:original_file_pointer + 4], byteorder='little')
            original_file_pointer += 4 + lfh_filename_len + lfh_extra_field_len

            # Write the local file header
            mangled_data += null_header
            mangled_data += data[original_file_pointer:(original_file_pointer + entry['compressed_size'])]
            entry['new_file_pointer'] = header_offset
            header_offset += null_header_len + entry['compressed_size']

        central_dir_start = len(mangled_data) - mangled_data_start
        # Shuffle the central directory entries randomly, again
        random.shuffle(central_dir_entries)
        for entry in central_dir_entries:
            # Write the central directory file header
            mangled_data += b'PK\x01\x02'
            # OS = 0xDE, version made = 20.5 (205 = 0xCD), version extract = 2.0
            mangled_data += b'\xCD\xDE\x14\x00'
            # General purpose bit = 0
            mangled_data += b'\x00\x00'
            # Compression method
            mangled_data += struct.pack('<H', entry['compression_method'])
            # Last mod file time/date = 0
            mangled_data += b'\x00\x00\x00\x00'
            # CRC32 = 0
            mangled_data += b'\x00\x00\x00\x00'
            # Compressed size
            mangled_data += struct.pack('<I', entry['compressed_size'])
            # Uncompressed size = 0x7FFFFFFF
            mangled_data += struct.pack('<I', 0x7FFFFFFF)
            # Filename length
            file_name_bytes = entry['file_name'].encode('utf-8')
            mangled_data += struct.pack('<H', len(file_name_bytes))
            # Extra field length = 0
            mangled_data += b'\x00\x00'
            # File comment length = 0
            mangled_data += b'\x00\x00'
            # Disk number start = 65534
            mangled_data += b'\xFE\xFF'
            # Internal file attributes = 0
            mangled_data += b'\x00\x00'
            # External file attributes = 0
            mangled_data += b'\x00\x00\x00\x00'
            # Relative offset of local header
            mangled_data += struct.pack('<I', entry['new_file_pointer'])
            # File name
            mangled_data += file_name_bytes
            # No extra field, no file comment

        central_dir_end = len(mangled_data) - mangled_data_start
        # Write the End of Central Directory record
        mangled_data += b'PK\x05\x06'
        # Number of this disk = 65535
        mangled_data += b'\xFF\xFF'
        # Number of the disk with the start of the central directory = 0
        mangled_data += b'\x00\x00'
        # Number of central directory records on this disk = 0
        mangled_data += b'\x00\x00'
        # Total number of central directory records = 0
        mangled_data += b'\x00\x00'
        # Size of the central directory
        mangled_data += struct.pack('<I', central_dir_end - central_dir_start)
        # Offset of central directory
        mangled_data += struct.pack('<I', central_dir_start)
        comment_bytes = comment.encode('utf-8') if comment else b''
        # Comment length
        mangled_data += struct.pack('<H', len(comment_bytes))
        # Comment
        mangled_data += comment_bytes

        # Write the mangled data to the output file
        with open(output_zip_path, 'wb') as mangled_zip:
            mangled_zip.write(mangled_data)

        print(f"Successfully mangled ZIP file: {output_zip_path}")
        return True

    
    except Exception as e:
        print(f"Error mangling ZIP file: {e}")
        return False