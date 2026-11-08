# ⚡ ComfyUI Cloud Studio - Smart Presets & Downloader Engine

Motor modular de aprovisionamiento y gestor inteligente de descargas para **ComfyUI en Google Colab / Cloud GPU**. Permite desacoplar la configuración de modelos, LoRAs y custom nodes del notebook de Colab mediante archivos JSON atómicos y versionados en GitHub.

---

## 🌟 Características Principales

- **Catálogo Dinámico de Presets:** Nuevos modelos y configuraciones se añaden creando un archivo `.json` sin tocar el notebook.
- **UI Profesional en Colab (`ipywidgets`):** Pestañas interactivas para elegir presets, pegar listas masivas de LoRAs y gestionar tokens.
- **Descargas Ultrarrápidas:** Integración multihilo con `aria2c` (16 conexiones paralelas) y fallback transparente a `requests`.
- **Resolutor Inteligente de Civitai & Hugging Face:** Soporte automático para URLs de versiones, API Keys privadas y modelos protegidos (*gated*).
- **Control de Caché y Manifiesto:** Evita descargas duplicadas comprobando tamaños y registros históricos.
- **Soporte Híbrido:** Lee los presets oficiales del repositorio y presets privados guardados en Google Drive (`/content/drive/MyDrive/ComfyUI/custom_presets`).

---

## 📁 Estructura del Proyecto

```text
comfyui-cloud-studio/
├── presets/                          # 📁 Catálogo oficial de setups JSON
│   ├── anime/
│   │   ├── anima_kirazuri_v4_int8.json
│   │   └── anima_kirazuri_v4_bf16.json
│   ├── qwen/
│   │   └── qwen_image_2_1.json
│   ├── flux/
│   └── sdxl/
├── studio/                           # 📁 Motor Python desacoplado
│   ├── config.py                     # Rutas y constantes de ComfyUI
│   ├── downloader.py                 # Descarga aria2c + requests con 16 hilos
│   ├── civitai.py                    # Resolutor de versiones y nombres
│   ├── symlinks.py                   # Enlaces simbólicos de compatibilidad
│   ├── manifest.py                   # Registro de archivos ya descargados
│   ├── cleaner.py                    # Purga preventiva de archivos residuales
│   ├── presets_manager.py            # Carga y fusión de presets (Git + Drive)
│   └── ui.py                         # Interfaz gráfica interactiva
├── notebooks/
│   └── ComfyUI_Cloud_Studio.ipynb   # Notebook optimizado para Colab (Celda 2 ultraligera)
├── main.py                           # CLI para automatización headless
└── requirements.txt
```

---

## 🚀 Uso en Google Colab

En el notebook `ComfyUI_Cloud_Studio.ipynb`, la Celda 2 ahora es ultraligera:

```python
#@title 2. Workflow Presets Catalog & Smart Downloader
import os, sys

REPO_URL = "https://github.com/cchrrisppatrickk/comfyui-cloud-studio.git"
REPO_DIR = "/content/comfyui-cloud-studio"

if not os.path.exists(REPO_DIR):
    !git clone --depth 1 $REPO_URL $REPO_DIR
else:
    !git -C $REPO_DIR pull

if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from studio.ui import render_downloader_ui
render_downloader_ui()
```

---

## ➕ Cómo Agregar un Nuevo Preset (Desde tu PC Local)

1. Crea un archivo `.json` dentro de `presets/<categoria>/<tu_setup>.json`:
```json
{
  "id": "mi-setup-sdxl-turbo",
  "title": "⚡ SDXL Turbo + VAE + ControlNet",
  "category": "SDXL",
  "description": "Configuración ultrarrápida de 1-step para prototipado en Colab.",
  "recommended_vram": "12GB+",
  "models": {
    "checkpoints": [
      "https://huggingface.co/stabilityai/sdxl-turbo/resolve/main/sd_xl_turbo_1.0_fp16.safetensors"
    ],
    "vae": [
      "https://huggingface.co/madebyollin/sdxl-vae-fp16-fix/resolve/main/sdxl_vae.safetensors"
    ],
    "loras": [
      "https://civitai.com/api/download/models/123456"
    ]
  },
  "custom_nodes": [
    "https://github.com/ltdrdata/ComfyUI-Manager"
  ]
}
```

2. Haz commit y súbelo a GitHub:
```bash
git add presets/
git commit -m "feat: nuevo preset SDXL Turbo"
git push
```

3. **¡Listo!** En Google Colab, al ejecutar la Celda 2, el nuevo preset aparecerá de inmediato en el menú desplegable.

---

## 💻 Uso desde Línea de Comandos (CLI)

También puedes utilizar el motor sin interfaz gráfica:

```bash
# Listar todos los presets disponibles
python main.py --list

# Instalar un preset específico
python main.py --preset qwen-image-2-1

# Purgar residuos y sanar caché
python main.py --purge
```
