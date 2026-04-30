-- ============================================================
-- MÓDULO DE RECEPÇÃO - Migration 016
-- Data: 2026-04-30
-- Descrição: Escritórios (subdivisão da unidade).
--   BH tem 2 escritórios físicos (Barão / Raja). Outras unidades
--   podem ter ou não escritórios — escritorio_id é nullable em salas.
-- ============================================================

USE cpe_plus;

-- ---------- Escritórios ----------
CREATE TABLE IF NOT EXISTS recepcao_escritorios (
  id            INT PRIMARY KEY AUTO_INCREMENT,
  unit_id       INT NOT NULL,
  nome          VARCHAR(120) NOT NULL,
  ativo         TINYINT(1) DEFAULT 1,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (unit_id) REFERENCES unidades_cpe(id) ON DELETE CASCADE,
  UNIQUE KEY uniq_unit_nome (unit_id, nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Popula os 2 escritórios de BH (idempotente — depende de unidades_cpe já estar criada)
INSERT IGNORE INTO recepcao_escritorios (unit_id, nome)
SELECT u.id, 'Escritório Barão' FROM unidades_cpe u WHERE u.sigla = 'BH';

INSERT IGNORE INTO recepcao_escritorios (unit_id, nome)
SELECT u.id, 'Escritório Raja'  FROM unidades_cpe u WHERE u.sigla = 'BH';

-- ---------- escritorio_id em recepcao_salas ----------
SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'recepcao_salas'
    AND COLUMN_NAME  = 'escritorio_id'
);
SET @sql := IF(@col_exists = 0,
  'ALTER TABLE recepcao_salas
    ADD COLUMN escritorio_id INT DEFAULT NULL AFTER unit_id,
    ADD INDEX idx_sala_escritorio (escritorio_id),
    ADD CONSTRAINT fk_sala_escritorio
      FOREIGN KEY (escritorio_id) REFERENCES recepcao_escritorios(id)
      ON DELETE SET NULL',
  'SELECT "escritorio_id já existe" AS msg'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ---------- Verificação ----------
SELECT
  (SELECT COUNT(*) FROM information_schema.tables
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'recepcao_escritorios') AS tabela_escritorios,
  (SELECT COUNT(*) FROM information_schema.columns
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'recepcao_salas'
      AND COLUMN_NAME = 'escritorio_id') AS coluna_em_salas,
  (SELECT COUNT(*) FROM recepcao_escritorios e
    JOIN unidades_cpe u ON u.id = e.unit_id WHERE u.sigla = 'BH') AS escritorios_bh;
-- Esperado: 1 | 1 | 2
