"""
Router do módulo Recepção:
- Salas de reunião (CRUD por unidade)
- Reservas (agendamento, confirmação em 40min, cancelamento)
- Envios de mercadoria (CRUD + integração Correios via Linketrack)

Endpoints (prefixo /api/recepcao):
    GET    /salas                       Lista salas (filtra por unit_id, ativa)
    POST   /salas                       Cria sala (ADMIN ou RESPONSAVEL_GRUPO)
    PUT    /salas/{id}                  Atualiza sala
    DELETE /salas/{id}                  Deleta sala (cascade nas reservas)

    GET    /reservas                    Lista reservas (filtros: sala_id, inicio, fim, status)
    POST   /reservas                    Cria reserva (qualquer usuário)
    POST   /reservas/{id}/confirmar     Confirma reserva (dono)
    POST   /reservas/{id}/cancelar      Cancela reserva (dono ou admin)

    GET    /envios                      Lista envios
    POST   /envios                      Cria envio
    PUT    /envios/{id}                 Atualiza envio
    DELETE /envios/{id}                 Deleta envio
    GET    /envios/{id}/rastrear        Consulta status nos Correios (cacheia em status_correios)
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from database import (
    get_db_or_404,
    convert_datetime_to_string,
    convert_datetime_list,
)
from services.seurastreio_service import rastrear as rastrear_seurastreio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recepcao", tags=["recepcao"])


CONFIRMACAO_MINUTOS = 40
ROLES_GERENCIAM_SALA = {"ADMIN", "TI", "MANAGER", "RESPONSAVEL_GRUPO"}


# ============================================================
# SCHEMAS
# ============================================================

class SalaBase(BaseModel):
    unit_id: int = Field(..., gt=0)
    escritorio_id: Optional[int] = None
    nome: str = Field(..., min_length=2, max_length=120)
    tipo: str = Field("sala", pattern="^(sala|auditorio)$")
    capacidade: Optional[int] = Field(None, ge=1, le=10000)
    descricao: Optional[str] = Field(None, max_length=500)
    cor: Optional[str] = Field("#3b82f6", max_length=7)
    ativa: bool = True


class SalaCreate(SalaBase):
    criado_por: int = Field(..., gt=0)


class SalaUpdate(BaseModel):
    unit_id: Optional[int] = None
    escritorio_id: Optional[int] = None  # use 0 para limpar (sem escritório)
    nome: Optional[str] = Field(None, min_length=2, max_length=120)
    tipo: Optional[str] = Field(None, pattern="^(sala|auditorio)$")
    capacidade: Optional[int] = Field(None, ge=1, le=10000)
    descricao: Optional[str] = Field(None, max_length=500)
    cor: Optional[str] = Field(None, max_length=7)
    ativa: Optional[bool] = None
    atualizado_por: int = Field(..., gt=0)


class EscritorioBase(BaseModel):
    unit_id: int = Field(..., gt=0)
    nome: str = Field(..., min_length=2, max_length=120)
    ativo: bool = True


class EscritorioCreate(EscritorioBase):
    pass


class EscritorioUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=120)
    ativo: Optional[bool] = None


class ReservaCreate(BaseModel):
    sala_id: int = Field(..., gt=0)
    usuario_id: int = Field(..., gt=0)
    titulo: str = Field(..., min_length=2, max_length=200)
    descricao: Optional[str] = Field(None, max_length=500)
    inicio: datetime
    fim: datetime
    # IDs de outros usuários para convidar; o autor da reserva NÃO precisa estar aqui.
    convidados_ids: Optional[List[int]] = None


class ReservaCancel(BaseModel):
    usuario_id: int = Field(..., gt=0)
    motivo: Optional[str] = Field(None, max_length=255)


class ConvidarBody(BaseModel):
    convidador_id: int = Field(..., gt=0)
    convidados_ids: List[int] = Field(..., min_length=1)


class ResponderConviteBody(BaseModel):
    usuario_id: int = Field(..., gt=0)
    aceitar: bool


class EnvioCreate(BaseModel):
    remetente_id: int = Field(..., gt=0)
    destino: str = Field(..., min_length=2, max_length=255)
    destinatario: str = Field(..., min_length=2, max_length=150)
    valor_mercadoria: float = Field(0, ge=0)
    codigo_correios: Optional[str] = Field(None, max_length=30)
    observacoes: Optional[str] = Field(None, max_length=500)


class EnvioUpdate(BaseModel):
    destino: Optional[str] = Field(None, min_length=2, max_length=255)
    destinatario: Optional[str] = Field(None, min_length=2, max_length=150)
    valor_mercadoria: Optional[float] = Field(None, ge=0)
    codigo_correios: Optional[str] = Field(None, max_length=30)
    observacoes: Optional[str] = Field(None, max_length=500)
    # Permite atualizar o status manualmente quando a API dos Correios
    # estiver inacessível (firewall, sem internet, etc).
    status_correios: Optional[str] = Field(None, max_length=120)
    status_local: Optional[str]    = Field(None, max_length=180)


class EventoCreate(BaseModel):
    tipo: str = Field(..., min_length=1, max_length=40)
    descricao: str = Field(..., min_length=2, max_length=255)
    local: Optional[str] = Field(None, max_length=180)
    data_evento: str  # ISO datetime "YYYY-MM-DDTHH:MM"


class EventoUpdate(BaseModel):
    tipo: Optional[str] = Field(None, min_length=1, max_length=40)
    descricao: Optional[str] = Field(None, min_length=2, max_length=255)
    local: Optional[str] = Field(None, max_length=180)
    data_evento: Optional[str] = None


# ============================================================
# HELPERS
# ============================================================

def _get_user_role(cursor, user_id: int) -> Optional[str]:
    cursor.execute("SELECT role FROM users WHERE id = %s", (user_id,))
    row = cursor.fetchone()
    return (row or {}).get("role")


def _criar_notificacao(cursor, usuario_id: int, mensagem: str, tipo: str = "info"):
    """Insere notificação na tabela existente. Falha silenciosa para não quebrar o fluxo."""
    try:
        cursor.execute(
            "INSERT INTO notificacoes (usuario_id, mensagem, tipo, lido) VALUES (%s, %s, %s, 0)",
            (usuario_id, mensagem[:255], tipo),
        )
    except Exception as err:
        logger.warning(f"[RECEPCAO/NOTIF] Falha ao gravar notificação: {err}")


def _convidar_usuarios(cursor, reserva_id: int, convidador_id: int,
                       convidados_ids: List[int], titulo_reserva: str,
                       inicio_reserva: datetime) -> int:
    """
    Cria convites e dispara notificações.
    Idempotente — usa INSERT IGNORE; se já houver convite, não duplica.
    Retorna quantos convites novos foram criados.
    """
    if not convidados_ids:
        return 0

    # filtra IDs duplicados e o próprio dono (não convida a si mesmo)
    ids = sorted({int(i) for i in convidados_ids if i and i != convidador_id})
    if not ids:
        return 0

    # valida que são usuários ativos
    fmt = ",".join(["%s"] * len(ids))
    cursor.execute(
        f"SELECT id FROM users WHERE id IN ({fmt}) AND is_active = 1",
        ids,
    )
    validos = [row["id"] for row in cursor.fetchall()]
    if not validos:
        return 0

    novos = 0
    quando = inicio_reserva.strftime("%d/%m %H:%M") if inicio_reserva else ""
    msg = (
        f'Você foi convidado para a reunião "{titulo_reserva}" em {quando}. '
        f"Confirme presença na página de Recepção."
    )

    for uid in validos:
        cursor.execute(
            "INSERT IGNORE INTO recepcao_convidados "
            "(reserva_id, usuario_id, convidado_por, status) "
            "VALUES (%s, %s, %s, 'pendente')",
            (reserva_id, uid, convidador_id),
        )
        if cursor.rowcount > 0:
            novos += 1
            try:
                # ticket_id é reaproveitado para guardar reserva_id (sem migration);
                # tipo 'convite_reuniao' é o que o front (nav.js) reconhece.
                cursor.execute(
                    "INSERT INTO notificacoes "
                    "(ticket_id, usuario_id, mensagem, tipo, lido) "
                    "VALUES (%s, %s, %s, 'convite_reuniao', 0)",
                    (reserva_id, uid, msg[:255]),
                )
            except Exception as err:
                logger.warning(f"[RECEPCAO/CONVIDAR] notif fail uid={uid}: {err}")
    return novos


def _conflito_de_horario(cursor, sala_id: int, inicio: datetime, fim: datetime,
                         excluir_reserva_id: Optional[int] = None) -> bool:
    sql = """
        SELECT id FROM recepcao_reservas
        WHERE sala_id = %s
          AND status IN ('pendente','confirmada')
          AND inicio < %s AND fim > %s
    """
    params = [sala_id, fim, inicio]
    if excluir_reserva_id:
        sql += " AND id != %s"
        params.append(excluir_reserva_id)
    cursor.execute(sql, params)
    return cursor.fetchone() is not None


def _expirar_pendentes(cursor):
    """
    Marca como 'expirada' qualquer reserva pendente cujo prazo de confirmação já passou.
    Idempotente — pode rodar a cada listagem ou via scheduler.
    """
    cursor.execute(
        "UPDATE recepcao_reservas SET status='expirada', cancelada_em=NOW(), "
        "motivo_cancel='Confirmação não recebida em 40min' "
        "WHERE status='pendente' AND confirmacao_prazo < NOW()"
    )
    return cursor.rowcount


def _concluir_passadas(cursor):
    """Marca como 'concluida' reservas confirmadas cujo fim já passou."""
    cursor.execute(
        "UPDATE recepcao_reservas SET status='concluida' "
        "WHERE status='confirmada' AND fim < NOW()"
    )
    return cursor.rowcount


# ============================================================
# ESCRITÓRIOS (subdivisão da unidade)
# ============================================================

@router.get("/escritorios")
async def list_escritorios(unit_id: Optional[int] = None,
                           somente_ativos: bool = False):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        sql = (
            "SELECT e.id, e.unit_id, e.nome, e.ativo, e.created_at, "
            "       u.nome AS unit_nome, u.sigla AS unit_sigla "
            "FROM recepcao_escritorios e "
            "JOIN unidades_cpe u ON u.id = e.unit_id "
            "WHERE 1=1"
        )
        params = []
        if unit_id is not None:
            sql += " AND e.unit_id = %s"; params.append(unit_id)
        if somente_ativos:
            sql += " AND e.ativo = 1"
        sql += " ORDER BY u.nome, e.nome"
        cursor.execute(sql, params)
        return convert_datetime_list(cursor.fetchall())
    except Exception as err:
        logger.error(f"[RECEPCAO/ESCRITORIOS/LIST] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar escritórios: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.post("/escritorios", status_code=status.HTTP_201_CREATED)
async def create_escritorio(data: EscritorioCreate, criado_por: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        role = _get_user_role(cursor, criado_por)
        if role not in ROLES_GERENCIAM_SALA:
            raise HTTPException(status_code=403, detail="Sem permissão para cadastrar escritórios")

        cursor.execute("SELECT id FROM unidades_cpe WHERE id = %s AND ativo = 1", (data.unit_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="Unidade inválida ou inativa")

        cursor.execute(
            "SELECT id FROM recepcao_escritorios WHERE unit_id = %s AND nome = %s",
            (data.unit_id, data.nome),
        )
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Já existe um escritório com esse nome nesta unidade")

        cursor.execute(
            "INSERT INTO recepcao_escritorios (unit_id, nome, ativo) VALUES (%s,%s,%s)",
            (data.unit_id, data.nome, 1 if data.ativo else 0),
        )
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute(
            "SELECT id, unit_id, nome, ativo, created_at FROM recepcao_escritorios WHERE id = %s",
            (new_id,),
        )
        return convert_datetime_to_string(cursor.fetchone())
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[RECEPCAO/ESCRITORIOS/CREATE] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar escritório: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.put("/escritorios/{escritorio_id}")
async def update_escritorio(escritorio_id: int, data: EscritorioUpdate,
                            atualizado_por: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        role = _get_user_role(cursor, atualizado_por)
        if role not in ROLES_GERENCIAM_SALA:
            raise HTTPException(status_code=403, detail="Sem permissão")

        cursor.execute("SELECT id FROM recepcao_escritorios WHERE id = %s", (escritorio_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Escritório não encontrado")

        updates, params = [], []
        if data.nome is not None:  updates.append("nome=%s");  params.append(data.nome)
        if data.ativo is not None: updates.append("ativo=%s"); params.append(1 if data.ativo else 0)
        if not updates:
            raise HTTPException(status_code=400, detail="Nada para atualizar")
        params.append(escritorio_id)
        cursor.execute(f"UPDATE recepcao_escritorios SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()

        cursor.execute(
            "SELECT id, unit_id, nome, ativo, created_at FROM recepcao_escritorios WHERE id = %s",
            (escritorio_id,),
        )
        return convert_datetime_to_string(cursor.fetchone())
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[RECEPCAO/ESCRITORIOS/UPDATE] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar escritório: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.delete("/escritorios/{escritorio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_escritorio(escritorio_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        role = _get_user_role(cursor, usuario_id)
        if role not in ROLES_GERENCIAM_SALA:
            raise HTTPException(status_code=403, detail="Sem permissão")

        cursor.execute(
            "SELECT COUNT(*) AS total FROM recepcao_salas WHERE escritorio_id = %s",
            (escritorio_id,),
        )
        if (cursor.fetchone() or {}).get("total", 0) > 0:
            raise HTTPException(
                status_code=400,
                detail="Existem salas vinculadas a este escritório. Remova-as antes.",
            )
        cursor.execute("DELETE FROM recepcao_escritorios WHERE id = %s", (escritorio_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Escritório não encontrado")
        conn.commit()
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[RECEPCAO/ESCRITORIOS/DELETE] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao deletar escritório: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ============================================================
# SALAS
# ============================================================

@router.get("/salas")
async def list_salas(unit_id: Optional[int] = None,
                     escritorio_id: Optional[int] = None,
                     ativa: Optional[bool] = None):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        sql = (
            "SELECT s.id, s.unit_id, s.escritorio_id, s.nome, s.tipo, s.capacidade, "
            "       s.descricao, s.cor, s.ativa, s.criado_por, s.created_at, s.updated_at, "
            "       u.nome AS unit_nome, u.sigla AS unit_sigla, "
            "       e.nome AS escritorio_nome "
            "FROM recepcao_salas s "
            "LEFT JOIN unidades_cpe u         ON u.id = s.unit_id "
            "LEFT JOIN recepcao_escritorios e ON e.id = s.escritorio_id "
            "WHERE 1=1"
        )
        params = []
        if unit_id is not None:
            sql += " AND s.unit_id = %s"; params.append(unit_id)
        if escritorio_id is not None:
            # Sala sem escritorio_id = "comum" à unidade (aparece em qualquer escritório)
            sql += " AND (s.escritorio_id = %s OR s.escritorio_id IS NULL)"; params.append(escritorio_id)
        if ativa is not None:
            sql += " AND s.ativa = %s"; params.append(1 if ativa else 0)
        sql += " ORDER BY u.nome, e.nome, s.nome"
        cursor.execute(sql, params)
        return convert_datetime_list(cursor.fetchall())
    except Exception as err:
        logger.error(f"[RECEPCAO/SALAS/LIST] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar salas: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.post("/salas", status_code=status.HTTP_201_CREATED)
async def create_sala(data: SalaCreate):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        role = _get_user_role(cursor, data.criado_por)
        if role not in ROLES_GERENCIAM_SALA:
            raise HTTPException(
                status_code=403,
                detail="Apenas Administrador ou Responsável de Grupo podem cadastrar salas",
            )

        cursor.execute("SELECT id FROM unidades_cpe WHERE id = %s AND ativo = 1", (data.unit_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="Unidade inválida ou inativa")

        if data.escritorio_id:
            cursor.execute(
                "SELECT id FROM recepcao_escritorios WHERE id = %s AND unit_id = %s AND ativo = 1",
                (data.escritorio_id, data.unit_id),
            )
            if not cursor.fetchone():
                raise HTTPException(status_code=400, detail="Escritório inválido para esta unidade")

        cursor.execute(
            "INSERT INTO recepcao_salas "
            "(unit_id, escritorio_id, nome, tipo, capacidade, descricao, cor, ativa, criado_por) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                data.unit_id, data.escritorio_id, data.nome, data.tipo, data.capacidade,
                data.descricao, data.cor or "#3b82f6",
                1 if data.ativa else 0, data.criado_por,
            ),
        )
        conn.commit()
        new_id = cursor.lastrowid
        cursor.execute(
            "SELECT id, unit_id, escritorio_id, nome, tipo, capacidade, descricao, cor, ativa, "
            "       criado_por, created_at, updated_at FROM recepcao_salas WHERE id = %s",
            (new_id,),
        )
        return convert_datetime_to_string(cursor.fetchone())
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[RECEPCAO/SALAS/CREATE] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar sala: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.put("/salas/{sala_id}")
async def update_sala(sala_id: int, data: SalaUpdate):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        role = _get_user_role(cursor, data.atualizado_por)
        if role not in ROLES_GERENCIAM_SALA:
            raise HTTPException(status_code=403, detail="Sem permissão para editar sala")

        cursor.execute("SELECT id FROM recepcao_salas WHERE id = %s", (sala_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Sala não encontrada")

        updates, params = [], []
        if data.unit_id is not None:
            cursor.execute("SELECT id FROM unidades_cpe WHERE id = %s", (data.unit_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=400, detail="Unidade inválida")
            updates.append("unit_id=%s"); params.append(data.unit_id)
        if data.escritorio_id is not None:
            if data.escritorio_id == 0:
                # sentinela para limpar
                updates.append("escritorio_id=%s"); params.append(None)
            else:
                cursor.execute(
                    "SELECT id FROM recepcao_escritorios WHERE id = %s",
                    (data.escritorio_id,),
                )
                if not cursor.fetchone():
                    raise HTTPException(status_code=400, detail="Escritório inválido")
                updates.append("escritorio_id=%s"); params.append(data.escritorio_id)
        if data.nome is not None:        updates.append("nome=%s");        params.append(data.nome)
        if data.tipo is not None:        updates.append("tipo=%s");        params.append(data.tipo)
        if data.capacidade is not None:  updates.append("capacidade=%s");  params.append(data.capacidade)
        if data.descricao is not None:   updates.append("descricao=%s");   params.append(data.descricao)
        if data.cor is not None:         updates.append("cor=%s");         params.append(data.cor)
        if data.ativa is not None:       updates.append("ativa=%s");       params.append(1 if data.ativa else 0)

        if not updates:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

        params.append(sala_id)
        cursor.execute(f"UPDATE recepcao_salas SET {', '.join(updates)} WHERE id = %s", params)
        conn.commit()

        cursor.execute(
            "SELECT id, unit_id, escritorio_id, nome, tipo, capacidade, descricao, cor, ativa, "
            "       criado_por, created_at, updated_at FROM recepcao_salas WHERE id = %s",
            (sala_id,),
        )
        return convert_datetime_to_string(cursor.fetchone())
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[RECEPCAO/SALAS/UPDATE] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar sala: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.delete("/salas/{sala_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sala(sala_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        role = _get_user_role(cursor, usuario_id)
        if role not in ROLES_GERENCIAM_SALA:
            raise HTTPException(status_code=403, detail="Sem permissão para deletar sala")

        cursor.execute("DELETE FROM recepcao_salas WHERE id = %s", (sala_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Sala não encontrada")
        conn.commit()
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[RECEPCAO/SALAS/DELETE] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao deletar sala: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ============================================================
# RESERVAS
# ============================================================

@router.get("/reservas")
async def list_reservas(
    sala_id: Optional[int] = None,
    unit_id: Optional[int] = None,
    inicio: Optional[datetime] = None,
    fim: Optional[datetime] = None,
    usuario_id: Optional[int] = None,
):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        # housekeeping em cada listagem (barato e mantém o calendário sempre coerente)
        _expirar_pendentes(cursor)
        _concluir_passadas(cursor)
        conn.commit()

        sql = (
            "SELECT r.id, r.sala_id, r.usuario_id, r.titulo, r.descricao, "
            "       r.inicio, r.fim, r.status, r.confirmacao_prazo, r.confirmada_em, "
            "       r.cancelada_em, r.motivo_cancel, r.created_at, "
            "       s.nome AS sala_nome, s.cor AS sala_cor, s.unit_id, s.escritorio_id, "
            "       e.nome AS escritorio_nome, "
            "       u.name AS usuario_nome "
            "FROM recepcao_reservas r "
            "JOIN recepcao_salas s            ON s.id = r.sala_id "
            "LEFT JOIN recepcao_escritorios e ON e.id = s.escritorio_id "
            "JOIN users u ON u.id = r.usuario_id "
            "WHERE 1=1"
        )
        params = []
        if sala_id is not None:
            sql += " AND r.sala_id = %s"; params.append(sala_id)
        if unit_id is not None:
            sql += " AND s.unit_id = %s"; params.append(unit_id)
        if inicio is not None:
            sql += " AND r.fim >= %s"; params.append(inicio)
        if fim is not None:
            sql += " AND r.inicio <= %s"; params.append(fim)
        if usuario_id is not None:
            sql += " AND r.usuario_id = %s"; params.append(usuario_id)
        sql += " ORDER BY r.inicio"
        cursor.execute(sql, params)
        return convert_datetime_list(cursor.fetchall())
    except Exception as err:
        logger.error(f"[RECEPCAO/RESERVAS/LIST] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar reservas: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.post("/reservas", status_code=status.HTTP_201_CREATED)
async def create_reserva(data: ReservaCreate):
    if data.fim <= data.inicio:
        raise HTTPException(status_code=400, detail="Fim deve ser maior que o início")

    if data.inicio < datetime.now() - timedelta(minutes=1):
        raise HTTPException(status_code=400, detail="Não é possível agendar no passado")

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, ativa FROM recepcao_salas WHERE id = %s", (data.sala_id,))
        sala = cursor.fetchone()
        if not sala or not sala["ativa"]:
            raise HTTPException(status_code=400, detail="Sala inválida ou inativa")

        cursor.execute("SELECT id FROM users WHERE id = %s AND is_active = 1", (data.usuario_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="Usuário inválido ou inativo")

        if _conflito_de_horario(cursor, data.sala_id, data.inicio, data.fim):
            raise HTTPException(status_code=409, detail="Já existe uma reserva nesse horário")

        # Nova regra: deadline de confirmação é o próprio horário de início.
        # 40min antes do início o usuário receberá uma notificação automática
        # do scheduler para lembrar de confirmar.
        prazo = data.inicio
        cursor.execute(
            "INSERT INTO recepcao_reservas "
            "(sala_id, usuario_id, titulo, descricao, inicio, fim, status, confirmacao_prazo) "
            "VALUES (%s,%s,%s,%s,%s,%s,'pendente',%s)",
            (data.sala_id, data.usuario_id, data.titulo, data.descricao,
             data.inicio, data.fim, prazo),
        )
        new_id = cursor.lastrowid

        _criar_notificacao(
            cursor, data.usuario_id,
            f"Reserva criada (#{new_id}). Você receberá um lembrete "
            f"{CONFIRMACAO_MINUTOS} min antes do início para confirmar — "
            f"sem confirmação até o horário de início, a sala é liberada.",
            tipo="sucesso",
        )

        # Convida os usuários (se houver) — gera notificações para cada um
        if data.convidados_ids:
            _convidar_usuarios(
                cursor, new_id, data.usuario_id,
                data.convidados_ids, data.titulo, data.inicio,
            )

        conn.commit()

        cursor.execute(
            "SELECT r.*, s.nome AS sala_nome, s.cor AS sala_cor, u.name AS usuario_nome "
            "FROM recepcao_reservas r "
            "JOIN recepcao_salas s ON s.id = r.sala_id "
            "JOIN users u ON u.id = r.usuario_id "
            "WHERE r.id = %s",
            (new_id,),
        )
        return convert_datetime_to_string(cursor.fetchone())
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[RECEPCAO/RESERVAS/CREATE] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar reserva: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.post("/reservas/{reserva_id}/confirmar")
async def confirmar_reserva(reserva_id: int, usuario_id: int = Query(..., gt=0)):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, usuario_id, status, confirmacao_prazo "
            "FROM recepcao_reservas WHERE id = %s",
            (reserva_id,),
        )
        reserva = cursor.fetchone()
        if not reserva:
            raise HTTPException(status_code=404, detail="Reserva não encontrada")

        # admin pode confirmar por qualquer um
        role = _get_user_role(cursor, usuario_id)
        if reserva["usuario_id"] != usuario_id and role not in {"ADMIN", "TI", "MANAGER"}:
            raise HTTPException(status_code=403, detail="Apenas o autor pode confirmar a reserva")

        if reserva["status"] == "confirmada":
            return {"ok": True, "msg": "Reserva já confirmada"}
        if reserva["status"] != "pendente":
            raise HTTPException(
                status_code=400,
                detail=f"Não é possível confirmar uma reserva no status '{reserva['status']}'",
            )
        if reserva["confirmacao_prazo"] and reserva["confirmacao_prazo"] < datetime.now():
            cursor.execute(
                "UPDATE recepcao_reservas SET status='expirada', cancelada_em=NOW(), "
                "motivo_cancel='Confirmação não recebida até o início da reunião' WHERE id=%s",
                (reserva_id,),
            )
            conn.commit()
            raise HTTPException(
                status_code=400,
                detail="Prazo de confirmação expirou (a reunião já passou do horário de início)",
            )

        cursor.execute(
            "UPDATE recepcao_reservas SET status='confirmada', confirmada_em=NOW() WHERE id=%s",
            (reserva_id,),
        )
        _criar_notificacao(cursor, reserva["usuario_id"],
                           f"Reserva #{reserva_id} confirmada com sucesso.", tipo="sucesso")
        conn.commit()
        return {"ok": True, "msg": "Reserva confirmada"}
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[RECEPCAO/RESERVAS/CONFIRMAR] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao confirmar reserva: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.post("/reservas/{reserva_id}/cancelar")
async def cancelar_reserva(reserva_id: int, body: ReservaCancel):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, usuario_id, status FROM recepcao_reservas WHERE id = %s", (reserva_id,))
        reserva = cursor.fetchone()
        if not reserva:
            raise HTTPException(status_code=404, detail="Reserva não encontrada")

        role = _get_user_role(cursor, body.usuario_id)
        if reserva["usuario_id"] != body.usuario_id and role not in {"ADMIN", "TI", "MANAGER"}:
            raise HTTPException(status_code=403, detail="Apenas o autor ou um admin pode cancelar")

        if reserva["status"] in {"cancelada", "expirada", "concluida"}:
            return {"ok": True, "msg": "Reserva já encerrada"}

        cursor.execute(
            "UPDATE recepcao_reservas SET status='cancelada', cancelada_em=NOW(), "
            "motivo_cancel=%s WHERE id=%s",
            (body.motivo or "Cancelada pelo usuário", reserva_id),
        )
        _criar_notificacao(cursor, reserva["usuario_id"],
                           f"Reserva #{reserva_id} foi cancelada.", tipo="aviso")
        conn.commit()
        return {"ok": True, "msg": "Reserva cancelada"}
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[RECEPCAO/RESERVAS/CANCELAR] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao cancelar reserva: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ============================================================
# CONVIDADOS DE RESERVA
# ============================================================

@router.get("/reservas/{reserva_id}/convidados")
async def list_convidados(reserva_id: int):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT c.id, c.reserva_id, c.usuario_id, c.status, c.respondido_em, "
            "       c.convidado_por, c.created_at, "
            "       u.name AS usuario_nome, u.email AS usuario_email, "
            "       cb.name AS convidado_por_nome "
            "FROM recepcao_convidados c "
            "JOIN users u  ON u.id  = c.usuario_id "
            "JOIN users cb ON cb.id = c.convidado_por "
            "WHERE c.reserva_id = %s "
            "ORDER BY c.created_at",
            (reserva_id,),
        )
        return convert_datetime_list(cursor.fetchall())
    except Exception as err:
        logger.error(f"[RECEPCAO/CONVIDADOS/LIST] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar convidados: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.post("/reservas/{reserva_id}/convidar")
async def convidar_para_reserva(reserva_id: int, body: ConvidarBody):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, usuario_id, titulo, inicio FROM recepcao_reservas WHERE id = %s",
            (reserva_id,),
        )
        reserva = cursor.fetchone()
        if not reserva:
            raise HTTPException(status_code=404, detail="Reserva não encontrada")

        role = _get_user_role(cursor, body.convidador_id)
        if reserva["usuario_id"] != body.convidador_id and role not in {"ADMIN", "TI", "MANAGER"}:
            raise HTTPException(status_code=403, detail="Apenas o autor da reserva pode convidar")

        novos = _convidar_usuarios(
            cursor, reserva_id, body.convidador_id,
            body.convidados_ids, reserva["titulo"], reserva["inicio"],
        )
        conn.commit()
        return {"ok": True, "novos": novos}
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[RECEPCAO/CONVIDAR] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao convidar: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.post("/convites/{convite_id}/responder")
async def responder_convite(convite_id: int, body: ResponderConviteBody):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT c.id, c.reserva_id, c.usuario_id, c.status, "
            "       r.titulo, r.usuario_id AS dono_id, u.name AS convidado_nome "
            "FROM recepcao_convidados c "
            "JOIN recepcao_reservas r ON r.id = c.reserva_id "
            "JOIN users u ON u.id = c.usuario_id "
            "WHERE c.id = %s",
            (convite_id,),
        )
        convite = cursor.fetchone()
        if not convite:
            raise HTTPException(status_code=404, detail="Convite não encontrado")
        if convite["usuario_id"] != body.usuario_id:
            raise HTTPException(status_code=403, detail="Este convite não é seu")

        novo_status = "aceito" if body.aceitar else "recusado"
        if convite["status"] == novo_status:
            return {"ok": True, "msg": f"Convite já estava como {novo_status}"}

        cursor.execute(
            "UPDATE recepcao_convidados SET status=%s, respondido_em=NOW() WHERE id=%s",
            (novo_status, convite_id),
        )
        # Notifica o dono da reserva
        verbo = "aceitou" if body.aceitar else "recusou"
        msg = f'{convite["convidado_nome"]} {verbo} o convite para "{convite["titulo"]}".'
        try:
            cursor.execute(
                "INSERT INTO notificacoes (ticket_id, usuario_id, mensagem, tipo, lido) "
                "VALUES (%s, %s, %s, %s, 0)",
                (convite["reserva_id"], convite["dono_id"], msg[:255],
                 "convite_aceito_reuniao" if body.aceitar else "convite_recusado_reuniao"),
            )
        except Exception as err:
            logger.warning(f"[RECEPCAO/RESPONDER] notif fail: {err}")
        conn.commit()
        return {"ok": True, "status": novo_status}
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[RECEPCAO/RESPONDER] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao responder convite: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.get("/convites/usuario/{usuario_id}")
async def list_convites_usuario(usuario_id: int, somente_pendentes: bool = False):
    """Convites recebidos por um usuário (com info da reserva)."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        sql = (
            "SELECT c.id, c.reserva_id, c.status, c.respondido_em, c.created_at, "
            "       r.titulo, r.inicio, r.fim, r.status AS reserva_status, "
            "       s.nome AS sala_nome, "
            "       cb.name AS convidado_por_nome "
            "FROM recepcao_convidados c "
            "JOIN recepcao_reservas r ON r.id = c.reserva_id "
            "JOIN recepcao_salas s    ON s.id = r.sala_id "
            "JOIN users cb            ON cb.id = c.convidado_por "
            "WHERE c.usuario_id = %s "
        )
        params = [usuario_id]
        if somente_pendentes:
            sql += " AND c.status = 'pendente' "
        sql += " ORDER BY r.inicio DESC LIMIT 200"
        cursor.execute(sql, params)
        return convert_datetime_list(cursor.fetchall())
    except Exception as err:
        logger.error(f"[RECEPCAO/CONVITES/LIST] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar convites: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ============================================================
# ENVIOS
# ============================================================

@router.get("/envios")
async def list_envios(remetente_id: Optional[int] = None):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        sql = (
            "SELECT e.id, e.remetente_id, e.destino, e.destinatario, e.valor_mercadoria, "
            "       e.codigo_correios, e.status_correios, e.status_data, e.status_local, "
            "       e.ultima_atualizacao, e.observacoes, e.created_at, e.updated_at, "
            "       u.name AS remetente_nome "
            "FROM recepcao_envios e "
            "JOIN users u ON u.id = e.remetente_id "
            "WHERE 1=1"
        )
        params = []
        if remetente_id is not None:
            sql += " AND e.remetente_id = %s"; params.append(remetente_id)
        sql += " ORDER BY e.created_at DESC"
        cursor.execute(sql, params)
        return convert_datetime_list(cursor.fetchall())
    except Exception as err:
        logger.error(f"[RECEPCAO/ENVIOS/LIST] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar envios: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.post("/envios", status_code=status.HTTP_201_CREATED)
async def create_envio(data: EnvioCreate):
    if data.codigo_correios and not validar_codigo(data.codigo_correios):
        raise HTTPException(
            status_code=400,
            detail="Código dos Correios inválido (esperado AA123456789BR)",
        )

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE id = %s AND is_active = 1", (data.remetente_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="Remetente inválido")

        cursor.execute(
            "INSERT INTO recepcao_envios "
            "(remetente_id, destino, destinatario, valor_mercadoria, codigo_correios, observacoes) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (data.remetente_id, data.destino, data.destinatario,
             data.valor_mercadoria, (data.codigo_correios or "").upper() or None, data.observacoes),
        )
        conn.commit()
        new_id = cursor.lastrowid

        cursor.execute(
            "SELECT e.*, u.name AS remetente_nome FROM recepcao_envios e "
            "JOIN users u ON u.id = e.remetente_id WHERE e.id = %s",
            (new_id,),
        )
        return convert_datetime_to_string(cursor.fetchone())
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[RECEPCAO/ENVIOS/CREATE] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar envio: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.put("/envios/{envio_id}")
async def update_envio(envio_id: int, data: EnvioUpdate):
    if data.codigo_correios and not validar_codigo(data.codigo_correios):
        raise HTTPException(status_code=400, detail="Código dos Correios inválido")

    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM recepcao_envios WHERE id = %s", (envio_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Envio não encontrado")

        updates, params = [], []
        if data.destino is not None:           updates.append("destino=%s");           params.append(data.destino)
        if data.destinatario is not None:      updates.append("destinatario=%s");      params.append(data.destinatario)
        if data.valor_mercadoria is not None:  updates.append("valor_mercadoria=%s");  params.append(data.valor_mercadoria)
        if data.codigo_correios is not None:
            updates.append("codigo_correios=%s")
            params.append((data.codigo_correios or "").upper() or None)
        if data.observacoes is not None:       updates.append("observacoes=%s");       params.append(data.observacoes)
        if data.status_correios is not None:
            updates.append("status_correios=%s")
            params.append((data.status_correios or "")[:120] or None)
            # marcamos a hora da última atualização — assim o usuário
            # sabe quando foi a edição manual
            updates.append("ultima_atualizacao=NOW()")
        if data.status_local is not None:
            updates.append("status_local=%s")
            params.append((data.status_local or "")[:180] or None)

        if not updates:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

        params.append(envio_id)
        cursor.execute(f"UPDATE recepcao_envios SET {', '.join(updates)} WHERE id=%s", params)
        conn.commit()

        cursor.execute(
            "SELECT e.*, u.name AS remetente_nome FROM recepcao_envios e "
            "JOIN users u ON u.id = e.remetente_id WHERE e.id = %s",
            (envio_id,),
        )
        return convert_datetime_to_string(cursor.fetchone())
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[RECEPCAO/ENVIOS/UPDATE] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar envio: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.delete("/envios/{envio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_envio(envio_id: int):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("DELETE FROM recepcao_envios WHERE id = %s", (envio_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Envio não encontrado")
        conn.commit()
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[RECEPCAO/ENVIOS/DELETE] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao deletar envio: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ============================================================
# EVENTOS DE ENVIO (timeline manual estilo Correios)
# ============================================================

