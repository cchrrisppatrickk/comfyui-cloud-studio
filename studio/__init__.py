# Lazy imports to allow headless CLI execution without IPython / ipywidgets
from studio.presets_manager import get_all_presets, save_custom_preset
from studio.downloader import download_file, download_node
from studio.cleaner import purgar_residuos_y_sanar_cache

def render_downloader_ui(*args, **kwargs):
    from studio.ui import render_downloader_ui as _render
    return _render(*args, **kwargs)

__all__ = [
    "render_downloader_ui",
    "get_all_presets",
    "save_custom_preset",
    "download_file",
    "download_node",
    "purgar_residuos_y_sanar_cache"
]
