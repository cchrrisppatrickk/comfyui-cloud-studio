import os
import sys
from IPython.display import display, HTML, clear_output

from studio.config import WORKSPACE, DRIVE_WORKSPACE, TARGET_DIRS, get_colab_secret
from studio.cleaner import purgar_residuos_y_sanar_cache, clean_url
from studio.presets_manager import get_all_presets, get_presets_by_family, save_custom_preset
from studio.downloader import download_file, download_node
from studio.civitai import mask_url

def render_downloader_ui(workspace=WORKSPACE):
    """
    Renderiza la consola interactiva en Google Colab con ipywidgets.
    Incluye navegación por Familia/Versión, ficha técnica del modelo con enlaces directos
    a Civitai/Hugging Face, descarga masiva de LoRAs y saneamiento de caché.
    """
    try:
        import ipywidgets as widgets
    except ImportError:
        print("⚠️ Advertencia: 'ipywidgets' no está instalado. Ejecuta: !pip install ipywidgets")
        return

    # 1. Recuperar credenciales automáticas
    default_hf = get_colab_secret("HF_TOKEN")
    default_civitai = get_colab_secret("CIVITAI_API_KEY")

    # 2. Cargar Catálogo agrupado por familias
    catalog = get_all_presets()
    families_dict = get_presets_by_family()

    family_options = ["(Todas las Familias)"] + list(families_dict.keys())

    # ==========================================
    #  PESTAÑA 1: SELECTORES Y FICHA DE MODELO
    # ==========================================
    family_dropdown = widgets.Dropdown(
        options=family_options,
        value=family_options[0],
        description="Familia:",
        layout=widgets.Layout(width="98%")
    )

    preset_dropdown = widgets.Dropdown(
        options=[],
        description="Versión:",
        layout=widgets.Layout(width="98%")
    )

    preset_info_box = widgets.HTML(layout=widgets.Layout(width="98%", margin="8px 0"))

    def get_filtered_presets(selected_family):
        if selected_family == "(Todas las Familias)":
            return catalog
        return families_dict.get(selected_family, {})

    def update_version_dropdown(change=None):
        fam = family_dropdown.value
        filtered = get_filtered_presets(fam)
        options = []
        for pid, p in filtered.items():
            author = p.get("author", "Comunidad")
            version = p.get("version", "")
            title = p.get("title", pid)
            display_label = f"{title} [{version} por {author}]"
            options.append((display_label, pid))

        preset_dropdown.options = options
        if options:
            preset_dropdown.value = options[0][1]
        else:
            preset_dropdown.value = None
        update_preset_card()

    def update_preset_card(change=None):
        pid = preset_dropdown.value
        if not pid or pid not in catalog:
            preset_info_box.value = ""
            return

        p = catalog[pid]
        title = p.get("title", pid)
        family = p.get("family", "General")
        version = p.get("version", "v1.0")
        author = p.get("author", "Comunidad")
        base_model = p.get("base_model", "N/A")
        desc = p.get("description", "Sin descripción detallada.")
        vram = p.get("recommended_vram", "Estándar (12GB+)")
        source_url = p.get("source_url", "")
        source_type = p.get("source_type", "Civitai / Hugging Face")
        params = p.get("parameters", {})
        models = p.get("models", {})
        nodes = p.get("custom_nodes", [])

        # Estilo de badge de VRAM
        is_t4_safe = "T4" in vram or "12GB" in vram or "Baja" in vram
        vram_badge_color = "#15803d" if is_t4_safe else "#b45309"
        vram_icon = "⚡" if is_t4_safe else "🔥"

        # Badge de origen (Civitai vs Hugging Face)
        is_civitai = "civitai" in source_type.lower() or "civitai" in source_url.lower()
        source_badge_color = "#0284c7" if is_civitai else "#d97706"

        # Enlace HTML
        link_html = ""
        if source_url:
            link_html = f"""
            <a href="{source_url}" target="_blank" style="display:inline-block; background:{source_badge_color}; color:#ffffff; padding:4px 10px; border-radius:4px; text-decoration:none; font-size:12px; font-weight:600; margin-left:8px;">
                🔗 Ver en {source_type}
            </a>
            """

        # Parámetros recomendados HTML
        params_html = ""
        if params:
            chips = []
            for k, val in params.items():
                chips.append(f"<span style='background:#334155; padding:2px 8px; border-radius:4px; margin-right:6px;'><b>{k.upper()}:</b> {val}</span>")
            params_html = f"""
            <div style="margin-top:8px; font-size:12px; color:#cbd5e1;">
                ⚙️ <b>Configuración Recomendada:</b> {' '.join(chips)}
            </div>
            """

        # Desglose de archivos a descargar
        files_breakdown = []
        for cat, urls in models.items():
            for u in urls:
                clean_name = u.split("/")[-1].split("?")[0]
                files_breakdown.append(f"<li><span style='color:#93c5fd;'>[{cat}]</span> {clean_name}</li>")
        for nu in nodes:
            node_name = nu.rstrip("/").split("/")[-1]
            files_breakdown.append(f"<li><span style='color:#86efac;'>[custom_node]</span> {node_name}</li>")

        breakdown_html = f"""
        <details style="margin-top:8px; font-size:12px; color:#94a3b8; cursor:pointer;">
            <summary style="font-weight:600; color:#cbd5e1;">📦 Ver desglose de componentes ({len(files_breakdown)} elementos)</summary>
            <ul style="margin:4px 0 0 16px; padding:0; line-height:1.5;">
                {''.join(files_breakdown)}
            </ul>
        </details>
        """

        # Render completo de la tarjeta
        preset_info_box.value = f"""
        <div style="background:#0f172a; color:#f8fafc; padding:14px 16px; border-radius:8px; font-size:13px; border:1px solid #1e293b; border-left:5px solid #3b82f6; box-shadow:0 4px 6px -1px rgba(0,0,0,0.3);">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
                <div>
                    <span style="font-size:16px; font-weight:700; color:#ffffff;">{title}</span>
                    <span style="background:#1e293b; color:#94a3b8; padding:2px 8px; border-radius:4px; font-size:11px; margin-left:6px;">{version}</span>
                </div>
                <div>
                    <span style="background:{vram_badge_color}; color:#ffffff; padding:3px 8px; border-radius:4px; font-size:11px; font-weight:600;">
                        {vram_icon} {vram}
                    </span>
                    {link_html}
                </div>
            </div>

            <div style="color:#94a3b8; font-size:12px; margin:6px 0 8px 0;">
                👤 <b>Autor/Entrenador:</b> <span style="color:#e2e8f0;">{author}</span> &nbsp;|&nbsp;
                🧬 <b>Modelo Base:</b> <span style="color:#e2e8f0;">{base_model}</span> &nbsp;|&nbsp;
                📁 <b>Familia:</b> <span style="color:#e2e8f0;">{family}</span>
            </div>

            <div style="background:#1e293b; color:#e2e8f0; padding:10px 12px; border-radius:6px; line-height:1.45; font-size:12.5px; margin:6px 0;">
                {desc}
            </div>

            {params_html}
            {breakdown_html}
        </div>
        """

        if pid in catalog:
            btn_download_preset.description = f"⚡ Descargar e Instalar {catalog[pid].get('title', pid)}"

    family_dropdown.observe(update_version_dropdown, names="value")
    preset_dropdown.observe(update_preset_card, names="value")

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
        widgets.HTML("<b>1. Selecciona el Modelo General o Familia:</b>"),
        family_dropdown,
        widgets.HTML("<b style='margin-top:6px;'>2. Selecciona la Versión / Variante de la Comunidad:</b>"),
        preset_dropdown,
        preset_info_box,
        chk_autopurge,
        btn_download_preset
    ])

    # Inicializar selectores
    update_version_dropdown()

    # ==========================================
    #  PESTAÑA 2: DESCARGAS MANUALES / LORAS
    # ==========================================
    txt_loras = widgets.Textarea(
        placeholder="Pega aquí URLs de LoRAs (Hugging Face o Civitai), una por línea o separadas por comas...",
        description="LoRAs:",
        layout=widgets.Layout(width="98%", height="110px")
    )

    txt_checkpoints = widgets.Textarea(
        placeholder="URLs de Checkpoints completos (Civitai / HF)...",
        description="Checkpoints:",
        layout=widgets.Layout(width="98%", height="70px")
    )

    txt_diffusion = widgets.Textarea(
        placeholder="URLs de Diffusion Models (UNET / Flux / Qwen / Anima)...",
        description="Diffusion:",
        layout=widgets.Layout(width="98%", height="70px")
    )

    txt_vaes_te = widgets.Textarea(
        placeholder="URLs de VAEs o Text Encoders...",
        description="VAE / TE:",
        layout=widgets.Layout(width="98%", height="70px")
    )

    txt_nodes = widgets.Textarea(
        placeholder="URLs de repositorios Git de Custom Nodes (ej. https://github.com/kijai/ComfyUI-KJNodes)...",
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
        widgets.HTML("<b>Instalación por URLs Manuales o por Lotes (soporta múltiples LoRAs):</b>"),
        txt_loras,
        txt_checkpoints,
        txt_diffusion,
        txt_vaes_te,
        txt_nodes,
        btn_download_manual
    ])

    # ==========================================
    #  PESTAÑA 3: GUARDAR PRESET / CREDS
    # ==========================================
    txt_preset_name = widgets.Text(
        placeholder="Ej: mi_setup_flux_anime",
        description="ID Preset:",
        layout=widgets.Layout(width="98%")
    )
    txt_preset_title = widgets.Text(
        placeholder="Ej: 🎨 Mi Finetune Favorito Anime",
        description="Título:",
        layout=widgets.Layout(width="98%")
    )
    txt_preset_family = widgets.Text(
        placeholder="Ej: 🌸 Anima, ⚡ Qwen o Flux",
        description="Familia:",
        layout=widgets.Layout(width="98%")
    )
    txt_preset_author = widgets.Text(
        placeholder="Tu nombre o creador del modelo en Civitai",
        description="Autor:",
        layout=widgets.Layout(width="98%")
    )
    txt_preset_url = widgets.Text(
        placeholder="https://civitai.com/models/...",
        description="Enlace Fuente:",
        layout=widgets.Layout(width="98%")
    )
    txt_preset_desc = widgets.Text(
        placeholder="Descripción breve del estilo y recomendaciones...",
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
        txt_preset_family,
        txt_preset_author,
        txt_preset_url,
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
    tabs.set_title(0, "⚡ Presets & Modelos")
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
        if not pid or pid not in catalog:
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
                print("❌ Debes ingresar un ID para el nuevo preset.")
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
                custom_nodes_list=nodes,
                family=txt_preset_family.value.strip() or "Personalizados",
                author=txt_preset_author.value.strip() or "Usuario",
                source_url=txt_preset_url.value.strip()
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

    # Encabezado visual profesional
    display(HTML('''
    <div style="background: linear-gradient(90deg, #1e3a8a 0%, #312e81 100%); color: #fff; padding: 14px 18px; border-radius: 8px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin-bottom: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <b style="font-size: 16px; letter-spacing: 0.5px;">⚡ ComfyUI Cloud Studio - Smart Presets & Downloader</b>
                <div style="font-size: 12px; color: #93c5fd; margin-top: 2px;">Navegación jerárquica de modelos, variantes de Civitai y aprovisionamiento multihilo</div>
            </div>
            <div style="background: rgba(255,255,255,0.15); padding: 4px 10px; border-radius: 4px; font-size: 11px;">v2.6 Pro Edition</div>
        </div>
    </div>
    '''))

    display(tabs, out_panel)