def _sincronizar_status_envio(cursor, envio_id: int) -> None:
    """Após inserir/editar/excluir evento, atualiza o registro do envio
    com os dados do evento mais recente (visível na listagem da tabela)."""
    cursor.execute(
        "SELECT descricao, local, data_evento FROM recepcao_envio_eventos "
        "WHERE envio_id = %s ORDER BY data_evento DESC, id DESC LIMIT 1",
        (envio_id,),
    )
    ultimo = cursor.fetchone()
    if ultimo:
        cursor.execute(
            "UPDATE recepcao_envios SET status_correios=%s, status_local=%s, "
            "       status_data=%s, ultima_atualizacao=NOW() WHERE id=%s",
            (
                (ultimo["descricao"] or "")[:120],
                (ultimo["local"] or "")[:180] if ultimo["local"] else None,
                ultimo["data_evento"],
                envio_id,
            ),
        )
    else:
        cursor.execute(
            "UPDATE recepcao_envios SET status_correios=NULL, status_local=NULL, "
            "       status_data=NULL, ultima_atualizacao=NOW() WHERE id=%s",
            (envio_id,),
        )


@router.get("/envios/{envio_id}/eventos")
async def listar_eventos(envio_id: int):
    """Lista eventos do envio em ordem cronológica decrescente (mais recente primeiro)."""
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, envio_id, tipo, descricao, local, data_evento, created_at "
            "FROM recepcao_envio_eventos WHERE envio_id = %s "
            "ORDER BY data_evento DESC, id DESC",
            (envio_id,),
        )
        eventos = cursor.fetchall()
        return [convert_datetime_to_string(e) for e in eventos]
    except Exception as err:
        logger.error(f"[RECEPCAO/EVENTOS/LIST] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar eventos: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.post("/envios/{envio_id}/eventos", status_code=status.HTTP_201_CREATED)
async def criar_evento(envio_id: int, payload: EventoCreate):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM recepcao_envios WHERE id = %s", (envio_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Envio não encontrado")

        cursor.execute(
            "INSERT INTO recepcao_envio_eventos (envio_id, tipo, descricao, local, data_evento) "
            "VALUES (%s, %s, %s, %s, %s)",
            (envio_id, payload.tipo, payload.descricao,
             payload.local or None, payload.data_evento.replace("T", " ")),
        )
        novo_id = cursor.lastrowid
        _sincronizar_status_envio(cursor, envio_id)
        conn.commit()

        cursor.execute("SELECT * FROM recepcao_envio_eventos WHERE id = %s", (novo_id,))
        return convert_datetime_to_string(cursor.fetchone())
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[RECEPCAO/EVENTOS/CREATE] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao criar evento: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.put("/eventos/{evento_id}")
async def atualizar_evento(evento_id: int, payload: EventoUpdate):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT envio_id FROM recepcao_envio_eventos WHERE id = %s", (evento_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Evento não encontrado")
        envio_id = row["envio_id"]

        campos, valores = [], []
        for campo in ("tipo", "descricao", "local"):
            v = getattr(payload, campo)
            if v is not None:
                campos.append(f"{campo} = %s"); valores.append(v)
        if payload.data_evento is not None:
            campos.append("data_evento = %s")
            valores.append(payload.data_evento.replace("T", " "))

        if campos:
            valores.append(evento_id)
            cursor.execute(
                f"UPDATE recepcao_envio_eventos SET {', '.join(campos)} WHERE id = %s",
                valores,
            )
        _sincronizar_status_envio(cursor, envio_id)
        conn.commit()

        cursor.execute("SELECT * FROM recepcao_envio_eventos WHERE id = %s", (evento_id,))
        return convert_datetime_to_string(cursor.fetchone())
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[RECEPCAO/EVENTOS/UPDATE] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar evento: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@router.delete("/eventos/{evento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_evento(evento_id: int):
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT envio_id FROM recepcao_envio_eventos WHERE id = %s", (evento_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Evento não encontrado")
        envio_id = row["envio_id"]

        cursor.execute("DELETE FROM recepcao_envio_eventos WHERE id = %s", (evento_id,))
        _sincronizar_status_envio(cursor, envio_id)
        conn.commit()
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[RECEPCAO/EVENTOS/DELETE] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao deletar evento: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ============================================================
# RASTREAMENTO via API seurastreio.com.br (com cache de 4h)
# ============================================================

