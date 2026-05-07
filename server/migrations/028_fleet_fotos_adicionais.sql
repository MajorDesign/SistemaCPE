-- ============================================================
-- MÓDULO DE FROTAS — Migration 025
-- Data: 2026-05-07
-- Descrição: Adiciona coluna "legenda" em fleet_vehicle_photos
--            para suportar fotos adicionais (angulo='adicional_*')
--            com nome livre dado pelo usuário (ex: "Roda dianteira").
-- ============================================================

USE cpe_plus;

ALTER TABLE fleet_vehicle_photos
  ADD COLUMN legenda VARCHAR(80) NULL
  AFTER angulo;
