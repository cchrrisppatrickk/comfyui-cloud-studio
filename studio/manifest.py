import os
import json
from studio.config import WORKSPACE, DRIVE_WORKSPACE

def get_manifest_path():
    drive_manifest = os.path.join(DRIVE_WORKSPACE, ".download_manifest.json")
    local_manifest = os.path.join(WORKSPACE, ".download_manifest.json")
    if os.path.exists("/content/drive/MyDrive"):
        return drive_manifest
    return local_manifest

def load_manifest():
    path = get_manifest_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_manifest(manifest_dict):
    path = get_manifest_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(manifest_dict, f, indent=2)
        os.replace(tmp, path)
    except Exception:
        pass
