import os
import sys
from IPython.display import display, HTML, clear_output

from studio.config import WORKSPACE, DRIVE_WORKSPACE, TARGET_DIRS, get_colab_secret
from studio.cleaner import purgar_residuos_y_sanar_cache, clean_url
from studio.presets_manager import get_all_presets, save_custom_preset
from studio.downloader import download_file, download_node
from studio.civitai import mask_url

def render_downloader_ui(workspace=WORKSPACE):
    """
    Renderiza la interfaz gráfica en Google Colab con ipywidgets.
    Permite seleccionar presets oficiales o de Drive, pegar listas de LoRAs/modelos,
    sanar caché y guardar nuevos presets.
    """
    try:
        import ipywidgets as widgets
    except ImportError:
        print("⚠️ Advertencia: 'ipywidgets' no está instalado. Ejecuta: !pip install ipywidgets")
        return

    # 1. Recuperar credenciales automáticas si existen
    default_hf = get_colab_secret("HF_TOKEN")
    default_civitai = get_colab_secret("CIVITAI_API_KEY")

    # 2. Cargar Catálogo de Presets
    catalog = get_all_presets()
    preset_keys = list(catalog.keys())
    if not preset_keys:
        preset_keys = ["(No se encontraron presets)"]

    # ==========================================
    #  WIDGETS: PESTAÑA 1 - WORKFLOW PRESETS
    # ==========================================
    dropdown_options = [(catalog[k].get("title", k), k) for k in catalog]
    preset_dropdown = widgets.Dropdown(
        options=dropdown_options,
        value=dropdown_options[0][1] if dropdown_options else None,
        description="Preset:",
        layout=widgets.Layout(width="98%")
    )

    preset_info_box = widgets.HTML(layout=widgets.Layout(width="98%", margin="5px 0 10px 0"))

    def update_preset_info(change=None):
        pid = preset_dropdown.value
        if pid in catalog:
            p = catalog[pid]
            desc = p.get("description", "Sin descripción")
            vram = p.get("recommended_vram", "Estándar")
            source = "📁 Drive" if p.get("_source") in ("drive", "drive_legacy") else "🌐 Oficial"
            num_models = sum(len(v) for v in p.get("models", {}).values())
            num_nodes = len(p.get("custom_nodes", []))

            preset_info_box.value = f"""
            <div style="background:#1e293b; color:#f8fafc; padding:10px 14px; border-radius:6px; font-size:13px; border-left:4px solid #3b82f6;">
                <b>{p.get('title', pid)}</b> &nbsp;<span style="background:#0f172a; padding:2px 8px; border-radius:4px; font-size:11px;">{source}</span><br>
                <div style="color:#94a3b8; margin:4px 0;">{desc}</div>
                <div style="font-size:12px; margin-top:4px;">
                    ⚡ <b>VRAM Recomendada:</b> <span style="color:#38bdf8;">{vram}</span> |
                    📦 <b>Modelos:</b> {num_models} |
                    🧩 <b>Nodos:</b> {num_nodes}
                </div>
            </div>
            """
        else:
            preset_info_box.value = ""

    preset_dropdown.observe(update_preset_info, names="value")
    update_preset_info()

    chk_autopurge = widgets.Checkbox(
        value=True,
        description="Auto-purga preventiva de residuos y sanación de caché",
        layout=widgets.Layout(width="98%")
    )

    btn_download_preset = widgets.Button(
        description="⚡ Descargar e Instalar Preset (1 Clic)",
        button_style="success",
        icon="bolt",
        layout=widgets.Layout(width="98%", height="42px", margin="8px 0")
    )

    tab_preset_box = widgets.VBox([
        widgets.HTML("<b>Selecciona un Workflow Preset optimizado:</b>"),
        preset_dropdown,
        preset_info_box,
        chk_autopurge,
        btn_download_preset
    ])

    # ==========================================
    #  WIDGETS: PESTAÑA 2 - DESCARGAS MANUALES / LORAS
    # ==========================================
    txt_loras = widgets.Textarea(
        placeholder="Pega aquí URLs de LoRAs (Hugging Face / Civitai), una por línea o separadas por comas...",
        description="LoRAs:",
        layout=widgets.Layout(width="98%", height="110px")
    )

    txt_checkpoints = widgets.Textarea(
        placeholder="URLs de Checkpoints / Modelos completos...",
        description="Checkpoints:",
        layout=widgets.Layout(width="98%", height="70px")
    )

    txt_diffusion = widgets.Textarea(
        placeholder="URLs de Diffusion Models (UNET / Flux / Qwen / etc.)...",
        description="Diffusion:",
        layout=widgets.Layout(width="98%", height="70px")
    )

    txt_vaes_te = widgets.Textarea(
        placeholder="URLs de VAEs o Text Encoders...",
        description="VAE / TE:",
        layout=widgets.Layout(width="98%", height="70px")
    )

    txt_nodes = widgets.Textarea(
        placeholder="URLs de repositorios Git de Custom Nodes...",
        description="Nodos Git:",
        layout=widgets.Layout(width="98%", height="70px")
    )

    btn_download_manual = widgets.Button(
        description="📥 Descargar Enlaces Manuales",
        button_style="primary",
        icon="download",
        layout=widgets.Layout(width="98%", height="42px", margin="8px 0")
    )

    tab_manual_box = widgets.VBox([
        widgets.HTML("<b>Instalación por URLs Manuales o por Lotes:</b>"),
        txt_loras,
        txt_checkpoints,
        txt_diffusion,
        txt_vaes_te,
        txt_nodes,
        btn_download_manual
    ])

    # ==========================================
    #  WIDGETS: PESTAÑA 3 - GUARDAR PRESET / CREDS
    # ==========================================
    txt_preset_name = widgets.Text(
        placeholder="Ej: Mi_Setup_Flux_Anime",
        description="Nombre ID:",
        layout=widgets.Layout(width="98%")
    )
    txt_preset_title = widgets.Text(
        placeholder="Ej: 🎨 Mi Setup Favorito Flux Anime",
        description="Título:",
        layout=widgets.Layout(width="98%")
    )
    txt_preset_desc = widgets.Text(
        placeholder="Descripción breve de los componentes del workflow...",
        description="Descripción:",
        layout=widgets.Layout(width="98%")
    )

    btn_save_preset = widgets.Button(
        description="💾 Guardar Entorno Actual como Preset en Drive",
        button_style="info",
        icon="save",
        layout=widgets.Layout(width="98%", height="38px", margin="6px 0")
    )

    txt_hf_token = widgets.Password(
        value=default_hf,
        placeholder="Token de Hugging Face (opcional para modelos gated)",
        description="HF Token:",
        layout=widgets.Layout(width="98%")
    )

    txt_civitai_key = widgets.Password(
        value=default_civitai,
        placeholder="API Key de Civitai (opcional para modelos restringidos)",
        description="Civitai Key:",
        layout=widgets.Layout(width="98%")
    )

    btn_purge_cache = widgets.Button(
        description="🧹 Purgar Residuos y Sanar Caché Ahora",
        button_style="warning",
        icon="trash",
        layout=widgets.Layout(width="98%", height="38px", margin="10px 0")
    )

    tab_tools_box = widgets.VBox([
        widgets.HTML("<b>Guardar los enlaces manuales actuales como nuevo Preset:</b>"),
        txt_preset_name,
        txt_preset_title,
        txt_preset_desc,
        btn_save_preset,
        widgets.HTML("<hr><b>Credenciales de API (Opcionales):</b>"),
        txt_hf_token,
        txt_civitai_key,
        widgets.HTML("<hr><b>Mantenimiento:</b>"),
        btn_purge_cache
    ])

    # ==========================================
    #  PESTAÑAS PRINCIPALES Y SALIDA DE LOGS
    # ==========================================
    tabs = widgets.Tab(children=[tab_preset_box, tab_manual_box, tab_tools_box])
    tabs.set_title(0, "⚡ Presets Oficiales")
    tabs.set_title(1, "📦 Descargas & LoRAs")
    tabs.set_title(2, "⚙️ Herramientas & Tokens")

    out_panel = widgets.Output(layout=widgets.Layout(border="1px solid #334155", padding="10px", margin="10px 0", background="#0b0f19"))

    # ==========================================
    #  LÓGICA DE EVENTOS (HANDLERS)
    # ==========================================
    def parse_urls_field(field_text):
        if not field_text:
            return []
        cleaned_list = []
        for line in field_text.replace(',', '\n').split('\n'):
            u = clean_url(line)
            if u and u not in cleaned_list:
                cleaned_list.append(u)
        return cleaned_list

    def execute_downloads(items_dict, hf_key, civ_key, autopurge=True):
        with out_panel:
            out_panel.clear_output()
            if autopurge:
                purgar_residuos_y_sanar_cache(verbose=True)

            total = sum(len(v) for v in items_dict.values())
            if total == 0:
                print("⚠️ No hay modelos ni nodos especificados para descargar.")
                return

            print(f"\n🚀 Iniciando procesamiento de {total} elemento(s)...")
            ok_count = 0
            fail_count = 0

            for cat, urls in items_dict.items():
                if not urls:
                    continue
                target_dir = TARGET_DIRS.get(cat, os.path.join(WORKSPACE, "models", cat))
                os.makedirs(target_dir, exist_ok=True)

                for u in urls:
                    print(f"\n▶ [{cat}] {mask_url(u)}")
                    try:
                        if cat == "custom_nodes":
                            success = download_node(u, target_dir)
                        else:
                            success = download_file(u, target_dir, civitai_key=civ_key, hf_token=hf_key)

                        if success:
                            ok_count += 1
                        else:
                            fail_count += 1
                    except Exception as ex:
                        print(f"  ❌ Error inesperado: {ex}")
                        fail_count += 1

            print("\n" + "="*50)
            print(f"🏁 Finalizado: ✅ {ok_count} correctos | ❌ {fail_count} fallidos")
            print("="*50)

            if ok_count > 0:
                display(HTML('''
                <div style="background:#166534; color:#dcfce7; padding:10px; border-radius:6px; font-weight:bold; text-align:center; margin-top:8px;">
                    🎉 ¡Descargas completadas! Todos los modelos y dependencias están listos en ComfyUI.
                </div>
                '''))

    def on_click_preset(_):
        pid = preset_dropdown.value
        if pid not in catalog:
            with out_panel:
                print("❌ Por favor selecciona un preset válido.")
            return

        p = catalog[pid]
        items = {k: list(v) for k, v in p.get("models", {}).items()}
        if "custom_nodes" in p:
            items["custom_nodes"] = list(p.get("custom_nodes", []))

        execute_downloads(
            items,
            hf_key=txt_hf_token.value.strip(),
            civ_key=txt_civitai_key.value.strip(),
            autopurge=chk_autopurge.value
        )

    def on_click_manual(_):
        items = {
            "loras": parse_urls_field(txt_loras.value),
            "checkpoints": parse_urls_field(txt_checkpoints.value),
            "diffusion_models": parse_urls_field(txt_diffusion.value),
            "vae": parse_urls_field(txt_vaes_te.value),
            "custom_nodes": parse_urls_field(txt_nodes.value),
        }
        execute_downloads(
            items,
            hf_key=txt_hf_token.value.strip(),
            civ_key=txt_civitai_key.value.strip(),
            autopurge=False
        )

    def on_click_save_preset(_):
        name = txt_preset_name.value.strip()
        if not name:
            with out_panel:
                print("❌ Debes ingresar un nombre o ID para el nuevo preset.")
            return

        models = {
            "loras": parse_urls_field(txt_loras.value),
            "checkpoints": parse_urls_field(txt_checkpoints.value),
            "diffusion_models": parse_urls_field(txt_diffusion.value),
            "vae": parse_urls_field(txt_vaes_te.value),
        }
        models = {k: v for k, v in models.items() if v}
        nodes = parse_urls_field(txt_nodes.value)

        with out_panel:
            path = save_custom_preset(
                preset_id=name,
                title=txt_preset_title.value.strip() or name,
                description=txt_preset_desc.value.strip(),
                models_dict=models,
                custom_nodes_list=nodes
            )
            print(f"✨ Preset guardado exitosamente. Recarga la celda para verlo en la lista.")

    def on_click_purge(_):
        with out_panel:
            out_panel.clear_output()
            purgar_residuos_y_sanar_cache(verbose=True)

    btn_download_preset.on_click(on_click_preset)
    btn_download_manual.on_click(on_click_manual)
    btn_save_preset.on_click(on_click_save_preset)
    btn_purge_cache.on_click(on_click_purge)

    # Encabezado visual
    display(HTML('''
    <div style="background: linear-gradient(90deg, #1e3a8a 0%, #312e81 100%); color: #fff; padding: 14px 18px; border-radius: 8px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin-bottom: 12px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <b style="font-size: 16px; letter-spacing: 0.5px;">⚡ ComfyUI Cloud Studio - Smart Presets & Downloader</b>
                <div style="font-size: 12px; color: #93c5fd; margin-top: 2px;">Gestor modular de modelos, LoRAs y nodos para Google Colab</div>
            </div>
            <div style="background: rgba(255,255,255,0.15); padding: 4px 10px; border-radius: 4px; font-size: 11px;">v2.5 Modular</div>
        </div>
    </div>
    '''))

    display(tabs, out_panel)
