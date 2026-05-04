-- ============================================================
-- MÓDULO DE RECEPÇÃO - Migration 017
-- Data: 2026-05-04
-- Descrição: Histórico de eventos de cada envio (timeline manual,
--   similar à tela dos Correios). Cada envio tem N eventos com
--   tipo (com ícone), descrição, local e data/hora.
-- ============================================================

USE cpe_plus;

CREATE TABLE IF NOT EXISTS recepcao_envio_eventos (
  id            INT PRIMARY KEY AUTO_INCREMENT,
  envio_id      INT NOT NULL,
  tipo          VARCHAR(40) NOT NULL DEFAULT 'em_transito',
  descricao     VARCHAR(255) NOT NULL,
  local         VARCHAR(180) DEFAULT NULL,
  data_evento   DATETIME NOT NULL,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (envio_id) REFERENCES recepcao_envios(id) ON DELETE CASCADE,
  INDEX idx_evento_envio (envio_id),
  INDEX idx_evento_data  (data_evento)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Verificação
SELECT
  (SELECT COUNT(*) FROM information_schema.tables
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'recepcao_envio_eventos') AS tabela_eventos;
-- Esperado: 1
