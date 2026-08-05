-- ============================================================
-- MÓDULO DE FROTAS - Migration 083
-- Data: 2026-08-05
-- Descrição: Anti-burla no checklist de veículos
--   1) Coluna file_hash em fleet_checklist_photos —
--      SHA-256 do arquivo. Índice único por (checklist_id, file_hash)
--      impede o condutor de reenviar a MESMA foto em ângulos diferentes.
--   2) Ângulo 'painel' passa a existir (foto do painel mostrando KM).
--      A validação de obrigatoriedade das 7 fotos é feita no backend
--      pra checklists criados a partir desta data (compat com histórico).
-- ============================================================

USE cpe_plus;

-- 1) Hash do arquivo — evita reuso literal da mesma foto
ALTER TABLE fleet_checklist_photos
  ADD COLUMN IF NOT EXISTS file_hash CHAR(64) NULL
    COMMENT 'SHA-256 hex dos bytes do arquivo — anti-reuso' AFTER foto_path;

-- Índice único por (checklist, hash): rejeita a mesma foto no mesmo checklist,
-- mas permite o mesmo hash em checklists diferentes (ex: recusa + reenvio).
ALTER TABLE fleet_checklist_photos
  ADD UNIQUE INDEX IF NOT EXISTS uq_checklist_hash (checklist_id, file_hash);

-- Índice de consulta pra estatísticas globais (opcional):
ALTER TABLE fleet_checklist_photos
  ADD INDEX IF NOT EXISTS idx_file_hash (file_hash);
