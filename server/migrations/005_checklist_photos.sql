-- ============================================================
-- MÓDULO DE FROTAS - Migration 005
-- Data: 2026-04-15
-- Descrição: Tabela de fotos de inspeção por checklist
-- ============================================================

USE cpe_plus;

CREATE TABLE IF NOT EXISTS fleet_checklist_photos (
  id           INT PRIMARY KEY AUTO_INCREMENT,
  checklist_id INT NOT NULL,
  angulo       VARCHAR(50) DEFAULT 'frente',
  foto_path    VARCHAR(500) NOT NULL,
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (checklist_id) REFERENCES fleet_checklists(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
