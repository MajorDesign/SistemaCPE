-- ============================================================
-- MÓDULO DE FROTAS - Migration 004
-- Data: 2026-04-15
-- Descrição: Adiciona coluna "angulo" à fleet_vehicle_photos
--            para suportar 6 ângulos específicos por veículo.
-- ============================================================

USE cpe_plus;

ALTER TABLE fleet_vehicle_photos
  ADD COLUMN angulo VARCHAR(50) DEFAULT 'frente'
  AFTER foto_path;

-- Definir angulo='frente' para fotos existentes (retrocompatibilidade)
UPDATE fleet_vehicle_photos SET angulo = 'frente' WHERE angulo IS NULL;
