# Termo de Responsabilidade Notebook — CPE

Aplicativo desktop (Tkinter) que gera e envia o termo de responsabilidade
do notebook para a pasta correta no sistema CPE (Contratos e Termos).

## Estrutura

```
tools/termo_notebook/
├── termo_notebook.py       # código-fonte
├── logo.png                # ícone da janela / ícone do .exe
├── requirements.txt        # dependências Python
├── VERSION                 # versão atual (editar ao publicar)
├── config.ini              # URL do servidor CPE
├── TermoNotebookCPE.spec   # spec do PyInstaller
│
├── scripts/                # ⚙️  scripts de build
│   ├── build.bat           # onefile (EXE único — para release)
│   └── build_rapido.bat    # onedir (pasta — abre mais rápido)
│
├── release/                # 🚀 EXECUTÁVEL FINAL VAI AQUI
│   └── TermoNotebookCPE_v1.0.3.exe   (versão no nome)
│
├── dist/                   # 🗑️  artefatos intermediários (ignorar)
└── build/                  # 🗑️  artefatos intermediários (ignorar)
```

## Como publicar uma nova versão

1. Edite [`VERSION`](VERSION) e troque, por exemplo, `1.0.3` → `1.0.4`.
2. Rode `scripts\build.bat`.
3. O executável final aparece em `release\TermoNotebookCPE_v1.0.4.exe`.
4. A página `download-agents.html` detecta o novo arquivo automaticamente.

## Sincronização de versão

- A versão é lida do arquivo [`VERSION`](VERSION) em 3 lugares:
  1. Título da janela do aplicativo (`_read_app_version` no `termo_notebook.py`).
  2. Nome do arquivo em `release/` (gravado pelo `build.bat`).
  3. Página `download-agents.html` (o backend lê o nome do arquivo em `release/`).

## Configuração do servidor

Arquivo `config.ini`:

```ini
[server]
url = http://172.16.0.129:8000
```

Troque pelo IP:porta do FastAPI. O aplicativo também permite alterar pela UI
("Configurar servidor").
