-- ============================================================
-- MÓDULO DE RECEPÇÃO - Migration 015
-- Data: 2026-04-30
-- Descrição: Convidados da reunião + status de resposta.
-- ============================================================
-- Cada reserva pode ter N convidados. Cada convidado responde
-- aceitar/recusar e gera notificação no sino.
-- ============================================================

USE cpe_plus;

CREATE TABLE IF NOT EXISTS recepcao_convidados (
  id              INT PRIMARY KEY AUTO_INCREMENT,
  reserva_id      INT NOT NULL,
  usuario_id      BIGINT NOT NULL,
  status          ENUM('pendente','aceito','recusado') DEFAULT 'pendente',
  respondido_em   DATETIME DEFAULT NULL,
  convidado_por   BIGINT NOT NULL,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (reserva_id)    REFERENCES recepcao_reservas(id) ON DELETE CASCADE,
  FOREIGN KEY (usuario_id)    REFERENCES users(id),
  FOREIGN KEY (convidado_por) REFERENCES users(id),
  UNIQUE KEY uniq_reserva_usuario (reserva_id, usuario_id),
  INDEX idx_convidado_status   (usuario_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Verificação
SELECT
  (SELECT COUNT(*) FROM information_schema.tables
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'recepcao_convidados') AS recepcao_convidados;
-- Deve retornar 1.
