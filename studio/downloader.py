import os
import time
import subprocess
import requests
from studio.config import DEFAULT_UA, TARGET_DIRS, WORKSPACE
from studio.manifest import load_manifest, save_manifest
from studio.cleaner import clean_url, MIN_VALID_SIZE, VALID_EXTS
from studio.civitai import parse_civitai_target, resolve_filename, mask_url, normalize_url_key
from studio.symlinks import create_helper_symlinks

def build_headers(url, civitai_key="", hf_token=""):
    """Construye las cabeceras HTTP de autenticación."""
    h = {"User-Agent": DEFAULT_UA}
    if 'civitai' in url:
        h['Referer'] = 'https://civitai.com/'
        if civitai_key:
            h['Authorization'] = f'Bearer {civitai_key}'
    if 'huggingface.co' in url and hf_token:
        h['Authorization'] = f'Bearer {hf_token}'
    return h

def download_aria2(url, filename, target_dir, civitai_key="", hf_token=""):
    """Descarga de alto rendimiento usando aria2c con 16 conexiones simultáneas."""
    os.makedirs(target_dir, exist_ok=True)
    cmd = [
        "aria2c",
        f"--user-agent={DEFAULT_UA}",
        "--continue=true",
        "--max-connection-per-server=16",
        "--split=16",
        "--min-split-size=1M",
        "--file-allocation=none",
        "--max-tries=3",
        "--retry-wait=3",
        "--summary-interval=0",
        "--console-log-level=warn",
        f"--dir={target_dir}",
        f"--out={filename}"
    ]
    for k, v in build_headers(url, civitai_key, hf_token).items():
        cmd.append(f"--header={k}: {v}")
    cmd.append(url)

    print(f"      🚀 aria2c (16 hilos en paralelo)...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    out = os.path.join(target_dir, filename)

    if res.returncode == 0 and os.path.exists(out):
        sz = os.path.getsize(out)
        if sz >= MIN_VALID_SIZE:
            print(f"      ✅ aria2c OK ({sz/1e6:.1f} MB)")
            return True
        else:
            try:
                with open(out, 'r', errors='ignore') as f:
                    first_line = f.readline()
                if "git-lfs" in first_line:
                    print(f"      ⚠️ Advertencia: El archivo descargado es solo un puntero Git-LFS ({sz} bytes).")
            except Exception:
                pass
            if os.path.exists(out):
                os.remove(out)

    print(f"      ❌ aria2c finalizó con código {res.returncode}")
    return False

def download_requests(url, filename, target_dir, civitai_key="", hf_token=""):
    """Descarga de respaldo (fallback) en streaming con barra de progreso porcentual."""
    os.makedirs(target_dir, exist_ok=True)
    print("      🔁 Fallback: Descarga estándar vía requests...")
    headers = build_headers(url, civitai_key, hf_token)
    try:
        with requests.get(url, headers=headers, allow_redirects=True, stream=True, timeout=60) as r:
            r.raise_for_status()
            out = os.path.join(target_dir, filename)
            total = int(r.headers.get('content-length', 0))
            done = 0
            with open(out, 'wb') as f:
                for chunk in r.iter_content(1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        done += len(chunk)
                        if total:
                            print(f"\r      ⬇️ Progreso: {done*100/total:5.1f}% ({done/1e6:.1f}/{total/1e6:.1f} MB)", end="", flush=True)
            print()
            if total and done != total:
                return False

            sz = os.path.getsize(out)
            if sz < MIN_VALID_SIZE:
                if os.path.exists(out):
                    os.remove(out)
                return False
            return True
    except Exception as e:
        print(f"\n      ❌ Fallo requests fallback: {e}")
        return False

def download_file(raw_url, target_dir, civitai_key="", hf_token="", force=False):
    """
    Descarga un archivo individual con resolución de URL, comprobación de manifest,
    descarga multihilo y creación de enlaces simbólicos.
    """
    os.makedirs(target_dir, exist_ok=True)
    cleaned = clean_url(raw_url)
    if not cleaned:
        return False

    url, civitai_ver = parse_civitai_target(cleaned, civitai_key)
    key = normalize_url_key(url)
    manifest = load_manifest()

    # 1. Comprobar Manifiesto
    entry = manifest.get(key)
    if entry and not force:
        full = os.path.join(entry.get("dir", target_dir), entry.get("filename", ""))
        if os.path.exists(full):
            actual = os.path.getsize(full)
            expected = entry.get("size", 0)
            if not expected or actual == expected:
                print(f"   ⏭️ SKIP (registrado en manifest): {entry['filename']} ({actual/1e6:.1f} MB)")
                create_helper_symlinks(target_dir, entry['filename'], full)
                return True

    print(f"   📥 Descargando: {mask_url(url)}")
    filename = resolve_filename(url, civitai_ver, civitai_key, hf_token)
    out = os.path.join(target_dir, filename)

    # 2. Comprobar si ya existe físicamente en el disco
    if os.path.exists(out) and not force and os.path.getsize(out) >= MIN_VALID_SIZE:
        size = os.path.getsize(out)
        print(f"   ⏭️ SKIP (archivo existente): {filename} ({size/1e6:.1f} MB)")
        manifest[key] = {"url": mask_url(url), "filename": filename, "dir": target_dir, "size": size, "ts": time.time()}
        save_manifest(manifest)
        create_helper_symlinks(target_dir, filename, out)
        return True

    # 3. Intentar aria2c y fallback requests
    ok = download_aria2(url, filename, target_dir, civitai_key, hf_token) or \
         download_requests(url, filename, target_dir, civitai_key, hf_token)

    if not ok:
        print(f"   ❌ ERROR al descargar: {mask_url(url)}")
        return False

    # Confirmar archivo en disco
    if not os.path.exists(out):
        cands = [f for f in os.listdir(target_dir) if f.lower().endswith(VALID_EXTS)]
        if cands:
            out = os.path.join(target_dir, cands[0])
            filename = os.path.basename(out)

    size = os.path.getsize(out) if os.path.exists(out) else 0
    manifest[key] = {"url": mask_url(url), "filename": filename, "dir": target_dir, "size": size, "ts": time.time()}
    save_manifest(manifest)
    print(f"   💾 Guardado correctamente: {filename} ({size/1e6:.1f} MB)")
    create_helper_symlinks(target_dir, filename, out)
    return True

def download_node(raw_url, target_dir):
    """Clona un repositorio Git de Custom Node e instala sus dependencias si existen."""
    os.makedirs(target_dir, exist_ok=True)
    node_name = raw_url.rstrip('/').split('/')[-1].replace('.git', '')
    path = os.path.join(target_dir, node_name)

    if os.path.exists(os.path.join(path, ".git")):
        print(f"   ⏭️ Nodo ya presente: {node_name}")
        return True

    print(f"   ⬇️ Clonando Custom Node: {node_name}...")
    r = subprocess.run(["git", "clone", "--recursive", raw_url, path], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"      ❌ Error al clonar {node_name}: {r.stderr.strip()[-300:]}")
        return False

    req = os.path.join(path, "requirements.txt")
    if os.path.exists(req):
        print(f"      📦 Instalando dependencias de {node_name}...")
        # Usar uv si está disponible, o pip estándar
        pip_cmd = ["uv", "pip", "install", "--system", "-r", req] if subprocess.run(["which", "uv"], capture_output=True).returncode == 0 else ["pip", "install", "-r", req]
        res = subprocess.run(pip_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"      ⚠️ Advertencia en dependencias de {node_name}:\n{res.stderr.strip()[-300:]}")
        else:
            print(f"      ✅ Dependencias instaladas con éxito.")
    return True
