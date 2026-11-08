import os
import json
from studio.config import WORKSPACE, DRIVE_WORKSPACE, TARGET_DIRS
from studio.manifest import load_manifest, save_manifest

VALID_EXTS = ('.safetensors', '.ckpt', '.pt', '.pth', '.bin', '.gguf', '.sft', '.pkl')
MIN_VALID_SIZE = 1024 * 1024  # 1 MB

def clean_url(url):
    """Higieniza URLs y corrige punteros LFS o enlaces malformados."""
    url = (url or "").strip()
    if not url:
        return ""
    if "huggingface.co" in url and "/blob/" in url:
        url = url.replace("/blob/", "/resolve/")
    
    # Redirección de punteros LFS conocidos de Kirazuri Anima hacia sus binarios funcionales
    if "motimalu/kirazuri-anima" in url:
        if "text_encoders/qwen_3_06b_base.safetensors" in url or "qwen_3_06b_base.safetensors" in url:
            return "https://huggingface.co/circlestone-labs/Anima/resolve/main/split_files/text_encoders/qwen_3_06b_base.safetensors"
        if "vae/qwen_image_vae.safetensors" in url or "qwen_image_vae.safetensors" in url:
            return "https://huggingface.co/circlestone-labs/Anima/resolve/main/split_files/vae/qwen_image_vae.safetensors"
    return url

def purgar_residuos_y_sanar_cache(verbose=True):
    """
    Elimina archivos .aria2, temporales, binarios corruptos (<1MB) y enlaces rotos.
    Sana el archivo de manifiesto para sincronizar el estado real del disco.
    """
    purged_items = []
    models_root = os.path.join(WORKSPACE, "models")
    search_dirs = [models_root] + [d for d in TARGET_DIRS.values() if os.path.exists(d)]
    
    # 1. Purgar residuos de descargas y archivos truncados
    scanned_paths = set()
    for base in search_dirs:
        if not os.path.exists(base):
            continue
        for root, _, files in os.walk(base):
            for fn in files:
                p = os.path.join(root, fn)
                if p in scanned_paths:
                    continue
                scanned_paths.add(p)
                
                if fn.endswith(('.aria2', '.tmp', '.part', '.crdownload')):
                    try:
                        os.remove(p)
                        purged_items.append(f"Archivo temporal/aria2: {fn}")
                    except Exception:
                        pass
                elif any(fn.lower().endswith(ext) for ext in VALID_EXTS):
                    if os.path.islink(p):
                        continue
                    try:
                        sz = os.path.getsize(p)
                        if sz < MIN_VALID_SIZE:
                            os.remove(p)
                            purged_items.append(f"Binario corrupto o puntero Git-LFS ({sz}B): {fn}")
                    except Exception:
                        pass

    # 2. Purgar enlaces simbólicos rotos (dangling symlinks)
    for base in search_dirs:
        if not os.path.exists(base):
            continue
        for fn in os.listdir(base):
            p = os.path.join(base, fn)
            if os.path.islink(p) and not os.path.exists(p):
                try:
                    os.unlink(p)
                    purged_items.append(f"Enlace roto (symlink): {fn}")
                except Exception:
                    pass

    # 3. Sanar Manifiesto de descargas
    manifest = load_manifest()
    keys_to_delete = []
    for k, v in list(manifest.items()):
        target = os.path.join(v.get("dir", ""), v.get("filename", ""))
        if not os.path.exists(target) or os.path.getsize(target) < MIN_VALID_SIZE:
            keys_to_delete.append(k)
            if k in manifest:
                del manifest[k]

    if keys_to_delete:
        save_manifest(manifest)
        purged_items.append(f"{len(keys_to_delete)} entrada(s) obsoleta(s) eliminada(s) del Manifiesto.")

    # 4. Sanar Cola de Descargas si existe
    queue_file = (os.path.join(DRIVE_WORKSPACE, ".download_queue.json")
                  if os.path.exists("/content/drive/MyDrive")
                  else os.path.join(WORKSPACE, ".download_queue.json"))
    if os.path.exists(queue_file):
        try:
            with open(queue_file, "r", encoding="utf-8") as f:
                saved_q = json.load(f)
            updated_q = {}
            for cat, urls in saved_q.items():
                updated_q[cat] = [clean_url(u) for u in urls if clean_url(u)]
            with open(queue_file, "w", encoding="utf-8") as f:
                json.dump(updated_q, f, indent=2)
            purged_items.append("Cola .download_queue.json saneada.")
        except Exception:
            pass

    if verbose:
        if purged_items:
            print("🧹 [Auto-Purga] Se limpiaron los siguientes residuos del entorno:")
            for item in purged_items:
                print(f"   ↳ 🗑️ {item}")
        else:
            print("✨ [Auto-Purga] El entorno y la caché están limpios de residuos.")
    return len(purged_items)
