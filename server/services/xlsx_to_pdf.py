"""Conversor xlsx -> pdf via Excel COM (Office 365 instalado no CPEDC22).

2026-10-01: parte do modulo Assistencia Tecnica / Certificados.

Por que Excel COM e nao LibreOffice/aspose:
- Excel COM da fidelidade visual perfeita (certificados tem formatacao
  complexa, bordas, fontes especificas).
- Office 365 ja esta instalado no servidor em prod (CPEDC22).

Caveats importantes:
- Excel COM NAO e thread-safe. Uso de `_COM_LOCK` global pra serializar
  conversoes (uma por vez no processo).
- Precisa de CoInitialize() por thread.
- Precisa pastas `Desktop` em %WINDIR%\\System32\\config\\systemprofile\\
  e %WINDIR%\\SysWOW64\\config\\systemprofile\\ (bug conhecido quando
  roda sob service Windows / Session 0). O instalador do modulo deve
  garantir isso — ver script scripts/setup_excel_com.ps1.
- Conversao e sincrona e pode levar 10-30s. Em producao, considerar
  rodar em thread pool / worker queue pra nao bloquear request.
"""
from __future__ import annotations

import os
import logging
import threading
import time
import unicodedata
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _normalize_sheet_name(s: str) -> str:
    """Pra matching tolerante: lowercase, sem acento, sem espaco/undescore."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return "".join(s.lower().split()).replace("_", "").replace("-", "")

# Lock global: Excel COM nao e thread-safe. Serializa conversoes.
_COM_LOCK = threading.Lock()

# Timeout maximo por conversao (segundos). Se Excel travar, levantamos
# RuntimeError pra nao bloquear o endpoint pra sempre.
_CONVERT_TIMEOUT_SEC = 60


class XlsxToPdfError(RuntimeError):
    """Erro na conversao xlsx -> pdf."""


def _import_com():
    """Import lazy do pywin32 — so disponivel no Windows com Office."""
    try:
        import pythoncom  # noqa: F401
        import win32com.client as w32
        return pythoncom, w32
    except ImportError as e:
        raise XlsxToPdfError(
            "pywin32 nao instalado. Rode: pip install pywin32"
        ) from e


def convert(xlsx_path: str, pdf_path: str, sheet_name: Optional[str] = None) -> dict:
    """Converte xlsx -> pdf usando Excel COM. Serializado por lock.

    Args:
        xlsx_path: caminho ABSOLUTO do xlsx de entrada (deve existir).
        pdf_path:  caminho ABSOLUTO do pdf de saida (sera sobrescrito).
        sheet_name: se fornecido, exporta apenas essa aba (matching tolerante
                    a acento/espaco/case). Se nao achar, loga warning e
                    exporta o workbook inteiro (fallback).

    Returns:
        dict com {"ok": True, "size_bytes": int, "took_sec": float,
                  "sheet_exported": str | None}

    Raises:
        XlsxToPdfError: se input nao existe, excel falha ou output invalido.
    """
    xlsx_path = os.path.abspath(xlsx_path)
    pdf_path = os.path.abspath(pdf_path)

    if not os.path.exists(xlsx_path):
        raise XlsxToPdfError(f"xlsx nao existe: {xlsx_path}")
    if os.path.getsize(xlsx_path) == 0:
        raise XlsxToPdfError(f"xlsx esta vazio: {xlsx_path}")

    # Garante que o diretorio de saida existe
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    # Remove PDF antigo pra evitar permissao conflito
    if os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except OSError:
            pass

    pythoncom, w32 = _import_com()

    with _COM_LOCK:
        start = time.monotonic()
        pythoncom.CoInitialize()
        excel = None
        wb = None
        try:
            excel = w32.Dispatch("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False
            excel.ScreenUpdating = False

            wb = excel.Workbooks.Open(xlsx_path, ReadOnly=True)

            # Escolhe o alvo da exportacao: aba especifica ou workbook inteiro.
            export_target = wb
            sheet_exportada: Optional[str] = None
            if sheet_name:
                alvo_norm = _normalize_sheet_name(sheet_name)
                achada = None
                for i in range(1, wb.Sheets.Count + 1):
                    sh = wb.Sheets.Item(i)
                    nome_sh = str(sh.Name)
                    if _normalize_sheet_name(nome_sh) == alvo_norm:
                        achada = sh
                        break
                if achada is not None:
                    export_target = achada
                    sheet_exportada = str(achada.Name)
                    logger.info(f"[xlsx->pdf] exportando apenas sheet '{sheet_exportada}' (pediu '{sheet_name}')")
                else:
                    sheets_disp = ", ".join(str(wb.Sheets.Item(i).Name) for i in range(1, wb.Sheets.Count + 1))
                    logger.warning(
                        f"[xlsx->pdf] sheet '{sheet_name}' nao achada em {xlsx_path}. "
                        f"Abas disponiveis: [{sheets_disp}]. Fallback: workbook inteiro."
                    )

            # Type=0 (xlTypePDF), Quality=0 (xlQualityStandard)
            export_target.ExportAsFixedFormat(
                Type=0,
                Filename=pdf_path,
                Quality=0,
                IncludeDocProperties=True,
                IgnorePrintAreas=False,
                OpenAfterPublish=False,
            )
            took = time.monotonic() - start

            if not os.path.exists(pdf_path):
                raise XlsxToPdfError(f"pdf nao foi gerado: {pdf_path}")
            size = os.path.getsize(pdf_path)
            if size < 500:
                raise XlsxToPdfError(f"pdf gerado muito pequeno ({size} bytes), suspeito")

            logger.info(
                f"[xlsx->pdf] OK src={xlsx_path} dst={pdf_path} "
                f"size={size} took={took:.2f}s sheet={sheet_exportada or 'ALL'}"
            )
            return {"ok": True, "size_bytes": size, "took_sec": round(took, 2),
                    "sheet_exported": sheet_exportada}

        except Exception as e:
            logger.error(f"[xlsx->pdf] FAIL src={xlsx_path}: {e}")
            raise XlsxToPdfError(f"Falha ao converter xlsx: {e}") from e
        finally:
            try:
                if wb is not None:
                    wb.Close(SaveChanges=False)
            except Exception:
                pass
            try:
                if excel is not None:
                    excel.Quit()
            except Exception:
                pass
            # Libera handles COM
            try:
                import gc
                del wb, excel
                gc.collect()
            except Exception:
                pass
            pythoncom.CoUninitialize()
