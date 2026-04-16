-- ============================================================
-- MÓDULO DE FROTAS - Migration 007
-- Data: 2026-04-16
-- Descrição:
--   1) Status 'devolvido' no checklist (condutor devolveu, aguarda vistoria retorno)
--   2) Status 'revisao' no veículo
--   3) Tabela fleet_maintenance (controle de manutenções)
--   4) Tabela fleet_vehicle_history (histórico de mudanças do veículo)
--   5) Coluna descricao em fleet_checklist_problems
-- ============================================================

USE cpe_plus;

-- 1) Ampliar status do checklist
ALTER TABLE fleet_checklists
  MODIFY COLUMN status ENUM(
    'aguardando_vistoria',
    'aguardando_aprovacao',
    'aprovado',
    'em_viagem',
    'devolvido',
    'retornado',
    'retornado_com_avaria',
    'cancelado'
  ) DEFAULT 'aguardando_vistoria';

-- 2) Ampliar status do veículo
ALTER TABLE fleet_vehicles
  MODIFY COLUMN status ENUM(
    'ativo','em_viagem','manutencao','revisao','inativo'
  ) DEFAULT 'ativo';

-- 3) Tabela de manutenções
CREATE TABLE IF NOT EXISTS fleet_maintenance (
  id              INT PRIMARY KEY AUTO_INCREMENT,
  vehicle_id      INT NOT NULL,
  tipo            ENUM('troca_oleo','troca_pneu','revisao','troca_filtro',
                       'alinhamento','balanceamento','funilaria','eletrica','outro')
                  NOT NULL DEFAULT 'outro',
  descricao       TEXT,
  data_entrada    DATE,
  data_conclusao  DATE,
  km_atual        INT,
  custo           DECIMAL(10,2) DEFAULT 0,
  fornecedor      VARCHAR(200),
  status          ENUM('agendado','em_andamento','concluido','cancelado') DEFAULT 'agendado',
  observacoes     TEXT,
  created_by      BIGINT,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (vehicle_id) REFERENCES fleet_vehicles(id) ON DELETE CASCADE,
  FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4) Histórico do veículo
CREATE TABLE IF NOT EXISTS fleet_vehicle_history (
  id              INT PRIMARY KEY AUTO_INCREMENT,
  vehicle_id      INT NOT NULL,
  evento          VARCHAR(100) NOT NULL,
  descricao       TEXT,
  status_anterior VARCHAR(50),
  status_novo     VARCHAR(50),
  user_id         BIGINT,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (vehicle_id) REFERENCES fleet_vehicles(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id)    REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
