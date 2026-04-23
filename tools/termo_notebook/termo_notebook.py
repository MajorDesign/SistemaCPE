"""
CPE - Termo de Responsabilidade de Notebook Corporativo
---------------------------------------------------------
- Coleta especificacoes do notebook (placa mae, modelo, RAM, HD)
- Solicita nome completo + CPF do usuario
- Gera PDF pre-preenchido
- Faz login no sistema CPE e envia o PDF para a pasta "Termos Notebooks 2026"

Autor: CPE Tecnologia
"""

import os
import sys
import io
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
import requests

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
    Table, TableStyle, PageBreak
)
from reportlab.lib.units import cm
from reportlab.lib import colors


# =========================================================
# CONFIG
# =========================================================
# Versão é lida do arquivo VERSION (ao lado do .py ou dentro do bundle do PyInstaller).
# Atualizar SEMPRE o arquivo VERSION ao publicar uma nova build.
def _read_app_version():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    candidatos = [
        os.path.join(base, "VERSION"),
        os.path.join(os.path.dirname(base), "VERSION"),
    ]
    for p in candidatos:
        try:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        v = line.strip()
                        if v and not v.startswith("#"):
                            return v
        except Exception:
            pass
    return "0.0.0"

__version__ = _read_app_version()
APP_TITLE = f"CPE — Termo de Responsabilidade  v{__version__}"
PASTA_NOME_TARGET = "Termos Notebooks 2026"

def _resource(rel):
    """Resolve caminho de recurso (compativel com PyInstaller --onefile)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)

def _exe_dir():
    """Diretorio onde o EXE esta rodando (nao o temporario do PyInstaller)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(_exe_dir(), "config.ini")

def _load_config():
    """Lee config.ini ao lado do EXE (se existir). Fallback: env var, depois localhost."""
    import configparser
    if os.path.exists(CONFIG_PATH):
        try:
            cp = configparser.ConfigParser()
            cp.read(CONFIG_PATH, encoding="utf-8")
            url = cp.get("server", "url", fallback=None)
            if url:
                return url.strip().rstrip("/")
        except Exception as e:
            print(f"[CONFIG] erro lendo config.ini: {e}")
    env = os.environ.get("CPE_SERVER_URL")
    if env:
        return env.strip().rstrip("/")
    return "http://127.0.0.1:8000"

def _save_config(url):
    """Salva o URL do servidor em config.ini."""
    import configparser
    cp = configparser.ConfigParser()
    cp["server"] = {"url": url.strip().rstrip("/")}
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            cp.write(f)
        return True
    except Exception as e:
        print(f"[CONFIG] erro salvando: {e}")
        return False

SERVER_URL = _load_config()
LOGO_PATH = _resource("logo.png")

MESES_PT = {
    1:"JANEIRO",2:"FEVEREIRO",3:"MARCO",4:"ABRIL",5:"MAIO",6:"JUNHO",
    7:"JULHO",8:"AGOSTO",9:"SETEMBRO",10:"OUTUBRO",11:"NOVEMBRO",12:"DEZEMBRO"
}


