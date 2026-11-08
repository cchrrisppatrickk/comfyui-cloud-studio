import os

# Entornos y rutas base por defecto
WORKSPACE = os.environ.get("COMFY_WORKSPACE", "/content/ComfyUI")
DRIVE_WORKSPACE = os.environ.get("COMFY_DRIVE_WORKSPACE", "/content/drive/MyDrive/ComfyUI")

# Dónde buscar presets personalizados de usuario en Google Drive
DRIVE_PRESETS_DIR = os.path.join(DRIVE_WORKSPACE, "custom_presets")

# Mapeo de subdirectorios de destino para ComfyUI
TARGET_DIRS = {
    "diffusion_models/anima": os.path.join(WORKSPACE, "models/diffusion_models/anima"),
    "diffusion_models/qwen":  os.path.join(WORKSPACE, "models/diffusion_models/qwen"),
    "diffusion_models":       os.path.join(WORKSPACE, "models/diffusion_models"),
    "text_encoders":          os.path.join(WORKSPACE, "models/text_encoders"),
    "checkpoints":            os.path.join(WORKSPACE, "models/checkpoints"),
    "unet":                   os.path.join(WORKSPACE, "models/unet"),
    "clip":                   os.path.join(WORKSPACE, "models/clip"),
    "clip_vision":            os.path.join(WORKSPACE, "models/clip_vision"),
    "vae":                    os.path.join(WORKSPACE, "models/vae"),
    "loras":                  os.path.join(WORKSPACE, "models/loras"),
    "controlnet":             os.path.join(WORKSPACE, "models/controlnet"),
    "upscale_models":         os.path.join(WORKSPACE, "models/upscale_models"),
    "latent_upscale_models":  os.path.join(WORKSPACE, "models/latent_upscale_models"),
    "embeddings":             os.path.join(WORKSPACE, "models/embeddings"),
    "custom_nodes":           os.path.join(WORKSPACE, "custom_nodes"),
}

DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

def get_colab_secret(secret_name):
    """Obtiene secretos almacenados en Colab userdata o variables de entorno."""
    try:
        from google.colab import userdata
        val = userdata.get(secret_name)
        return (val or "").strip()
    except Exception:
        pass
    return os.environ.get(secret_name, "").strip()
