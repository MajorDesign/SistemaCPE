-- ============================================================
-- MÓDULO DE FROTAS — Migration 026
-- Data: 2026-05-07
-- Descrição: Centro de custo por grupo.
--   - Aluguel mensal nos veículos (snapshot do contrato)
--   - group_id nas viagens (centro de custo da viagem) — auto-set do condutor
--   - Em manutenção: causa, condutor_responsavel_id, group_id (NULL = Frotas)
-- ============================================================

USE cpe_plus;

-- 1) Aluguel mensal por veículo
ALTER TABLE fleet_vehicles
  ADD COLUMN valor_aluguel_mensal DECIMAL(10,2) NOT NULL DEFAULT 0
  AFTER status;

-- 2) Centro de custo (grupo) na viagem
ALTER TABLE fleet_trips
  ADD COLUMN group_id INT NULL AFTER condutor_id,
  ADD INDEX idx_fleet_trips_group_id (group_id);

-- 3) Manutenção: causa, condutor responsável, group_id
ALTER TABLE fleet_maintenance
  ADD COLUMN causa ENUM('normal','colisao','arranhao','outro')
       NOT NULL DEFAULT 'normal' AFTER tipo,
  ADD COLUMN condutor_responsavel_id BIGINT NULL AFTER causa,
  ADD COLUMN group_id INT NULL AFTER condutor_responsavel_id,
  ADD INDEX idx_fleet_maintenance_group_id (group_id),
  ADD INDEX idx_fleet_maintenance_causa (causa);

-- 4) Backfill: derivar group_id das viagens a partir do condutor
UPDATE fleet_trips ft
  JOIN users u ON u.id = ft.condutor_id
   SET ft.group_id = u.group_id
 WHERE ft.condutor_id IS NOT NULL AND ft.group_id IS NULL;
