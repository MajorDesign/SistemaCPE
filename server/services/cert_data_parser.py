"""Parser da data de calibracao em certificados.

Procura em qualquer celula do arquivo um rotulo contendo as palavras
'data' + 'calibrac' (case-insensitive, acentuacao tolerante) e devolve
a data da celula adjacente (mesma linha, coluna seguinte ou subsequente
dentro das proximas 3 colunas na mesma linha), aceitando varios formatos:

    - datetime do Excel (openpyxl ja devolve datetime)
    - string "dd/mm/yyyy", "dd-mm-yyyy", "yyyy-mm-dd"
    - string com data embutida ("Data: 05/01/2026")

Retorna `datetime.date` ou None se nao achar.

Suporta .xlsx (openpyxl) e .xls (xlrd 1.2 — ultima versao com suporte a
XLS; xlrd 2.x so le xlsx).
"""
from __future__ import annotations

import datetime as _dt
import logging
import re
import unicodedata
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Procura "data" + alguma coisa + "calibrac" na mesma celula.
_LABEL_RE = re.compile(r"\bdata\b[^\n]*calibrac", re.IGNORECASE)

# Formatos de data por tentativa:
_FORMATS = (
    "%d/%m/%Y", "%d/%m/%y",
    "%d-%m-%Y", "%d-%m-%y",
    "%Y-%m-%d",
    "%d.%m.%Y",
)

# Dentro de string (ex: "Data: 05/01/2026")
_DATE_IN_TEXT = re.compile(
    r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{4}-\d{2}-\d{2})"
)


def _normalize(s: str) -> str:
    """Lowercase + remove acentos pra matching robusto."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower().strip()


def _try_parse_date_value(val) -> Optional[_dt.date]:
    """Converte um valor de celula em date. Aceita datetime, str varios formatos."""
    if val is None:
        return None
    if isinstance(val, _dt.datetime):
        return val.date()
    if isinstance(val, _dt.date):
        return val
    if isinstance(val, (int, float)):
        # Serial do Excel (dias desde 1900-01-01, com ajuste de bug Lotus)
        try:
            if 20000 < float(val) < 80000:
                base = _dt.date(1899, 12, 30)  # ajuste bug Lotus 1900
                return base + _dt.timedelta(days=int(val))
        except Exception:
            return None
        return None
    s = str(val).strip()
    if not s:
        return None
    for fmt in _FORMATS:
        try:
            return _dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # Tenta extrair data de dentro do texto (ex: "Data: 05/01/2026 / Validade: ...")
    m = _DATE_IN_TEXT.search(s)
    if m:
        token = m.group(1)
        for fmt in _FORMATS:
            try:
                return _dt.datetime.strptime(token, fmt).date()
            except ValueError:
                continue
    return None


def _find_in_cells(grid: list[list]) -> Optional[_dt.date]:
    """Procura 'data da calibracao' em grid 2D de valores de celulas.

    Para cada celula com o rotulo:
      - tenta parsear o valor na mesma celula (apos ":" ou embutido)
      - senao, olha as 3 celulas seguintes na mesma linha
      - senao, olha 1 celula abaixo
    """
    for ri, row in enumerate(grid):
        for ci, cell in enumerate(row):
            if cell is None:
                continue
            txt = str(cell)
            if not _LABEL_RE.search(_normalize(txt)):
                continue
            logger.debug(f"[cert_parser] rotulo achado em r={ri} c={ci}: {txt!r}")

            # 1) data embutida na propria celula (apos ":" ou separador)
            d = _try_parse_date_value(txt)
            if d:
                return d

            # 2) proximas celulas na mesma linha
            for off in range(1, 4):
                if ci + off < len(row):
                    d = _try_parse_date_value(row[ci + off])
                    if d:
                        return d

            # 3) celula de baixo
            if ri + 1 < len(grid) and ci < len(grid[ri + 1]):
                d = _try_parse_date_value(grid[ri + 1][ci])
                if d:
                    return d
    return None


# =========================================================================
# Readers por formato
# =========================================================================
def _read_xlsx(path: str) -> list[list]:
    """Le todas as celulas do primeiro sheet como grid 2D."""
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb.active
        grid: list[list] = []
        for row in ws.iter_rows(values_only=True):
            grid.append(list(row))
        return grid
    finally:
        wb.close()


def _read_xls(path: str) -> list[list]:
    """Le todas as celulas do primeiro sheet como grid 2D (via xlrd 1.2)."""
    import xlrd  # 1.2.0

    book = xlrd.open_workbook(path)
    try:
        sh = book.sheet_by_index(0)
        grid: list[list] = []
        for r in range(sh.nrows):
            row = []
            for c in range(sh.ncols):
                cell = sh.cell(r, c)
                v = cell.value
                # XL_CELL_DATE = 3 — converte com xldate_as_tuple
                if cell.ctype == xlrd.XL_CELL_DATE:
                    try:
                        y, m, d, hh, mm, ss = xlrd.xldate_as_tuple(v, book.datemode)
                        v = _dt.datetime(y or 1900, m or 1, d or 1, hh, mm, ss)
                    except Exception:
                        pass
                row.append(v)
            grid.append(row)
        return grid
    finally:
        book.release_resources()


# =========================================================================
# API publica
# =========================================================================
def extract_data_calibracao(path: str, ext: str) -> Optional[_dt.date]:
    """Le o arquivo e devolve a data_calibracao, ou None se nao achar.

    Nao levanta — em qualquer erro, loga e devolve None (data_calibracao
    opcional; o cert e salvo mesmo sem data).
    """
    try:
        p = Path(path)
        if not p.exists():
            return None
        ext = (ext or "").lower()
        if ext == ".xlsx":
            grid = _read_xlsx(str(p))
        elif ext == ".xls":
            grid = _read_xls(str(p))
        else:
            logger.warning(f"[cert_parser] extensao nao suportada: {ext}")
            return None
        d = _find_in_cells(grid)
        if d is None:
            logger.info(f"[cert_parser] data de calibracao NAO encontrada em {p.name}")
        else:
            logger.info(f"[cert_parser] data de calibracao {d.isoformat()} encontrada em {p.name}")
        return d
    except Exception as e:
        logger.warning(f"[cert_parser] falha ao extrair data: {e}")
        return None
