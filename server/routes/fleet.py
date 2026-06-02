"""
Módulo de Frotas - Gestão de veículos, checklists e viagens/custos
"""

from fastapi import APIRouter, HTTPException, status, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse
from database import get_db_or_404, convert_datetime_to_string, convert_datetime_list
import os
import uuid
import shutil
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fleet", tags=["Fleet"])

# Diretório de uploads: web/uploads/fleet/
UPLOAD_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "web", "uploads", "fleet")
)
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}


# ============================================================
# HELPER: obter user_id da sessão
# ============================================================

def _resolve_user_id(request: Request) -> int | None:
    """
    Tenta autenticar via cookie cpe_session (priority) ou header X-Auth-Token (fallback).
    Retorna user_id se válido, None caso contrário.
    Testa ambas as fontes independentemente — um cookie inválido não bloqueia o header.
    """
    from security import parse_session_token, COOKIE_NAME

    # 1. Tentar cookie HTTP-only
    cookie_token = request.cookies.get(COOKIE_NAME)
    if cookie_token:
        uid = parse_session_token(cookie_token)
        if uid:
            return uid

    # 2. Fallback: header X-Auth-Token (cross-origin/XAMPP local)
    header_token = request.headers.get("X-Auth-Token") or request.headers.get("x-auth-token")
    if header_token:
        uid = parse_session_token(header_token)
        if uid:
            return uid

    return None


def _get_user_id(request: Request) -> int:
    uid = _resolve_user_id(request)
    if not uid:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return uid


def _get_user_role(request: Request) -> dict:
    from security import get_user_by_id
    uid = _resolve_user_id(request)
    if not uid:
        raise HTTPException(status_code=401, detail="Não autenticado")
    user = get_user_by_id(uid)
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return user


# ID do grupo "Frotas" em cpe_grupo — responsáveis podem gerenciar status de veículos
FLEET_GROUP_ID = 13

def _can_manage_fleet(user: dict) -> bool:
    role = user.get("role")
    if role in ("ADMIN", "TI"):
        return True
    return role == "RESPONSAVEL_GRUPO" and user.get("group_id") == FLEET_GROUP_ID


def _can_delete_vehicle(user: dict) -> bool:
    """
    Apenas ADMIN ou Responsável do grupo Frotas podem excluir veículos.
    TI deliberadamente fica de fora — exclusão é decisão de gestão, não de
    suporte técnico. (Pedido explícito do usuário em 2026-05-06.)
    """
    role = user.get("role")
    if role == "ADMIN":
        return True
    return role == "RESPONSAVEL_GRUPO" and user.get("group_id") == FLEET_GROUP_ID


# ============================================================
# VEÍCULOS
# ============================================================

@router.get("/vehicles")
def list_vehicles(request: Request, include_inativos: int = 0):
    """Lista veículos. `include_inativos=1` retorna também os inativos
    (apenas Frotas/ADMIN/TI pode usar; usuários comuns sempre veem só ativos)."""
    user = _get_user_role(request)
    user_id = user["id"]
    is_fleet_mgr = _can_manage_fleet(user)

    # Só Frotas/ADMIN/TI pode ver inativos (eles fazem reativação)
    if include_inativos and not is_fleet_mgr:
        include_inativos = 0

    where_status = "" if include_inativos else "WHERE v.status != 'inativo'"

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(f"""
            SELECT v.*,
                   p.foto_path AS foto_referencia,
                   u.name AS created_by_name,
                   (SELECT 1 FROM fleet_vehicle_subscriptions s
                     WHERE s.vehicle_id = v.id AND s.user_id = %s AND s.tipo='return'
                     LIMIT 1
                   ) AS is_subscribed,
                   (SELECT CONCAT(m.tipo,' a partir de ',m.data_entrada)
                    FROM fleet_maintenance m
                    WHERE m.vehicle_id = v.id AND m.status IN ('agendado','em_andamento')
                      AND m.data_entrada IS NOT NULL
                    ORDER BY m.data_entrada LIMIT 1
                   ) AS manutencao_proxima,
                   (SELECT CONCAT(sol.name,'|',TIME_FORMAT(r.horario_inicio,'%%H:%%i'),'|',TIME_FORMAT(r.horario_fim,'%%H:%%i'),'|',r.destino)
                    FROM fleet_reservations r
                    JOIN users sol ON sol.id = r.solicitante_id
                    WHERE r.vehicle_id = v.id AND r.status = 'aprovado'
                      AND r.data_reserva = CURDATE()
                      AND r.horario_fim >= CURTIME()
                    ORDER BY r.horario_inicio LIMIT 1
                   ) AS reserva_ativa,
                   (SELECT ck.id FROM fleet_checklists ck
                    WHERE ck.vehicle_id = v.id
                      AND ck.status NOT IN ('retornado','retornado_com_avaria','cancelado')
                    ORDER BY ck.id DESC LIMIT 1
                   ) AS checklist_pendente_id,
                   (SELECT ck.status FROM fleet_checklists ck
                    WHERE ck.vehicle_id = v.id
                      AND ck.status NOT IN ('retornado','retornado_com_avaria','cancelado')
                    ORDER BY ck.id DESC LIMIT 1
                   ) AS checklist_pendente_status
            FROM fleet_vehicles v
            LEFT JOIN fleet_vehicle_photos p
                   ON p.vehicle_id = v.id AND p.is_current = 1 AND p.angulo = 'frente'
            LEFT JOIN users u ON u.id = v.created_by
            {where_status}
            ORDER BY FIELD(v.status,'ativo','em_viagem','manutencao','revisao','inativo'), v.modelo
        """, (user_id,))
        vehicles = cursor.fetchall()
        # Aluguel mensal é confidencial — só Frotas/ADMIN/TI vê.
        if not is_fleet_mgr:
            for v in vehicles:
                v.pop("valor_aluguel_mensal", None)
        return {"success": True, "vehicles": vehicles}
    finally:
        cursor.close()
        conn.close()


