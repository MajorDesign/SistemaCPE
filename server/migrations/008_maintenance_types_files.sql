-- ============================================================
-- MÓDULO DE FROTAS - Migration 008
-- Data: 2026-04-16
-- Descrição:
--   1) Tipos de serviço cadastráveis (fleet_maintenance_types)
--   2) Anexos/recibos de manutenção (fleet_maintenance_files)
--   3) Alterar fleet_maintenance.tipo para VARCHAR (ref types)
-- ============================================================

USE cpe_plus;

-- 1) Tipos de serviço
CREATE TABLE IF NOT EXISTS fleet_maintenance_types (
  id          INT PRIMARY KEY AUTO_INCREMENT,
  name        VARCHAR(100) NOT NULL,
  created_by  BIGINT,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO fleet_maintenance_types (name) VALUES
  ('Troca de Oleo'), ('Troca de Pneu'), ('Revisao'), ('Troca de Filtro'),
  ('Alinhamento'), ('Balanceamento'), ('Funilaria/Pintura'), ('Eletrica'),
  ('Troca de Correia'), ('Troca de Pastilha de Freio'), ('Lavagem/Higienizacao');

-- 2) Alterar campo tipo de ENUM para VARCHAR
ALTER TABLE fleet_maintenance MODIFY COLUMN tipo VARCHAR(100) NOT NULL DEFAULT 'Outro';

-- 3) Arquivos/recibos de manutenção
CREATE TABLE IF NOT EXISTS fleet_maintenance_files (
  id              INT PRIMARY KEY AUTO_INCREMENT,
  maintenance_id  INT NOT NULL,
  file_path       VARCHAR(500) NOT NULL,
  nome_arquivo    VARCHAR(200),
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (maintenance_id) REFERENCES fleet_maintenance(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
