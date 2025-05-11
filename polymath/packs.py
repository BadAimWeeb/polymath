from polymath import utils, dmgzipext, dmgzipgen, converter, overlay1214
import hashlib
import time
import os
import tempfile

class PacksManager:
    def __init__(self, config):
        self.config = config
        self.folder = utils.get_path("storage/")
        if not os.path.exists(self.folder):
            os.mkdir(self.folder)
        self.packs_folder = self.folder + "packs/"
        self.registry = utils.SavedDict(self.folder + "registry.json")
        if not os.path.exists(self.packs_folder):
            os.mkdir(self.packs_folder)

    def register(self, pack, spigot_id, ip):
        with tempfile.TemporaryDirectory() as temp_dir:
            extpackdir = os.path.join(temp_dir, "pack")
            overlay1214dir = os.path.join(temp_dir, "overlay")
            os.mkdir(extpackdir)
            dmgzipext.extract_damaged_zip_buf(pack, extpackdir)
            converter.convert_resource_pack(extpackdir, overlay1214dir)
            overlay1214.overlay1214(extpackdir, overlay1214dir)
            dmgzipgen.create_valid_zip_from_directory(extpackdir, os.path.join(temp_dir, "pack.zip"))
            dmgzipgen.mangle_zip_file(os.path.join(temp_dir, "pack.zip"), os.path.join(temp_dir, "pack_mangled.zip"))
            with open(os.path.join(temp_dir, "pack_mangled.zip"), "rb") as f:
                pack = f.read()

        sha1 = hashlib.sha1()
        sha1.update(pack)
        id_hash = sha1.hexdigest()

        with open(os.path.join(self.packs_folder, id_hash), "wb") as pack_file:
            pack_file.write(pack)

        self.registry[id_hash] = {
            "id": spigot_id,
            "ip": ip,
            "last_download": int(time.time()),
        }

        return id_hash

    def fetch(self, id_hash):
        output = os.path.join(self.packs_folder, id_hash)
        if id_hash in self.registry and os.path.exists(output):
            self.registry[id_hash]["last_download"] = time.time()
            return output