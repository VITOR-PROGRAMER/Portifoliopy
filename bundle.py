#!/usr/bin/env python3
from __future__ import annotations
import argparse
import base64
import json
import mimetypes
import re
from pathlib import Path

LINK_CSS_RE = re.compile(
    r'<link\b(?=[^>]*\brel=["\']?stylesheet["\']?)(?=[^>]*\bhref=["\']([^"\']+)["\'])[^>]*>',
    re.IGNORECASE,
)
SCRIPT_SRC_RE = re.compile(
    r'<script\b(?=[^>]*\bsrc=["\']([^"\']+)["\'])[^>]*>\s*</script>',
    re.IGNORECASE,
)
COUNTS_BLOCK_RE = re.compile(
    r'<script\b(?=[^>]*\bid=["\']counts["\'])(?=[^>]*\btype=["\']application/json["\'])[^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
IMG_SRC_RE = re.compile(
    r'(<img\b[^>]*?\bsrc=["\'])([^"\']+)(["\'][^>]*>)',
    re.IGNORECASE,
)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        raise SystemExit(f"Erro lendo {path}: {e}")


def encode_file_as_data_uri(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    mime = mime or "application/octet-stream"
    b = path.read_bytes()
    b64 = base64.b64encode(b).decode("ascii")
    return f"data:{mime};base64,{b64}"


def inline_css(html: str, html_dir: Path) -> str:

    # Substitui <link rel="stylesheet" href="..."> local por <style>...</style>
    # Ignora links remotos (http/https//)
    def repl(m: re.Match) -> str:
        href = m.group(1).strip()
        if href.startswith(("http://", "https://", "//")):
            return m.group(0)  # mantém como está
        css_path = (html_dir / href).resolve()
        if not css_path.exists():
            css_path = (html_dir / Path(href)).resolve()
        css = read_text(css_path)
        return f"<style>\n{css}\n</style>"

    return LINK_CSS_RE.sub(repl, html)


def inline_js(html: str, html_dir: Path) -> str:
    """
    Substitui <script src="..."></script> locais por <script>...</script>
    Mantém scripts remotos (http/https//) como estão.
    """

    def repl(m: re.Match) -> str:
        src = m.group(1).strip()

        # Ignora scripts externos (CDNs, Google Fonts etc.)
        if src.startswith(("http://", "https://", "//")):
            return m.group(0)

        # Caminho absoluto do JS local
        js_path = (html_dir / src).resolve()
        if not js_path.exists():
            js_path = (html_dir / Path(src)).resolve()

        try:
            js_code = read_text(js_path)
        except Exception as e:
            print(f"[WARN] Falha ao ler JS '{src}': {e}")
            return m.group(0)  # mantém o original se não conseguir ler

        return f"<script>\n{js_code}\n</script>"

    return SCRIPT_SRC_RE.sub(repl, html)


def inline_counts_json(html: str, counts_path: Path) -> str:
    counts_json = json.dumps(
        json.loads(read_text(counts_path)), ensure_ascii=False, indent=2
    )
    script_block = (
        f'<script id="counts" type="application/json">\n{counts_json}\n</script>'
    )

    if COUNTS_BLOCK_RE.search(html):
        return COUNTS_BLOCK_RE.sub(script_block, html)

    lower = html.lower()
    idx = lower.rfind("</body>")
    if idx != -1:
        return html[:idx] + script_block + "\n" + html[idx:]
    return html + "\n" + script_block


def inline_images(html: str, html_dir: Path) -> str:
    # Converte <img src="local"> para data URI (ignora http(s) e data:)
    def repl(m: re.Match) -> str:
        prefix, src, suffix = m.groups()
        if src.startswith(("http://", "https://", "data:")):
            return m.group(0)
        img_path = (html_dir / src).resolve()
        if not img_path.exists():
            img_path = (html_dir / Path(src)).resolve()
        try:
            data_uri = encode_file_as_data_uri(img_path)
            return f"{prefix}{data_uri}{suffix}"
        except Exception:
            return m.group(0)

    return IMG_SRC_RE.sub(repl, html)


def main():
    p = argparse.ArgumentParser(
        description="Empacota HTML + CSS + JS + JSON em um único arquivo."
    )
    p.add_argument(
        "--html", required=True, type=Path, help="Caminho do index.html de origem"
    )
    p.add_argument(
        "--out", required=True, type=Path, help="Arquivo HTML de saída (bundle)"
    )
    p.add_argument("--json", required=False, type=Path, help="Caminho do counts.json")
    p.add_argument(
        "--inline-images",
        action="store_true",
        help="Embute imagens locais como data URI",
    )
    args = p.parse_args()

    html_path: Path = args.html.resolve()
    html_dir = html_path.parent
    html = read_text(html_path)

    # 1) CSS local inline
    html = inline_css(html, html_dir)
    # 2) JS local inline
    html = inline_js(html, html_dir)
    # 3) counts.json inline (se fornecido)
    if args.json:
        counts_path = args.json.resolve()
        html = inline_counts_json(html, counts_path)
    # 4) imagens locais inline (opcional)
    if args.inline_images:
        html = inline_images(html, html_dir)

    # 5) saída
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html, encoding="utf-8")
    print(f"✅ Gerado: {args.out}")


if __name__ == "__main__":
    main()
