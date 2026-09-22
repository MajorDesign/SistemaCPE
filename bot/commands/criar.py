"""
/criarchamado — wizard multi-step pra abrir um chamado sem sair do Discord.

UX (limitacoes do Discord):
  - Modal do Discord aceita no maximo 5 componentes TextInput (nao aceita
    SelectMenu dentro). Solucao: SelectMenus em cascata antes.
  - Regra 3s: cada Interaction.response deve ser chamada em ate 3s. Como
    cada callback faz fetch HTTP antes de responder, usamos defer() como
    resposta rapida e edit_original_response() com o conteudo real.
  - Modal precisa ser a PRIMEIRA resposta da interacao (nao pode vir
    depois de defer). Solucao: view intermediaria com botao "Preencher"
    que abre o modal ao clicar (interacao nova, sem fetch antes).

Fluxo:
  /criarchamado
    → defer + fetch(groups) + followup(SetorView)
  SetorView.select → defer + fetch(cats) + edit(CategoriaView ou PreencherView)
  CategoriaView.select → defer + fetch(subs) + edit(SubView ou (fetch(campos) + edit(PreencherView/BrowserFallbackView)))
  SubView.select → defer + fetch(campos) + edit(PreencherView/BrowserFallbackView)
  PreencherView.button → send_modal(CriarChamadoModal)
  CriarChamadoModal.submit → defer + POST /api/tickets + followup(embed sucesso)

Se >3 campos custom obrigatorios: BrowserFallbackView com botao pro navegador.

Todas as respostas sao ephemeral (so quem chamou ve).
"""

import re
import logging
from datetime import datetime
from typing import Optional, List

import discord
from discord import app_commands

from api_client import (
    get_link, get_session,
    list_groups, list_categorias, list_subcategorias, list_campos,
    create_ticket, ApiError,
)

logger = logging.getLogger("cpe-bot.criar")

MAX_CUSTOM_FIELDS_IN_MODAL = 3
TICKET_URL_BASE = "https://cpecontrol.cpetecnologia.com.br/SistemaCPE/web/pages/tickets.html"
# Backend valida descricao 5..5000; deixa margem pra o user editar
MAX_PREFILL_DESCRICAO = 1800


def register(tree: app_commands.CommandTree, guild: discord.Object) -> None:

    @tree.command(
        name="criarchamado",
        description="Abre um chamado no CPE Control sem sair do Discord",
        guild=guild,
    )
    async def criarchamado(inter: discord.Interaction) -> None:
        await _iniciar_wizard(inter, prefill_descricao=None, aviso_extra=None)

    # 2026-09-22 (Fase 3): context menu — botao direito numa mensagem
    # do Discord vira "Apps → CPE Control → Criar chamado a partir desta".
    # A mensagem selecionada vira prefill da descricao do modal.
    @tree.context_menu(name="Criar chamado", guild=guild)
    async def criar_de_mensagem(inter: discord.Interaction, msg: discord.Message):
        # Monta prefill: autor + conteudo
        autor = msg.author.display_name or msg.author.name
        conteudo = (msg.content or "").strip()
        prefill = f"[Discord] {autor} disse:\n\n{conteudo}" if conteudo else f"[Discord] Mensagem de {autor} (sem texto)"
        if len(prefill) > MAX_PREFILL_DESCRICAO:
            prefill = prefill[:MAX_PREFILL_DESCRICAO - 20] + "…\n\n(mensagem truncada)"

        # Se tem anexos, avisa (nao anexamos automatico — anexos ficam
        # pra fase futura ou o user anexa via navegador depois de criado)
        aviso = None
        if msg.attachments:
            names = ", ".join(a.filename for a in msg.attachments[:3])
            extra = f" (+{len(msg.attachments) - 3} mais)" if len(msg.attachments) > 3 else ""
            aviso = (
                f"📎 A mensagem tem **{len(msg.attachments)} anexo(s)** ({names}{extra}) "
                f"que não vão automaticamente pro chamado. Após criar, abra no navegador "
                f"pra anexá-los."
            )

        await _iniciar_wizard(inter, prefill_descricao=prefill, aviso_extra=aviso)