# =========================================================
# COLETA DE HARDWARE (WMIC)
# =========================================================
def _wmic(obj, field):
    """Executa wmic e retorna o valor do campo (primeiro)."""
    try:
        p = subprocess.run(
            ["wmic", obj, "get", field, "/value"],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        for line in p.stdout.splitlines():
            if "=" in line:
                val = line.split("=", 1)[1].strip()
                if val:
                    return val
    except Exception as e:
        print(f"[WMIC] erro {obj} {field}: {e}")
    return ""


def _wmic_multi(obj, field):
    """Retorna lista de dicts de cada instancia."""
    try:
        p = subprocess.run(
            ["wmic", obj, "get", field, "/value"],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        rows, buf = [], {}
        for line in p.stdout.splitlines():
            line = line.strip()
            if not line:
                if buf:
                    rows.append(buf); buf = {}
            elif "=" in line:
                k, v = line.split("=", 1)
                buf[k.strip()] = v.strip()
        if buf:
            rows.append(buf)
        return rows
    except Exception as e:
        print(f"[WMIC-multi] erro: {e}")
        return []


def coletar_hardware():
    """Retorna dict com placa_mae, modelo_nb, serial, memoria, hd."""
    placa_mae = (_wmic("baseboard", "Manufacturer") + " " + _wmic("baseboard", "Product")).strip() or "N/A"
    modelo_nb = _wmic("csproduct", "Name") or _wmic("computersystem", "Model") or "N/A"
    serial = (
        _wmic("bios", "SerialNumber")
        or _wmic("csproduct", "IdentifyingNumber")
        or "N/A"
    ).strip() or "N/A"

    # RAM total
    mem_total = _wmic("computersystem", "TotalPhysicalMemory")
    try:
        mem_gb = round(int(mem_total) / (1024 ** 3))
        memoria = f"{mem_gb} GB"
    except Exception:
        memoria = "N/A"

    # HDs / SSDs
    discos = _wmic_multi("diskdrive", "model,size,mediatype,interfacetype")
    hd_parts = []
    for d in discos:
        size = d.get("Size", "")
        model = (d.get("Model", "") or "").strip()
        if not size or not size.isdigit():
            continue
        gb = round(int(size) / (1024 ** 3))
        if gb < 5:
            continue  # ignorar pendrives/SD
        hd_parts.append(f"{gb} GB ({model})" if model else f"{gb} GB")
    hd = " + ".join(hd_parts) if hd_parts else "N/A"

    return {
        "placa_mae": placa_mae,
        "modelo_nb": modelo_nb,
        "serial": serial,
        "memoria": memoria,
        "hd": hd,
    }


# =========================================================
# PDF: TERMO DE RESPONSABILIDADE
# =========================================================
def gerar_pdf(data):
    """data: dict com nome, cpf, placa_mae, modelo_nb, memoria, hd."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        topMargin=1.8 * cm, bottomMargin=2 * cm,
        title="Termo de Responsabilidade - Notebook Corporativo"
    )

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body", parent=styles["Normal"], fontName="Times-Roman",
        fontSize=11, leading=15, alignment=TA_JUSTIFY,
    )
    title = ParagraphStyle(
        "Title", parent=styles["Heading1"], fontName="Times-Bold",
        fontSize=13, leading=16, alignment=TA_CENTER, textColor=colors.black,
    )
    subtitle = ParagraphStyle(
        "Subtitle", parent=styles["Heading2"], fontName="Times-Bold",
        fontSize=12, leading=15, alignment=TA_CENTER, textColor=colors.black,
    )
    center = ParagraphStyle(
        "Center", parent=body, alignment=TA_CENTER,
    )

    story = []

    # -------- HEADER: logo + titulo --------
    logo_cell = ""
    if os.path.exists(LOGO_PATH):
        try:
            logo_cell = RLImage(LOGO_PATH, width=4.2 * cm, height=1.6 * cm)
        except Exception:
            logo_cell = ""

    title_cell = [
        Paragraph("<b>TERMO DE RESPONSABILIDADE</b>", title),
        Paragraph("<b>NOTEBOOK CORPORATIVO</b>", subtitle),
    ]
    header_tbl = Table(
        [[logo_cell, title_cell]],
        colWidths=[5 * cm, 11.5 * cm]
    )
    header_tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
        ("LINEAFTER", (0, 0), (0, -1), 0.8, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.8 * cm))

    # -------- PARAGRAFO 1 --------
    nome = (data.get("nome") or "").upper()
    cpf = data.get("cpf") or ""
    modelo = data.get("modelo_nb") or ""
    placa = data.get("placa_mae") or ""
    serial = data.get("serial") or ""
    mem = data.get("memoria") or ""
    hd = data.get("hd") or ""

    p1 = (
        f"Eu, <b>{nome}</b>, brasileiro, inscrito no CPF de nº <b>{cpf}</b>, "
        "mediante este instrumento de aceitação, responsabilizo-me pelo uso e conservação do notebook "
        f"<b>{modelo}</b>, nº de série/modelo: <b>{serial}</b>, placa-mãe: <b>{placa}</b>, "
        f"memória RAM: <b>{mem}</b>, armazenamento: <b>{hd}</b>, com bateria e carregador, "
        "de propriedade da CPE Equipamentos Topográficos Ltda, "
        "CNPJ 18.323.709/0001-93, endereço na av. Barão Homem de Melo, 4282 4º e 5º andares - Estoril, "
        "CEP 30494-270, Belo Horizonte/MG."
    )
    story.append(Paragraph(p1, body))
    story.append(Spacer(1, 0.4 * cm))

    p2 = (
        "Comprometo-me em caso de extravio e/ou dano, total ou parcial do aparelho citado acima, "
        "a ressarcir o proprietário dos prejuízos decorrentes. O valor do prejuízo poderá ser dividido e "
        "será descontado nos valores recebidos de comissão."
    )
    story.append(Paragraph(p2, body))
    story.append(Spacer(1, 0.4 * cm))

    p3 = (
        "Comprometo-me ainda, a utilizá-lo de forma estritamente para minhas atividades profissionais, "
        "no período em que exercer vínculo com a empresa CPE Equipamentos Topográficos, a contar desta data."
    )
    story.append(Paragraph(p3, body))
    story.append(Spacer(1, 0.4 * cm))

    p4 = (
        "Pastas, arquivos, documentos e programas disponibilizados/salvos neste são de direito da empresa "
        "e não podem ser repassados para fins que não sejam corporativos. Podendo o autor responder com "
        "desligamento com justa causa."
    )
    story.append(Paragraph(p4, body))
    story.append(Spacer(1, 0.4 * cm))

    p5 = (
        "Nestes termos, e após conferir e achar de acordo, declaro que recebi o bem relacionado e que o "
        "mesmo encontra-se em perfeita condição de uso."
    )
    story.append(Paragraph(p5, body))
    story.append(Spacer(1, 1.5 * cm))

    # -------- DATA --------
    hoje = datetime.now()
    data_str = f"Belo Horizonte, {hoje.day:02d} de {MESES_PT[hoje.month]} de {hoje.year}."
    story.append(Paragraph(data_str, center))
    story.append(Spacer(1, 1.5 * cm))

    # -------- ASSINATURA --------
    story.append(Paragraph("____________________________________________", center))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(f"<b>{nome}</b>", center))

    doc.build(story)
    return buf.getvalue()


# =========================================================
# API: LOGIN + UPLOAD
# =========================================================
class ApiClient:
    def __init__(self, base_url):
        self.base = base_url.rstrip("/")
        self.token = None
        self.session = requests.Session()

    def _check_api_response(self, r, contexto):
        """Detecta se o servidor respondeu como um servidor errado (Apache/HTML)
        em vez do FastAPI esperado. Lança exceção com mensagem clara."""
        ct = (r.headers.get("Content-Type") or "").lower()
        if "text/html" in ct or r.text.lstrip().lower().startswith("<!doctype"):
            raise Exception(
                f"URL do servidor incorreta.\n\n"
                f"O endereço {self.base} respondeu como um servidor Web comum "
                f"(ex: Apache/IIS), não o FastAPI do CPE.\n\n"
                f"Clique em \"Configurar servidor\" e informe a URL correta, "
                f"por exemplo: http://172.16.0.10:8000"
            )

    def login(self, credential, password):
        try:
            r = self.session.post(
                f"{self.base}/api/auth/login",
                json={"credential": credential, "password": password},
                timeout=15,
            )
        except requests.exceptions.ConnectionError:
            raise Exception(
                f"Não foi possível conectar ao servidor em {self.base}.\n\n"
                f"Verifique se o FastAPI está rodando e se o IP/porta estão corretos "
                f"em \"Configurar servidor\"."
            )
        except requests.exceptions.Timeout:
            raise Exception(f"Tempo esgotado ao conectar em {self.base}.")

        self._check_api_response(r, "login")
        if r.status_code == 401:
            raise Exception("Email/usuário ou senha incorretos.")
        if r.status_code != 200:
            raise Exception(f"Erro no login ({r.status_code}): {r.text[:200]}")
        data = r.json()
        self.token = data.get("access_token")
        if not self.token:
            raise Exception("Servidor nao retornou token")
        return data.get("user") or {}

    def _headers(self):
        return {"X-Auth-Token": self.token or ""}

    def listar_pastas(self):
        r = self.session.get(
            f"{self.base}/api/contratos/pastas",
            headers=self._headers(), timeout=15,
        )
        self._check_api_response(r, "listar pastas")
        if r.status_code != 200:
            raise Exception(f"Erro ao listar pastas ({r.status_code}): {r.text[:200]}")
        return r.json().get("pastas", [])

    def ensure_pasta(self, nome, user):
        """Garante que exista uma subpasta com 'nome' no grupo do usuário.
        Se não existir, cria dentro da pasta raiz do grupo."""
        pastas = self.listar_pastas()
        alvo = next((p for p in pastas if str(p.get("nome","")).strip().lower() == nome.lower()), None)
        if alvo:
            return alvo
        # Acha a pasta raiz do grupo do usuário
        gid = user.get("group_id") if isinstance(user, dict) else None
        raiz = next(
            (p for p in pastas if p.get("is_root") and (gid is None or p.get("group_id") == gid)),
            None,
        )
        if not raiz:
            raise Exception(
                "Seu usuário não está vinculado a um grupo com pasta de contratos. "
                "Peça ao administrador para configurar."
            )
        r = self.session.post(
            f"{self.base}/api/contratos/pastas",
            headers={**self._headers(), "Content-Type": "application/json"},
            json={"parent_id": raiz["id"], "nome": nome},
            timeout=15,
        )
        self._check_api_response(r, "criar pasta")
        if r.status_code not in (200, 201):
            raise Exception(f"Erro ao criar pasta '{nome}' ({r.status_code}): {r.text[:200]}")
        # Relista para pegar o registro completo (com id definitivo)
        pastas = self.listar_pastas()
        alvo = next((p for p in pastas if str(p.get("nome","")).strip().lower() == nome.lower()), None)
        if not alvo:
            raise Exception(f"Pasta '{nome}' foi criada mas não está visível.")
        return alvo

    def upload_contrato(self, pasta_id, nome, descricao, filename, content_bytes):
        files = {"file": (filename, content_bytes, "application/pdf")}
        data = {"pasta_id": str(pasta_id), "nome": nome, "descricao": descricao or ""}
        r = self.session.post(
            f"{self.base}/api/contratos",
            headers=self._headers(), data=data, files=files, timeout=30,
        )
        self._check_api_response(r, "upload")
        if r.status_code != 200:
            raise Exception(f"Erro upload ({r.status_code}): {r.text[:200]}")
        return r.json()

    def submit_termo(self, nome, descricao, filename, content_bytes):
        """Envia termo direto para a pasta T.I. (qualquer usuário autenticado pode)."""
        files = {"file": (filename, content_bytes, "application/pdf")}
        data = {"nome": nome, "descricao": descricao or ""}
        r = self.session.post(
            f"{self.base}/api/agents/termo-notebook/submit",
            headers=self._headers(), data=data, files=files, timeout=30,
        )
        self._check_api_response(r, "enviar termo")
        if r.status_code != 200:
            raise Exception(f"Erro ao enviar termo ({r.status_code}): {r.text[:200]}")
        return r.json()


# =========================================================
# GUI
# =========================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("560x560")
        self.resizable(False, False)
        self.configure(bg="#f3f4f6")

        # Hardware ainda sera coletado em background
        self.hw = {
            "placa_mae": "Detectando...",
            "modelo_nb": "Detectando...",
            "serial":    "Detectando...",
            "memoria":   "Detectando...",
            "hd":        "Detectando...",
        }
        self.api = ApiClient(SERVER_URL)

        self._build_ui()

        # Inicia coleta de HW em thread separada apos janela renderizar
        self.after(50, self._iniciar_coleta_hw)

    def _iniciar_coleta_hw(self):
        t = threading.Thread(target=self._coletar_hw_worker, daemon=True)
        t.start()

    def _coletar_hw_worker(self):
        try:
            hw = coletar_hardware()
        except Exception as e:
            hw = {"placa_mae":"Erro","modelo_nb":"Erro","serial":"Erro","memoria":"Erro","hd":str(e)[:60]}
        # Atualizar UI no thread principal
        self.after(0, lambda: self._atualizar_hw_labels(hw))

    def _atualizar_hw_labels(self, hw):
        self.hw = hw
        self.lbl_placa.config(text=hw.get("placa_mae", "—"))
        self.lbl_modelo.config(text=hw.get("modelo_nb", "—"))
        self.lbl_serial.config(text=hw.get("serial", "—"))
        self.lbl_ram.config(text=hw.get("memoria", "—"))
        self.lbl_hd.config(text=hw.get("hd", "—"))

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg="#1f2937", height=64)
        header.pack(fill="x")
        tk.Label(
            header, text="CPE — Termo de Responsabilidade",
            fg="white", bg="#1f2937",
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left", padx=20, pady=16)
        tk.Label(
            header, text="Notebook Corporativo",
            fg="#FFC107", bg="#1f2937",
            font=("Segoe UI", 10),
        ).pack(side="left", padx=0, pady=16)

        right_frame = tk.Frame(header, bg="#1f2937")
        right_frame.pack(side="right", padx=16, pady=14)
        self.lbl_server = tk.Label(
            right_frame, text=f"Servidor: {SERVER_URL}",
            fg="#9ca3af", bg="#1f2937", font=("Segoe UI", 8),
        )
        self.lbl_server.pack(side="top", anchor="e")
        tk.Button(
            right_frame, text="⚙ Configurar servidor",
            bg="#374151", fg="#FFC107", bd=0, relief="flat",
            font=("Segoe UI", 8), cursor="hand2", padx=6, pady=2,
            command=self._configurar_servidor,
        ).pack(side="top", anchor="e", pady=(2, 0))

        body = tk.Frame(self, bg="#f3f4f6", padx=20, pady=16)
        body.pack(fill="both", expand=True)

        # --- HW info ---
        lf1 = tk.LabelFrame(body, text="  Informações do notebook (detectadas automaticamente)  ",
                            bg="#fff", fg="#374151", font=("Segoe UI", 9, "bold"),
                            padx=12, pady=10)
        lf1.pack(fill="x", pady=(0, 14))

        def row(parent, label, value, r):
            tk.Label(parent, text=label, bg="#fff", fg="#6b7280",
                     font=("Segoe UI", 9)).grid(row=r, column=0, sticky="w", pady=3)
            v = tk.Label(parent, text=value, bg="#fff", fg="#111827",
                         font=("Consolas", 10, "bold"), anchor="w", wraplength=360, justify="left")
            v.grid(row=r, column=1, sticky="w", padx=(14, 0), pady=3)
            return v

        self.lbl_placa  = row(lf1, "Placa-mãe:",     self.hw["placa_mae"], 0)
        self.lbl_modelo = row(lf1, "Modelo:",         self.hw["modelo_nb"], 1)
        self.lbl_serial = row(lf1, "Nº de série:",    self.hw["serial"],    2)
        self.lbl_ram    = row(lf1, "Memória RAM:",    self.hw["memoria"],   3)
        self.lbl_hd     = row(lf1, "Armazenamento:",  self.hw["hd"],        4)

        # --- Dados do usuario ---
        lf2 = tk.LabelFrame(body, text="  Seus dados  ",
                            bg="#fff", fg="#374151", font=("Segoe UI", 9, "bold"),
                            padx=12, pady=10)
        lf2.pack(fill="x", pady=(0, 14))

        tk.Label(lf2, text="Nome completo:", bg="#fff", font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", pady=4)
        self.ent_nome = tk.Entry(lf2, font=("Segoe UI", 10), width=44, relief="solid", bd=1)
        self.ent_nome.grid(row=0, column=1, padx=(14, 0), pady=4, sticky="ew")

        tk.Label(lf2, text="CPF:", bg="#fff", font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", pady=4)
        self.ent_cpf = tk.Entry(lf2, font=("Segoe UI", 10), width=22, relief="solid", bd=1)
        self.ent_cpf.grid(row=1, column=1, padx=(14, 0), pady=4, sticky="w")
        self.ent_cpf.bind("<KeyRelease>", self._mask_cpf)

        tk.Label(lf2, text="Data:", bg="#fff", font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w", pady=4)
        hoje = datetime.now().strftime("%d/%m/%Y")
        tk.Label(lf2, text=hoje, bg="#fff", fg="#111827",
                 font=("Consolas", 10, "bold")).grid(row=2, column=1, sticky="w", padx=(14, 0), pady=4)

        # Status
        self.lbl_status = tk.Label(body, text="", bg="#f3f4f6", fg="#6b7280",
                                    font=("Segoe UI", 9), wraplength=500, justify="left")
        self.lbl_status.pack(fill="x", pady=(0, 8))

        # Botões — fluxo em 2 passos: (1) Gerar/visualizar, (2) Enviar
        self._pdf_bytes = None
        self._pdf_tmp_path = None

        btn_frame = tk.Frame(body, bg="#f3f4f6")
        btn_frame.pack(fill="x")

        self.btn_primary = tk.Button(
            btn_frame, text="📄  Gerar e Visualizar Termo",
            bg="#FFC107", fg="#1f2937", font=("Segoe UI", 11, "bold"),
            relief="flat", padx=18, pady=10, cursor="hand2",
            command=self._gerar_e_visualizar
        )
        self.btn_primary.pack(side="right")

        self.btn_secondary = tk.Button(
            btn_frame, text="Cancelar",
            bg="#e5e7eb", fg="#6b7280", font=("Segoe UI", 10),
            relief="flat", padx=14, pady=10, cursor="hand2",
            command=self.destroy
        )
        self.btn_secondary.pack(side="right", padx=(0, 8))

    def _configurar_servidor(self):
        global SERVER_URL
        atual = SERVER_URL
        novo = simpledialog.askstring(
            "Configurar servidor",
            "URL do servidor CPE (exemplo: http://172.16.12.151:8000):",
            initialvalue=atual, parent=self,
        )
        if not novo: return
        novo = novo.strip().rstrip("/")
        if not novo.startswith("http"):
            novo = "http://" + novo
        if _save_config(novo):
            SERVER_URL = novo
            self.api = ApiClient(SERVER_URL)
            self.lbl_server.config(text=f"Servidor: {SERVER_URL}")
            messagebox.showinfo("Configurado", f"Servidor atualizado para:\n{novo}\n\nArquivo salvo em:\n{CONFIG_PATH}")
        else:
            messagebox.showerror("Erro", f"Não foi possível salvar em:\n{CONFIG_PATH}\n\nVerifique permissão de escrita.")

    # ---- CPF mask ----
    def _mask_cpf(self, event=None):
        raw = "".join(c for c in self.ent_cpf.get() if c.isdigit())[:11]
        if len(raw) > 9:
            masked = f"{raw[:3]}.{raw[3:6]}.{raw[6:9]}-{raw[9:]}"
        elif len(raw) > 6:
            masked = f"{raw[:3]}.{raw[3:6]}.{raw[6:]}"
        elif len(raw) > 3:
            masked = f"{raw[:3]}.{raw[3:]}"
        else:
            masked = raw
        self.ent_cpf.delete(0, tk.END)
        self.ent_cpf.insert(0, masked)

    def _set_status(self, msg, color="#6b7280"):
        self.lbl_status.config(text=msg, fg=color)
        self.update()

    def _validar_dados(self):
        """Valida nome/CPF/hardware. Retorna (nome, cpf) ou None."""
        nome = self.ent_nome.get().strip()
        cpf = self.ent_cpf.get().strip()
        if not nome or len(nome.split()) < 2:
            messagebox.showwarning("Atenção", "Informe o nome completo (nome + sobrenome).")
            return None
        digits = "".join(c for c in cpf if c.isdigit())
        if len(digits) != 11:
            messagebox.showwarning("Atenção", "CPF inválido. Deve ter 11 dígitos.")
            return None
        if self.hw.get("placa_mae") == "Detectando...":
            messagebox.showinfo("Aguarde", "Ainda detectando o hardware. Aguarde alguns segundos.")
            return None
        return nome, cpf

    def _gerar_e_visualizar(self):
        """Etapa 1: gera o PDF, salva em arquivo temporário e abre no visualizador.
        Depois troca o botão para o modo 'Enviar Termo'."""
        dados = self._validar_dados()
        if not dados:
            return
        nome, cpf = dados

        try:
            self._set_status("Gerando PDF...")
            self.btn_primary.config(state="disabled", text="Gerando...")
            self.update_idletasks()

            pdf_bytes = gerar_pdf({
                "nome": nome, "cpf": cpf,
                "placa_mae": self.hw["placa_mae"],
                "modelo_nb": self.hw["modelo_nb"],
                "serial":    self.hw["serial"],
                "memoria":   self.hw["memoria"],
                "hd":        self.hw["hd"],
            })

            if len(pdf_bytes) > 2 * 1024 * 1024:
                raise Exception(f"PDF gerado tem {len(pdf_bytes)//1024} KB (limite: 2048 KB).")

            # Salvar em arquivo temporário (%TEMP%)
            import tempfile
            primeiro = nome.split()[0]
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_nome = "".join(c if c.isalnum() else "_" for c in primeiro)
            tmp_name = f"termo_{safe_nome}_{stamp}.pdf"
            tmp_path = os.path.join(tempfile.gettempdir(), tmp_name)
            with open(tmp_path, "wb") as f:
                f.write(pdf_bytes)

            self._pdf_bytes = pdf_bytes
            self._pdf_tmp_path = tmp_path

            # Abrir no visualizador padrão do sistema (Adobe / Edge / navegador)
            try:
                os.startfile(tmp_path)
            except Exception as e:
                # Fallback: mostrar caminho ao usuário
                messagebox.showwarning(
                    "Abra manualmente",
                    f"Não consegui abrir o PDF automaticamente.\n\nAbra manualmente:\n{tmp_path}"
                )

            # Mudar botões para estado "enviar"
            self._set_status("Pré-visualização gerada. Confira o termo e clique em ENVIAR quando estiver pronto.", "#2563eb")
            self.btn_primary.config(
                text="✉  Enviar Termo para T.I.",
                bg="#16A34A", fg="#ffffff",
                activebackground="#15803d",
                state="normal",
                command=self._enviar_termo,
            )
            self.btn_secondary.config(
                text="↻  Gerar de novo",
                bg="#e5e7eb", fg="#374151",
                command=self._resetar_pdf,
            )

        except Exception as e:
            self._set_status(f"Erro ao gerar PDF: {e}", "#DC2626")
            messagebox.showerror("Erro", str(e))
            self.btn_primary.config(state="normal", text="📄  Gerar e Visualizar Termo")

    def _resetar_pdf(self):
        """Permite editar os dados e gerar um PDF novo."""
        self._pdf_bytes = None
        try:
            if self._pdf_tmp_path and os.path.exists(self._pdf_tmp_path):
                os.remove(self._pdf_tmp_path)
        except Exception:
            pass
        self._pdf_tmp_path = None
        self._set_status("")
        self.btn_primary.config(
            text="📄  Gerar e Visualizar Termo",
            bg="#FFC107", fg="#1f2937",
            activebackground="#F59E0B",
            command=self._gerar_e_visualizar,
        )
        self.btn_secondary.config(
            text="Cancelar",
            bg="#e5e7eb", fg="#6b7280",
            command=self.destroy,
        )

    def _enviar_termo(self):
        """Etapa 2: faz login e envia o PDF já gerado para a pasta T.I."""
        if not self._pdf_bytes:
            messagebox.showwarning("Atenção", "Gere o termo antes de enviar.")
            return

        nome, cpf = self._validar_dados() or (None, None)
        if not nome:
            return

        self.btn_primary.config(state="disabled", text="Enviando...")

        try:
            # 1) LOGIN
            self._set_status("Autenticando no servidor...")
            login_win = LoginDialog(self)
            self.wait_window(login_win)
            creds = login_win.result
            if not creds:
                self._set_status("Envio cancelado.", "#DC2626")
                self.btn_primary.config(state="normal", text="✉  Enviar Termo para T.I.")
                return

            user = self.api.login(creds["cred"], creds["pwd"])
            self._set_status(f"Autenticado como {user.get('name','')}. Enviando termo para T.I...")

            # 2) Upload via endpoint dedicado (pasta fixa T.I. — qualquer user pode)
            primeiro = nome.split()[0]
            ultimo = nome.split()[-1] if len(nome.split()) > 1 else ""
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"termo_{primeiro}_{ultimo}_{stamp}.pdf"
            nome_contrato = f"Termo de Responsabilidade - {nome}"
            descricao = (f"Notebook {self.hw['modelo_nb']} | SN: {self.hw['serial']} | "
                         f"Placa-mãe: {self.hw['placa_mae']} | "
                         f"RAM: {self.hw['memoria']} | Storage: {self.hw['hd']}")

            res = self.api.submit_termo(nome_contrato, descricao, filename, self._pdf_bytes)

            self._set_status("✓ Enviado com sucesso!", "#16A34A")
            messagebox.showinfo(
                "Sucesso",
                f"Termo enviado para a T.I.\n\nPasta: {res.get('pasta','Termos Notebooks 2026')}\nArquivo: {filename}"
            )
            self.destroy()

        except Exception as e:
            self._set_status(f"Erro: {e}", "#DC2626")
            messagebox.showerror("Erro", str(e))
            self.btn_primary.config(state="normal", text="✉  Enviar Termo para T.I.")


# =========================================================
# LOGIN DIALOG
# =========================================================
class LoginDialog(tk.Toplevel):
    """Modal de login com layout moderno — usa grid para garantir que o botão
    Entrar sempre apareça, mesmo em Windows com DPI escalado."""

    # Paleta
    BG        = "#ffffff"
    BG_HEADER = "#1f2937"
    GOLD      = "#FFC107"
    GOLD_HV   = "#F59E0B"
    MUTED     = "#6b7280"
    TEXT      = "#111827"
    BORDER    = "#d1d5db"
    BORDER_FOCUS = "#FFC107"

    def __init__(self, parent):
        super().__init__(parent)
        self.result = None
        self.title("Login CPE")
        self.configure(bg=self.BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # ----- Layout: grid com rows expansíveis -----
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)       # corpo (cresce)
        self.rowconfigure(2, weight=0)       # rodapé (fixo)

        # ---- HEADER (banner escuro) ----
        header = tk.Frame(self, bg=self.BG_HEADER, height=90)
        header.grid(row=0, column=0, sticky="nsew")
        header.grid_propagate(False)
        tk.Label(header, text="🔐", bg=self.BG_HEADER, fg=self.GOLD,
                 font=("Segoe UI Emoji", 22)).pack(pady=(14, 0))
        tk.Label(header, text="Autenticação CPE", bg=self.BG_HEADER, fg="#ffffff",
                 font=("Segoe UI", 13, "bold")).pack()
        tk.Label(header, text="Informe suas credenciais para enviar o termo",
                 bg=self.BG_HEADER, fg="#9CA3AF",
                 font=("Segoe UI", 9)).pack(pady=(2, 8))

        # ---- CORPO (campos) ----
        body = tk.Frame(self, bg=self.BG, padx=28, pady=22)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)

        # Usuário
        tk.Label(body, text="Email ou usuário", bg=self.BG, fg=self.TEXT,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        self.ent_cred = tk.Entry(body, font=("Segoe UI", 11), bd=0,
                                 highlightthickness=1,
                                 highlightbackground=self.BORDER,
                                 highlightcolor=self.BORDER_FOCUS)
        self.ent_cred.grid(row=1, column=0, sticky="ew", ipady=8, pady=(4, 14))

        # Senha
        tk.Label(body, text="Senha", bg=self.BG, fg=self.TEXT,
                 font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w")
        pwd_wrap = tk.Frame(body, bg=self.BG)
        pwd_wrap.grid(row=3, column=0, sticky="ew", pady=(4, 4))
        pwd_wrap.columnconfigure(0, weight=1)

        self.ent_pwd = tk.Entry(pwd_wrap, font=("Segoe UI", 11), bd=0,
                                show="•",
                                highlightthickness=1,
                                highlightbackground=self.BORDER,
                                highlightcolor=self.BORDER_FOCUS)
        self.ent_pwd.grid(row=0, column=0, sticky="ew", ipady=8)

        self._show_pwd = False
        self.btn_eye = tk.Button(pwd_wrap, text="👁", font=("Segoe UI Emoji", 11),
                                 bg=self.BG, bd=0, cursor="hand2",
                                 activebackground=self.BG,
                                 command=self._toggle_pwd)
        self.btn_eye.grid(row=0, column=1, padx=(6, 0))

        # Mensagem de rodapé do corpo
        tk.Label(body, text="Pressione Enter para entrar.", bg=self.BG, fg=self.MUTED,
                 font=("Segoe UI", 8)).grid(row=4, column=0, sticky="w", pady=(10, 0))

        # ---- RODAPÉ (botões — SEMPRE visível) ----
        footer = tk.Frame(self, bg="#F9FAFB", height=72)
        footer.grid(row=2, column=0, sticky="nsew")
        footer.grid_propagate(False)
        footer.columnconfigure(0, weight=1)

        btns = tk.Frame(footer, bg="#F9FAFB")
        btns.grid(row=0, column=0, sticky="e", padx=20, pady=16)

        btn_cancel = tk.Button(btns, text="Cancelar",
                               bg="#e5e7eb", fg="#374151",
                               activebackground="#d1d5db",
                               relief="flat", bd=0, cursor="hand2",
                               font=("Segoe UI", 10),
                               padx=18, pady=10,
                               command=self._cancel)
        btn_cancel.pack(side="left", padx=(0, 8))

        btn_ok = tk.Button(btns, text="Entrar  ➔",
                           bg=self.GOLD, fg=self.TEXT,
                           activebackground=self.GOLD_HV,
                           relief="flat", bd=0, cursor="hand2",
                           font=("Segoe UI", 10, "bold"),
                           padx=24, pady=10,
                           command=self._ok)
        btn_ok.pack(side="left")

        # Bindings
        self.ent_cred.focus_set()
        self.bind("<Return>", lambda _: self._ok())
        self.bind("<Escape>", lambda _: self._cancel())

        # Centralizar na tela depois que o widget calcular tamanho real
        self.update_idletasks()
        w, h = 480, 440
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(480, 440)

    def _toggle_pwd(self):
        self._show_pwd = not self._show_pwd
        self.ent_pwd.configure(show="" if self._show_pwd else "•")

    def _ok(self):
        c = self.ent_cred.get().strip()
        p = self.ent_pwd.get()
        if not c or not p:
            messagebox.showwarning("Atenção", "Preencha todos os campos.", parent=self)
            return
        self.result = {"cred": c, "pwd": p}
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    try:
        App().mainloop()
    except Exception as e:
        messagebox.showerror("Erro fatal", str(e))
