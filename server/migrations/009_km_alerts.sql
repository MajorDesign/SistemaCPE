-- ============================================================
-- MÓDULO DE FROTAS - Migration 009
-- Data: 2026-04-16
-- Descrição:
--   1) Tabela fleet_km_alerts (alertas por KM - ex: troca de óleo)
-- ============================================================

USE cpe_plus;

CREATE TABLE IF NOT EXISTS fleet_km_alerts (
  id          INT PRIMARY KEY AUTO_INCREMENT,
  vehicle_id  INT NOT NULL,
  tipo        VARCHAR(100) NOT NULL COMMENT 'Ex: Troca de Oleo, Revisao, Troca de Pneu',
  km_limite   INT NOT NULL COMMENT 'KM em que o alerta dispara',
  notificado  TINYINT(1) DEFAULT 0 COMMENT '1=já notificado',
  created_by  BIGINT,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (vehicle_id) REFERENCES fleet_vehicles(id) ON DELETE CASCADE,
  FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