async def _iniciar_wizard(
    inter: discord.Interaction,
    *,
    prefill_descricao: Optional[str],
    aviso_extra: Optional[str],
) -> None:
    """Ponto comum entre /criarchamado e o context menu 'Criar chamado'.
    Faz vinculo/sessao/list_groups e mostra o SetorView."""
    did = str(inter.user.id)
    await inter.response.defer(ephemeral=True, thinking=True)

    try:
        await get_link(did)
    except ApiError as e:
        if e.status == 404:
            await inter.followup.send(
                "🔗 Você ainda não vinculou sua conta.\n"
                "Use **`/vincular email:seu.email@cpetecnologia.com.br`** primeiro.",
                ephemeral=True,
            )
            return
        await inter.followup.send(f"❌ Erro: {e.detail}", ephemeral=True)
        return

    try:
        sess = await get_session(did)
        groups = await list_groups(sess["token"])
    except ApiError as e:
        await inter.followup.send(f"❌ {e.detail}", ephemeral=True)
        return

    if not groups:
        await inter.followup.send(
            "❌ Nenhum setor disponível pra você criar chamado.",
            ephemeral=True,
        )
        return

    view = SetorView(
        groups=groups,
        token=sess["token"], cpe_user_id=sess["user_id"],
        prefill_descricao=prefill_descricao,
    )
    header = "**Passo 1/4** · Escolha o setor pra qual o chamado é:"
    if aviso_extra:
        header = f"{aviso_extra}\n\n{header}"
    await inter.followup.send(header, view=view, ephemeral=True)


# =========================================================
# VIEWS EM CADEIA
# =========================================================

class SetorView(discord.ui.View):
    def __init__(self, *, groups: list, token: str, cpe_user_id: int, prefill_descricao: Optional[str] = None):
        super().__init__(timeout=300)
        self.token = token
        self.cpe_user_id = cpe_user_id
        self.prefill_descricao = prefill_descricao
        self._options = _build_options(groups, label_key="name")

        select = discord.ui.Select(
            placeholder="Escolha um setor...",
            options=self._options,
            min_values=1, max_values=1,
        )
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, inter: discord.Interaction):
        # Defer sempre — garantia dos 3s do Discord
        await inter.response.defer()
        group_id = int(inter.data["values"][0])
        setor_label = _label_from_options(self._options, str(group_id))

        try:
            cats = await list_categorias(group_id, self.token)
        except ApiError as e:
            await inter.edit_original_response(content=f"❌ {e.detail}", view=None)
            return

        if not cats:
            # Setor sem catalogo — vai direto pra tela de preencher
            await _mostrar_preencher(
                inter,
                group_id=group_id, group_label=setor_label,
                cat_id=None, cat_label=None,
                sub_id=None, sub_label=None,
                campos=[],
                token=self.token, cpe_user_id=self.cpe_user_id,
                prefill_descricao=self.prefill_descricao,
            )
            return

        view = CategoriaView(
            categorias=cats, group_id=group_id, group_label=setor_label,
            token=self.token, cpe_user_id=self.cpe_user_id,
            prefill_descricao=self.prefill_descricao,
        )
        await inter.edit_original_response(
            content=f"**Passo 2/4** · Setor: **{setor_label}**\nEscolha a categoria:",
            view=view,
        )


class CategoriaView(discord.ui.View):
    def __init__(self, *, categorias, group_id, group_label, token, cpe_user_id, prefill_descricao: Optional[str] = None):
        super().__init__(timeout=300)
        self.group_id = group_id
        self.group_label = group_label
        self.token = token
        self.cpe_user_id = cpe_user_id
        self.prefill_descricao = prefill_descricao
        self._options = _build_options(categorias, label_key="nome")

        select = discord.ui.Select(
            placeholder="Escolha uma categoria...",
            options=self._options,
            min_values=1, max_values=1,
        )
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, inter: discord.Interaction):
        await inter.response.defer()
        cat_id = int(inter.data["values"][0])
        cat_label = _label_from_options(self._options, str(cat_id))

        try:
            subs = await list_subcategorias(cat_id, self.token)
        except ApiError as e:
            await inter.edit_original_response(content=f"❌ {e.detail}", view=None)
            return

        if subs:
            view = SubcategoriaView(
                subs=subs,
                group_id=self.group_id, group_label=self.group_label,
                cat_id=cat_id, cat_label=cat_label,
                token=self.token, cpe_user_id=self.cpe_user_id,
                prefill_descricao=self.prefill_descricao,
            )
            await inter.edit_original_response(
                content=f"**Passo 3/4** · {self.group_label} › **{cat_label}**\nEscolha a subcategoria:",
                view=view,
            )
            return

        # Sem sub — busca campos e vai pra tela final
        try:
            campos = await list_campos(cat_id, None, self.token)
        except ApiError as e:
            await inter.edit_original_response(content=f"❌ {e.detail}", view=None)
            return
        await _mostrar_preencher(
            inter,
            group_id=self.group_id, group_label=self.group_label,
            cat_id=cat_id, cat_label=cat_label,
            sub_id=None, sub_label=None,
            campos=campos,
            token=self.token, cpe_user_id=self.cpe_user_id,
            prefill_descricao=self.prefill_descricao,
        )


