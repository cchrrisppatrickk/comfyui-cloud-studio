import os
from studio.config import WORKSPACE

def create_helper_symlinks(target_dir, filename, full_filepath):
    """
    Crea enlaces simbólicos de compatibilidad para ComfyUI:
    - Enlaza subdirectorios como diffusion_models/anima o diffusion_models/qwen hacia diffusion_models/ raíz.
    - Enlaces cruzados entre models/text_encoders y models/clip.
    """
    if not os.path.exists(full_filepath):
        return

    # 1. Enlazar subcarpetas específicas (qwen, anima) hacia la raíz diffusion_models/
    if target_dir.endswith("diffusion_models/anima") or target_dir.endswith("diffusion_models/qwen"):
        parent_dir = os.path.dirname(target_dir)
        parent_sym = os.path.join(parent_dir, filename)
        if not os.path.exists(parent_sym):
            try:
                os.symlink(full_filepath, parent_sym)
            except Exception:
                pass
    elif target_dir.endswith("diffusion_models"):
        fn_lower = filename.lower()
        if "qwen" in fn_lower:
            qwen_dir = os.path.join(target_dir, "qwen")
            os.makedirs(qwen_dir, exist_ok=True)
            qwen_sym = os.path.join(qwen_dir, filename)
            if not os.path.exists(qwen_sym):
                try:
                    os.symlink(full_filepath, qwen_sym)
                except Exception:
                    pass
        if "anima" in fn_lower or "kirazuri" in fn_lower:
            anima_dir = os.path.join(target_dir, "anima")
            os.makedirs(anima_dir, exist_ok=True)
            anima_sym = os.path.join(anima_dir, filename)
            if not os.path.exists(anima_sym):
                try:
                    os.symlink(full_filepath, anima_sym)
                except Exception:
                    pass

    # 2. Enlaces cruzados entre text_encoders y clip
    if target_dir.endswith("text_encoders"):
        clip_dir = os.path.join(WORKSPACE, "models/clip")
        os.makedirs(clip_dir, exist_ok=True)
        clip_sym = os.path.join(clip_dir, filename)
        if not os.path.exists(clip_sym):
            try:
                os.symlink(full_filepath, clip_sym)
            except Exception:
                pass
    elif target_dir.endswith("models/clip"):
        te_dir = os.path.join(WORKSPACE, "models/text_encoders")
        os.makedirs(te_dir, exist_ok=True)
        te_sym = os.path.join(te_dir, filename)
        if not os.path.exists(te_sym):
            try:
                os.symlink(full_filepath, te_sym)
            except Exception:
                pass
