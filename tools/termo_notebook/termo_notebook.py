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
APP_TITLE = "CPE — Termo de Responsabilidade"
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

    def login(self, credential, password):
        r = self.session.post(
            f"{self.base}/api/auth/login",
            json={"credential": credential, "password": password},
            timeout=15,
        )
        if r.status_code != 200:
            raise Exception(f"Credenciais invalidas ({r.status_code}): {r.text}")
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
        if r.status_code != 200:
            raise Exception(f"Erro ao listar pastas: {r.text}")
        return r.json().get("pastas", [])

    def upload_contrato(self, pasta_id, nome, descricao, filename, content_bytes):
        files = {"file": (filename, content_bytes, "application/pdf")}
        data = {"pasta_id": str(pasta_id), "nome": nome, "descricao": descricao or ""}
        r = self.session.post(
            f"{self.base}/api/contratos",
            headers=self._headers(), data=data, files=files, timeout=30,
        )
        if r.status_code != 200:
            raise Exception(f"Erro upload ({r.status_code}): {r.text}")
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

        # Botões
        btn_frame = tk.Frame(body, bg="#f3f4f6")
        btn_frame.pack(fill="x")
        self.btn_confirmar = tk.Button(
            btn_frame, text="✓  Confirmar e Enviar",
            bg="#FFC107", fg="#1f2937", font=("Segoe UI", 11, "bold"),
            relief="flat", padx=18, pady=10, cursor="hand2",
            command=self._confirmar
        )
        self.btn_confirmar.pack(side="right")

        self.btn_cancelar = tk.Button(
            btn_frame, text="Cancelar",
            bg="#e5e7eb", fg="#6b7280", font=("Segoe UI", 10),
            relief="flat", padx=14, pady=10, cursor="hand2",
            command=self.destroy
        )
        self.btn_cancelar.pack(side="right", padx=(0, 8))

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

    def _confirmar(self):
        nome = self.ent_nome.get().strip()
        cpf = self.ent_cpf.get().strip()
        if not nome or len(nome.split()) < 2:
            messagebox.showwarning("Atenção", "Informe o nome completo (nome + sobrenome).")
            return
        digits = "".join(c for c in cpf if c.isdigit())
        if len(digits) != 11:
            messagebox.showwarning("Atenção", "CPF inválido. Deve ter 11 dígitos.")
            return
        if self.hw.get("placa_mae") == "Detectando...":
            messagebox.showinfo("Aguarde", "Ainda detectando o hardware do notebook. Aguarde alguns segundos.")
            return

        if not messagebox.askyesno("Confirmar envio",
                                   f"Confirma o envio do termo?\n\nNome: {nome}\nCPF: {cpf}\n"
                                   f"Modelo: {self.hw['modelo_nb']}"):
            return

        self.btn_confirmar.config(state="disabled", text="Processando...")

        try:
            # 1) LOGIN
            self._set_status("Autenticando no servidor...")
            login_win = LoginDialog(self)
            self.wait_window(login_win)
            creds = login_win.result
            if not creds:
                self.btn_confirmar.config(state="normal", text="✓  Confirmar e Enviar")
                self._set_status("Envio cancelado.", "#DC2626")
                return

            user = self.api.login(creds["cred"], creds["pwd"])
            self._set_status(f"Autenticado como {user.get('name','')}. Buscando pasta de destino...")

            # 2) Buscar pasta "Termos Notebooks 2026"
            pastas = self.api.listar_pastas()
            alvo = next((p for p in pastas if str(p.get("nome", "")).strip().lower() == PASTA_NOME_TARGET.lower()), None)
            if not alvo:
                raise Exception(
                    f"Pasta '{PASTA_NOME_TARGET}' não encontrada ou você não tem acesso. "
                    "Peça para o administrador criar essa pasta dentro do seu grupo."
                )

            # 3) Gerar PDF
            self._set_status("Gerando PDF...")
            pdf_bytes = gerar_pdf({
                "nome": nome, "cpf": cpf,
                "placa_mae": self.hw["placa_mae"],
                "modelo_nb": self.hw["modelo_nb"],
                "serial":    self.hw["serial"],
                "memoria":   self.hw["memoria"],
                "hd":        self.hw["hd"],
            })

            # Limite do servidor: 2 MB
            if len(pdf_bytes) > 2 * 1024 * 1024:
                raise Exception(f"PDF gerado tem {len(pdf_bytes)//1024} KB (limite: 2048 KB).")

            # 4) Upload
            self._set_status(f"Enviando {len(pdf_bytes)//1024} KB para o servidor...")
            primeiro = nome.split()[0]
            ultimo = nome.split()[-1] if len(nome.split()) > 1 else ""
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"termo_{primeiro}_{ultimo}_{stamp}.pdf"

            nome_contrato = f"Termo de Responsabilidade - {nome}"
            descricao = (f"Notebook {self.hw['modelo_nb']} | SN: {self.hw['serial']} | "
                         f"Placa-mãe: {self.hw['placa_mae']} | "
                         f"RAM: {self.hw['memoria']} | Storage: {self.hw['hd']}")

            res = self.api.upload_contrato(alvo["id"], nome_contrato, descricao, filename, pdf_bytes)

            self._set_status("✓ Enviado com sucesso!", "#16A34A")
            messagebox.showinfo("Sucesso",
                                f"Termo enviado para a pasta '{PASTA_NOME_TARGET}'.\n\n"
                                f"Arquivo: {filename}")
            self.destroy()

        except Exception as e:
            self._set_status(f"Erro: {e}", "#DC2626")
            messagebox.showerror("Erro", str(e))
            self.btn_confirmar.config(state="normal", text="✓  Confirmar e Enviar")


# =========================================================
# LOGIN DIALOG
# =========================================================
class LoginDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.result = None
        self.title("Login CPE")
        self.geometry("360x220")
        self.resizable(False, False)
        self.configure(bg="#f3f4f6")
        self.transient(parent)
        self.grab_set()

        tk.Label(self, text="Autenticação CPE", bg="#f3f4f6",
                 font=("Segoe UI", 12, "bold"), fg="#111827").pack(pady=(16, 4))
        tk.Label(self, text="Informe suas credenciais do sistema", bg="#f3f4f6",
                 font=("Segoe UI", 9), fg="#6b7280").pack(pady=(0, 10))

        frm = tk.Frame(self, bg="#f3f4f6")
        frm.pack(padx=20, fill="x")

        tk.Label(frm, text="Email ou usuário:", bg="#f3f4f6", font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", pady=4)
        self.ent_cred = tk.Entry(frm, font=("Segoe UI", 10), width=32, relief="solid", bd=1)
        self.ent_cred.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        tk.Label(frm, text="Senha:", bg="#f3f4f6", font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w", pady=4)
        self.ent_pwd = tk.Entry(frm, font=("Segoe UI", 10), show="•", width=32, relief="solid", bd=1)
        self.ent_pwd.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        btns = tk.Frame(self, bg="#f3f4f6")
        btns.pack(fill="x", padx=20, pady=(8, 16))
        tk.Button(btns, text="Cancelar", bg="#e5e7eb", fg="#374151",
                  relief="flat", padx=14, pady=6, font=("Segoe UI", 10),
                  command=self._cancel).pack(side="right", padx=(6, 0))
        tk.Button(btns, text="Entrar", bg="#FFC107", fg="#1f2937",
                  relief="flat", padx=18, pady=6, font=("Segoe UI", 10, "bold"),
                  command=self._ok).pack(side="right")

        self.ent_cred.focus_set()
        self.bind("<Return>", lambda _: self._ok())
        self.bind("<Escape>", lambda _: self._cancel())

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