class SubcategoriaView(discord.ui.View):
    def __init__(self, *, subs, group_id, group_label, cat_id, cat_label, token, cpe_user_id, prefill_descricao: Optional[str] = None):
        super().__init__(timeout=300)
        self.group_id = group_id
        self.group_label = group_label
        self.cat_id = cat_id
        self.cat_label = cat_label
        self.token = token
        self.cpe_user_id = cpe_user_id
        self.prefill_descricao = prefill_descricao
        self._options = _build_options(subs, label_key="nome")

        select = discord.ui.Select(
            placeholder="Escolha uma subcategoria...",
            options=self._options,
            min_values=1, max_values=1,
        )
        select.callback = self._on_select
        self.add_item(select)

    async def _on_select(self, inter: discord.Interaction):
        await inter.response.defer()
        sub_id = int(inter.data["values"][0])
        sub_label = _label_from_options(self._options, str(sub_id))

        try:
            campos = await list_campos(self.cat_id, sub_id, self.token)
        except ApiError as e:
            await inter.edit_original_response(content=f"❌ {e.detail}", view=None)
            return

        await _mostrar_preencher(
            inter,
            group_id=self.group_id, group_label=self.group_label,
            cat_id=self.cat_id, cat_label=self.cat_label,
            sub_id=sub_id, sub_label=sub_label,
            campos=campos,
            token=self.token, cpe_user_id=self.cpe_user_id,
            prefill_descricao=self.prefill_descricao,
        )


async def _mostrar_preencher(
    inter, *,
    group_id, group_label,
    cat_id, cat_label,
    sub_id, sub_label,
    campos, token, cpe_user_id,
    prefill_descricao: Optional[str] = None,
):
    """Fetch campos ja foi feito. Decide entre PreencherView (abre modal)
    ou BrowserFallbackView (>3 campos obrigatorios)."""
    obrigatorios = [c for c in (campos or []) if c.get("obrigatorio")]

    trilha = group_label or "?"
    if cat_label:
        trilha += f" › {cat_label}"
        if sub_label:
            trilha += f" › {sub_label}"

    if len(obrigatorios) > MAX_CUSTOM_FIELDS_IN_MODAL:
        # Overflow — abre no navegador. NAO promete prefill: o frontend
        # web hoje so parseia ?ticket_id, nao ?group_id/categoria_id.
        view = BrowserFallbackView()
        labels = ", ".join(c["label"] for c in obrigatorios[:5])
        extra = f" (+{len(obrigatorios)-5})" if len(obrigatorios) > 5 else ""
        await inter.edit_original_response(
            content=(
                f"⚠️ **{trilha}**\n\n"
                f"Esta categoria exige **{len(obrigatorios)} campos personalizados** "
                f"({labels}{extra}) — só cabem {MAX_CUSTOM_FIELDS_IN_MODAL} num formulário "
                f"do Discord.\n\nAbra a tela de novo chamado no navegador pra preencher:"
            ),
            view=view,
        )
        return

    # Cabe no modal — mostra botao pra abrir
    view = PreencherView(
        group_id=group_id, group_label=group_label,
        categoria_id=cat_id, categoria_label=cat_label,
        subcategoria_id=sub_id, subcategoria_label=sub_label,
        campos=obrigatorios, token=token, cpe_user_id=cpe_user_id,
        prefill_descricao=prefill_descricao,
    )
    resumo_campos = ""
    if obrigatorios:
        resumo_campos = f"\n\nCampos extras que serão pedidos: **{', '.join(c['label'] for c in obrigatorios)}**"
    await inter.edit_original_response(
        content=(
            f"**Passo 4/4** · {trilha}{resumo_campos}\n\n"
            f"Clique abaixo pra abrir o formulário e preencher título/descrição:"
        ),
        view=view,
    )


