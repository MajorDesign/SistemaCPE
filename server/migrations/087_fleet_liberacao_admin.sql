-- ============================================================
-- MÓDULO DE FROTAS - Migration 087
-- Data: 2026-08-11
-- Descrição: Liberação de emergência pelo ADMIN
--   Admin pode forçar aprovação do checklist pulando as validações
--   normais (fotos faltando, assinatura, etc). Registra motivo +
--   quem forçou + quando pra auditoria.
--   Aplicável em: aguardando_vistoria, em_viagem, devolvido.
-- ============================================================

USE cpe_plus;

ALTER TABLE fleet_checklists
  ADD COLUMN IF NOT EXISTS liberacao_admin_por BIGINT NULL
    COMMENT 'Admin que forçou a liberação (bypass do fluxo normal)',
  ADD COLUMN IF NOT EXISTS liberacao_admin_em DATETIME NULL,
  ADD COLUMN IF NOT EXISTS liberacao_admin_motivo TEXT NULL
    COMMENT 'Motivo obrigatório pra auditoria',
  ADD COLUMN IF NOT EXISTS liberacao_admin_from_status VARCHAR(30) NULL
    COMMENT 'Status de origem antes da liberação forçada',
  ADD CONSTRAINT fk_lib_admin_por
    FOREIGN KEY (liberacao_admin_por) REFERENCES users(id) ON DELETE SET NULL;
