-- ============================================================
-- MÓDULO DE RECEPÇÃO - Migration 019
-- Data: 2026-05-04
-- Descrição: Muda a regra de confirmação da reserva.
--   ANTES: 40 min após criação → expira se não confirmar.
--   AGORA: 40 min ANTES do início → notifica usuário responsável.
--          Se não confirmar até o horário de início → expira.
--
--   Adiciona flag `notificou_confirmacao` para evitar enviar a
--   notificação T-40min mais de uma vez por reserva.
-- ============================================================

USE cpe_plus;

SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'recepcao_reservas'
    AND COLUMN_NAME  = 'notificou_confirmacao'
);
SET @sql := IF(@col_exists = 0,
  'ALTER TABLE recepcao_reservas
     ADD COLUMN notificou_confirmacao TINYINT(1) DEFAULT 0 AFTER confirmacao_prazo',
  'SELECT "notificou_confirmacao já existe" AS msg'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Verificação
SELECT
  (SELECT COUNT(*) FROM information_schema.columns
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'recepcao_reservas'
      AND COLUMN_NAME = 'notificou_confirmacao') AS coluna_flag;
-- Esperado: 1