class PreencherView(discord.ui.View):
    """View intermediaria com botao que abre o Modal. Necessario porque
    Modal precisa ser a primeira resposta da interacao — e nao podemos
    fazer fetch de campos + send_modal na mesma callback (fetch pode
    demorar >3s)."""

    def __init__(self, *, group_id, group_label, categoria_id, categoria_label,
                  subcategoria_id, subcategoria_label, campos, token, cpe_user_id,
                  prefill_descricao: Optional[str] = None):
        super().__init__(timeout=600)
        self.group_id = group_id
        self.group_label = group_label
        self.categoria_id = categoria_id
        self.categoria_label = categoria_label
        self.subcategoria_id = subcategoria_id
        self.subcategoria_label = subcategoria_label
        self.campos = campos
        self.token = token
        self.cpe_user_id = cpe_user_id
        self.prefill_descricao = prefill_descricao

    @discord.ui.button(label="Preencher chamado →", style=discord.ButtonStyle.primary)
    async def preencher(self, inter: discord.Interaction, button: discord.ui.Button):
        modal = CriarChamadoModal(
            group_id=self.group_id, group_label=self.group_label,
            categoria_id=self.categoria_id, categoria_label=self.categoria_label,
            subcategoria_id=self.subcategoria_id, subcategoria_label=self.subcategoria_label,
            campos=self.campos, token=self.token, cpe_user_id=self.cpe_user_id,
            prefill_descricao=self.prefill_descricao,
        )
        await inter.response.send_modal(modal)


class BrowserFallbackView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(discord.ui.Button(
            label="Abrir tela de novo chamado",
            style=discord.ButtonStyle.link,
            url=TICKET_URL_BASE,
        ))


# =========================================================
# MODAL
# =========================================================

