-- ============================================================
-- MÓDULO DE RECEPÇÃO - Migration 018
-- Data: 2026-05-04
-- Descrição: Adiciona coluna `ultima_consulta_api` em recepcao_envios
--   para implementar cache de rastreio (TTL 4h por envio).
--   Evita estourar o limite de 50 consultas/mês do plano gratuito
--   da API seurastreio.com.br.
-- ============================================================

USE cpe_plus;

SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'recepcao_envios'
    AND COLUMN_NAME  = 'ultima_consulta_api'
);
SET @sql := IF(@col_exists = 0,
  'ALTER TABLE recepcao_envios
     ADD COLUMN ultima_consulta_api DATETIME DEFAULT NULL AFTER ultima_atualizacao',
  'SELECT "ultima_consulta_api já existe" AS msg'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Verificação
SELECT
  (SELECT COUNT(*) FROM information_schema.columns
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'recepcao_envios'
      AND COLUMN_NAME = 'ultima_consulta_api') AS coluna_cache;
-- Esperado: 1