# Janela mínima entre consultas do mesmo envio (em horas).
# Plano gratuito = 50 consultas/mês; com 4h por envio, a mesma
# encomenda só consome 2 consultas/dia no máximo, mesmo que vários
# usuários tentem rastrear simultaneamente.
RASTREIO_CACHE_HORAS = 4


def _envio_para_resultado_cache(envio: dict) -> dict:
    """Monta o payload do cache a partir das colunas já gravadas no envio."""
    proxima = None
    if envio.get("ultima_consulta_api"):
        proxima = envio["ultima_consulta_api"] + timedelta(hours=RASTREIO_CACHE_HORAS)

    eventos = []
    if envio.get("status_correios"):
        eventos.append({
            "codigo":    "",
            "descricao": envio["status_correios"],
            "detalhe":   "",
            "data":      envio["status_data"].isoformat(sep=" ") if envio.get("status_data") else "",
            "local":     envio.get("status_local") or "",
        })

    return {
        "ok": True,
        "cached": True,
        "codigo":          envio["codigo_correios"],
        "status":          "found" if envio.get("status_correios") else "pending",
        "descricao":       envio.get("status_correios") or "",
        "data":            envio["status_data"].isoformat(sep=" ") if envio.get("status_data") else None,
        "local":           envio.get("status_local"),
        "eventos":         eventos,
        "previsaoEntrega": None,
        "linkDetalhes":    f"https://seurastreio.com.br/objetos/{envio['codigo_correios']}" if envio.get("codigo_correios") else None,
        "ultima_consulta_api": envio["ultima_consulta_api"].isoformat(sep=" ") if envio.get("ultima_consulta_api") else None,
        "proxima_consulta_em": proxima.isoformat(sep=" ") if proxima else None,
        "cache_horas": RASTREIO_CACHE_HORAS,
        "message": (
            f"Dados do cache (atualizado nas últimas {RASTREIO_CACHE_HORAS}h). "
            f"Próxima consulta liberada em {proxima.strftime('%d/%m %H:%M')}." if proxima else ""
        ),
    }


