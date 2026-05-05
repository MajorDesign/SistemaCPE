-- ============================================================
-- MÓDULO AGENDA - Migration 022
-- Data: 2026-05-05
-- Descrição: Compartilhamento de agenda entre usuários.
--   Usuário A solicita ver a agenda de B → B aceita/recusa →
--   Se aceito, A vê os eventos de B (título + horário + local).
-- ============================================================

USE cpe_plus;

CREATE TABLE IF NOT EXISTS agenda_compartilhamentos (
  id             INT PRIMARY KEY AUTO_INCREMENT,
  dono_id        BIGINT NOT NULL COMMENT 'dono da agenda',
  solicitante_id BIGINT NOT NULL COMMENT 'quem quer ver',
  status         ENUM('pendente','aceito','recusado') DEFAULT 'pendente',
  solicitado_em  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  respondido_em  DATETIME DEFAULT NULL,
  FOREIGN KEY (dono_id)        REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (solicitante_id) REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE KEY uniq_comp (dono_id, solicitante_id),
  INDEX idx_dono_status (dono_id, status),
  INDEX idx_sol_status  (solicitante_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SELECT
  (SELECT COUNT(*) FROM information_schema.tables
   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'agenda_compartilhamentos') AS tabela_criada;
-- Esperado: 1
