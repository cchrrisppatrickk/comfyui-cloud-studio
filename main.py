import argparse
import sys
from studio.presets_manager import get_all_presets
from studio.downloader import download_file, download_node
from studio.cleaner import purgar_residuos_y_sanar_cache
from studio.config import TARGET_DIRS, WORKSPACE, get_colab_secret
from studio.civitai import mask_url

def main():
    parser = argparse.ArgumentParser(description="ComfyUI Cloud Studio CLI Downloader")
    parser.add_argument("--list", action="store_true", help="Listar todos los presets disponibles")
    parser.add_argument("--preset", type=str, help="ID del preset a descargar e instalar")
    parser.add_argument("--purge", action="store_true", help="Ejecutar purga de residuos y sanación de caché")
    parser.add_argument("--hf-token", type=str, default="", help="Hugging Face Token")
    parser.add_argument("--civitai-key", type=str, default="", help="Civitai API Key")

    args = parser.parse_args()
    presets = get_all_presets()

    if args.list:
        print("\n📋 Catálogo de Presets Disponibles:")
        for pid, p in presets.items():
            source = "📁 Drive" if p.get("_source") == "drive" else "🌐 Oficial"
            print(f"  • {pid} [{source}] - {p.get('title', pid)}")
            if "description" in p:
                print(f"    ↳ {p['description']}")
        return

    if args.purge:
        purgar_residuos_y_sanar_cache(verbose=True)

    if args.preset:
        if args.preset not in presets:
            print(f"❌ Error: El preset '{args.preset}' no existe. Usa --list para ver los disponibles.")
            sys.exit(1)

        p = presets[args.preset]
        print(f"\n🚀 Instalando preset: {p.get('title', args.preset)}")
        hf = args.hf_token or get_colab_secret("HF_TOKEN")
        civ = args.civitai_key or get_colab_secret("CIVITAI_API_KEY")

        for cat, urls in p.get("models", {}).items():
            td = TARGET_DIRS.get(cat, f"{WORKSPACE}/models/{cat}")
            for u in urls:
                print(f"\n▶ [{cat}] {mask_url(u)}")
                download_file(u, td, civitai_key=civ, hf_token=hf)

        for nu in p.get("custom_nodes", []):
            td = TARGET_DIRS.get("custom_nodes", f"{WORKSPACE}/custom_nodes")
            download_node(nu, td)

        print("\n🎉 ¡Preset instalado con éxito!")

if __name__ == "__main__":
    main()