@router.get("/envios/{envio_id}/rastrear")
async def rastrear_via_api(envio_id: int):
    """
    Consulta rastreamento via API seurastreio.com.br com cache de 4h.

    Se o envio foi consultado há menos de 4h, retorna os dados do banco
    (sem consumir consulta da API). Caso contrário, faz a chamada real
    e atualiza o cache.
    """
    conn = get_db_or_404()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, codigo_correios, status_correios, status_local, status_data, "
            "       ultima_atualizacao, ultima_consulta_api "
            "FROM recepcao_envios WHERE id = %s",
            (envio_id,),
        )
        envio = cursor.fetchone()
        if not envio:
            raise HTTPException(status_code=404, detail="Envio não encontrado")
        if not envio["codigo_correios"]:
            raise HTTPException(status_code=400, detail="Este envio não tem código de rastreio")

        # ---- CACHE: se consulta foi feita há menos de RASTREIO_CACHE_HORAS, devolve do banco
        if envio.get("ultima_consulta_api"):
            agora = datetime.now()
            delta = agora - envio["ultima_consulta_api"]
            if delta < timedelta(hours=RASTREIO_CACHE_HORAS):
                logger.info(
                    f"[RECEPCAO/ENVIOS/RASTREAR] cache HIT envio={envio_id} "
                    f"(consultado há {int(delta.total_seconds()/60)}min)"
                )
                return _envio_para_resultado_cache(envio)

        # ---- Sem cache válido — consulta a API
        resultado = rastrear_seurastreio(envio["codigo_correios"])

        # Sucesso: grava no banco + marca timestamp de consulta
        if resultado.get("ok"):
            cursor.execute(
                "UPDATE recepcao_envios SET status_correios=%s, status_local=%s, "
                "       status_data=%s, ultima_atualizacao=NOW(), ultima_consulta_api=NOW() "
                "WHERE id=%s",
                (
                    (resultado.get("descricao") or "")[:120] or None,
                    (resultado.get("local") or "")[:180] if resultado.get("local") else None,
                    resultado.get("data"),
                    envio_id,
                ),
            )
            conn.commit()
            resultado["cached"] = False

        return resultado
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"[RECEPCAO/ENVIOS/RASTREAR] {err}")
        raise HTTPException(status_code=500, detail=f"Erro ao rastrear: {err}")
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