class CriarChamadoModal(discord.ui.Modal):
    def __init__(
        self, *,
        group_id, group_label,
        categoria_id, categoria_label,
        subcategoria_id, subcategoria_label,
        campos, token, cpe_user_id,
        prefill_descricao: Optional[str] = None,
    ):
        titulo_modal = "Novo chamado"
        if group_label:
            titulo_modal = f"Chamado · {group_label[:35]}"
        super().__init__(title=titulo_modal[:45], timeout=600)

        self.group_id = group_id
        self.group_label = group_label
        self.categoria_id = categoria_id
        self.categoria_label = categoria_label
        self.subcategoria_id = subcategoria_id
        self.subcategoria_label = subcategoria_label
        self.token = token
        self.cpe_user_id = cpe_user_id
        self.campos_def = campos or []

        self.titulo = discord.ui.TextInput(
            label="Título",
            placeholder="Ex: Fatura com valor errado",
            min_length=3, max_length=255,
            required=True,
        )
        self.add_item(self.titulo)

        # Se veio do context menu, pre-preenche descricao com a mensagem
        # selecionada — user pode editar antes de enviar.
        descricao_default = (prefill_descricao or "").strip()
        if descricao_default and len(descricao_default) > MAX_PREFILL_DESCRICAO:
            descricao_default = descricao_default[:MAX_PREFILL_DESCRICAO]
        self.descricao = discord.ui.TextInput(
            label="Descrição",
            style=discord.TextStyle.paragraph,
            placeholder="Detalhe o problema, contexto, o que você já tentou…",
            min_length=5, max_length=2000,
            required=True,
            default=descricao_default if descricao_default else None,
        )
        self.add_item(self.descricao)

        self.custom_inputs: List[tuple] = []
        for c in self.campos_def[:MAX_CUSTOM_FIELDS_IN_MODAL]:
            placeholder = None
            if c["tipo"] == "numero":
                placeholder = "Somente números (aceita vírgula pra decimal)"
            elif c["tipo"] == "data":
                placeholder = "AAAA-MM-DD (ex: 2026-09-22)"
            inp = discord.ui.TextInput(
                label=c["label"][:45],
                placeholder=placeholder,
                required=True,
                max_length=200,
                style=discord.TextStyle.short,
            )
            self.custom_inputs.append((c, inp))
            self.add_item(inp)

    async def on_submit(self, inter: discord.Interaction) -> None:
        await inter.response.defer(ephemeral=True, thinking=True)

        # Valida + normaliza campos custom
        campos_valores = []
        for c, inp in self.custom_inputs:
            raw = inp.value.strip()
            if c["tipo"] == "numero":
                cleaned = raw.replace(",", ".")
                if not re.match(r"^\d+(\.\d{1,4})?$", cleaned):
                    await inter.followup.send(
                        f"❌ Campo **{c['label']}** precisa ser numérico. Valor: `{raw}`",
                        ephemeral=True,
                    )
                    return
                raw = cleaned
            elif c["tipo"] == "data":
                # Regex + strptime — regex sozinho aceita 2026-13-45
                if not re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
                    await inter.followup.send(
                        f"❌ Campo **{c['label']}** precisa ser data AAAA-MM-DD. Valor: `{raw}`",
                        ephemeral=True,
                    )
                    return
                try:
                    datetime.strptime(raw, "%Y-%m-%d")
                except ValueError:
                    await inter.followup.send(
                        f"❌ Campo **{c['label']}** tem data inválida: `{raw}`",
                        ephemeral=True,
                    )
                    return
            campos_valores.append({"campo_id": c["id"], "valor": raw})

        payload = {
            "solicitante_id": self.cpe_user_id,
            "group_id": self.group_id,
            "categoria_id": self.categoria_id,
            "subcategoria_id": self.subcategoria_id,
            "assunto": self.titulo.value.strip(),
            "descricao_inicial": self.descricao.value.strip(),
            "origem": "discord_bot",
        }
        if campos_valores:
            payload["campos_valores"] = campos_valores

        try:
            created = await create_ticket(payload, self.token)
        except ApiError as e:
            emoji = "⏱️" if e.status == 429 else "❌"
            await inter.followup.send(f"{emoji} Erro ao criar chamado: {e.detail}", ephemeral=True)
            return
        except Exception as e:
            logger.error(f"[criar] erro inesperado no submit: {e}")
            await inter.followup.send("❌ Erro ao contactar o CPE Control.", ephemeral=True)
            return

        # Sucesso
        numero = created.get("numero") or created.get("id_alfanumerica") or "(sem número)"
        ticket_id = created.get("id")
        cat_str = self.categoria_label or "—"
        if self.subcategoria_label:
            cat_str += f" › {self.subcategoria_label}"

        embed = discord.Embed(
            title=f"✅ Chamado {numero} aberto",
            description=f"**{self.titulo.value.strip()}**",
            color=0x10B981,
        )
        embed.add_field(name="Setor", value=self.group_label or "—", inline=True)
        embed.add_field(name="Categoria", value=cat_str, inline=True)
        # Usa custom_inputs pra iterar — evita drift entre campos_def e valores capturados
        if campos_valores:
            resumo = "\n".join(
                f"• **{c['label']}:** {v['valor']}"
                for (c, _inp), v in zip(self.custom_inputs, campos_valores)
            )
            embed.add_field(name="Campos preenchidos", value=resumo, inline=False)
        embed.set_footer(text="Você será notificado por email das atualizações")

        view = discord.ui.View()
        if ticket_id:
            view.add_item(discord.ui.Button(
                label="Abrir no navegador",
                style=discord.ButtonStyle.link,
                url=f"{TICKET_URL_BASE}?ticket_id={ticket_id}",
            ))

        await inter.followup.send(
            embed=embed,
            view=view if ticket_id else None,
            ephemeral=True,
        )

    async def on_error(self, inter: discord.Interaction, error: Exception) -> None:
        logger.error(f"[criar/modal] on_error: {error}")
        # Robusto: se ainda nao respondeu, envia primeira resposta; se ja
        # defered, usa followup. Evita silencio total se erro veio antes
        # do defer (ou o defer em si falhou).
        try:
            msg = "❌ Ocorreu um erro processando o formulário. Tente de novo."
            if not inter.response.is_done():
                await inter.response.send_message(msg, ephemeral=True)
            else:
                await inter.followup.send(msg, ephemeral=True)
        except discord.HTTPException as http_err:
            logger.warning(f"[criar/modal] on_error fallback tambem falhou: {http_err}")


# =========================================================
# HELPERS
# =========================================================

def _build_options(items: list, *, label_key: str) -> List[discord.SelectOption]:
    """Constroi ate 25 SelectOption (limite Discord). Trunca labels em 100."""
    opts = []
    for item in items[:25]:
        label = str(item.get(label_key, f"#{item.get('id')}"))[:100]
        opts.append(discord.SelectOption(label=label, value=str(item["id"])))
    return opts


def _label_from_options(options: list, value: str) -> str:
    for o in options:
        if o.value == value:
            return o.label
    return value
