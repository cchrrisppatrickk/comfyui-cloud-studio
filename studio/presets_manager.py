import os
import json
from pathlib import Path
from studio.config import DRIVE_WORKSPACE, DRIVE_PRESETS_DIR

# Directorio raíz de presets oficiales dentro del repositorio
REPO_DIR = Path(__file__).resolve().parent.parent
OFFICIAL_PRESETS_DIR = REPO_DIR / "presets"

def load_official_presets():
    """Carga todos los archivos .json dentro de la carpeta presets/ del repositorio."""
    presets = {}
    if not OFFICIAL_PRESETS_DIR.exists():
        return presets

    for json_file in OFFICIAL_PRESETS_DIR.rglob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                preset_id = data.get("id") or json_file.stem
                if "title" not in data:
                    data["title"] = preset_id
                data["_source"] = "official"
                data["_file_path"] = str(json_file)
                presets[preset_id] = data
        except Exception as e:
            print(f"⚠️ Error cargando preset oficial {json_file}: {e}")
    return presets

def load_drive_presets():
    """Carga presets personalizados guardados en Google Drive."""
    presets = {}

    # 1. Directorio de presets individuales en Drive
    if os.path.exists(DRIVE_PRESETS_DIR):
        for json_file in Path(DRIVE_PRESETS_DIR).glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    preset_id = data.get("id") or json_file.stem
                    data["_source"] = "drive"
                    data["_file_path"] = str(json_file)
                    presets[preset_id] = data
            except Exception as e:
                print(f"⚠️ Error cargando preset de Drive {json_file}: {e}")

    # 2. Archivo legacy presets.json en Drive
    legacy_file = os.path.join(DRIVE_WORKSPACE, "presets.json")
    if os.path.exists(legacy_file):
        try:
            with open(legacy_file, "r", encoding="utf-8") as f:
                legacy_dict = json.load(f)
                for k, v in legacy_dict.items():
                    if k not in presets:
                        v["_source"] = "drive_legacy"
                        presets[k] = v
        except Exception:
            pass

    return presets

def get_all_presets():
    """
    Combina presets oficiales y personalizados de Drive.
    Los oficiales tienen prioridad o pueden convivir de forma ordenada.
    """
    official = load_official_presets()
    drive = load_drive_presets()
    
    # Fusionar: Los de drive complementan o sobreescriben si tienen el mismo ID
    combined = {**drive, **official}
    return combined

def save_custom_preset(preset_id, title, description, models_dict, custom_nodes_list):
    """Guarda un nuevo preset como archivo JSON atómico en Google Drive."""
    target_dir = DRIVE_PRESETS_DIR if os.path.exists("/content/drive/MyDrive") else str(OFFICIAL_PRESETS_DIR / "custom")
    os.makedirs(target_dir, exist_ok=True)
    
    clean_id = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in preset_id.strip())
    filepath = os.path.join(target_dir, f"{clean_id}.json")
    
    data = {
        "id": clean_id,
        "title": title or clean_id,
        "description": description or "Preset personalizado de usuario",
        "models": models_dict,
        "custom_nodes": custom_nodes_list
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Preset guardado con éxito en: {filepath}")
    return filepath
