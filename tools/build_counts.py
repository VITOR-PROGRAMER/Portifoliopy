from pathlib import Path
import json

# Caminhos base
BASE = Path(__file__).resolve().parents[1]  # .../PORTIFOLIO
PROJETOS = BASE / "Projetos"
WEB_DATA = BASE / "WEB" / "data"
WEB_DATA.mkdir(parents=True, exist_ok=True)

# Skills (nomes das pastas dentro de "Projetos")
skills = ["excel", "powerbi", "vba", "sql", "java", "python", "ia", "redes", "process"]


def cap(skill: str) -> str:
    """Capitaliza o nome da pasta (Excel, Python, etc.)"""
    return skill[:1].upper() + skill[1:].lower()


def listar_projetos(skill: str) -> dict:
    """Retorna os nomes de subpastas e arquivos de uma skill."""
    pasta = PROJETOS / cap(skill)
    if not pasta.exists():
        return {"pastas": [], "arquivos": []}

    subpastas = []
    arquivos = []

    for item in pasta.iterdir():
        if item.is_dir():
            subpastas.append(item.name)
        elif item.is_file():
            arquivos.append(item.name)

    return {"pastas": sorted(subpastas), "arquivos": sorted(arquivos)}


# Gera estrutura completa
dados = {}

for skill in skills:
    info = listar_projetos(skill)
    dados[skill] = {
        "quantidade_pastas": len(info["pastas"]),
        "quantidade_arquivos": len(info["arquivos"]),
        "pastas": info["pastas"],
        "arquivos": info["arquivos"],
    }

# Estrutura final no JSON
out = {
    "skills": skills,
    "dados": dados,
    "total_geral": sum(
        v["quantidade_pastas"] + v["quantidade_arquivos"] for v in dados.values()
    ),
}

# Grava o JSON
destino = WEB_DATA / "counts.json"
destino.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"[OK] Gerado {destino}")
print(json.dumps(out, indent=2, ensure_ascii=False))