@router.post("/vehicles")
def create_vehicle(request: Request, data: dict):
    user = _get_user_role(request)
    if not _can_manage_fleet(user):
        raise HTTPException(
            status_code=403,
            detail="Apenas Administrador, T.I. ou Responsável do grupo Frotas podem cadastrar veículos."
        )
    user_id = user["id"]
    placa = (data.get("placa") or "").strip().upper()
    modelo = (data.get("modelo") or "").strip()
    if not placa or not modelo:
        raise HTTPException(status_code=400, detail="Placa e modelo são obrigatórios")

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            INSERT INTO fleet_vehicles
                (placa, modelo, tipo, ano, cor, unidade, km_atual, status,
                 valor_aluguel_mensal, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'ativo', %s, %s)
        """, (
            placa,
            modelo,
            data.get("tipo", "carro"),
            data.get("ano") or None,
            data.get("cor", ""),
            data.get("unidade", ""),
            data.get("km_atual") or 0,
            float(data.get("valor_aluguel_mensal") or 0),
            user_id,
        ))
        conn.commit()
        new_id = cursor.lastrowid
        logger.info(f"[FLEET] Veículo criado: {placa} (id={new_id})")
        return {"success": True, "id": new_id, "message": "Veículo cadastrado com sucesso!"}
    except Exception as e:
        conn.rollback()
        if "Duplicate entry" in str(e):
            raise HTTPException(status_code=400, detail=f"Placa '{placa}' já cadastrada")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.put("/vehicles/{vehicle_id}")
def update_vehicle(vehicle_id: int, request: Request, data: dict):
    user = _get_user_role(request)
    if not _can_manage_fleet(user):
        raise HTTPException(
            status_code=403,
            detail="Apenas Administrador, T.I. ou Responsável do grupo Frotas podem editar veículos."
        )
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            UPDATE fleet_vehicles
            SET modelo=%s, tipo=%s, ano=%s, cor=%s, unidade=%s, km_atual=%s,
                status=%s, valor_aluguel_mensal=%s
            WHERE id=%s
        """, (
            data.get("modelo"),
            data.get("tipo"),
            data.get("ano") or None,
            data.get("cor"),
            data.get("unidade"),
            data.get("km_atual") or 0,
            data.get("status"),
            float(data.get("valor_aluguel_mensal") or 0),
            vehicle_id,
        ))
        conn.commit()
        return {"success": True, "message": "Veículo atualizado com sucesso!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


_MOVIMENTACAO_STATUS = (
    "aprovado", "em_viagem", "devolvido", "retornado", "retornado_com_avaria",
)


def _vehicle_has_movement(cursor, vehicle_id: int) -> bool:
    """
    Decide se o veículo já teve movimentação real (saída aprovada de
    checklist, viagem registrada ou manutenção). Quando houver, o DELETE
    vira soft delete pra preservar histórico. Quando não, é seguro apagar
    de verdade junto com os registros auxiliares (fotos, reservas
    canceladas, alertas).
    """
    placeholders = ",".join(["%s"] * len(_MOVIMENTACAO_STATUS))
    cursor.execute(
        f"SELECT 1 FROM fleet_checklists "
        f" WHERE vehicle_id = %s AND status IN ({placeholders}) LIMIT 1",
        (vehicle_id, *_MOVIMENTACAO_STATUS),
    )
    if cursor.fetchone():
        return True

    cursor.execute(
        "SELECT 1 FROM fleet_trips WHERE vehicle_id = %s LIMIT 1",
        (vehicle_id,),
    )
    if cursor.fetchone():
        return True

    cursor.execute(
        "SELECT 1 FROM fleet_maintenance WHERE vehicle_id = %s LIMIT 1",
        (vehicle_id,),
    )
    if cursor.fetchone():
        return True

    return False


# ============================================================
# DELETE — Hard delete se nunca foi usado, soft delete se já teve
# movimentação. Só ADMIN ou Responsável do grupo Frotas.
# ============================================================
@router.delete("/vehicles/{vehicle_id}")
def delete_vehicle(vehicle_id: int, request: Request):
    user = _get_user_role(request)
    if not _can_delete_vehicle(user):
        raise HTTPException(
            status_code=403,
            detail="Apenas Administrador ou Responsável do grupo Frotas podem excluir veículos."
        )

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, placa, status FROM fleet_vehicles WHERE id = %s",
            (vehicle_id,),
        )
        veiculo = cursor.fetchone()
        if not veiculo:
            raise HTTPException(status_code=404, detail="Veículo não encontrado")

        if veiculo["status"] == "em_viagem":
            raise HTTPException(
                status_code=400,
                detail="Não é possível excluir um veículo que está em viagem. "
                       "Aguarde o retorno ou cancele a viagem antes."
            )

        if veiculo["status"] == "inativo":
            return {
                "success": True,
                "mode": "noop",
                "message": "Veículo já estava inativo",
            }

        teve_movimento = _vehicle_has_movement(cursor, vehicle_id)

        # ─────────────────────────────────────────────────────────
        # Caminho 1: SOFT DELETE — veículo já teve checklist aprovado
        # ou viagem ou manutenção. Preserva todo o histórico.
        # ─────────────────────────────────────────────────────────
        if teve_movimento:
            cursor.execute(
                "UPDATE fleet_vehicles SET status = 'inativo' WHERE id = %s",
                (vehicle_id,),
            )
            conn.commit()
            logger.info(
                f"[FLEET] Veículo {veiculo['placa']} (id={vehicle_id}) "
                f"INATIVADO (soft delete) por user {user.get('id')} ({user.get('role')}) "
                f"— já tinha movimentação."
            )
            return {
                "success": True,
                "mode": "soft",
                "message": (
                    f"Veículo {veiculo['placa']} foi inativado pois já tem movimentação "
                    f"registrada (checklists/viagens/manutenções). O histórico foi preservado."
                ),
            }

        # ─────────────────────────────────────────────────────────
        # Caminho 2: HARD DELETE — nunca foi usado. Limpa todos os
        # registros auxiliares (fotos, reservas, alertas, checklists
        # pendentes/cancelados) antes de apagar o veículo.
        # ─────────────────────────────────────────────────────────
        cursor.execute("DELETE FROM fleet_vehicle_photos  WHERE vehicle_id = %s", (vehicle_id,))
        cursor.execute("DELETE FROM fleet_vehicle_history WHERE vehicle_id = %s", (vehicle_id,))
        cursor.execute("DELETE FROM fleet_km_alerts       WHERE vehicle_id = %s", (vehicle_id,))
        cursor.execute("DELETE FROM fleet_reservations    WHERE vehicle_id = %s", (vehicle_id,))
        # Checklists aqui só podem estar em ('aguardando_vistoria',
        # 'aguardando_aprovacao','cancelado') — _vehicle_has_movement
        # retornaria True caso contrário e cairíamos no soft delete.
        cursor.execute("DELETE FROM fleet_checklists      WHERE vehicle_id = %s", (vehicle_id,))
        cursor.execute("DELETE FROM fleet_vehicles        WHERE id = %s",         (vehicle_id,))

        conn.commit()
        logger.info(
            f"[FLEET] Veículo {veiculo['placa']} (id={vehicle_id}) "
            f"APAGADO (hard delete) por user {user.get('id')} ({user.get('role')}) "
            f"— nunca foi movimentado."
        )
        return {
            "success": True,
            "mode": "hard",
            "message": (
                f"Veículo {veiculo['placa']} foi removido permanentemente "
                f"(nunca teve movimentação registrada)."
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"[FLEET/DELETE] erro: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao excluir: {e}")
    finally:
        cursor.close()
        conn.close()


ALLOWED_ANGULOS = {
    'frente', 'lateral', 'parachoque_dianteiro',
    'parachoque_traseiro', 'quatro_portas', 'paralama_traseiro',
    'problema', 'avaria_retorno',
}

@router.post("/vehicles/{vehicle_id}/photo")
async def upload_vehicle_photo(
    vehicle_id: int,
    request: Request,
    file: UploadFile = File(...),
    motivo: str = Form(""),
    angulo: str = Form("frente"),
    legenda: str = Form(""),
):
    """Upload de foto do veículo.

    - Ângulos fixos (frente, lateral, parachoque_*, paralama_*, quatro_portas):
      single-photo com histórico (arquiva a anterior).
    - Ângulos `adicional_*` ou `arranhado_*`: multi-photo (não arquiva nada).
      Cada upload gera um angulo único `adicional_<uuid8>` para preservar
      múltiplos `is_current=1` simultaneamente.
    """
    user_id = _get_user_id(request)

    is_adicional = (angulo or "").startswith("adicional")
    is_arranhado = (angulo or "").startswith("arranhado_")

    if not is_adicional and not is_arranhado and angulo not in ALLOWED_ANGULOS:
        angulo = "frente"

    # Adicionais sempre recebem uma chave única para coexistirem
    if is_adicional:
        angulo = f"adicional_{uuid.uuid4().hex[:8]}"

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Formato inválido. Use JPG, PNG ou WEBP.")

    filename = f"v{vehicle_id}_{angulo}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    photo_url = f"/SistemaCPE/web/uploads/fleet/{filename}"
    legenda_clean = (legenda or "").strip()[:80] or None

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        if not is_adicional and not is_arranhado:
            # Single-photo: arquiva a foto atual deste ângulo
            cursor.execute(
                """UPDATE fleet_vehicle_photos
                   SET is_current=0, substituida_por_user_id=%s, motivo_substituicao=%s
                   WHERE vehicle_id=%s AND is_current=1 AND angulo=%s""",
                (user_id, motivo or f"Substituição de foto — {angulo}", vehicle_id, angulo),
            )

        cursor.execute(
            """INSERT INTO fleet_vehicle_photos
               (vehicle_id, foto_path, angulo, legenda, is_current)
               VALUES (%s, %s, %s, %s, 1)""",
            (vehicle_id, photo_url, angulo, legenda_clean),
        )
        photo_id = cursor.lastrowid
        conn.commit()
        return {
            "success":   True,
            "id":        photo_id,
            "foto_path": photo_url,
            "angulo":    angulo,
            "legenda":   legenda_clean,
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.delete("/vehicles/{vehicle_id}/photo/{photo_id}")
def delete_vehicle_photo(vehicle_id: int, photo_id: int, request: Request):
    """Remove uma foto do veículo. Só permitido para fotos adicionais
    (angulo LIKE 'adicional_%') — fotos dos ângulos padrão são substituídas
    via upload, não removidas."""
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, angulo, foto_path FROM fleet_vehicle_photos WHERE id=%s AND vehicle_id=%s",
            (photo_id, vehicle_id),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Foto não encontrada.")
        if not (row["angulo"] or "").startswith("adicional"):
            raise HTTPException(
                status_code=400,
                detail="Apenas fotos adicionais podem ser removidas. Para trocar uma foto de ângulo padrão, faça upload de uma nova.",
            )

        cursor.execute("DELETE FROM fleet_vehicle_photos WHERE id=%s", (photo_id,))
        conn.commit()

        # Best-effort: apagar arquivo físico
        try:
            rel = (row["foto_path"] or "").replace("/SistemaCPE/web/uploads/fleet/", "")
            if rel:
                fp = os.path.join(UPLOAD_DIR, rel)
                if os.path.exists(fp):
                    os.remove(fp)
        except Exception:
            pass

        return {"success": True, "id": photo_id}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.get("/vehicles/{vehicle_id}/photos")
def get_vehicle_photos(vehicle_id: int, request: Request):
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT p.*, u.name AS substituida_por_nome
            FROM fleet_vehicle_photos p
            LEFT JOIN users u ON u.id = p.substituida_por_user_id
            WHERE p.vehicle_id = %s
            ORDER BY p.angulo, p.is_current DESC, p.created_at DESC
        """, (vehicle_id,))
        photos = cursor.fetchall()
        photos = convert_datetime_list(photos)
        return {"success": True, "photos": photos}
    finally:
        cursor.close()
        conn.close()


# ============================================================
# CHECKLISTS
# ============================================================

@router.get("/checklists")
def list_checklists(request: Request):
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT c.id, c.status, c.destino,
                   c.data_saida, c.horario_saida, c.km_saida,
                   c.data_retorno, c.km_retorno,
                   c.condutor_id, c.liberador_id,
                   c.recusa_justificativa,
                   v.placa, v.modelo, v.tipo,
                   cond.name AS condutor_nome,
                   lib.name  AS liberador_nome,
                   rec.name  AS recebedor_nome,
                   c.created_at
            FROM fleet_checklists c
            JOIN  fleet_vehicles v ON v.id = c.vehicle_id
            JOIN  users cond ON cond.id = c.condutor_id
            LEFT JOIN users lib ON lib.id = c.liberador_id
            LEFT JOIN users rec ON rec.id = c.recebedor_id
            ORDER BY c.created_at DESC
            LIMIT 200
        """)
        rows = cursor.fetchall()
        rows = convert_datetime_list(rows)
        return {"success": True, "checklists": rows}
    finally:
        cursor.close()
        conn.close()


@router.get("/checklists/{checklist_id}")
def get_checklist(checklist_id: int, request: Request):
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT c.*,
                   v.placa, v.modelo, v.tipo,
                   cond.name  AS condutor_nome,
                   lib.name   AS liberador_nome,
                   rec.name   AS recebedor_nome,
                   apv.name   AS aprovado_por_nome,
                   rp.name    AS recusa_por_nome,
                   ph.foto_path AS foto_veiculo
            FROM fleet_checklists c
            JOIN  fleet_vehicles v   ON v.id = c.vehicle_id
            JOIN  users cond ON cond.id = c.condutor_id
            LEFT JOIN users lib  ON lib.id  = c.liberador_id
            LEFT JOIN users rec  ON rec.id  = c.recebedor_id
            LEFT JOIN users apv  ON apv.id  = c.aprovado_por
            LEFT JOIN users rp   ON rp.id   = c.recusa_por
            LEFT JOIN fleet_vehicle_photos ph ON ph.vehicle_id = v.id AND ph.is_current = 1 AND ph.angulo = 'frente'
            WHERE c.id = %s
        """, (checklist_id,))
        checklist = cursor.fetchone()
        if not checklist:
            raise HTTPException(status_code=404, detail="Checklist não encontrado")

        cursor.execute(
            "SELECT * FROM fleet_checklist_problems WHERE checklist_id = %s",
            (checklist_id,)
        )
        checklist["problems"] = cursor.fetchall()

        # Inspection photos enriquecidas com a `legenda` do ângulo correspondente
        # da tabela de fotos do veículo (quando angulo='adicional_*').
        cursor.execute(
            """SELECT cp.*, vp.legenda AS legenda
                 FROM fleet_checklist_photos cp
                 LEFT JOIN fleet_vehicle_photos vp
                   ON vp.vehicle_id = %s
                  AND vp.angulo     = cp.angulo
                  AND vp.is_current = 1
                WHERE cp.checklist_id = %s
                ORDER BY cp.angulo, cp.created_at""",
            (checklist["vehicle_id"], checklist_id)
        )
        checklist["inspection_photos"] = cursor.fetchall()

        checklist = convert_datetime_to_string(checklist)
        return {"success": True, "checklist": checklist}
    finally:
        cursor.close()
        conn.close()


@router.post("/checklists/{checklist_id}/photos")
async def upload_checklist_photo(
    checklist_id: int,
    request: Request,
    file: UploadFile = File(...),
    angulo: str = Form("frente"),
):
    _get_user_id(request)

    if (
        angulo not in ALLOWED_ANGULOS
        and not angulo.startswith("arranhado_")
        and not angulo.startswith("adicional")
    ):
        angulo = "frente"

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Formato inválido. Use JPG, PNG ou WEBP.")

    filename = f"cl{checklist_id}_{angulo}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    photo_url = f"/SistemaCPE/web/uploads/fleet/{filename}"

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "INSERT INTO fleet_checklist_photos (checklist_id, angulo, foto_path) VALUES (%s, %s, %s)",
            (checklist_id, angulo, photo_url),
        )
        conn.commit()
        return {"success": True, "foto_path": photo_url, "angulo": angulo}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.post("/checklists/{checklist_id}/scratch-data")
def save_scratch_data(checklist_id: int, request: Request, data: dict):
    """Atualiza descricao_adicional do problema 'Arranhado/Risco' com JSON dos pontos."""
    _get_user_id(request)
    scratch_json = data.get("data", "")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            UPDATE fleet_checklist_problems
            SET descricao_adicional = %s
            WHERE checklist_id = %s AND item_nome = 'Arranhado/Risco'
            ORDER BY id DESC LIMIT 1
        """, (scratch_json, checklist_id))
        conn.commit()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.post("/checklists")
def create_checklist(request: Request, data: dict):
    user = _get_user_role(request)
    user_id = user["id"]
    # Usuário comum só pode se cadastrar como condutor do próprio checklist.
    # Só o responsável do grupo Frotas (ou ADMIN/TI) pode indicar outro condutor.
    if not _can_manage_fleet(user):
        data["condutor_id"] = user_id
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        # Verificar se o veículo tem checklist pendente (não finalizado)
        vehicle_id = data.get("vehicle_id")
        cursor.execute("""
            SELECT id, status FROM fleet_checklists
            WHERE vehicle_id = %s AND status NOT IN ('retornado','retornado_com_avaria','cancelado')
            LIMIT 1
        """, (vehicle_id,))
        pendente = cursor.fetchone()
        if pendente:
            status_labels = {
                'aguardando_vistoria': 'aguardando vistoria de saida',
                'aprovado': 'aprovado (aguardando inicio de viagem)',
                'em_viagem': 'em viagem',
                'devolvido': 'devolvido (aguardando vistoria de retorno)',
            }
            lbl = status_labels.get(pendente['status'], pendente['status'])
            raise HTTPException(
                status_code=400,
                detail=f"Este veiculo possui checklist #{pendente['id']} ainda {lbl}. Finalize-o antes de criar um novo."
            )

        # Verificar se tem manutenção agendada para hoje
        cursor.execute("""
            SELECT m.id, m.tipo, m.data_entrada
            FROM fleet_maintenance m
            WHERE m.vehicle_id = %s AND m.status IN ('agendado','em_andamento')
              AND m.data_entrada IS NOT NULL
              AND m.data_entrada <= CURDATE()
              AND (m.data_conclusao IS NULL OR m.data_conclusao >= CURDATE())
        """, (vehicle_id,))
        manut_bloqueio = cursor.fetchone()
        if manut_bloqueio:
            raise HTTPException(
                status_code=400,
                detail=f"Veiculo com manutencao agendada ({manut_bloqueio['tipo']}) a partir de {manut_bloqueio['data_entrada']}. Aguarde liberacao pelo responsavel."
            )

        # Verificar reserva aprovada para outro usuário (30min antes até fim)
        cursor.execute("""
            SELECT r.id, r.solicitante_id, r.horario_inicio, r.horario_fim, sol.name AS sol_nome
            FROM fleet_reservations r
            JOIN users sol ON sol.id = r.solicitante_id
            WHERE r.vehicle_id = %s AND r.status = 'aprovado'
              AND r.data_reserva = CURDATE()
              AND ADDTIME(r.horario_inicio, '-01:00:00') <= CURTIME()
              AND r.horario_fim > CURTIME()
              AND r.solicitante_id != %s
        """, (vehicle_id, user_id))
        reserva_bloqueio = cursor.fetchone()
        if reserva_bloqueio:
            raise HTTPException(
                status_code=400,
                detail=f"Veiculo reservado por {reserva_bloqueio['sol_nome']} de {reserva_bloqueio['horario_inicio']} a {reserva_bloqueio['horario_fim']}"
            )

        cursor.execute("""
            INSERT INTO fleet_checklists (
                vehicle_id, condutor_id, destino,
                data_saida, horario_saida, km_saida, nivel_combustivel_saida,
                cartao_combustivel_saida, documento_veiculo_saida,
                assinatura_condutor_saida, observacoes, status
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'aguardando_vistoria')
        """, (
            data.get("vehicle_id"),
            data.get("condutor_id"),
            data.get("destino"),
            data.get("data_saida"),
            data.get("horario_saida"),
            data.get("km_saida"),
            data.get("nivel_combustivel_saida"),
            1 if data.get("cartao_combustivel_saida") else 0,
            1 if data.get("documento_veiculo_saida") else 0,
            data.get("assinatura_condutor_saida"),
            data.get("observacoes"),
        ))
        checklist_id = cursor.lastrowid

        for p in (data.get("problems") or []):
            nome = (p.get("item_nome") or "").strip()
            if nome:
                cursor.execute(
                    """INSERT INTO fleet_checklist_problems
                       (checklist_id, item_nome, descricao_adicional, fase)
                       VALUES (%s,%s,%s,'saida')""",
                    (checklist_id, nome, p.get("descricao_adicional", "")),
                )

        # Veículo permanece 'ativo' até o vistoriador aprovar a saída
        conn.commit()
        logger.info(f"[FLEET] Checklist criado id={checklist_id} (aguardando_vistoria)")
        return {"success": True, "id": checklist_id, "message": "Checklist de saída registrado! Aguardando vistoria."}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.post("/checklists/{checklist_id}/vistoriar-saida")
