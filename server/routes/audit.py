"""
Rotas de auditoria: logs de ações
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import text
from database import engine
from security import get_current_user

router = APIRouter(prefix="/api/audit", tags=["Audit"])

# =========================================
# 📊 LIST AUDIT LOGS
# =========================================

@router.get("/logs")
async def list_audit_logs(
    current_user: Dict[str, Any] = Depends(get_current_user),
    limit: int = 50,
):
    """Lista logs de auditoria"""
    print(f"[AUDIT/LIST] Listando logs (solicitado por: {current_user['id']})")
    
    try:
        # Apenas ADMIN pode ver todos os logs
        if current_user["role"] != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas ADMINs podem ver logs de auditoria"
            )

        with engine.connect() as conn:
            logs_result = conn.execute(
                text("""
                    SELECT 
                        id, user_id, department_id, module, action, object_type,
                        object_id, ip_address, description, created_at
                    FROM audit_logs
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"limit": limit}
            ).mappings().all()

        logs = [
            {
                "id": log["id"],
                "user_id": log["user_id"],
                "department_id": log["department_id"],
                "module": log["module"],
                "action": log["action"],
                "object_type": log["object_type"],
                "object_id": log["object_id"],
                "ip_address": log["ip_address"],
                "description": log["description"],
                "created_at": log["created_at"].isoformat() if log["created_at"] else None,
            }
            for log in logs_result
        ]

        print(f"[AUDIT/LIST] ✓ {len(logs)} logs carregados")
        return {
            "success": True,
            "total": len(logs),
            "logs": logs
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUDIT/LIST] ✗ Erro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro: {str(e)}"
        )


# =========================================
# ✍️ CREATE AUDIT LOG
# =========================================

@router.post("/logs")
async def create_audit_log(
    data: dict,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Cria um novo log de auditoria"""
    print(f"[AUDIT/CREATE] Criando log de auditoria...")
    
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO audit_logs (
                    user_id, department_id, module, action, object_type,
                    object_id, ip_address, description
                ) VALUES (
                    :user_id, :dept_id, :module, :action, :object_type,
                    :object_id, :ip_address, :description
                )
            """), {
                "user_id": current_user["id"],
                "dept_id": current_user.get("department_id"),
                "module": data.get("module"),
                "action": data.get("action"),
                "object_type": data.get("object_type"),
                "object_id": data.get("object_id"),
                "ip_address": data.get("ip_address"),
                "description": data.get("description"),
            })

        print(f"[AUDIT/CREATE] ✓ Log de auditoria registrado\n")
        return {"ok": True}

    except Exception as e:
        print(f"[AUDIT/CREATE] ✗ Erro (ignorado): {e}\n")
        return {"ok": True}  # Não interrompe o fluxo


# =========================================
# 📈 GET AUDIT STATS
# =========================================

@router.get("/stats")
async def get_audit_stats(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Retorna estatísticas de auditoria"""
    print(f"[AUDIT/STATS] Buscando estatísticas...")
    
    try:
        # Apenas ADMIN pode ver stats
        if current_user["role"] != "ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Apenas ADMINs podem ver estatísticas"
            )

        with engine.connect() as conn:
            # Total de logs
            total_result = conn.execute(
                text("SELECT COUNT(*) as total FROM audit_logs")
            ).mappings().first()

            # Logs por módulo
            by_module = conn.execute(
                text("""
                    SELECT module, COUNT(*) as total
                    FROM audit_logs
                    GROUP BY module
                    ORDER BY total DESC
                """)
            ).mappings().all()

            # Logs por ação
            by_action = conn.execute(
                text("""
                    SELECT action, COUNT(*) as total
                    FROM audit_logs
                    GROUP BY action
                    ORDER BY total DESC
                """)
            ).mappings().all()

        stats = {
            "total_logs": total_result["total"] if total_result else 0,
            "by_module": [{"module": m["module"], "total": m["total"]} for m in by_module],
            "by_action": [{"action": a["action"], "total": a["total"]} for a in by_action],
        }

        print(f"[AUDIT/STATS] ✓ Estatísticas carregadas")
        return {
            "success": True,
            "stats": stats
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUDIT/STATS] ✗ Erro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro: {str(e)}"
        )