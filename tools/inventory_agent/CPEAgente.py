#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CPE Control — Agente de Inventário T.I.  v1.3.0
Arquivo único: instala deps, registra startup, ícone na bandeja.
"""

# ══════════════════════════════════════════════════════════════
VERSAO     = "1.3.2"
API_URL    = "http://127.0.0.1:8000"
AGENT_KEY  = "cpe-inv-2026"
INTERVAL   = 300
TIMEOUT_S  = 15
LOCATION_ESTADO = ""
LOCATION_CIDADE = ""
# ══════════════════════════════════════════════════════════════

import os, sys, subprocess, time, json, platform, socket
import logging, argparse, tempfile, threading
from datetime import datetime

# ─── Log (arquivo; stdout só se disponível) ───────────────────
_DIR    = os.path.dirname(os.path.abspath(__file__))
_LOGF   = os.path.join(_DIR, "cpe_agent.log")
_hdlrs  = []
try:    _hdlrs.append(logging.FileHandler(_LOGF, encoding="utf-8"))
except Exception: pass
if sys.stdout:
    try: _hdlrs.append(logging.StreamHandler(sys.stdout))
    except Exception: pass
logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [AGENTE-CPE] %(levelname)s %(message)s",
    handlers=_hdlrs or [logging.NullHandler()])
log = logging.getLogger(__name__)

# ─── tkinter (built-in, sempre disponível) ────────────────────
import tkinter as tk
from tkinter import ttk

# ══════════════════════════════════════════════════════════════
#  Instala deps externas; mostra mini-janela e reinicia se faltar
# ══════════════════════════════════════════════════════════════
_PKGS = ["psutil>=5.9", "requests>=2.31", "pystray>=0.19", "Pillow>=10.0"]

def _deps_ok() -> bool:
    for m in ("psutil", "requests", "pystray", "PIL"):
        try: __import__(m)
        except ImportError: return False
    return True

if not _deps_ok():
    def _instalar():
        root = tk.Tk()
        root.title("CPE Control")
        root.geometry("340x160")
        root.resizable(False, False)
        root.configure(bg="#111827")
        root.overrideredirect(True)
        root.update_idletasks()
        root.geometry(f"+{(root.winfo_screenwidth()-340)//2}+{(root.winfo_screenheight()-160)//2}")
        outer = tk.Frame(root, bg="#374151", padx=1, pady=1)
        outer.pack(fill="both", expand=True)
        inner = tk.Frame(outer, bg="#111827")
        inner.pack(fill="both", expand=True)
        tk.Label(inner, text="CPE Control — Agente T.I.", bg="#111827",
                 fg="#FFC107", font=("Segoe UI", 11, "bold")).pack(pady=(18,4))
        lbl = tk.Label(inner, text="Instalando dependências...",
                       bg="#111827", fg="#9ca3af", font=("Segoe UI", 9))
        lbl.pack()
        pb = ttk.Progressbar(inner, mode="indeterminate", length=280)
        pb.pack(pady=10); pb.start(8)
        def _run():
            subprocess.run([sys.executable, "-m", "pip", "install", "-q"] + _PKGS,
                           capture_output=True)
            root.after(0, lbl.configure, {"text": "Reiniciando..."})
            time.sleep(0.5)
            subprocess.Popen([sys.executable] + sys.argv)
            root.after(0, root.destroy)
        threading.Thread(target=_run, daemon=True).start()
        root.mainloop()
        sys.exit(0)
    _instalar()

import psutil, requests, pystray
from PIL import Image, ImageDraw

# ══════════════════════════════════════════════════════════════
#  Cores
# ══════════════════════════════════════════════════════════════
C_BG = "#111827"; C_CARD = "#1f2937"; C_ACCENT = "#FFC107"
C_TEXT = "#f9fafb"; C_MUTED = "#9ca3af"
C_OK = "#22c55e"; C_ERR = "#ef4444"; C_BORDER = "#374151"

# ══════════════════════════════════════════════════════════════
#  Estado global
# ══════════════════════════════════════════════════════════════
_state = {"online": False, "ultimo_envio": None,
          "hostname": platform.node(), "ip": "", "versao": VERSAO}

# ══════════════════════════════════════════════════════════════
#  Ícone da bandeja (PIL)
# ══════════════════════════════════════════════════════════════
def _icone(size=64, online=True) -> Image.Image:
    img  = Image.new("RGBA", (size, size), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    m = 1
    draw.ellipse([m,m,size-m,size-m], fill="#FFC107", outline="#E6A800", width=2)
    cx = cy = size//2; r = size//2 - m - 1
    for frac in (0.33, 0.67):
        yy = int(cy - r + 2*r*frac)
        hw = int((r**2-(yy-cy)**2)**0.5)
        draw.line([cx-hw+2,yy, cx+hw-2,yy], fill="#1f2937", width=max(1,size//32))
    ew = r//2
    draw.ellipse([cx-ew,cy-r+2,cx+ew,cy+r-2], outline="#1f2937", width=max(1,size//32))
    draw.line([cx,cy-r+2,cx,cy+r-2], fill="#1f2937", width=max(1,size//32))
    dr = size//7; dx = dy = size - dr*2 - 1
    draw.ellipse([dx,dy,dx+dr*2,dy+dr*2],
                 fill="#22c55e" if online else "#6b7280",
                 outline="white", width=max(1,size//24))
    return img

def _logo_canvas(canvas: tk.Canvas, size: int):
    cx = cy = size//2; r = size//2 - 2
    canvas.create_oval(2,2,size-2,size-2, fill=C_ACCENT, outline="#E6A800", width=2)
    for frac in (0.35, 0.65):
        yy = int(cy - r + 2*r*frac)
        hw = int((r**2-(yy-cy)**2)**0.5)
        canvas.create_line(cx-hw+3,yy, cx+hw-3,yy, fill="#1f2937", width=1)
    ew = r//2
    canvas.create_oval(cx-ew,cy-r+2,cx+ew,cy+r-2, outline="#1f2937", width=1)
    canvas.create_line(cx,cy-r+2,cx,cy+r-2, fill="#1f2937", width=1)

# ══════════════════════════════════════════════════════════════
#  Janela instaladora
# ══════════════════════════════════════════════════════════════
class InstallerApp:
    STEPS = ["Verificando dependências",
             "Buscando atualizações",
             "Registrando inicialização automática",
             "Conectando ao servidor"]

    def __init__(self):
        self.root = tk.Tk()
        self._sw: list[tuple] = []   # (StringVar, icon_lbl, text_lbl)
        self._setup(); self._build()

    def _setup(self):
        self.root.title("CPE Control — Agente T.I.")
        self.root.geometry("440x540"); self.root.resizable(False, False)
        self.root.configure(bg=C_BG); self.root.overrideredirect(True)
        self.root.update_idletasks()
        sw,sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"440x540+{(sw-440)//2}+{(sh-540)//2}")
        self._dx = self._dy = 0

    def _bind_drag(self, w):
        w.bind("<ButtonPress-1>",  lambda e: self._sd(e))
        w.bind("<B1-Motion>",      lambda e: self._dd(e))
    def _sd(self,e): self._dx,self._dy = e.x,e.y
    def _dd(self,e):
        self.root.geometry(f"+{self.root.winfo_x()+(e.x-self._dx)}+{self.root.winfo_y()+(e.y-self._dy)}")

    def _build(self):
        # Título
        tb = tk.Frame(self.root, bg=C_CARD, height=38)
        tb.pack(fill="x"); tb.pack_propagate(False)
        self._bind_drag(tb)
        tk.Label(tb, text="  ● CPE Control", bg=C_CARD, fg=C_ACCENT,
                 font=("Segoe UI",10,"bold")).pack(side="left", pady=8)
        tk.Button(tb, text=" × ", bg=C_CARD, fg=C_MUTED, bd=0, font=("Segoe UI",13),
                  activebackground=C_ERR, activeforeground="white", cursor="hand2",
                  command=self._close).pack(side="right", padx=2)
        # Logo
        hdr = tk.Frame(self.root, bg=C_BG); hdr.pack(fill="x", pady=(20,4))
        c = tk.Canvas(hdr, width=60, height=60, bg=C_BG, highlightthickness=0); c.pack()
        _logo_canvas(c, 60)
        tk.Label(hdr, text="Agente de Inventário T.I.", bg=C_BG, fg=C_TEXT,
                 font=("Segoe UI",13,"bold")).pack(pady=(10,2))
        tk.Label(hdr, text=f"v{VERSAO}  ·  CPE Control", bg=C_BG, fg=C_MUTED,
                 font=("Segoe UI",9)).pack()
        # Passos
        card = tk.Frame(self.root, bg=C_CARD,
                        highlightthickness=1, highlightbackground=C_BORDER)
        card.pack(fill="x", padx=28, pady=14)
        for i, label in enumerate(self.STEPS):
            row = tk.Frame(card, bg=C_CARD); row.pack(fill="x", padx=16, pady=10)
            ivar = tk.StringVar(value="○")
            ilbl = tk.Label(row, textvariable=ivar, bg=C_CARD, fg=C_MUTED,
                            font=("Segoe UI",11), width=2)
            ilbl.pack(side="left")
            tlbl = tk.Label(row, text=label, bg=C_CARD, fg=C_MUTED, font=("Segoe UI",10))
            tlbl.pack(side="left", padx=8)
            self._sw.append((ivar, ilbl, tlbl))
            if i < len(self.STEPS)-1:
                tk.Frame(card, bg=C_BORDER, height=1).pack(fill="x", padx=8)
        # Ativa primeiro
        self._sw[0][0].set("▶"); self._sw[0][1].config(fg=C_ACCENT); self._sw[0][2].config(fg=C_TEXT)
        # Progresso
        pf = tk.Frame(self.root, bg=C_BG); pf.pack(fill="x", padx=28)
        sty = ttk.Style(); sty.theme_use("default")
        sty.configure("Y.Horizontal.TProgressbar",
                       troughcolor=C_BORDER, background=C_ACCENT,
                       bordercolor=C_BORDER, lightcolor=C_ACCENT, darkcolor=C_ACCENT)
        self._pb = ttk.Progressbar(pf, style="Y.Horizontal.TProgressbar",
                                   length=384, mode="determinate", maximum=100)
        self._pb.pack(fill="x")
        self._svar = tk.StringVar(value="Aguardando...")
        tk.Label(self.root, textvariable=self._svar, bg=C_BG, fg=C_MUTED,
                 font=("Segoe UI",9)).pack(pady=(8,0))
        self._btn = tk.Button(self.root, text="Minimizar para a bandeja",
                              bg=C_ACCENT, fg="#1f2937", bd=0, font=("Segoe UI",10,"bold"),
                              padx=20, pady=10, cursor="hand2",
                              activebackground="#E6A800",
                              command=self._close, state="disabled")
        self._btn.pack(pady=14)
        tk.Label(self.root, text="O agente ficará ativo na bandeja do sistema",
                 bg=C_BG, fg=C_MUTED, font=("Segoe UI",8)).pack(pady=(0,10))

    def mark(self, idx: int, ok: bool, msg: str = ""):
        self.root.after(0, self._mark, idx, ok, msg)
    def status(self, msg: str):
        self.root.after(0, self._svar.set, msg)

    def _mark(self, idx: int, ok: bool, msg: str):
        ivar,ilbl,tlbl = self._sw[idx]
        ivar.set("✔" if ok else "✗")
        ilbl.config(fg=C_OK if ok else C_ERR); tlbl.config(fg=C_TEXT)
        self._pb["value"] = (idx+1)/len(self.STEPS)*100
        if msg: self._svar.set(msg)
        if ok and idx+1 < len(self.STEPS):
            nv,nl,nt = self._sw[idx+1]
            nv.set("▶"); nl.config(fg=C_ACCENT); nt.config(fg=C_TEXT)
        if idx == len(self.STEPS)-1:
            self._btn.config(state="normal")
            self.root.after(3500, self._close)

    def _close(self): self.root.destroy()
    def run(self):    self.root.mainloop()

# ══════════════════════════════════════════════════════════════
#  Janela de status (abre do ícone da bandeja)
# ══════════════════════════════════════════════════════════════
def _open_status():
    def _build():
        try: win = tk.Tk()
        except Exception: return
        win.title("CPE Control — Status")
        win.geometry("360x340"); win.resizable(False, False)
        win.configure(bg=C_BG); win.attributes("-topmost", True)
        win.update_idletasks()
        sw,sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"+{sw-380}+{sh-380}")
        # Header
        hdr = tk.Frame(win, bg=C_BG); hdr.pack(fill="x", pady=(14,0))
        c = tk.Canvas(hdr, width=40, height=40, bg=C_BG, highlightthickness=0); c.pack()
        _logo_canvas(c, 40)
        tk.Label(hdr, text="CPE Control — Agente T.I.", bg=C_BG, fg=C_ACCENT,
                 font=("Segoe UI",11,"bold")).pack(pady=(8,0))
        tk.Label(hdr, text=f"v{VERSAO}", bg=C_BG, fg=C_MUTED, font=("Segoe UI",8)).pack()
        # Card
        card = tk.Frame(win, bg=C_CARD,
                        highlightthickness=1, highlightbackground=C_BORDER)
        card.pack(fill="x", padx=20, pady=10)
        st = _state
        def _fmt():
            if not st["ultimo_envio"]: return "Ainda não enviado"
            d = int(time.time()-st["ultimo_envio"])
            return f"há {d}s" if d<60 else f"há {d//60} min"
        rows = [("Hostname", st["hostname"], C_TEXT),
                ("IP interno", st["ip"] or "—", C_TEXT),
                ("Status", "● Online" if st["online"] else "○ Offline",
                 C_OK if st["online"] else C_MUTED),
                ("Último envio", _fmt(), C_TEXT),
                ("Versão agente", f"v{st['versao']}", C_TEXT)]
        for i,(lbl,val,col) in enumerate(rows):
            f = tk.Frame(card, bg=C_CARD); f.pack(fill="x", padx=14, pady=7)
            tk.Label(f, text=lbl, bg=C_CARD, fg=C_MUTED,
                     font=("Segoe UI",9), width=16, anchor="w").pack(side="left")
            tk.Label(f, text=val, bg=C_CARD, fg=col,
                     font=("Segoe UI",9,"bold")).pack(side="left")
            if i < len(rows)-1:
                tk.Frame(card, bg=C_BORDER, height=1).pack(fill="x", padx=14)
        tk.Button(win, text="Fechar", bg=C_CARD, fg=C_TEXT, bd=0, font=("Segoe UI",10),
                  padx=20, pady=8, cursor="hand2",
                  activebackground=C_BORDER, command=win.destroy).pack(pady=10)
        win.mainloop()
    threading.Thread(target=_build, daemon=True).start()

# ══════════════════════════════════════════════════════════════
#  Startup automático (HKCU\Run — sem admin)
# ══════════════════════════════════════════════════════════════
_RUN_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
_RUN_VAL = "CPEInventarioAgente"

def _registrar_startup() -> bool:
    if platform.system() != "Windows": return False
    try:
        import winreg
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw): pythonw = sys.executable
        cmd = f'"{pythonw}" "{os.path.abspath(__file__)}"'
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(k, _RUN_VAL, 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(k); log.info(f"Startup OK: {cmd}"); return True
    except Exception as e:
        log.warning(f"Startup falhou: {e}"); return False

def _ja_registrado() -> bool:
    if platform.system() != "Windows": return False
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ)
        winreg.QueryValueEx(k, _RUN_VAL); winreg.CloseKey(k); return True
    except Exception: return False

# ══════════════════════════════════════════════════════════════
#  Instância única
# ══════════════════════════════════════════════════════════════
def _lock():
    path = os.path.join(tempfile.gettempdir(), "cpe_inv_agente.lock")
    try:
        lf = open(path, "w")
        if platform.system() == "Windows":
            import msvcrt; msvcrt.locking(lf.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl; fcntl.flock(lf, fcntl.LOCK_EX|fcntl.LOCK_NB)
        return lf
    except (IOError, OSError): return None

# ══════════════════════════════════════════════════════════════
#  Auto-update
# ══════════════════════════════════════════════════════════════
def _ver(v):
    try: return tuple(int(x) for x in str(v).split("."))
    except: return (0,)

def _update(skip=False):
    if skip: return
    try:
        r = requests.get(f"{API_URL}/api/inventario/agent/version", timeout=TIMEOUT_S)
        if not r.ok: return
        sv = r.json().get("version","0.0.0")
        if _ver(sv) <= _ver(VERSAO): return
        log.info(f"Atualizando para v{sv}...")
        r2 = requests.get(f"{API_URL}/api/inventario/agent/download", timeout=60)
        if not r2.ok: return
        meu = os.path.abspath(__file__); tmp = meu+".tmp"
        with open(tmp,"wb") as f: f.write(r2.content)
        os.replace(tmp, meu); log.info(f"Atualizado v{sv}. Reiniciando...")
        # Relaunch silencioso — sem console flash mesmo se rodando em python.exe
        if platform.system() == "Windows":
            subprocess.Popen([sys.executable]+sys.argv,
                             creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW)
        else:
            subprocess.Popen([sys.executable]+sys.argv)
        sys.exit(0)
    except Exception as e: log.warning(f"Update: {e}")

# ══════════════════════════════════════════════════════════════
#  Coleta de hardware
# ══════════════════════════════════════════════════════════════
# No Windows, usar STARTUPINFO + CREATE_NO_WINDOW para evitar que
# o console do PowerShell pisque na tela do usuário a cada coleta.
# Sem isso, executar o agente com pythonw.exe ainda mostra a janela
# do PowerShell brevemente (problema relatado em produção).
if platform.system() == "Windows":
    _SI = subprocess.STARTUPINFO()
    _SI.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    _SI.wShowWindow = 0  # SW_HIDE
    _NO_WINDOW_FLAGS = subprocess.CREATE_NO_WINDOW
else:
    _SI = None
    _NO_WINDOW_FLAGS = 0


def _ps(cmd):
    if platform.system() != "Windows": return ""
    try:
        r = subprocess.run(["powershell","-NoProfile","-NonInteractive",
                            "-OutputFormat","Text","-Command",cmd],
                           capture_output=True, timeout=10,
                           startupinfo=_SI, creationflags=_NO_WINDOW_FLAGS)
        return r.stdout.decode("utf-8-sig", errors="ignore").strip()
    except: return ""

def get_hostname():
    if platform.system()=="Windows":
        n = os.environ.get("COMPUTERNAME","").strip()
        if n: return n
    return socket.gethostname()

def get_arquitetura():
    if platform.system()=="Windows":
        a = os.environ.get("PROCESSOR_ARCHITECTURE","")
        return {"AMD64":"x86_64 (64-bit)","x86":"x86 (32-bit)","ARM64":"ARM64"}.get(a,a or platform.machine())
    return platform.machine()

def get_serial():
    if platform.system()=="Windows":
        v = _ps("(Get-WmiObject Win32_BIOS).SerialNumber")
        if v and v not in ("","None","Default string","To Be Filled By O.E.M."): return v
        return ""
    try: return subprocess.check_output(["dmidecode","-s","system-serial-number"],stderr=subprocess.DEVNULL,timeout=5,encoding="utf-8").strip()
    except: return ""

def get_marca_modelo():
    if platform.system()=="Windows":
        m = _ps("(Get-WmiObject Win32_ComputerSystem).Manufacturer")
        mo= _ps("(Get-WmiObject Win32_ComputerSystem).Model")
        for p in ("System manufacturer","System Product Name","To Be Filled By O.E.M.","Default string","None"):
            if m==p: m=""
            if mo==p: mo=""
        return m,mo
    try:
        m  = subprocess.check_output(["dmidecode","-s","system-manufacturer"],stderr=subprocess.DEVNULL,timeout=5,encoding="utf-8").strip()
        mo = subprocess.check_output(["dmidecode","-s","system-product-name"],stderr=subprocess.DEVNULL,timeout=5,encoding="utf-8").strip()
        return m,mo
    except: return "",""

def get_cpu_modelo():
    if platform.system()=="Windows":
        v = _ps("(Get-WmiObject Win32_Processor).Name")
        if v: return v
    return platform.processor() or "Desconhecido"

def get_tipo():
    ver = platform.version().lower()
    if "server" in ver or "server" in platform.release().lower(): return "servidor"
    try: return "notebook" if psutil.sensors_battery() is not None else "desktop"
    except: return "desktop"

def get_memoria():
    m = psutil.virtual_memory()
    return {"memoria_total_gb":round(m.total/1073741824,2),"memoria_uso_pct":round(m.percent,2)}

def get_disco():
    discos,tb,lb = [],0,0
    for p in psutil.disk_partitions(all=False):
        try:
            u = psutil.disk_usage(p.mountpoint)
            discos.append({"mountpoint":p.mountpoint,"fstype":p.fstype,
                           "total_gb":round(u.total/1073741824,2),
                           "livre_gb":round(u.free/1073741824,2),
                           "livre_pct":round(u.free/u.total*100,2) if u.total else 0})
            tb+=u.total; lb+=u.free
        except: pass
    return {"disco_total_gb":round(tb/1073741824,2),"disco_livre_gb":round(lb/1073741824,2),
            "disco_livre_pct":round(lb/tb*100,2) if tb else 0,"discos_json":discos}

def get_cpu():
    return {"cpu_modelo":get_cpu_modelo(),"cpu_nucleos":psutil.cpu_count(logical=True),
            "cpu_uso_pct":round(psutil.cpu_percent(interval=1),2)}

def get_ip():
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.settimeout(2)
        s.connect(("8.8.8.8",80)); ip=s.getsockname()[0]; s.close()
        if ip and not ip.startswith("127."): return ip
    except: pass
    try: return socket.gethostbyname(socket.gethostname())
    except: return ""

def get_geo():
    if LOCATION_ESTADO or LOCATION_CIDADE:
        ip=""
        try:
            r=requests.get("https://api.ipify.org?format=json",timeout=5)
            if r.ok: ip=r.json().get("ip","")
        except: pass
        return {"ip_externo":ip,"estado_br":LOCATION_ESTADO,"cidade":LOCATION_CIDADE}
    try:
        r=requests.get("https://ipinfo.io/json",timeout=6)
        if r.ok:
            d=r.json()
            return {"ip_externo":d.get("ip",""),"estado_br":d.get("region",""),"cidade":d.get("city","")}
    except: pass
    return {"ip_externo":"","estado_br":"","cidade":""}

def coletar():
    log.info("Coletando dados...")
    marca,modelo = get_marca_modelo()
    geo=get_geo(); mem=get_memoria(); disk=get_disco(); cpu=get_cpu()
    return {"hostname":get_hostname(),"usuario_logado":os.environ.get("USERNAME") or os.environ.get("USER") or "",
            "ip_interno":get_ip(),"ip_externo":geo["ip_externo"],"tipo":get_tipo(),
            "marca":marca,"modelo":modelo,"numero_serie":get_serial(),
            "sistema_operacional":f"{platform.system()} {platform.release()}",
            "versao_os":platform.version(),"arquitetura":get_arquitetura(),
            **mem,**disk,**cpu,
            "dias_ligado":int((time.time()-psutil.boot_time())/86400),
            "estado_br":geo["estado_br"],"cidade":geo["cidade"],"versao_agente":VERSAO}

def enviar(dados) -> bool:
    url=f"{API_URL}/api/inventario/agent/report"
    try:
        r=requests.post(url,json=dados,
                        headers={"X-Agent-Key":AGENT_KEY,"Content-Type":"application/json"},
                        timeout=TIMEOUT_S)
        if r.ok:
            log.info(f"Enviado — {dados['hostname']} | {r.json().get('action','?')}"); return True
        log.error(f"Servidor {r.status_code}: {r.text[:200]}")
    except requests.exceptions.ConnectionError: log.error(f"Sem conexão: {url}")
    except Exception as e: log.error(f"Erro: {e}")
    return False

# ══════════════════════════════════════════════════════════════
#  Tooltip da bandeja
# ══════════════════════════════════════════════════════════════
def _tooltip():
    if _state["ultimo_envio"]:
        d=int(time.time()-_state["ultimo_envio"])
        t=f"{d}s" if d<60 else f"{d//60}min"
        s="Online" if _state["online"] else "Offline"
        return f"CPE Control — {s} — Último envio: {t} atrás"
    return "CPE Control — Agente T.I."

# ══════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════
def main():
    # ── Se rodando com python.exe (console aberto), relança com pythonw.exe ──
    # Isso faz o console sumir imediatamente e o agente continuar só na bandeja.
    # Modo --test é exceção: precisa do console para imprimir os dados.
    if sys.platform == "win32" and "--test" not in sys.argv:
        _exe = sys.executable
        if os.path.basename(_exe).lower() not in ("pythonw.exe", "pythonw"):
            _pw = os.path.join(os.path.dirname(_exe), "pythonw.exe")
            if not os.path.exists(_pw):
                _pw = _exe.lower().replace("python.exe", "pythonw.exe")
            if os.path.exists(_pw):
                # Relança sem console e encerra o processo atual (fecha o prompt)
                subprocess.Popen(
                    [_pw, os.path.abspath(__file__)] + sys.argv[1:],
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
                )
                sys.exit(0)
            else:
                # Fallback: esconde a janela do console via API Win32
                import ctypes
                hw = ctypes.windll.kernel32.GetConsoleWindow()
                if hw:
                    ctypes.windll.user32.ShowWindow(hw, 0)  # SW_HIDE

    parser = argparse.ArgumentParser()
    parser.add_argument("--test",      action="store_true")
    parser.add_argument("--no-update", action="store_true")
    args = parser.parse_args()
    log.info(f"CPE Control Agent v{VERSAO} | {API_URL}")

    if args.test:
        dados = coletar()
        print("\n"+"="*60+"\n  DADOS COLETADOS (modo teste)\n"+"="*60)
        for k,v in dados.items():
            print(f"  {k:25s}: {json.dumps(v,ensure_ascii=False) if k=='discos_json' else v}")
        print("="*60+"\n"); return

    lk = _lock()
    if lk is None:
        log.info("Já em execução."); sys.exit(0)

    primeira_vez = not _ja_registrado()

    if primeira_vez:
        app = InstallerApp()
        def _steps():
            time.sleep(0.4)
            app.mark(0, True, "Dependências verificadas")
            time.sleep(0.3)
            try: _update(args.no_update); app.mark(1, True, "Versão mais recente")
            except Exception as e: app.mark(1, False, str(e))
            time.sleep(0.3)
            ok2 = _registrar_startup()
            app.mark(2, ok2, "Inicialização registrada" if ok2 else "Falha no registro (sem admin?)")
            time.sleep(0.3)
            try:
                d = coletar()
                _state["ip"] = d.get("ip_interno",""); _state["hostname"] = d.get("hostname",platform.node())
                ok3 = enviar(d)
                _state["online"]=ok3; _state["ultimo_envio"]=time.time() if ok3 else None
                app.mark(3, ok3, "Conectado! Dados enviados." if ok3 else "Servidor indisponível — tentará novamente")
            except Exception as e: app.mark(3, False, f"Erro: {e}")
        threading.Thread(target=_steps, daemon=True).start()
        app.run()
    else:
        # Execuções seguintes: silencioso (startup do Windows)
        try: _update(args.no_update)
        except Exception: pass
        try:
            d=coletar(); _state["ip"]=d.get("ip_interno",""); _state["hostname"]=d.get("hostname",platform.node())
            ok=enviar(d); _state["online"]=ok; _state["ultimo_envio"]=time.time() if ok else None
        except Exception: pass

    # ── Tray ──────────────────────────────────────────────────
    icon_ref = [None]

    def _on_open(ic, item):  _open_status()
    def _on_update(ic, item):
        threading.Thread(target=lambda: _update(False), daemon=True).start()
    def _on_exit(ic, item):  ic.stop(); sys.exit(0)

    icon = pystray.Icon(
        "CPE Control", _icone(64, _state["online"]), _tooltip(),
        menu=pystray.Menu(
            pystray.MenuItem("Abrir Status",    _on_open,   default=True),
            pystray.MenuItem("Atualizar Agora", _on_update),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Sair",            _on_exit),
        )
    )
    icon_ref[0] = icon

    def _loop():
        while True:
            time.sleep(INTERVAL)
            try:
                d=coletar(); _state["ip"]=d.get("ip_interno",""); _state["hostname"]=d.get("hostname",platform.node())
                ok=enviar(d); _state["online"]=ok
                if ok: _state["ultimo_envio"]=time.time()
                if icon_ref[0]:
                    icon_ref[0].icon  = _icone(64, ok)
                    icon_ref[0].title = _tooltip()
            except Exception as e: log.error(f"Loop: {e}")

    threading.Thread(target=_loop, daemon=True).start()
    icon.run()

if __name__ == "__main__":
    main()