def vistoriar_saida(checklist_id: int, request: Request, data: dict):
    """Vistoriador assina a saída — responsável do grupo Frotas, ADMIN ou TI."""
    user = _get_user_role(request)
    if not _can_manage_fleet(user):
        raise HTTPException(
            status_code=403,
            detail="Somente o responsável do grupo Frotas (ou ADMIN/TI) pode vistoriar."
        )
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT condutor_id, vehicle_id, status FROM fleet_checklists WHERE id=%s",
            (checklist_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Checklist não encontrado")
        if row["status"] != "aguardando_vistoria":
            raise HTTPException(status_code=400, detail="Checklist não está aguardando vistoria")
        if user["id"] == row["condutor_id"]:
            raise HTTPException(status_code=403, detail="O condutor não pode vistoriar sua própria saída")

        # Ignora liberador_id do body — sempre o próprio user autenticado
        liberador_id = user["id"]
        assinatura   = data.get("assinatura_liberador")

        cursor.execute("""
            UPDATE fleet_checklists
            SET liberador_id=%s, assinatura_liberador=%s,
                status='aprovado', aprovado_por=%s, aprovado_em=NOW()
            WHERE id=%s
        """, (liberador_id, assinatura, user["id"], checklist_id))

        conn.commit()
        logger.info(f"[FLEET] Checklist {checklist_id} vistoriado por user {user['id']}")
        return {"success": True, "message": "Saída autorizada pelo vistoriador!"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.put("/checklists/{checklist_id}/devolver")
def devolver_veiculo(checklist_id: int, request: Request, data: dict):
    """Condutor devolve o veículo — preenche dados de retorno e assina.
    Status → devolvido (aguardando vistoria de retorno pelo vistoriador original).
    """
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT vehicle_id, status, km_saida FROM fleet_checklists WHERE id=%s",
            (checklist_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Checklist nao encontrado")
        if row["status"] != "em_viagem":
            raise HTTPException(status_code=400, detail="Checklist nao esta em viagem")

        # KM retorno não pode ser menor que KM saída
        km_retorno = data.get("km_retorno")
        km_saida = row.get("km_saida") or 0
        if km_retorno and int(km_retorno) < int(km_saida):
            raise HTTPException(
                status_code=400,
                detail=f"KM de retorno ({km_retorno}) nao pode ser menor que KM de saida ({km_saida})"
            )

        cursor.execute("""
            UPDATE fleet_checklists SET
                data_retorno=%s, horario_retorno=%s, km_retorno=%s,
                nivel_combustivel_retorno=%s,
                cartao_combustivel_retorno=%s, documento_veiculo_retorno=%s,
                assinatura_condutor_retorno=%s,
                retorno_obs=%s,
                status='devolvido'
            WHERE id=%s
        """, (
            data.get("data_retorno"),
            data.get("horario_retorno"),
            data.get("km_retorno"),
            data.get("nivel_combustivel_retorno"),
            1 if data.get("cartao_combustivel_retorno") else 0,
            1 if data.get("documento_veiculo_retorno") else 0,
            data.get("assinatura_condutor_retorno"),
            data.get("retorno_obs"),
            checklist_id,
        ))

        # Atualizar KM atual do veículo
        km_retorno = data.get("km_retorno")
        if km_retorno:
            cursor.execute(
                "UPDATE fleet_vehicles SET km_atual=%s WHERE id=%s AND km_atual < %s",
                (km_retorno, row["vehicle_id"], km_retorno)
            )

        # Problemas relatados pelo condutor
        for p in (data.get("problems") or []):
            nome = (p.get("item_nome") or "").strip()
            if nome:
                cursor.execute(
                    """INSERT INTO fleet_checklist_problems
                       (checklist_id, item_nome, descricao_adicional, fase)
                       VALUES (%s,%s,%s,'retorno')""",
                    (checklist_id, nome, p.get("descricao_adicional", "")),
                )

        # Criar registro de viagem automaticamente se o condutor informou custos
        custos = data.get("custos") or {}
        c_comb = float(custos.get("combustivel") or 0)
        c_lav  = float(custos.get("lavagem") or 0)
        c_ped  = float(custos.get("pedagio") or 0)
        c_est  = float(custos.get("estacionamento") or 0)
        trip_id = None
        if any(v > 0 for v in (c_comb, c_lav, c_ped, c_est)):
            cursor.execute("""
                SELECT condutor_id, destino, data_saida, km_saida
                FROM fleet_checklists WHERE id=%s
            """, (checklist_id,))
            ck = cursor.fetchone()
            cursor.execute("""
                INSERT INTO fleet_trips
                    (vehicle_id, checklist_id, condutor_id, descricao,
                     data_saida, data_retorno, km_inicial, km_final,
                     custo_aluguel, custo_telemetria, custo_estacionamento,
                     custo_pedagio, custo_manutencao, custo_combustivel,
                     custo_lavagem, custo_outros)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                        0, 0, %s, %s, 0, %s, %s, 0)
            """, (
                row["vehicle_id"], checklist_id, ck["condutor_id"], ck.get("destino") or "",
                ck["data_saida"], data.get("data_retorno"),
                ck.get("km_saida") or 0, km_retorno or 0,
                c_est, c_ped, c_comb, c_lav,
            ))
            trip_id = cursor.lastrowid
            logger.info(f"[FLEET] Trip {trip_id} criada automaticamente (checklist {checklist_id})")

        conn.commit()
        logger.info(f"[FLEET] Checklist {checklist_id} devolvido, aguardando vistoria retorno")
        return {
            "success": True,
            "message": "Devolucao registrada! Aguardando vistoria de retorno.",
            "trip_id": trip_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.post("/checklists/{checklist_id}/vistoriar-retorno")
def vistoriar_retorno(checklist_id: int, request: Request, data: dict):
    """Vistoriador inspeciona o retorno do veículo.
    Se há problemas: veículo → manutencao, status → retornado_com_avaria.
    Caso contrário: veículo → ativo, status → retornado.
    """
    user = _get_user_role(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT vehicle_id, condutor_id, status FROM fleet_checklists WHERE id=%s",
            (checklist_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Checklist nao encontrado")
        if row["status"] != "devolvido":
            raise HTTPException(status_code=400, detail="Checklist nao esta devolvido")

        # Verificar se há problemas relatados pelo condutor OU pelo vistoriador
        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM fleet_checklist_problems WHERE checklist_id=%s AND fase='retorno'",
            (checklist_id,)
        )
        problemas_condutor = cursor.fetchone()["cnt"]

        problemas_vistoriador = data.get("problems") or []
        for p in problemas_vistoriador:
            nome = (p.get("item_nome") or "").strip()
            if nome:
                cursor.execute(
                    """INSERT INTO fleet_checklist_problems
                       (checklist_id, item_nome, descricao_adicional, fase)
                       VALUES (%s,%s,%s,'retorno')""",
                    (checklist_id, nome, p.get("descricao_adicional", "")),
                )

        tem_avaria = problemas_condutor > 0 or len(problemas_vistoriador) > 0
        novo_status = "retornado_com_avaria" if tem_avaria else "retornado"
        status_veiculo = "manutencao" if tem_avaria else "ativo"

        recebedor_id = data.get("recebedor_id") or user["id"]
        cursor.execute("""
            UPDATE fleet_checklists SET
                recebedor_id=%s, assinatura_recebedor=%s,
                assinatura_vistoriador_retorno=%s,
                status=%s
            WHERE id=%s
        """, (
            recebedor_id,
            data.get("assinatura_recebedor"),
            data.get("assinatura_recebedor"),
            novo_status,
            checklist_id,
        ))

        if tem_avaria:
            # Salvar descrição da avaria no veículo
            cursor.execute("""
                UPDATE fleet_vehicles SET status=%s, avaria_descricao=%s, avaria_em=NOW(),
                       avaria_corrigida_em=NULL, avaria_corrigida_por=NULL, avaria_correcao_obs=NULL
                WHERE id=%s
            """, (status_veiculo, f"Checklist #{checklist_id}", row["vehicle_id"]))
        else:
            cursor.execute(
                "UPDATE fleet_vehicles SET status=%s WHERE id=%s",
                (status_veiculo, row["vehicle_id"])
            )

        # Registrar no histórico do veículo
        _log_vehicle_history(cursor, row["vehicle_id"], "Vistoria de retorno",
                             f"Checklist #{checklist_id} — {'Com avaria' if tem_avaria else 'OK'}",
                             "em_viagem", status_veiculo, user["id"])

        # Promover fotos da inspeção para referência do veículo
        _promote_photos_to_reference(cursor, checklist_id, row["vehicle_id"], user["id"])

        # Notificar quem se inscreveu para "avise-me" — veículo voltou à empresa
        _notify_return_subscribers(cursor, row["vehicle_id"])

        conn.commit()
        msg = "Retorno registrado com avaria — veiculo em manutencao!" if tem_avaria else "Retorno confirmado com sucesso!"
        return {"success": True, "message": msg, "tem_avaria": tem_avaria}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.post("/checklists/{checklist_id}/recusar-retorno")
def recusar_retorno(checklist_id: int, request: Request, data: dict):
    """Vistoriador recusa a devolução — checklist volta para 'em_viagem'
    com a justificativa, e o condutor precisa corrigir e devolver novamente.
    """
    user = _get_user_role(request)
    justificativa = (data.get("justificativa") or "").strip()
    if not justificativa:
        raise HTTPException(status_code=400, detail="Justificativa e obrigatoria")

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT vehicle_id, status FROM fleet_checklists WHERE id=%s",
            (checklist_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Checklist nao encontrado")
        if row["status"] != "devolvido":
            raise HTTPException(status_code=400, detail="Checklist nao esta devolvido")

        # Limpar dados de retorno preenchidos pelo condutor e voltar para em_viagem
        cursor.execute("""
            UPDATE fleet_checklists SET
                data_retorno=NULL, horario_retorno=NULL, km_retorno=NULL,
                nivel_combustivel_retorno=NULL,
                assinatura_condutor_retorno=NULL, retorno_obs=NULL,
                recusa_justificativa=%s, recusa_por=%s, recusa_em=NOW(),
                status='em_viagem'
            WHERE id=%s
        """, (justificativa, user["id"], checklist_id))

        # Remover problemas de retorno que o condutor havia reportado
        cursor.execute(
            "DELETE FROM fleet_checklist_problems WHERE checklist_id=%s AND fase='retorno'",
            (checklist_id,)
        )

        # Remover fotos de avaria do retorno
        cursor.execute(
            "SELECT foto_path FROM fleet_checklist_photos WHERE checklist_id=%s AND angulo='avaria_retorno'",
            (checklist_id,)
        )
        avaria_files = cursor.fetchall()
        cursor.execute(
            "DELETE FROM fleet_checklist_photos WHERE checklist_id=%s AND angulo='avaria_retorno'",
            (checklist_id,)
        )
        for f in avaria_files:
            try:
                fp = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", f["foto_path"].lstrip("/")))
                if os.path.exists(fp):
                    os.remove(fp)
            except Exception:
                pass

        conn.commit()
        logger.info(f"[FLEET] Checklist {checklist_id} retorno recusado por user {user['id']}: {justificativa}")
        return {"success": True, "message": "Devolucao recusada. O condutor sera notificado para corrigir."}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


def _try_create_maintenance_trip(cursor, maintenance_id: int):
    """Cria registro em fleet_trips a partir de uma manutenção concluída com comprovante.
    Idempotente: se já existe trip_id vinculado ou faltam pré-condições, não faz nada.
    """
    cursor.execute(
        """SELECT id, vehicle_id, tipo, fornecedor, data_entrada, data_conclusao,
                  km_atual, custo, status, trip_id
           FROM fleet_maintenance WHERE id=%s""",
        (maintenance_id,)
    )
    m = cursor.fetchone()
    if not m:
        return None
    if m.get("trip_id"):
        return None
    if m["status"] != "concluido":
        return None
    if not m["custo"] or float(m["custo"]) <= 0:
        return None
    # Precisa ter comprovante anexado
    cursor.execute(
        "SELECT COUNT(*) AS n FROM fleet_maintenance_files WHERE maintenance_id=%s",
        (maintenance_id,)
    )
    if cursor.fetchone()["n"] == 0:
        return None

    descricao = f"Manutencao #{maintenance_id}: {m['tipo'] or ''}".strip()
    if m.get("fornecedor"):
        descricao = f"{descricao} ({m['fornecedor']})"
    data_saida   = m.get("data_entrada") or m.get("data_conclusao")
    data_retorno = m.get("data_conclusao") or m.get("data_entrada")
    km           = m.get("km_atual") or 0

    cursor.execute("""
        INSERT INTO fleet_trips
            (vehicle_id, descricao,
             data_saida, data_retorno, km_inicial, km_final,
             custo_aluguel, custo_telemetria, custo_estacionamento,
             custo_pedagio, custo_manutencao, custo_combustivel,
             custo_lavagem, custo_outros)
        VALUES (%s, %s, %s, %s, %s, %s,
                0, 0, 0, 0, %s, 0, 0, 0)
    """, (
        m["vehicle_id"], descricao,
        data_saida, data_retorno, km, km,
        float(m["custo"]),
    ))
    trip_id = cursor.lastrowid
    cursor.execute("UPDATE fleet_maintenance SET trip_id=%s WHERE id=%s", (trip_id, maintenance_id))
    return trip_id


def _auto_block_vehicle(cursor, vehicle_id, data_entrada, maint_status, user_id):
    """Bloqueia veículo automaticamente se manutenção com data_entrada <= hoje."""
    from datetime import date
    if not vehicle_id:
        return
    if maint_status not in ("agendado", "em_andamento"):
        return
    if not data_entrada:
        return
    try:
        dt = date.fromisoformat(str(data_entrada)[:10])
    except (ValueError, TypeError):
        return
    if dt <= date.today():
        cursor.execute("SELECT status FROM fleet_vehicles WHERE id=%s", (vehicle_id,))
        v = cursor.fetchone()
        if v and v["status"] == "ativo":
            cursor.execute(
                "UPDATE fleet_vehicles SET status='manutencao' WHERE id=%s",
                (vehicle_id,)
            )
            _log_vehicle_history(cursor, vehicle_id, "Manutencao agendada",
                                 "Bloqueado automaticamente por manutencao agendada",
                                 "ativo", "manutencao", user_id)


def _promote_photos_to_reference(cursor, checklist_id, vehicle_id, user_id):
    """Após retorno confirmado, as fotos de inspeção do checklist viram
    a nova foto de referência do veículo. Fotos antigas são apagadas do disco."""
    # Buscar fotos de inspeção (só ângulos de veículo, não problema/avaria)
    valid_angles = {'frente','lateral','parachoque_dianteiro',
                    'parachoque_traseiro','quatro_portas','paralama_traseiro'}
    cursor.execute(
        "SELECT id, angulo, foto_path FROM fleet_checklist_photos WHERE checklist_id=%s",
        (checklist_id,)
    )
    cl_photos = [p for p in cursor.fetchall() if p["angulo"] in valid_angles]

    for p in cl_photos:
        ang = p["angulo"]
        new_path = p["foto_path"]

        # Apagar foto de referência antiga do disco
        cursor.execute(
            "SELECT id, foto_path FROM fleet_vehicle_photos WHERE vehicle_id=%s AND angulo=%s AND is_current=1",
            (vehicle_id, ang)
        )
        old_refs = cursor.fetchall()
        for old in old_refs:
            if old["foto_path"] != new_path:
                try:
                    fp = os.path.normpath(os.path.join(
                        os.path.dirname(__file__), "..", "..", old["foto_path"].lstrip("/")))
                    if os.path.exists(fp):
                        os.remove(fp)
                except Exception:
                    pass
            cursor.execute("DELETE FROM fleet_vehicle_photos WHERE id=%s", (old["id"],))

        # Inserir nova referência apontando para o mesmo arquivo
        cursor.execute("""
            INSERT INTO fleet_vehicle_photos (vehicle_id, foto_path, angulo, is_current, substituida_por_user_id)
            VALUES (%s,%s,%s,1,%s)
        """, (vehicle_id, new_path, ang, user_id))

        # Remover registro da tabela de checklist (arquivo fica no disco, agora pertence a vehicle_photos)
        cursor.execute("DELETE FROM fleet_checklist_photos WHERE id=%s", (p["id"],))


def _log_vehicle_history(cursor, vehicle_id, evento, descricao, status_anterior, status_novo, user_id):
    """Registra um evento no histórico do veículo."""
    cursor.execute("""
        INSERT INTO fleet_vehicle_history (vehicle_id, evento, descricao, status_anterior, status_novo, user_id)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (vehicle_id, evento, descricao, status_anterior, status_novo, user_id))


# ============================================================
# AVISE-ME — usuário se inscreve para ser notificado quando o
# veículo voltar à empresa (status muda de em_viagem para outra).
# ============================================================

def _notify_return_subscribers(cursor, vehicle_id: int) -> int:
    """Notifica e remove todas as subscriptions tipo 'return' de um veículo.
    Chamado quando o veículo é vistoriado de retorno (em_viagem → ativo/manutencao).
    Retorna o número de notificações enviadas."""
    cursor.execute(
        "SELECT placa, modelo FROM fleet_vehicles WHERE id=%s",
        (vehicle_id,)
    )
    veh = cursor.fetchone()
    if not veh:
        return 0
    placa = veh["placa"] if isinstance(veh, dict) else veh[0]
    modelo = veh["modelo"] if isinstance(veh, dict) else veh[1]

    cursor.execute(
        "SELECT id, user_id FROM fleet_vehicle_subscriptions WHERE vehicle_id=%s AND tipo='return'",
        (vehicle_id,)
    )
    subs = cursor.fetchall()
    if not subs:
        return 0

    msg = f"O veículo {placa} ({modelo}) voltou para a empresa."
    sub_ids = []
    for s in subs:
        uid = s["user_id"] if isinstance(s, dict) else s[1]
        sid = s["id"] if isinstance(s, dict) else s[0]
        cursor.execute(
            "INSERT INTO notificacoes (usuario_id, mensagem, tipo, lido) VALUES (%s, %s, 'fleet_return', 0)",
            (uid, msg),
        )
        sub_ids.append(sid)

    if sub_ids:
        ph = ",".join(["%s"] * len(sub_ids))
        cursor.execute(f"DELETE FROM fleet_vehicle_subscriptions WHERE id IN ({ph})", sub_ids)

    return len(sub_ids)


@router.get("/vehicles/{vehicle_id}/subscription")
def get_vehicle_subscription(vehicle_id: int, request: Request):
    user_id = _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id FROM fleet_vehicle_subscriptions WHERE vehicle_id=%s AND user_id=%s AND tipo='return'",
            (vehicle_id, user_id),
        )
        row = cursor.fetchone()
        return {"success": True, "subscribed": bool(row)}
    finally:
        cursor.close()
        conn.close()


@router.post("/vehicles/{vehicle_id}/subscribe")
def subscribe_vehicle_return(vehicle_id: int, request: Request):
    """Inscreve o usuário para ser avisado quando o veículo voltar."""
    user_id = _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, status FROM fleet_vehicles WHERE id=%s", (vehicle_id,))
        veh = cursor.fetchone()
        if not veh:
            raise HTTPException(status_code=404, detail="Veículo não encontrado.")
        if veh["status"] != "em_viagem":
            raise HTTPException(
                status_code=400,
                detail="Avise-me só está disponível enquanto o veículo está em viagem."
            )

        cursor.execute(
            """INSERT IGNORE INTO fleet_vehicle_subscriptions
               (vehicle_id, user_id, tipo) VALUES (%s, %s, 'return')""",
            (vehicle_id, user_id),
        )
        conn.commit()
        return {"success": True, "subscribed": True}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.delete("/vehicles/{vehicle_id}/subscribe")
def unsubscribe_vehicle_return(vehicle_id: int, request: Request):
    user_id = _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "DELETE FROM fleet_vehicle_subscriptions WHERE vehicle_id=%s AND user_id=%s AND tipo='return'",
            (vehicle_id, user_id),
        )
        conn.commit()
        return {"success": True, "subscribed": False}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# ============================================================
# MANUTENÇÃO ATIVA DE UM VEÍCULO — usado pelo modal "Em Revisão"
# ============================================================
@router.get("/vehicles/{vehicle_id}/active-maintenance")
def vehicle_active_maintenance(vehicle_id: int, request: Request):
    """Retorna a manutenção ativa (agendado/em_andamento) mais recente do veículo,
    com tipo, descrição, data_entrada, data_conclusao prevista e fornecedor."""
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT m.id, m.tipo, m.causa, m.descricao, m.fornecedor,
                   m.data_entrada, m.data_conclusao, m.status,
                   m.km_atual, m.observacoes,
                   cr.name AS condutor_responsavel_nome
            FROM fleet_maintenance m
            LEFT JOIN users cr ON cr.id = m.condutor_responsavel_id
            WHERE m.vehicle_id = %s AND m.status IN ('agendado','em_andamento')
            ORDER BY m.data_entrada DESC, m.created_at DESC
            LIMIT 1
        """, (vehicle_id,))
        row = cursor.fetchone()
        if not row:
            return {"success": True, "maintenance": None}
        return {"success": True, "maintenance": convert_datetime_to_string(row)}
    finally:
        cursor.close()
        conn.close()


@router.post("/vehicles/{vehicle_id}/liberar")
def liberar_veiculo(vehicle_id: int, request: Request):
    """Somente responsável do grupo Frotas (ou ADMIN/TI) libera veículo em manutenção ou revisão."""
    user = _get_user_role(request)
    if not _can_manage_fleet(user):
        raise HTTPException(status_code=403, detail="Apenas o responsável do grupo Frotas pode liberar veículos.")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT status FROM fleet_vehicles WHERE id=%s", (vehicle_id,))
        v = cursor.fetchone()
        if not v:
            raise HTTPException(status_code=404, detail="Veiculo nao encontrado")
        if v["status"] not in ("manutencao", "revisao"):
            raise HTTPException(status_code=400, detail="Veiculo nao esta em manutencao/revisao")

        cursor.execute("UPDATE fleet_vehicles SET status='ativo' WHERE id=%s", (vehicle_id,))
        _log_vehicle_history(cursor, vehicle_id, "Liberado para uso",
                             f"Status anterior: {v['status']}",
                             v["status"], "ativo", user["id"])
        conn.commit()
        return {"success": True, "message": "Veiculo liberado para uso!"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.post("/vehicles/{vehicle_id}/reativar")
def reativar_veiculo(vehicle_id: int, request: Request):
    """Reativa um veículo que estava inativo (soft-deleted).
    Só ADMIN ou Responsável do grupo Frotas."""
    user = _get_user_role(request)
    if not _can_manage_fleet(user):
        raise HTTPException(
            status_code=403,
            detail="Apenas Administrador, T.I. ou Responsável do grupo Frotas podem reativar veículos."
        )
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, placa, status FROM fleet_vehicles WHERE id=%s", (vehicle_id,))
        v = cursor.fetchone()
        if not v:
            raise HTTPException(status_code=404, detail="Veiculo nao encontrado")
        if v["status"] != "inativo":
            raise HTTPException(status_code=400, detail=f"Veiculo nao esta inativo (status atual: {v['status']})")

        cursor.execute("UPDATE fleet_vehicles SET status='ativo' WHERE id=%s", (vehicle_id,))
        _log_vehicle_history(cursor, vehicle_id, "Reativado",
                             "Veiculo reativado pelo painel",
                             "inativo", "ativo", user["id"])
        conn.commit()
        logger.info(f"[FLEET] Veiculo {v['placa']} (id={vehicle_id}) reativado por user {user['id']}")
        return {"success": True, "message": f"Veiculo {v['placa']} reativado!"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.post("/vehicles/{vehicle_id}/corrigir-avaria")
def corrigir_avaria(vehicle_id: int, request: Request, data: dict):
    """Marca avaria como corrigida e libera veículo para uso."""
    user = _get_user_role(request)
    if not _can_manage_fleet(user):
        raise HTTPException(status_code=403, detail="Apenas o responsável do grupo Frotas pode corrigir avarias.")
    obs = (data.get("observacao") or "").strip()
    if not obs:
        raise HTTPException(status_code=400, detail="Descreva o que foi feito para corrigir a avaria")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT status FROM fleet_vehicles WHERE id=%s", (vehicle_id,))
        v = cursor.fetchone()
        if not v:
            raise HTTPException(status_code=404, detail="Veiculo nao encontrado")

        cursor.execute("""
            UPDATE fleet_vehicles SET
                status='ativo',
                avaria_corrigida_em=NOW(),
                avaria_corrigida_por=%s,
                avaria_correcao_obs=%s
            WHERE id=%s
        """, (user["id"], obs, vehicle_id))

        _log_vehicle_history(cursor, vehicle_id, "Avaria corrigida",
                             obs, v["status"], "ativo", user["id"])
        conn.commit()
        return {"success": True, "message": "Avaria corrigida! Veiculo liberado para uso."}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.post("/vehicles/{vehicle_id}/status")
def change_vehicle_status(vehicle_id: int, request: Request, data: dict):
    """Altera status do veículo (manutenção, revisão, inativo) e registra no histórico."""
    user = _get_user_role(request)
    if not _can_manage_fleet(user):
        raise HTTPException(status_code=403, detail="Apenas o responsável do grupo Frotas pode alterar o status do veículo.")
    novo_status = data.get("status")
    motivo = data.get("motivo", "")
    if novo_status not in ("manutencao", "revisao", "inativo", "ativo"):
        raise HTTPException(status_code=400, detail="Status invalido")

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT status FROM fleet_vehicles WHERE id=%s", (vehicle_id,))
        v = cursor.fetchone()
        if not v:
            raise HTTPException(status_code=404, detail="Veiculo nao encontrado")

        cursor.execute("UPDATE fleet_vehicles SET status=%s WHERE id=%s", (novo_status, vehicle_id))
        labels = {'manutencao': 'Manutencao/Reparo', 'revisao': 'Revisao', 'inativo': 'Inativado', 'ativo': 'Ativado'}
        _log_vehicle_history(cursor, vehicle_id, labels.get(novo_status, novo_status),
                             motivo, v["status"], novo_status, user["id"])
        conn.commit()
        return {"success": True, "message": f"Veiculo movido para: {labels.get(novo_status, novo_status)}"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.get("/vehicles/{vehicle_id}/history")
def get_vehicle_history(vehicle_id: int, request: Request):
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT h.*, u.name AS user_name
            FROM fleet_vehicle_history h
            LEFT JOIN users u ON u.id = h.user_id
            WHERE h.vehicle_id = %s
            ORDER BY h.created_at DESC LIMIT 50
        """, (vehicle_id,))
        rows = cursor.fetchall()
        rows = convert_datetime_list(rows)
        return {"success": True, "history": rows}
    finally:
        cursor.close()
        conn.close()


# ============================================================
# MANUTENÇÃO DE VEÍCULOS
# ============================================================

MAINTENANCE_LABELS = {
    'troca_oleo': 'Troca de Oleo',
    'troca_pneu': 'Troca de Pneu',
    'revisao': 'Revisao',
    'troca_filtro': 'Troca de Filtro',
    'alinhamento': 'Alinhamento',
    'balanceamento': 'Balanceamento',
    'funilaria': 'Funilaria/Pintura',
    'eletrica': 'Eletrica',
    'outro': 'Outro',
}

@router.get("/maintenance")
def list_maintenance(request: Request, vehicle_id: int = None, status: str = None):
    user = _get_user_role(request)
    if not _can_manage_fleet(user):
        raise HTTPException(
            status_code=403,
            detail="Apenas Administrador, T.I. ou Responsável do grupo Frotas podem ver manutenções."
        )
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        where = ["1=1"]
        params = []
        if vehicle_id:
            where.append("m.vehicle_id = %s")
            params.append(vehicle_id)
        if status:
            where.append("m.status = %s")
            params.append(status)

        cursor.execute(f"""
            SELECT m.*, v.placa, v.modelo,
                   u.name  AS criado_por_nome,
                   cr.name AS condutor_responsavel_nome,
                   g.name  AS centro_custo_nome,
                   (SELECT COUNT(*) FROM fleet_maintenance_files f WHERE f.maintenance_id = m.id) AS qtd_arquivos
            FROM fleet_maintenance m
            JOIN fleet_vehicles v ON v.id = m.vehicle_id
            LEFT JOIN users u  ON u.id  = m.created_by
            LEFT JOIN users cr ON cr.id = m.condutor_responsavel_id
            LEFT JOIN cpe_grupo g ON g.id = m.group_id
            WHERE {' AND '.join(where)}
            ORDER BY m.data_entrada DESC, m.created_at DESC
            LIMIT 200
        """, params)
        rows = cursor.fetchall()
        rows = convert_datetime_list(rows)
        return {"success": True, "records": rows}
    finally:
        cursor.close()
        conn.close()


_CAUSAS_VALIDAS = ("normal", "colisao", "arranhao", "outro")
_CARGO_PODE_IMPUTAR = ("ADMIN", "TI", "RESPONSAVEL_GRUPO")


def _resolve_responsavel(user: dict, data: dict, cursor):
    """Decide causa, condutor_responsavel_id e group_id da manutenção.

    Regra:
    - causa só vai pra colisao/arranhao se o usuário tem cargo permitido
      (ADMIN, TI, RESPONSAVEL_GRUPO) E informou um condutor responsável.
    - Caso contrário, vira 'normal' e group_id fica NULL (= grupo Frotas).
    - Para causas colisao/arranhao, group_id é resolvido do condutor responsável.
    """
    causa = (data.get("causa") or "normal").lower()
    if causa not in _CAUSAS_VALIDAS:
        causa = "normal"

    condutor_responsavel_id = data.get("condutor_responsavel_id") or None
    group_id = None

    pode_imputar = user.get("role") in _CARGO_PODE_IMPUTAR
    if not pode_imputar:
        # Usuário comum não pode atribuir responsabilidade — força normal/CPE
        return "normal", None, None

    if causa in ("colisao", "arranhao"):
        if not condutor_responsavel_id:
            # Sem responsável → tratamos como normal (custo fica em Frotas)
            return "normal", None, None
        group_id = _resolve_group_id_from_condutor(cursor, condutor_responsavel_id)

    return causa, condutor_responsavel_id, group_id


@router.post("/maintenance")
def create_maintenance(request: Request, data: dict):
    user = _get_user_role(request)
    user_id = user["id"]
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        causa, cond_resp_id, group_id = _resolve_responsavel(user, data, cursor)

        cursor.execute("""
            INSERT INTO fleet_maintenance
                (vehicle_id, tipo, causa, condutor_responsavel_id, group_id,
                 descricao, data_entrada, data_conclusao,
                 km_atual, custo, fornecedor, status, observacoes, created_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data.get("vehicle_id"),
            data.get("tipo", "outro"),
            causa,
            cond_resp_id,
            group_id,
            data.get("descricao"),
            data.get("data_entrada"),
            data.get("data_conclusao"),
            data.get("km_atual"),
            data.get("custo", 0),
            data.get("fornecedor"),
            data.get("status", "agendado"),
            data.get("observacoes"),
            user_id,
        ))
        mid = cursor.lastrowid

        # Auto-bloquear veículo se data_entrada <= hoje e status agendado/em_andamento
        _auto_block_vehicle(cursor, data.get("vehicle_id"), data.get("data_entrada"),
                            data.get("status", "agendado"), user_id)

        conn.commit()
        return {"success": True, "id": mid, "message": "Manutencao registrada!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.put("/maintenance/{maintenance_id}")
def update_maintenance(maintenance_id: int, request: Request, data: dict):
    user = _get_user_role(request)
    user_id = user["id"]
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        # Pegar vehicle_id do registro
        cursor.execute("SELECT vehicle_id FROM fleet_maintenance WHERE id=%s", (maintenance_id,))
        row = cursor.fetchone()
        vehicle_id = row["vehicle_id"] if row else data.get("vehicle_id")

        causa, cond_resp_id, group_id = _resolve_responsavel(user, data, cursor)

        cursor.execute("""
            UPDATE fleet_maintenance SET
                tipo=%s, causa=%s, condutor_responsavel_id=%s, group_id=%s,
                descricao=%s, data_entrada=%s, data_conclusao=%s,
                km_atual=%s, custo=%s, fornecedor=%s, status=%s, observacoes=%s
            WHERE id=%s
        """, (
            data.get("tipo"),
            causa,
            cond_resp_id,
            group_id,
            data.get("descricao"),
            data.get("data_entrada"),
            data.get("data_conclusao"),
            data.get("km_atual"),
            data.get("custo", 0),
            data.get("fornecedor"),
            data.get("status"),
            data.get("observacoes"),
            maintenance_id,
        ))

        # Se concluido/cancelado: liberar veículo; se agendado/em_andamento com data <= hoje: bloquear
        maint_status = data.get("status", "agendado")
        if maint_status in ("concluido", "cancelado"):
            # Só libera se não há outra manutencao ativa para o mesmo veículo
            cursor.execute("""
                SELECT COUNT(*) AS cnt FROM fleet_maintenance
                WHERE vehicle_id=%s AND id!=%s AND status IN ('agendado','em_andamento')
                  AND (data_entrada IS NULL OR data_entrada <= CURDATE())
            """, (vehicle_id, maintenance_id))
            if cursor.fetchone()["cnt"] == 0:
                cursor.execute(
                    "UPDATE fleet_vehicles SET status='ativo' WHERE id=%s AND status='manutencao'",
                    (vehicle_id,)
                )
        else:
            _auto_block_vehicle(cursor, vehicle_id, data.get("data_entrada"), maint_status, user_id)

        # Se concluído com comprovante anexado, criar trip automaticamente
        trip_id = None
        if maint_status == "concluido":
            trip_id = _try_create_maintenance_trip(cursor, maintenance_id)

        conn.commit()
        return {"success": True, "message": "Manutencao atualizada!", "trip_id": trip_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.delete("/maintenance/{maintenance_id}")
def delete_maintenance(maintenance_id: int, request: Request):
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("DELETE FROM fleet_maintenance WHERE id=%s", (maintenance_id,))
        conn.commit()
        return {"success": True, "message": "Registro excluido!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.post("/checklists/{checklist_id}/aprovar")
def aprovar_checklist(checklist_id: int, request: Request):
    user = _get_user_role(request)
    if user.get("role") not in ("ADMIN", "TI", "RESPONSAVEL_GRUPO"):
        raise HTTPException(status_code=403, detail="Sem permissão para aprovar checklists")

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            UPDATE fleet_checklists
            SET status='aprovado', aprovado_por=%s, aprovado_em=NOW()
            WHERE id=%s AND status='aguardando_aprovacao'
        """, (user["id"], checklist_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=400, detail="Checklist não está aguardando aprovação")
        conn.commit()
        return {"success": True, "message": "Checklist aprovado!"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.post("/checklists/{checklist_id}/iniciar-viagem")
def iniciar_viagem(checklist_id: int, request: Request):
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT vehicle_id FROM fleet_checklists WHERE id=%s AND status='aprovado'",
            (checklist_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="Checklist não está aprovado")
        cursor.execute("UPDATE fleet_checklists SET status='em_viagem' WHERE id=%s", (checklist_id,))
        cursor.execute("UPDATE fleet_vehicles SET status='em_viagem' WHERE id=%s", (row["vehicle_id"],))
        conn.commit()
        return {"success": True, "message": "Viagem iniciada!"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# ============================================================
# VIAGENS / CUSTOS
# ============================================================

@router.get("/trips")
def list_trips(request: Request, ano: int = None, mes: int = None, unidade: str = None):
    user = _get_user_role(request)
    is_fleet_mgr = _can_manage_fleet(user)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        where = ["1=1"]
        params = []
        # Usuário comum só vê suas próprias viagens (custos confidenciais
        # de outros usuários ficam fora). Apenas Frotas/ADMIN/TI vê tudo.
        if not is_fleet_mgr:
            where.append("t.condutor_id = %s")
            params.append(user["id"])
        if ano:
            where.append("YEAR(t.data_saida) = %s")
            params.append(ano)
        if mes:
            where.append("MONTH(t.data_saida) = %s")
            params.append(mes)
        if unidade:
            where.append("t.unidade = %s")
            params.append(unidade)

        cursor.execute(f"""
            SELECT t.*,
                   v.placa, v.modelo, v.tipo,
                   u.name AS condutor_nome,
                   (t.custo_aluguel + t.custo_telemetria + t.custo_estacionamento +
                    t.custo_pedagio + t.custo_manutencao + t.custo_combustivel + t.custo_outros
                   ) AS custo_total,
                   (t.km_final - t.km_inicial) AS km_rodado
            FROM fleet_trips t
            JOIN  fleet_vehicles v ON v.id = t.vehicle_id
            LEFT JOIN users u ON u.id = t.condutor_id
            WHERE {' AND '.join(where)}
            ORDER BY t.data_saida DESC
        """, params)
        trips = cursor.fetchall()

        totals = {
            "km_total":             sum(int(t.get("km_rodado") or 0) for t in trips),
            "custo_total":          sum(float(t.get("custo_total") or 0) for t in trips),
            "custo_aluguel":        sum(float(t.get("custo_aluguel") or 0) for t in trips),
            "custo_telemetria":     sum(float(t.get("custo_telemetria") or 0) for t in trips),
            "custo_estacionamento": sum(float(t.get("custo_estacionamento") or 0) for t in trips),
            "custo_pedagio":        sum(float(t.get("custo_pedagio") or 0) for t in trips),
            "custo_manutencao":     sum(float(t.get("custo_manutencao") or 0) for t in trips),
            "custo_combustivel":    sum(float(t.get("custo_combustivel") or 0) for t in trips),
            "custo_outros":         sum(float(t.get("custo_outros") or 0) for t in trips),
        }
        trips = convert_datetime_list(trips)
        return {"success": True, "trips": trips, "totals": totals}
    finally:
        cursor.close()
        conn.close()


def _resolve_group_id_from_condutor(cursor, condutor_id):
    """Retorna o group_id do condutor ou None se não houver."""
    if not condutor_id:
        return None
    cursor.execute("SELECT group_id FROM users WHERE id=%s", (condutor_id,))
    row = cursor.fetchone()
    if not row:
        return None
    return row["group_id"] if isinstance(row, dict) else row[0]


@router.post("/trips")
def create_trip(request: Request, data: dict):
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        condutor_id = data.get("condutor_id") or None
        group_id = _resolve_group_id_from_condutor(cursor, condutor_id)

        cursor.execute("""
            INSERT INTO fleet_trips (
                vehicle_id, checklist_id, condutor_id, group_id, unidade, descricao,
                data_saida, data_retorno, km_inicial, km_final,
                custo_aluguel, custo_telemetria, custo_estacionamento,
                custo_pedagio, custo_manutencao, custo_combustivel, custo_outros,
                observacoes
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data.get("vehicle_id"),
            data.get("checklist_id") or None,
            condutor_id,
            group_id,
            data.get("unidade"),
            data.get("descricao"),
            data.get("data_saida"),
            data.get("data_retorno") or None,
            data.get("km_inicial", 0),
            data.get("km_final", 0),
            data.get("custo_aluguel", 0),
            data.get("custo_telemetria", 0),
            data.get("custo_estacionamento", 0),
            data.get("custo_pedagio", 0),
            data.get("custo_manutencao", 0),
            data.get("custo_combustivel", 0),
            data.get("custo_outros", 0),
            data.get("observacoes"),
        ))
        conn.commit()
        return {"success": True, "id": cursor.lastrowid, "message": "Registro criado!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.put("/trips/{trip_id}")
def update_trip(trip_id: int, request: Request, data: dict):
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        condutor_id = data.get("condutor_id") or None
        group_id = _resolve_group_id_from_condutor(cursor, condutor_id)

        cursor.execute("""
            UPDATE fleet_trips SET
                vehicle_id=%s, condutor_id=%s, group_id=%s, unidade=%s, descricao=%s,
                data_saida=%s, data_retorno=%s, km_inicial=%s, km_final=%s,
                custo_aluguel=%s, custo_telemetria=%s, custo_estacionamento=%s,
                custo_pedagio=%s, custo_manutencao=%s, custo_combustivel=%s,
                custo_outros=%s, observacoes=%s
            WHERE id=%s
        """, (
            data.get("vehicle_id"),
            condutor_id,
            group_id,
            data.get("unidade"),
            data.get("descricao"),
            data.get("data_saida"),
            data.get("data_retorno") or None,
            data.get("km_inicial", 0),
            data.get("km_final", 0),
            data.get("custo_aluguel", 0),
            data.get("custo_telemetria", 0),
            data.get("custo_estacionamento", 0),
            data.get("custo_pedagio", 0),
            data.get("custo_manutencao", 0),
            data.get("custo_combustivel", 0),
            data.get("custo_outros", 0),
            data.get("observacoes"),
            trip_id,
        ))
        conn.commit()
        return {"success": True, "message": "Registro atualizado!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.delete("/trips/{trip_id}")
def delete_trip(trip_id: int, request: Request):
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("DELETE FROM fleet_trips WHERE id=%s", (trip_id,))
        conn.commit()
        return {"success": True, "message": "Registro excluído!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# ============================================================
# CENTRO DE CUSTO — agrega gastos por grupo no período
# ============================================================
@router.get("/cost-centers")
def cost_centers(request: Request, ano: int = None, mes: int = None):
    """Agrega custos por grupo (centro de custo) no período.

    Inclui:
    - Custos de viagem (combustível, estacionamento, pedágio, lavagem, outros)
      → grupo do condutor.
    - Manutenção com causa colisão/arranhão → grupo do condutor responsável.
    - Idle aluguel calculado on-the-fly: dias parados × (aluguel mensal / 30)
      para cada manutenção colisão/arranhão concluída.
    - Manutenção normal e seu idle → grupo Frotas (FLEET_GROUP_ID).

    Confidencial — só ADMIN/TI/Responsável de Frotas podem ver.
    """
    user = _get_user_role(request)
    if not _can_manage_fleet(user):
        raise HTTPException(
            status_code=403,
            detail="Apenas Administrador, T.I. ou Responsável do grupo Frotas podem ver o centro de custo."
        )

    today = datetime.now()
    ano = int(ano) if ano else today.year
    # mes pode ser None = ano inteiro
    mes = int(mes) if mes else None

    if mes:
        date_filter_trip = "YEAR(t.data_saida)=%s AND MONTH(t.data_saida)=%s"
        date_filter_maint = "YEAR(m.data_entrada)=%s AND MONTH(m.data_entrada)=%s"
        date_params = (ano, mes)
    else:
        date_filter_trip = "YEAR(t.data_saida)=%s"
        date_filter_maint = "YEAR(m.data_entrada)=%s"
        date_params = (ano,)

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        # Mapa group_id → {name, totals...}. Grupo "Frotas" sempre presente.
        cursor.execute("SELECT id, name FROM cpe_grupo")
        all_groups = {g["id"]: g["name"] for g in cursor.fetchall()}
        # Bucket especial p/ trips/manut sem condutor (cai em Frotas)
        if FLEET_GROUP_ID not in all_groups:
            all_groups[FLEET_GROUP_ID] = "Frotas"

        # Inicializa totais
        result = {gid: {
            "group_id":      gid,
            "group_name":    name,
            "combustivel":   0.0,
            "estacionamento": 0.0,
            "pedagio":       0.0,
            "lavagem":       0.0,
            "outros_viagem": 0.0,
            "arranhao":      0.0,
            "colisao":       0.0,
            "idle_aluguel":  0.0,
            "manutencao_normal": 0.0,
            "total":         0.0,
        } for gid, name in all_groups.items()}

        def _bucket(gid):
            """Devolve o bucket do grupo; cai em Frotas se gid for None/desconhecido."""
            if gid and gid in result:
                return result[gid]
            return result[FLEET_GROUP_ID]

        # 1) Custos de viagem
        cursor.execute(f"""
            SELECT
                t.group_id,
                COALESCE(SUM(t.custo_combustivel),    0) AS combustivel,
                COALESCE(SUM(t.custo_estacionamento), 0) AS estacionamento,
                COALESCE(SUM(t.custo_pedagio),        0) AS pedagio,
                COALESCE(SUM(t.custo_lavagem),        0) AS lavagem,
                COALESCE(SUM(t.custo_outros),         0) AS outros
            FROM fleet_trips t
            WHERE {date_filter_trip}
            GROUP BY t.group_id
        """, date_params)
        for row in cursor.fetchall():
            b = _bucket(row["group_id"])
            b["combustivel"]    += float(row["combustivel"])
            b["estacionamento"] += float(row["estacionamento"])
            b["pedagio"]        += float(row["pedagio"])
            b["lavagem"]        += float(row["lavagem"])
            b["outros_viagem"]  += float(row["outros"])

        # 2) Manutenção: separar normal/colisao/arranhao + calcular idle
        cursor.execute(f"""
            SELECT
                m.id, m.causa, m.group_id, m.custo,
                m.data_entrada, m.data_conclusao,
                v.valor_aluguel_mensal
            FROM fleet_maintenance m
            JOIN fleet_vehicles v ON v.id = m.vehicle_id
            WHERE {date_filter_maint}
              AND m.status NOT IN ('cancelado')
        """, date_params)

        for row in cursor.fetchall():
            causa = (row["causa"] or "normal").lower()
            custo = float(row["custo"] or 0)

            # Idle: só conta se tem início, fim e aluguel definido
            idle = 0.0
            if row["data_entrada"] and row["data_conclusao"] and row["valor_aluguel_mensal"]:
                dias = (row["data_conclusao"] - row["data_entrada"]).days
                if dias > 0:
                    idle = dias * (float(row["valor_aluguel_mensal"]) / 30.0)

            # Bucket: colisão/arranhão → group do responsável; outros → Frotas
            if causa in ("colisao", "arranhao"):
                b = _bucket(row["group_id"])
                if causa == "colisao":
                    b["colisao"] += custo
                else:
                    b["arranhao"] += custo
                b["idle_aluguel"] += idle
            else:
                b = result[FLEET_GROUP_ID]
                b["manutencao_normal"] += custo
                b["idle_aluguel"]      += idle

        # 3) Total por bucket + filtra grupos sem nada gasto
        out = []
        for gid, b in result.items():
            b["total"] = round(
                b["combustivel"] + b["estacionamento"] + b["pedagio"]
                + b["lavagem"] + b["outros_viagem"]
                + b["arranhao"] + b["colisao"] + b["idle_aluguel"]
                + b["manutencao_normal"],
                2,
            )
            for k in ("combustivel","estacionamento","pedagio","lavagem","outros_viagem",
                      "arranhao","colisao","idle_aluguel","manutencao_normal"):
                b[k] = round(b[k], 2)
            if b["total"] > 0 or gid == FLEET_GROUP_ID:
                out.append(b)

        # Ordena: Frotas no fim, demais por total desc
        out.sort(key=lambda x: (x["group_id"] == FLEET_GROUP_ID, -x["total"]))

        return {
            "success":   True,
            "ano":       ano,
            "mes":       mes,
            "centers":   out,
            "total_geral": round(sum(b["total"] for b in out), 2),
        }
    finally:
        cursor.close()
        conn.close()


# ============================================================
# DASHBOARD
# ============================================================

@router.get("/dashboard")
def get_dashboard(request: Request):
    """Dashboard agrega custos da frota — confidencial.
    Só ADMIN/TI/Responsável de Frotas podem ver."""
    user = _get_user_role(request)
    if not _can_manage_fleet(user):
        raise HTTPException(
            status_code=403,
            detail="Apenas Administrador, T.I. ou Responsável do grupo Frotas podem ver o dashboard de frotas."
        )
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        # Veículos por status
        cursor.execute("SELECT status, COUNT(*) AS total FROM fleet_vehicles GROUP BY status")
        vehicles_by_status = {r["status"]: r["total"] for r in cursor.fetchall()}

        # Totais do ano corrente
        cursor.execute("""
            SELECT
                COALESCE(SUM(custo_aluguel),0)        AS aluguel,
                COALESCE(SUM(custo_telemetria),0)     AS telemetria,
                COALESCE(SUM(custo_estacionamento),0) AS estacionamento,
                COALESCE(SUM(custo_pedagio),0)        AS pedagio,
                COALESCE(SUM(custo_manutencao),0)     AS manutencao,
                COALESCE(SUM(custo_combustivel),0)    AS combustivel,
                COALESCE(SUM(custo_outros),0)         AS outros,
                COALESCE(SUM(km_final - km_inicial),0) AS km_total
            FROM fleet_trips WHERE YEAR(data_saida) = YEAR(NOW())
        """)
        year_totals = cursor.fetchone() or {}

        # Custos mensais (últimos 6 meses)
        cursor.execute("""
            SELECT DATE_FORMAT(data_saida,'%Y-%m') AS mes,
                   SUM(custo_aluguel + custo_telemetria + custo_estacionamento +
                       custo_pedagio + custo_manutencao + custo_combustivel + custo_outros
                   ) AS total
            FROM fleet_trips
            WHERE data_saida >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY DATE_FORMAT(data_saida,'%Y-%m')
            ORDER BY mes
        """)
        monthly_costs = cursor.fetchall()

        # KM por veículo (top 10, ano corrente)
        cursor.execute("""
            SELECT v.placa, v.modelo,
                   COALESCE(SUM(t.km_final - t.km_inicial),0) AS km_total
            FROM fleet_vehicles v
            LEFT JOIN fleet_trips t ON t.vehicle_id = v.id
                AND YEAR(t.data_saida) = YEAR(NOW())
            GROUP BY v.id
            ORDER BY km_total DESC LIMIT 10
        """)
        km_by_vehicle = cursor.fetchall()

        # Checklists recentes
        cursor.execute("""
            SELECT c.id, c.status, c.destino, c.data_saida,
                   v.placa, v.modelo,
                   u.name AS condutor_nome
            FROM fleet_checklists c
            JOIN fleet_vehicles v ON v.id = c.vehicle_id
            JOIN users u ON u.id = c.condutor_id
            ORDER BY c.created_at DESC LIMIT 8
        """)
        recent_checklists = cursor.fetchall()
        recent_checklists = convert_datetime_list(recent_checklists)

        return {
            "success": True,
            "vehicles_by_status": vehicles_by_status,
            "year_totals": year_totals,
            "monthly_costs": monthly_costs,
            "km_by_vehicle": km_by_vehicle,
            "recent_checklists": recent_checklists,
        }
    finally:
        cursor.close()
        conn.close()


# ============================================================
# HELPERS PARA O FRONTEND
# ============================================================

@router.get("/motoristas")
def list_motoristas(request: Request):
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, name, email FROM users WHERE is_active=1 ORDER BY name"
        )
        return {"success": True, "motoristas": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@router.get("/liberadores")
def list_liberadores(request: Request):
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, name, email, role FROM users
            WHERE is_active=1
              AND role IN ('ADMIN','TI','RESPONSAVEL_GRUPO')
            ORDER BY name
        """)
        return {"success": True, "liberadores": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@router.get("/unidades")
def list_unidades(request: Request):
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT DISTINCT unidade FROM fleet_vehicles
            WHERE unidade IS NOT NULL AND unidade != ''
            ORDER BY unidade
        """)
        rows = cursor.fetchall()
        return {"success": True, "unidades": [r["unidade"] for r in rows]}
    finally:
        cursor.close()
        conn.close()


# ============================================================
# AGENDAMENTO / RESERVAS DE VEÍCULOS
# ============================================================

@router.get("/reservations")
def list_reservations(request: Request, month: str = None, vehicle_id: int = None):
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        where = ["1=1"]
        params = []
        if month:
            parts = month.split('-')
            where.append("YEAR(r.data_reserva) = %s AND MONTH(r.data_reserva) = %s")
            params.append(int(parts[0]))
            params.append(int(parts[1]))
        if vehicle_id:
            where.append("r.vehicle_id = %s")
            params.append(vehicle_id)

        cursor.execute(f"""
            SELECT r.*, v.placa, v.modelo,
                   sol.name AS solicitante_nome,
                   apv.name AS aprovador_nome
            FROM fleet_reservations r
            JOIN fleet_vehicles v ON v.id = r.vehicle_id
            JOIN users sol ON sol.id = r.solicitante_id
            LEFT JOIN users apv ON apv.id = r.aprovador_id
            WHERE {' AND '.join(where)}
            ORDER BY r.data_reserva, r.horario_inicio
        """, params)
        rows = cursor.fetchall()
        rows = convert_datetime_list(rows)
        # Converter date/timedelta para strings
        import datetime as _dt
        for r in rows:
            for k, v in r.items():
                if isinstance(v, _dt.date) and not isinstance(v, _dt.datetime):
                    r[k] = v.isoformat()
                elif isinstance(v, _dt.timedelta):
                    total = int(v.total_seconds())
                    r[k] = f"{total//3600:02d}:{(total%3600)//60:02d}"
                elif isinstance(v, _dt.datetime):
                    r[k] = v.isoformat()
        return {"success": True, "reservations": rows}
    finally:
        cursor.close()
        conn.close()


@router.post("/reservations")
def create_reservation(request: Request, data: dict):
    user_id = _get_user_id(request)
    vehicle_id = data.get("vehicle_id")
    data_reserva = data.get("data_reserva")
    horario_inicio = data.get("horario_inicio")
    horario_fim = data.get("horario_fim")
    destino = (data.get("destino") or "").strip()

    if not all([vehicle_id, data_reserva, horario_inicio, horario_fim, destino]):
        raise HTTPException(status_code=400, detail="Preencha todos os campos")

    # Não permitir agendamento retroativo
    try:
        hi = horario_inicio if len(horario_inicio) > 5 else f"{horario_inicio}:00"
        inicio_dt = datetime.fromisoformat(f"{data_reserva}T{hi}")
    except ValueError:
        raise HTTPException(status_code=400, detail="Data/horário inválidos.")
    if inicio_dt < datetime.now():
        raise HTTPException(
            status_code=400,
            detail="O horário do agendamento não pode ser menor do que a hora do dia atual."
        )

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        # Verificar se veículo está em manutenção/revisão
        cursor.execute("SELECT status FROM fleet_vehicles WHERE id=%s", (vehicle_id,))
        veh = cursor.fetchone()
        if veh and veh["status"] in ("manutencao", "revisao"):
            raise HTTPException(status_code=400, detail="Veiculo esta em manutencao/revisao e nao pode ser agendado")

        # Verificar se tem manutenção agendada na data solicitada
        cursor.execute("""
            SELECT m.id, m.tipo, m.data_entrada, m.data_conclusao
            FROM fleet_maintenance m
            WHERE m.vehicle_id = %s AND m.status IN ('agendado','em_andamento')
              AND m.data_entrada IS NOT NULL
              AND m.data_entrada <= %s
              AND (m.data_conclusao IS NULL OR m.data_conclusao >= %s)
        """, (vehicle_id, data_reserva, data_reserva))
        manut = cursor.fetchone()
        if manut:
            raise HTTPException(
                status_code=400,
                detail=f"Veiculo com manutencao agendada ({manut['tipo']}) a partir de {manut['data_entrada']}. Aguarde a liberacao pelo responsavel."
            )

        # Verificar conflito de horário (overlap)
        cursor.execute("""
            SELECT id, solicitante_id, horario_inicio, horario_fim
            FROM fleet_reservations
            WHERE vehicle_id = %s AND data_reserva = %s
              AND status IN ('pendente','aprovado')
              AND horario_inicio < %s AND horario_fim > %s
        """, (vehicle_id, data_reserva, horario_fim, horario_inicio))
        conflito = cursor.fetchone()
        if conflito:
            raise HTTPException(
                status_code=409,
                detail=f"Conflito: este veiculo ja tem reserva #{conflito['id']} de {conflito['horario_inicio']} a {conflito['horario_fim']} neste dia"
            )

        cursor.execute("""
            INSERT INTO fleet_reservations
                (vehicle_id, solicitante_id, destino, data_reserva, horario_inicio, horario_fim)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (vehicle_id, user_id, destino, data_reserva, horario_inicio, horario_fim))
        conn.commit()
        return {"success": True, "id": cursor.lastrowid, "message": "Reserva enviada para aprovacao!"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.post("/reservations/{res_id}/approve")
def approve_reservation(res_id: int, request: Request):
    user = _get_user_role(request)
    if user.get("role") not in ("ADMIN", "TI", "RESPONSAVEL_GRUPO"):
        raise HTTPException(status_code=403, detail="Sem permissao")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM fleet_reservations WHERE id=%s", (res_id,))
        r = cursor.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Reserva nao encontrada")
        if r["status"] != "pendente":
            raise HTTPException(status_code=400, detail="Reserva nao esta pendente")

        # Re-checar conflito com outras aprovadas
        cursor.execute("""
            SELECT id FROM fleet_reservations
            WHERE vehicle_id=%s AND data_reserva=%s AND id!=%s
              AND status='aprovado'
              AND horario_inicio < %s AND horario_fim > %s
        """, (r["vehicle_id"], r["data_reserva"], res_id, r["horario_fim"], r["horario_inicio"]))
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="Conflito com outra reserva ja aprovada neste horario")

        cursor.execute("""
            UPDATE fleet_reservations
            SET status='aprovado', aprovador_id=%s, aprovado_em=NOW(), notif_lida=0
            WHERE id=%s
        """, (user["id"], res_id))
        conn.commit()
        return {"success": True, "message": "Reserva aprovada!"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.post("/reservations/{res_id}/reject")
def reject_reservation(res_id: int, request: Request, data: dict):
    user = _get_user_role(request)
    if user.get("role") not in ("ADMIN", "TI", "RESPONSAVEL_GRUPO"):
        raise HTTPException(status_code=403, detail="Sem permissao")
    motivo = (data.get("motivo") or "").strip()
    if not motivo:
        raise HTTPException(status_code=400, detail="Motivo e obrigatorio")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            UPDATE fleet_reservations
            SET status='rejeitado', aprovador_id=%s, motivo_rejeicao=%s, notif_lida=0
            WHERE id=%s AND status='pendente'
        """, (user["id"], motivo, res_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=400, detail="Reserva nao esta pendente")
        conn.commit()
        return {"success": True, "message": "Reserva rejeitada."}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.post("/reservations/{res_id}/dismiss-notif")
def dismiss_reservation_notif(res_id: int, request: Request):
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("UPDATE fleet_reservations SET notif_lida=1 WHERE id=%s", (res_id,))
        conn.commit()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.delete("/reservations/{res_id}")
def cancel_reservation(res_id: int, request: Request):
    user_id = _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT solicitante_id, status FROM fleet_reservations WHERE id=%s", (res_id,))
        r = cursor.fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Reserva nao encontrada")
        if r["status"] not in ("pendente", "aprovado"):
            raise HTTPException(status_code=400, detail="Reserva nao pode ser cancelada")
        cursor.execute("UPDATE fleet_reservations SET status='cancelado' WHERE id=%s", (res_id,))
        conn.commit()
        return {"success": True, "message": "Reserva cancelada."}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# ============================================================
# TIPOS DE SERVIÇO DE MANUTENÇÃO
# ============================================================

@router.get("/maintenance-types")
def list_maintenance_types(request: Request):
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM fleet_maintenance_types ORDER BY name")
        return {"success": True, "types": cursor.fetchall()}
    finally:
        cursor.close()
        conn.close()


@router.post("/maintenance-types")
def create_maintenance_type(request: Request, data: dict):
    user_id = _get_user_id(request)
    name = (data.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nome do tipo e obrigatorio")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "INSERT INTO fleet_maintenance_types (name, created_by) VALUES (%s,%s)",
            (name, user_id)
        )
        conn.commit()
        return {"success": True, "id": cursor.lastrowid, "message": "Tipo criado!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.delete("/maintenance-types/{type_id}")
def delete_maintenance_type(type_id: int, request: Request):
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("DELETE FROM fleet_maintenance_types WHERE id=%s", (type_id,))
        conn.commit()
        return {"success": True, "message": "Tipo excluido!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# ============================================================
# RECIBOS / ARQUIVOS DE MANUTENÇÃO
# ============================================================

ALLOWED_FILE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.pdf'}

@router.get("/maintenance/{maintenance_id}/files")
def list_maintenance_files(maintenance_id: int, request: Request):
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM fleet_maintenance_files WHERE maintenance_id=%s ORDER BY created_at",
            (maintenance_id,)
        )
        rows = cursor.fetchall()
        rows = convert_datetime_list(rows)
        return {"success": True, "files": rows}
    finally:
        cursor.close()
        conn.close()


@router.post("/maintenance/{maintenance_id}/files")
async def upload_maintenance_file(
    maintenance_id: int,
    request: Request,
    file: UploadFile = File(...),
):
    _get_user_id(request)
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Formato invalido. Use JPG, PNG, WEBP ou PDF.")

    filename = f"maint{maintenance_id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_url = f"/SistemaCPE/web/uploads/fleet/{filename}"

    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "INSERT INTO fleet_maintenance_files (maintenance_id, file_path, nome_arquivo) VALUES (%s,%s,%s)",
            (maintenance_id, file_url, file.filename),
        )
        # Se a manutenção já estava concluída, o upload pode disparar a criação da trip
        trip_id = _try_create_maintenance_trip(cursor, maintenance_id)
        conn.commit()
        return {"success": True, "file_path": file_url, "nome_arquivo": file.filename, "trip_id": trip_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.delete("/maintenance-files/{file_id}")
def delete_maintenance_file(file_id: int, request: Request):
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT file_path FROM fleet_maintenance_files WHERE id=%s", (file_id,))
        row = cursor.fetchone()
        if row:
            # Tentar remover arquivo físico
            physical = os.path.normpath(
                os.path.join(os.path.dirname(__file__), "..", "..", row["file_path"].lstrip("/"))
            )
            if os.path.exists(physical):
                os.remove(physical)
        cursor.execute("DELETE FROM fleet_maintenance_files WHERE id=%s", (file_id,))
        conn.commit()
        return {"success": True, "message": "Arquivo excluido!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# ============================================================
# NOTIFICAÇÕES / ALERTAS
# ============================================================

@router.get("/notifications")
def get_notifications(request: Request):
    """Retorna alertas pendentes:
    1) Manutenções agendadas com data_entrada <= hoje (veículo deveria estar bloqueado)
    2) Alertas de KM atingido
    3) Reservas pendentes / aprovadas / rejeitadas
    """
    user = _get_user_role(request)
    uid = user["id"]
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        alerts = []

        # 1) Manutenções agendadas para hoje ou passado (veículo ainda ativo)
        cursor.execute("""
            SELECT m.id, m.tipo, m.data_entrada, m.status AS maint_status,
                   v.id AS vehicle_id, v.placa, v.modelo, v.status AS vehicle_status
            FROM fleet_maintenance m
            JOIN fleet_vehicles v ON v.id = m.vehicle_id
            WHERE m.status IN ('agendado','em_andamento')
              AND m.data_entrada IS NOT NULL
              AND m.data_entrada <= CURDATE()
            ORDER BY m.data_entrada
        """)
        for r in cursor.fetchall():
            alerts.append({
                "type": "maintenance",
                "icon": "bi-tools",
                "color": "#D97706",
                "title": f"{r['tipo']} — {r['placa']}",
                "message": f"{r['modelo']} agendado para {r['data_entrada']}",
                "vehicle_id": r["vehicle_id"],
                "maintenance_id": r["id"],
            })

        # 2) Manutenções com data futura (lembrete: veículo agendado)
        cursor.execute("""
            SELECT m.id, m.tipo, m.data_entrada,
                   v.id AS vehicle_id, v.placa, v.modelo
            FROM fleet_maintenance m
            JOIN fleet_vehicles v ON v.id = m.vehicle_id
            WHERE m.status = 'agendado'
              AND m.data_entrada IS NOT NULL
              AND m.data_entrada > CURDATE()
              AND m.data_entrada <= DATE_ADD(CURDATE(), INTERVAL 7 DAY)
            ORDER BY m.data_entrada
        """)
        for r in cursor.fetchall():
            alerts.append({
                "type": "maintenance_upcoming",
                "icon": "bi-calendar-event",
                "color": "#3B82F6",
                "title": f"{r['tipo']} — {r['placa']}",
                "message": f"{r['modelo']} agendado para {r['data_entrada']}",
                "vehicle_id": r["vehicle_id"],
                "maintenance_id": r["id"],
            })

        # 3) Alertas de KM atingido
        cursor.execute("""
            SELECT a.id AS alert_id, a.tipo, a.km_limite,
                   v.id AS vehicle_id, v.placa, v.modelo,
                   v.km_atual
            FROM fleet_km_alerts a
            JOIN fleet_vehicles v ON v.id = a.vehicle_id
            WHERE a.notificado = 0
        """)
        for r in cursor.fetchall():
            if r["km_atual"] >= r["km_limite"]:
                alerts.append({
                    "type": "km_alert",
                    "icon": "bi-speedometer",
                    "color": "#DC2626",
                    "title": f"{r['tipo']} — {r['placa']}",
                    "message": f"KM atual: {r['km_atual']:,} / Limite: {r['km_limite']:,}".replace(",", "."),
                    "vehicle_id": r["vehicle_id"],
                    "alert_id": r["alert_id"],
                })

        # 4) Reservas pendentes de aprovação (para ADMIN/TI/RESPONSAVEL_GRUPO)
        cursor.execute("""
            SELECT r.id, r.data_reserva, r.horario_inicio, r.horario_fim, r.destino,
                   v.placa, v.modelo, sol.name AS solicitante_nome
            FROM fleet_reservations r
            JOIN fleet_vehicles v ON v.id = r.vehicle_id
            JOIN users sol ON sol.id = r.solicitante_id
            WHERE r.status = 'pendente'
            ORDER BY r.data_reserva, r.horario_inicio
        """)
        for r in cursor.fetchall():
            alerts.append({
                "type": "reservation_pending",
                "icon": "bi-calendar-check",
                "color": "#7C3AED",
                "title": f"Reserva — {r['placa']}",
                "message": f"{r['solicitante_nome']} p/ {r['data_reserva']} {r['horario_inicio']}-{r['horario_fim']}",
                "reservation_id": r["id"],
            })

        # 5) Reservas aprovadas/rejeitadas não lidas (para o solicitante)
        cursor.execute("""
            SELECT r.id, r.status, r.data_reserva, r.horario_inicio, r.horario_fim,
                   r.motivo_rejeicao, v.placa, v.modelo, v.id AS vid
            FROM fleet_reservations r
            JOIN fleet_vehicles v ON v.id = r.vehicle_id
            WHERE r.solicitante_id = %s AND r.notif_lida = 0
              AND r.status IN ('aprovado','rejeitado')
        """, (uid,))
        for r in cursor.fetchall():
            if r["status"] == "aprovado":
                alerts.append({
                    "type": "reservation_approved", "icon": "bi-calendar-check-fill", "color": "#16A34A",
                    "title": f"Reserva aprovada — {r['placa']}", "message": f"Dia {r['data_reserva']}",
                    "reservation_id": r["id"],
                })
            else:
                alerts.append({
                    "type": "reservation_rejected", "icon": "bi-calendar-x-fill", "color": "#DC2626",
                    "title": f"Reserva recusada — {r['placa']}", "message": r["motivo_rejeicao"] or "Sem motivo",
                    "reservation_id": r["id"],
                })

        # 6) Reservas aprovadas HOJE — lembrar de fazer o checklist de saída
        cursor.execute("""
            SELECT r.id, r.horario_inicio, r.horario_fim, r.vehicle_id,
                   r.destino, r.solicitante_id, r.data_reserva,
                   v.placa, v.modelo
            FROM fleet_reservations r
            JOIN fleet_vehicles v ON v.id = r.vehicle_id
            WHERE r.solicitante_id = %s AND r.status = 'aprovado'
              AND r.data_reserva = CURDATE()
              AND r.horario_fim > CURTIME()
        """, (uid,))
        for r in cursor.fetchall():
            # Verificar se já tem checklist para este veículo hoje
            cursor.execute("""
                SELECT id FROM fleet_checklists
                WHERE vehicle_id=%s AND condutor_id=%s AND data_saida=CURDATE()
                  AND status NOT IN ('retornado','retornado_com_avaria','cancelado')
                LIMIT 1
            """, (r["vehicle_id"], uid))
            if not cursor.fetchone():
                # Normalizar tipos de horário/data para JSON
                hi = r["horario_inicio"]
                hf = r["horario_fim"]
                if hasattr(hi, "total_seconds"):
                    t = int(hi.total_seconds())
                    hi = f"{t//3600:02d}:{(t%3600)//60:02d}"
                if hasattr(hf, "total_seconds"):
                    t = int(hf.total_seconds())
                    hf = f"{t//3600:02d}:{(t%3600)//60:02d}"
                dt = r["data_reserva"]
                if hasattr(dt, "isoformat"):
                    dt = dt.isoformat()
                alerts.append({
                    "type": "reservation_checklist",
                    "icon": "bi-clipboard2-check-fill",
                    "color": "#D97706",
                    "title": f"Fazer checklist — {r['placa']}",
                    "message": f"Sua reserva e das {hi} as {hf}. Faca o checklist de saida!",
                    "vehicle_id": r["vehicle_id"],
                    "reservation_id": r["id"],
                    "destino": r["destino"],
                    "solicitante_id": r["solicitante_id"],
                    "horario_inicio": hi,
                    "horario_fim": hf,
                    "data_reserva": dt,
                })

        # 6b) Vistoria aprovada — condutor pode iniciar viagem
        cursor.execute("""
            SELECT ck.id, ck.data_saida, ck.horario_saida, ck.aprovado_em,
                   v.placa, v.modelo, apv.name AS aprovador_nome
            FROM fleet_checklists ck
            JOIN fleet_vehicles v ON v.id = ck.vehicle_id
            LEFT JOIN users apv ON apv.id = ck.aprovado_por
            WHERE ck.status = 'aprovado'
              AND ck.condutor_id = %s
            ORDER BY ck.aprovado_em DESC
        """, (uid,))
        for r in cursor.fetchall():
            alerts.append({
                "type": "checklist_aprovado",
                "icon": "bi-check-circle-fill",
                "color": "#16A34A",
                "title": f"Vistoria aprovada — {r['placa']}",
                "message": f"{r['aprovador_nome'] or 'Vistoriador'} autorizou a saída. Voce ja pode iniciar a viagem.",
                "checklist_id": r["id"],
            })

        # 6c) Devolução recusada — condutor precisa corrigir
        cursor.execute("""
            SELECT ck.id, v.placa, ck.recusa_justificativa, ck.recusa_em,
                   ru.name AS recusa_por_nome
            FROM fleet_checklists ck
            JOIN fleet_vehicles v ON v.id = ck.vehicle_id
            LEFT JOIN users ru ON ru.id = ck.recusa_por
            WHERE ck.status = 'em_viagem'
              AND ck.condutor_id = %s
              AND ck.recusa_justificativa IS NOT NULL
            ORDER BY ck.recusa_em DESC
        """, (uid,))
        for r in cursor.fetchall():
            alerts.append({
                "type": "checklist_recusado",
                "icon": "bi-exclamation-triangle-fill",
                "color": "#DC2626",
                "title": f"Devolução recusada — {r['placa']}",
                "message": f"{r['recusa_por_nome'] or 'Vistoriador'} recusou: {r['recusa_justificativa'][:100]}",
                "checklist_id": r["id"],
            })

        # 7) Checklists aguardando vistoria (para quem pode vistoriar)
        if _can_manage_fleet(user):
            cursor.execute("""
                SELECT ck.id, ck.data_saida, ck.horario_saida, ck.destino,
                       v.placa, v.modelo, cond.name AS condutor_nome
                FROM fleet_checklists ck
                JOIN fleet_vehicles v ON v.id = ck.vehicle_id
                JOIN users cond ON cond.id = ck.condutor_id
                WHERE ck.status = 'aguardando_vistoria'
                  AND ck.condutor_id <> %s
                ORDER BY ck.data_saida, ck.horario_saida
            """, (uid,))
            for r in cursor.fetchall():
                dt = r["data_saida"]
                if hasattr(dt, "isoformat"):
                    dt = dt.isoformat()
                hs = r["horario_saida"]
                if hasattr(hs, "total_seconds"):
                    t = int(hs.total_seconds())
                    hs = f"{t//3600:02d}:{(t%3600)//60:02d}"
                alerts.append({
                    "type": "checklist_vistoria_pendente",
                    "icon": "bi-shield-check",
                    "color": "#F59E0B",
                    "title": f"Vistoria pendente — {r['placa']}",
                    "message": f"{r['condutor_nome']} aguardando vistoria de saída para {dt} {hs or ''}".strip(),
                    "checklist_id": r["id"],
                })

        # Auto-cancelar reservas aprovadas sem checklist após 40 min do horário de início
        cursor.execute("""
            SELECT r.id, r.vehicle_id, r.solicitante_id, r.horario_inicio, v.placa
            FROM fleet_reservations r
            JOIN fleet_vehicles v ON v.id = r.vehicle_id
            WHERE r.status = 'aprovado'
              AND r.data_reserva = CURDATE()
              AND ADDTIME(r.horario_inicio, '00:40:00') <= CURTIME()
        """)
        for r in cursor.fetchall():
            cursor.execute("""
                SELECT id FROM fleet_checklists
                WHERE vehicle_id=%s AND condutor_id=%s AND data_saida=CURDATE()
                LIMIT 1
            """, (r["vehicle_id"], r["solicitante_id"]))
            if not cursor.fetchone():
                # Sem checklist → cancelar reserva por inatividade
                cursor.execute("""
                    UPDATE fleet_reservations
                    SET status='cancelado',
                        motivo_rejeicao='Cancelada automaticamente: checklist nao realizado em 40 minutos apos o horario de inicio'
                    WHERE id=%s
                """, (r["id"],))

        # Auto-corrigir: bloquear veículos que deveriam estar em manutencao
        cursor.execute("""
            SELECT DISTINCT m.vehicle_id
            FROM fleet_maintenance m
            JOIN fleet_vehicles v ON v.id = m.vehicle_id
            WHERE m.status IN ('agendado','em_andamento')
              AND m.data_entrada <= CURDATE()
              AND v.status = 'ativo'
        """)
        for r in cursor.fetchall():
            cursor.execute(
                "UPDATE fleet_vehicles SET status='manutencao' WHERE id=%s AND status='ativo'",
                (r["vehicle_id"],)
            )
        conn.commit()

        return {"success": True, "alerts": alerts, "count": len(alerts)}
    finally:
        cursor.close()
        conn.close()


# ============================================================
# ALERTAS DE KM
# ============================================================

@router.get("/km-alerts/{vehicle_id}")
def list_km_alerts(vehicle_id: int, request: Request):
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT a.*,
                   (SELECT km_atual FROM fleet_vehicles WHERE id = a.vehicle_id) AS km_atual
            FROM fleet_km_alerts a
            WHERE a.vehicle_id = %s
            ORDER BY a.km_limite
        """, (vehicle_id,))
        rows = cursor.fetchall()
        rows = convert_datetime_list(rows)
        return {"success": True, "alerts": rows}
    finally:
        cursor.close()
        conn.close()


@router.post("/km-alerts")
def create_km_alert(request: Request, data: dict):
    user_id = _get_user_id(request)
    vehicle_id = data.get("vehicle_id")
    tipo = (data.get("tipo") or "").strip()
    km_limite = data.get("km_limite")
    if not vehicle_id or not tipo or not km_limite:
        raise HTTPException(status_code=400, detail="vehicle_id, tipo e km_limite sao obrigatorios")
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "INSERT INTO fleet_km_alerts (vehicle_id, tipo, km_limite, created_by) VALUES (%s,%s,%s,%s)",
            (vehicle_id, tipo, km_limite, user_id)
        )
        conn.commit()
        return {"success": True, "id": cursor.lastrowid, "message": "Alerta de KM criado!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.delete("/km-alerts/{alert_id}")
def delete_km_alert(alert_id: int, request: Request):
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("DELETE FROM fleet_km_alerts WHERE id=%s", (alert_id,))
        conn.commit()
        return {"success": True, "message": "Alerta excluido!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.post("/km-alerts/{alert_id}/dismiss")
def dismiss_km_alert(alert_id: int, request: Request):
    """Marca alerta como notificado (dismiss)."""
    _get_user_id(request)
    conn = get_db_or_404()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("UPDATE fleet_km_alerts SET notificado=1 WHERE id=%s", (alert_id,))
        conn.commit()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
