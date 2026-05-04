-- ============================================================
-- MÓDULO AGENDA — Migration 021
-- Data: 2026-05-04
-- Descrição: Tabela para rastrear quais eventos do Carbonio já
--   tiveram lembrete enviado (sino do sistema), evitando duplicar
--   a notificação quando o scheduler tiver vários ticks no mesmo
--   minuto.
-- ============================================================

USE cpe_plus;

CREATE TABLE IF NOT EXISTS agenda_lembretes_enviados (
  id           INT PRIMARY KEY AUTO_INCREMENT,
  usuario_id   BIGINT NOT NULL,
  evento_uid   VARCHAR(255) NOT NULL,
  inicio_evt   DATETIME NOT NULL,
  enviado_em   DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_user_evento (usuario_id, evento_uid, inicio_evt),
  INDEX idx_enviado (enviado_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SELECT
  (SELECT COUNT(*) FROM information_schema.tables
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'agenda_lembretes_enviados') AS tabela_lembretes;
-- Esperado: 1
