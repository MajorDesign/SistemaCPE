-- ============================================================
-- MÓDULO AGENDA — Migration 020
-- Data: 2026-05-04
-- Descrição: Integração com Carbonio Community Edition 24.5.0.
--   Cada usuário do sistema pode conectar sua conta Carbonio.
--   O token de autenticação (válido ~12h) é guardado criptografado
--   na coluna `carbonio_token`. A senha NUNCA é armazenada.
-- ============================================================

USE cpe_plus;

SET @col_email := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'users'
    AND COLUMN_NAME  = 'carbonio_email'
);
SET @sql := IF(@col_email = 0,
  'ALTER TABLE users
     ADD COLUMN carbonio_email     VARCHAR(180) NULL,
     ADD COLUMN carbonio_token     TEXT         NULL,
     ADD COLUMN carbonio_token_exp DATETIME     NULL',
  'SELECT "colunas carbonio_* já existem" AS msg'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Verificação
SELECT
  (SELECT COUNT(*) FROM information_schema.columns
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users'
      AND COLUMN_NAME IN ('carbonio_email','carbonio_token','carbonio_token_exp')) AS colunas_criadas;
-- Esperado: 3
