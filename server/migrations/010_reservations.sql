-- ============================================================
-- MÓDULO DE FROTAS - Migration 010
-- Data: 2026-04-16
-- Descrição: Sistema de agendamento/reserva de veículos
-- ============================================================

USE cpe_plus;

CREATE TABLE IF NOT EXISTS fleet_reservations (
  id                      INT PRIMARY KEY AUTO_INCREMENT,
  vehicle_id              INT NOT NULL,
  solicitante_id          BIGINT NOT NULL,
  destino                 VARCHAR(200) NOT NULL,
  data_reserva            DATE NOT NULL,
  horario_inicio          TIME NOT NULL,
  horario_fim             TIME NOT NULL,
  status                  ENUM('pendente','aprovado','rejeitado','cancelado','concluido') DEFAULT 'pendente',
  aprovador_id            BIGINT,
  aprovado_em             TIMESTAMP NULL,
  motivo_rejeicao         TEXT,
  notif_lida              TINYINT(1) DEFAULT 0 COMMENT 'Solicitante já viu a resposta',
  created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (vehicle_id)      REFERENCES fleet_vehicles(id),
  FOREIGN KEY (solicitante_id)  REFERENCES users(id),
  FOREIGN KEY (aprovador_id)    REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_data_veiculo (vehicle_id, data_reserva, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
