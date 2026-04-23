"""
Incrementa o PATCH da versão em VERSION (ex.: 1.0.3 -> 1.0.4).
Uso:   python scripts/bump_version.py
Saída: imprime a nova versão em stdout (para o .bat capturar).
"""
import sys
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent  # tools/termo_notebook/
VERSION = ROOT / "VERSION"


def bump(current: str) -> str:
    parts = [p for p in current.strip().split(".") if p]
    # Garante ao menos 3 componentes (major.minor.patch)
    while len(parts) < 3:
        parts.append("0")
    try:
        parts[-1] = str(int(parts[-1]) + 1)
    except ValueError:
        raise SystemExit(f"VERSION invalida: '{current}' — use formato major.minor.patch")
    return ".".join(parts)


def main() -> None:
    if not VERSION.exists():
        VERSION.write_text("1.0.0\n", encoding="utf-8")
    atual = VERSION.read_text(encoding="utf-8").strip() or "0.0.0"
    novo  = bump(atual)
    VERSION.write_text(novo + "\n", encoding="utf-8")
    # Só a versão nova no stdout — o .bat captura
    sys.stdout.write(novo)


if __name__ == "__main__":
    main()
