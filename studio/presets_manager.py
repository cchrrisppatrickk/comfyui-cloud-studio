import os
import json
from pathlib import Path
from collections import defaultdict
from studio.config import DRIVE_WORKSPACE, DRIVE_PRESETS_DIR

# Directorio raíz de presets oficiales dentro del repositorio
REPO_DIR = Path(__file__).resolve().parent.parent
OFFICIAL_PRESETS_DIR = REPO_DIR / "presets"

def _normalize_preset_data(data, default_id, source="official", filepath=""):
    """Garantiza que el preset contenga todos los campos de metadatos esperados."""
    preset_id = data.get("id") or default_id
    data["id"] = preset_id
    if "title" not in data:
        data["title"] = preset_id
    if "family" not in data:
        # Intentar inferir la familia por categoría o nombre
        data["family"] = data.get("category", "Otros / Comunidad")
    if "version" not in data:
        data["version"] = "v1.0"
    if "author" not in data:
        data["author"] = "Comunidad"
    if "source_url" not in data:
        data["source_url"] = ""
    if "source_type" not in data:
        data["source_type"] = "Civitai / Hugging Face" if "civitai" in data.get("source_url", "").lower() else "Hugging Face"
    if "description" not in data:
        data["description"] = "Preset configurado para ComfyUI."
    if "recommended_vram" not in data:
        data["recommended_vram"] = "Estándar (12GB+)"
    if "parameters" not in data:
        data["parameters"] = {}
    if "models" not in data:
        data["models"] = {}
    if "custom_nodes" not in data:
        data["custom_nodes"] = []

    data["_source"] = source
    data["_file_path"] = str(filepath)
    return data

def load_official_presets():
    """Carga todos los archivos .json dentro de la carpeta presets/ del repositorio."""
    presets = {}
    if not OFFICIAL_PRESETS_DIR.exists():
        return presets

    for json_file in OFFICIAL_PRESETS_DIR.rglob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                data = _normalize_preset_data(raw_data, json_file.stem, "official", json_file)
                presets[data["id"]] = data
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
                    raw_data = json.load(f)
                    data = _normalize_preset_data(raw_data, json_file.stem, "drive", json_file)
                    presets[data["id"]] = data
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
                        data = _normalize_preset_data(v, k, "drive_legacy", legacy_file)
                        presets[k] = data
        except Exception:
            pass

    return presets

def get_all_presets():
    """
    Combina presets oficiales y personalizados de Drive.
    """
    official = load_official_presets()
    drive = load_drive_presets()
    return {**drive, **official}

def get_presets_by_family():
    """
    Agrupa los presets por Familia / Modelo General para selectores en dos niveles.
    Retorna un diccionario: { "🌸 Anima": { "id1": preset1, ... }, ... }
    """
    all_presets = get_all_presets()
    families = defaultdict(dict)
    for pid, p in all_presets.items():
        fam = p.get("family", "Otros / Comunidad")
        families[fam][pid] = p
    return dict(families)

def save_custom_preset(preset_id, title, description, models_dict, custom_nodes_list, family="Personalizados", author="Usuario", source_url=""):
    """Guarda un nuevo preset como archivo JSON atómico en Google Drive."""
    target_dir = DRIVE_PRESETS_DIR if os.path.exists("/content/drive/MyDrive") else str(OFFICIAL_PRESETS_DIR / "custom")
    os.makedirs(target_dir, exist_ok=True)
    
    clean_id = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in preset_id.strip())
    filepath = os.path.join(target_dir, f"{clean_id}.json")
    
    data = {
        "id": clean_id,
        "family": family,
        "title": title or clean_id,
        "version": "Custom v1.0",
        "author": author,
        "source_url": source_url,
        "description": description or "Preset personalizado guardado por el usuario",
        "recommended_vram": "12GB+",
        "models": models_dict,
        "custom_nodes": custom_nodes_list
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Preset guardado con éxito en: {filepath}")
    return filepath
