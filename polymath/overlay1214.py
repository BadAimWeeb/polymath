import os
import shutil
import json

def overlay1214(target_dir, overlay_1214):
    """
    Add an overlay for 1.21.4+ format to an extracted resource pack.

    Args:
        target_dir (str): The path to the extracted resource pack directory.
        overlay_1214 (str): The path for the directory to be used as overlay.
    """

    # Check if the target directory exists
    if not os.path.isdir(target_dir):
        raise FileNotFoundError(f"Target directory '{target_dir}' does not exist.")

    # Check if the overlay file exists
    if not os.path.isdir(overlay_1214):
        raise FileNotFoundError(f"Overlay directory '{overlay_1214}' does not exist.")
    
    mcmeta_path = os.path.join(target_dir, "pack.mcmeta")
    if not os.path.isfile(mcmeta_path):
        raise FileNotFoundError(f"pack.mcmeta file '{mcmeta_path}' does not exist.")

    os.mkdir(os.path.join(target_dir, "overlay_1_21_4"))
    shutil.copytree(overlay_1214, os.path.join(target_dir, "overlay_1_21_4"), dirs_exist_ok=True)

    with open(mcmeta_path, "r+") as mcmeta_file:
        mcmeta_data = json.load(mcmeta_file)

        if mcmeta_data.get("pack") is None:
            raise ValueError("pack key not found in pack.mcmeta")
        
        if mcmeta_data["pack"].get("pack_format") is None:
            raise ValueError("pack_format key not found in pack.mcmeta")
        
        mcmeta_data["pack"]["supported_formats"] = [mcmeta_data["pack"]["pack_format"], 99]
        if mcmeta_data["pack"]["pack_format"] < 16:
            mcmeta_data["pack"]["pack_format"] = 16

        if mcmeta_data.get("overlays") is None:
            mcmeta_data["overlays"] = {}

        if mcmeta_data["overlays"].get("entries") is None:
            mcmeta_data["overlays"]["entries"] = []

        mcmeta_data["overlays"]["entries"].append({
            "directory": "overlay_1_21_4",
            "formats": [44, 99]
        })

        mcmeta_file.seek(0)
        json.dump(mcmeta_data, mcmeta_file, indent=4)
        mcmeta_file.truncate()