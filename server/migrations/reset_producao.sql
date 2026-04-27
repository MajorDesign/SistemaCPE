-- ============================================================
-- RESET DE PRODUÇÃO (limpar dados de teste)
-- Data: 2026-04-23
-- ----
-- MANTÉM:
--   - users: só id=15 (Administrador)
--   - cpe_grupo, departments (estrutura)
--   - page_permissions
--   - ticket_prioridades, ticket_status, ticket_sla
--   - categorias, subcategorias
--   - fleet_maintenance_types
--   - contrato_pastas onde is_root=1 (pastas raiz por grupo)
--
-- APAGA: dados transacionais de testes (tickets, tasks, frotas,
--   contratos enviados, notificações, sessões, etc).
--
-- Reseta AUTO_INCREMENT das tabelas limpas para começar em 1.
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

-- ---- TICKETS --------------------------------------------------
TRUNCATE TABLE ticket_interacoes;
TRUNCATE TABLE ticket_avaliacoes;
TRUNCATE TABLE ticket_anexos;
TRUNCATE TABLE tickets;

-- ---- TAREFAS / KANBAN ----------------------------------------
TRUNCATE TABLE subtarefas_task;
TRUNCATE TABLE comentarios_task;
TRUNCATE TABLE historico_task;
TRUNCATE TABLE tarefa_categorias_task;
TRUNCATE TABLE tarefa_encaminhamentos_task;
TRUNCATE TABLE tarefa_historico_status_task;
TRUNCATE TABLE tarefa_membros_task;
TRUNCATE TABLE etapas_task;
TRUNCATE TABLE categorias_task;
TRUNCATE TABLE tarefas_task;
TRUNCATE TABLE convites_espaco_task;
TRUNCATE TABLE espaco_membros_task;
TRUNCATE TABLE espaco_grupo_sla_task;
TRUNCATE TABLE espaco_grupos_task;
TRUNCATE TABLE status_task;
TRUNCATE TABLE espacos_task;
TRUNCATE TABLE template_statuses_task;
TRUNCATE TABLE templates_espaco_task;

-- ---- FROTAS ---------------------------------------------------
TRUNCATE TABLE fleet_checklist_photos;
TRUNCATE TABLE fleet_checklist_problems;
TRUNCATE TABLE fleet_checklists;
TRUNCATE TABLE fleet_km_alerts;
TRUNCATE TABLE fleet_maintenance_files;
TRUNCATE TABLE fleet_maintenance;
TRUNCATE TABLE fleet_reservations;
TRUNCATE TABLE fleet_trips;
TRUNCATE TABLE fleet_vehicle_history;
TRUNCATE TABLE fleet_vehicle_photos;
TRUNCATE TABLE fleet_vehicles;

-- ---- CONTRATOS ENVIADOS (mantém pastas raiz) ------------------
TRUNCATE TABLE contratos;
DELETE FROM contrato_pastas WHERE is_root = 0;

-- ---- NOTIFICAÇÕES / SESSÃO -----------------------------------
TRUNCATE TABLE notificacoes;
TRUNCATE TABLE user_access_exceptions;

-- ---- COFRE DE SENHAS / DOCUMENTOS ----------------------------
TRUNCATE TABLE passwords;
TRUNCATE TABLE documents;

-- ---- USUÁRIOS (mantém só o Administrador id=15) ---------------
DELETE FROM users WHERE id <> 15;

SET FOREIGN_KEY_CHECKS = 1;

-- ---- RESET AUTO_INCREMENT das tabelas não-vazias --------------
-- users: próximo id a partir de 16 (admin é 15)
ALTER TABLE users AUTO_INCREMENT = 16;

-- contrato_pastas: continua do próximo id após as raízes existentes
SET @next_cp := (SELECT IFNULL(MAX(id), 0) + 1 FROM contrato_pastas);
SET @sql_cp  := CONCAT('ALTER TABLE contrato_pastas AUTO_INCREMENT = ', @next_cp);
PREPARE s FROM @sql_cp; EXECUTE s; DEALLOCATE PREPARE s;
