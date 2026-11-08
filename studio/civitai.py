import re
import os
import urllib.parse
import requests
from studio.config import DEFAULT_UA

VALID_EXTENSIONS = ('.safetensors', '.ckpt', '.pt', '.pth', '.bin', '.gguf', '.sft', '.pkl')

def mask_url(url):
    """Oculta tokens sensibles en las URLs para logs limpios."""
    return re.sub(r'([?&]token=)[^&]+', r'\1***', url or "")

def normalize_url_key(url):
    """Genera una clave única normalizada para el manifiesto."""
    u = re.sub(r'[?&]token=[^&]+', '', url or "").rstrip('?&')
    m = re.search(r'civitai\.(?:com|red)/api/download/models/(\d+)', u)
    if m:
        fm = re.search(r'fileId=(\d+)', u)
        return f"civitai:{m.group(1)}:{fm.group(1) if fm else 'default'}"
    return u

def parse_civitai_target(url, civitai_key=""):
    """
    Interpreta enlaces de Civitai (páginas de modelo, versiones o enlaces de descarga)
    y retorna la URL de descarga directa junto con el version_id.
    """
    version_id = None
    direct_url = url
    if "civitai.com" in url or "civitai.red" in url:
        m_dl = re.search(r'civitai\.(?:com|red)/api/download/models/(\d+)', url)
        if m_dl:
            version_id = m_dl.group(1)
        else:
            parsed = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed.query)
            if 'modelVersionId' in qs:
                version_id = qs['modelVersionId'][0]
                file_param = f"?fileId={qs['fileId'][0]}" if 'fileId' in qs else ''
                direct_url = f"https://civitai.com/api/download/models/{version_id}{file_param}"
            else:
                m_model = re.search(r'/models/(\d+)', parsed.path)
                if m_model:
                    model_id = m_model.group(1)
                    try:
                        headers = {"User-Agent": DEFAULT_UA}
                        if civitai_key:
                            headers["Authorization"] = f"Bearer {civitai_key}"
                        r = requests.get(f"https://civitai.com/api/v1/models/{model_id}", headers=headers, timeout=12)
                        if r.status_code == 200:
                            data = r.json()
                            versions = data.get("modelVersions", [])
                            if versions:
                                version_id = str(versions[0]["id"])
                                direct_url = f"https://civitai.com/api/download/models/{version_id}"
                    except Exception as e:
                        print(f"      ⚠️ Error al consultar Civitai Model API: {e}")

        if civitai_key and "token=" not in direct_url:
            sep = "&" if "?" in direct_url else "?"
            direct_url = f"{direct_url}{sep}token={civitai_key}"

    return direct_url, version_id

def extract_filename_from_headers(headers, final_url):
    """Extrae el nombre de archivo desde el header Content-Disposition."""
    cd = headers.get('content-disposition', '')
    if cd:
        m = re.findall(r'filename\*?=(?:UTF-8\'\')?"?([^;\r\n"]+)"?', cd)
        if m:
            return urllib.parse.unquote(m[0].strip())
    path = urllib.parse.urlparse(final_url).path
    return os.path.basename(path) or None

def filename_from_civitai_api(version_id, civitai_key=""):
    """Consulta la API de Civitai para obtener el nombre oficial del archivo primario."""
    if not version_id:
        return None
    try:
        headers = {"User-Agent": DEFAULT_UA}
        if civitai_key:
            headers["Authorization"] = f"Bearer {civitai_key}"
        r = requests.get(f"https://civitai.com/api/v1/model-versions/{version_id}", headers=headers, timeout=15)
        if r.status_code == 200:
            files = r.json().get('files', [])
            if files:
                primary = next((f for f in files if f.get('primary')), files[0])
                name = primary.get('name')
                if name:
                    return name
    except Exception as e:
        print(f"      ⚠️ Civitai Version API error: {e}")
    return None

def resolve_filename(url, civitai_ver_id=None, civitai_key="", hf_token=""):
    """
    Determina de manera robusta el nombre de archivo a través de:
    1. API de Civitai (si aplica)
    2. URL limpia
    3. Solicitud HEAD HTTP
    4. GET Stream parcial
    """
    if civitai_ver_id:
        fn = filename_from_civitai_api(civitai_ver_id, civitai_key)
        if fn and any(fn.lower().endswith(ext) for ext in VALID_EXTENSIONS):
            print(f"      ✅ Nombre resuelto vía Civitai API: {fn}")
            return fn

    path = urllib.parse.urlparse(url).path
    base = os.path.basename(path)
    if base and any(base.lower().endswith(ext) for ext in VALID_EXTENSIONS):
        fn = urllib.parse.unquote(base)
        print(f"      ✅ Nombre extraído de URL: {fn}")
        return fn

    headers = {"User-Agent": DEFAULT_UA}
    if 'civitai' in url:
        headers['Referer'] = 'https://civitai.com/'
        if civitai_key:
            headers['Authorization'] = f'Bearer {civitai_key}'
    if 'huggingface.co' in url and hf_token:
        headers['Authorization'] = f'Bearer {hf_token}'

    try:
        r = requests.head(url, headers=headers, allow_redirects=True, timeout=12)
        if r.status_code in (200, 302):
            fn = extract_filename_from_headers(r.headers, r.url)
            if fn and any(fn.lower().endswith(ext) for ext in VALID_EXTENSIONS):
                print(f"      ✅ Nombre resuelto vía HEAD: {fn}")
                return fn
    except Exception:
        pass

    try:
        with requests.get(url, headers=headers, allow_redirects=True, stream=True, timeout=12) as r:
            if r.status_code == 200:
                fn = extract_filename_from_headers(r.headers, r.url)
                if fn and any(fn.lower().endswith(ext) for ext in VALID_EXTENSIONS):
                    print(f"      ✅ Nombre resuelto vía GET Stream: {fn}")
                    return fn
    except Exception:
        pass

    if base:
        return urllib.parse.unquote(base)
    return "downloaded_model.safetensors"
