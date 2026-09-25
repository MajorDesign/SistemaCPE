"""Testa os 3 fixes da rodada 0.1.42:
  1. Backend: ChatConnectionManager.connect broadcasta presence_update
  2. Backend: ChatConnectionManager.disconnect broadcasta presence_update
  3. Backend: /presence/set envia chave 'presence' (nao so 'status')
  4. Frontend: MessageList.tsx renderiza <img> quando avatar_url existe
  5. Frontend: useMessageNotifications trata canal desconhecido como DM

Roda so verificacao estatica (regex) — nao precisa API rodando.
"""
from __future__ import annotations
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.dirname(HERE)
REPO_SISTEMA = os.path.dirname(SERVER)
REPO_DESKTOP = os.path.join(os.path.dirname(REPO_SISTEMA), "cpecontrol-desktop")

FAIL = 0
PASS = 0


def check(label, condition, detail=""):
    global FAIL, PASS
    mark = "\x1b[32mOK \x1b[0m" if condition else "\x1b[31mFAIL\x1b[0m"
    print(f"  [{mark}] {label}{f' - {detail}' if detail else ''}")
    if condition:
        PASS += 1
    else:
        FAIL += 1


def main():
    print("== test_presence_avatar_notif ==")

    # 1-3: Backend chat.py
    chat_py = os.path.join(SERVER, "routes", "chat.py")
    chat_src = open(chat_py, encoding="utf-8").read()

    # 1. connect faz broadcast presence_update online
    connect_block = re.search(
        r'async def connect\(self.*?(?=\n    def |\n    async def )',
        chat_src, flags=re.S)
    has_connect_bcast = bool(connect_block and
        re.search(r'send_to_users.*?presence_update.*?online', connect_block.group(0), flags=re.S))
    check("1. connect() broadcasta presence_update online", has_connect_bcast)

    # 2. disconnect faz broadcast presence_update offline
    disc_block = re.search(
        r'def disconnect\(self.*?(?=\n    async def send_to_users|\n    def )',
        chat_src, flags=re.S)
    has_disc_bcast = bool(disc_block and
        re.search(r'presence_update.*?offline', disc_block.group(0), flags=re.S))
    check("2. disconnect() broadcasta presence_update offline", has_disc_bcast)

    # 3. /presence/set envia chave 'presence' (alem de 'status')
    presence_set = re.search(
        r'"type":\s*"presence_update"[^}]*"presence":', chat_src)
    check("3. /presence/set envia chave 'presence'", bool(presence_set))

    # 4. Frontend MessageList.tsx tem MsgGroupAvatar com <img>
    ml_path = os.path.join(REPO_DESKTOP, "src", "renderer", "chat", "MessageList.tsx")
    if os.path.exists(ml_path):
        ml_src = open(ml_path, encoding="utf-8").read()
        has_component = "function MsgGroupAvatar" in ml_src
        has_img_render = bool(re.search(
            r'MsgGroupAvatar[\s\S]{0,300}avatarUrl=\{g\.messages\[0\]\.author\?\.avatar_url\}', ml_src))
        has_assetUrl = "assetUrl(avatarUrl)" in ml_src
        check("4a. MessageList tem componente MsgGroupAvatar", has_component)
        check("4b. MsgGroupAvatar recebe author.avatar_url", has_img_render)
        check("4c. Renderiza via assetUrl()", has_assetUrl)
    else:
        check("4. MessageList.tsx encontrado", False, f"nao existe em {ml_path}")

    # 5. useMessageNotifications trata canal desconhecido como DM
    unot_path = os.path.join(REPO_DESKTOP, "src", "renderer", "chat", "useMessageNotifications.ts")
    if os.path.exists(unot_path):
        unot_src = open(unot_path, encoding="utf-8").read()
        # Antes: const isDm = channel?.tipo === 'dm';  (undefined -> false)
        # Depois: const isDm = channel ? channel.tipo === 'dm' : true;
        has_retro = "channel ? channel.tipo === 'dm' : true" in unot_src
        check("5. useMessageNotifications: canal undefined vira DM (retroativo)", has_retro)
    else:
        check("5. useMessageNotifications.ts encontrado", False)

    # 6. CSS pra img no avatar
    css_path = os.path.join(REPO_DESKTOP, "src", "renderer", "chat", "chat.css")
    if os.path.exists(css_path):
        css_src = open(css_path, encoding="utf-8").read()
        has_img_css = ".msg-group__avatar--img" in css_src and "object-fit: cover" in css_src
        check("6. CSS .msg-group__avatar--img presente", has_img_css)

    print()
    print(f"resultado: {PASS} passou, {FAIL} falhou")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
