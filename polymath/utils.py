import os
import json
import collections.abc


def get_path(name):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), name)


class SavedDict(collections.abc.MutableMapping):
    def __init__(self, file_name):
        self.file = get_path(file_name)

        if not os.path.isfile(self.file):
            self.store = dict()
        else:
            with open(self.file, "r") as json_file:
                self.store = json.load(json_file)
                if type(self.store) is not dict:
                    raise ValueError()

    def write(self):
        with open(self.file, "w") as outfile:
            json.dump(self.store, outfile)

    def __getitem__(self, key):
        return self.store[self._keytransform(key)]

    def __setitem__(self, key, value):
        self.store[self._keytransform(key)] = value
        self.write()

    def __delitem__(self, key):
        del self.store[self._keytransform(key)]
        self.write()

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def _keytransform(self, key):
        return str(key)

def remove_empty_dirs(target_directory):
    """
    Recursively removes empty subdirectories within a target directory.

    Args:
        target_directory (str): The path to the directory to scan.

    Returns:
        int: The number of directories removed.
             Returns -1 if the target_directory is not a valid directory.
    """
    if not os.path.isdir(target_directory):
        # Indicate an error condition, e.g., by returning -1 or raising an exception
        # Returning -1 here for simplicity
        print(f"Error: Provided path '{target_directory}' is not a valid directory.")
        return -1

    removed_count = 0
    # Walk the directory tree from bottom-up
    # topdown=False ensures subdirectories are processed before parent directories
    for dirpath, dirnames, filenames in os.walk(target_directory, topdown=False):
        # Check if the current directory is empty
        # It's empty if it contains no files and no subdirectories
        try:
            if not os.listdir(dirpath):
                # Check if we are trying to remove the root target_directory itself
                # Avoid removing the root if it becomes empty unless specifically desired
                # This implementation will attempt to remove it if it becomes empty
                # if dirpath == target_directory:
                #     continue # Optional: uncomment to prevent removing the root directory

                try:
                    os.rmdir(dirpath)
                    removed_count += 1
                except OSError as e:
                    # Handle potential errors like permission denied
                    # Log or print error if needed in the calling application
                    print(f"Could not remove directory '{dirpath}': {e}")
                    # Optionally re-raise or handle differently
            # else:
            #     # Directory is not empty
            #     pass
        except FileNotFoundError:
            # This can happen if a directory was removed by a previous iteration
            # (e.g., a parent of an already removed dir) - generally safe to ignore
            pass
        except Exception as e:
            # Catch unexpected errors during processing
            print(f"An unexpected error occurred while processing '{dirpath}': {e}")
            # Optionally re-raise or handle differently

    return removed_count
