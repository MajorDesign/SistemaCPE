-- ============================================================
-- MÓDULO DE RECEPÇÃO - Migration 014c (CONSOLIDADA / RECOVERY)
-- Data: 2026-04-30
-- Descrição: Versão única e idempotente. Pode ser executada
-- mesmo que 014 ou 014b tenham sido aplicadas parcialmente.
-- ============================================================
-- Esta migração:
--   1) Cria unidades_cpe (se não existir) e popula BH/SP
--   2) Adiciona users.unit_id (se não existir)
--   3) Cria recepcao_salas (se não existir)
--   4) DERRUBA e recria recepcao_reservas com tipos de FK corretos
--   5) DERRUBA e recria recepcao_envios com tipos de FK corretos
--
-- Importante: itens 4 e 5 dropam as tabelas — mas como estavam
-- com defeito desde a 014, presumivelmente estão vazias ou nem
-- existem. Não afeta unidades, salas nem usuários.
-- ============================================================

USE cpe_plus;

-- ---------- 1) UNIDADES CPE ----------
CREATE TABLE IF NOT EXISTS unidades_cpe (
  id            INT PRIMARY KEY AUTO_INCREMENT,
  nome          VARCHAR(120) NOT NULL,
  sigla         VARCHAR(20) DEFAULT NULL,
  cidade        VARCHAR(120) DEFAULT NULL,
  uf            CHAR(2)      DEFAULT NULL,
  endereco      VARCHAR(255) DEFAULT NULL,
  ativo         TINYINT(1)   DEFAULT 1,
  created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uniq_nome (nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO unidades_cpe (nome, sigla, cidade, uf) VALUES
  ('CPE Belo Horizonte', 'BH', 'Belo Horizonte', 'MG'),
  ('CPE São Paulo',      'SP', 'São Paulo',      'SP');

-- ---------- 2) users.unit_id ----------
SET @col_exists := (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME   = 'users'
    AND COLUMN_NAME  = 'unit_id'
);
SET @sql := IF(@col_exists = 0,
  'ALTER TABLE users ADD COLUMN unit_id INT DEFAULT NULL AFTER group_id, ADD INDEX idx_users_unit (unit_id)',
  'SELECT "unit_id já existe" AS msg'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- ---------- 3) SALAS ----------
CREATE TABLE IF NOT EXISTS recepcao_salas (
  id            INT PRIMARY KEY AUTO_INCREMENT,
  unit_id       INT NOT NULL,
  nome          VARCHAR(120) NOT NULL,
  tipo          ENUM('sala','auditorio') DEFAULT 'sala',
  capacidade    INT DEFAULT NULL,
  descricao     VARCHAR(500) DEFAULT NULL,
  cor           VARCHAR(7)   DEFAULT '#3b82f6',
  ativa         TINYINT(1)   DEFAULT 1,
  criado_por    BIGINT       DEFAULT NULL,
  created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (unit_id) REFERENCES unidades_cpe(id) ON DELETE CASCADE,
  INDEX idx_sala_unit (unit_id, ativa)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------- 4) RESERVAS (drop + recreate com BIGINT) ----------
DROP TABLE IF EXISTS recepcao_reservas;
CREATE TABLE recepcao_reservas (
  id              INT PRIMARY KEY AUTO_INCREMENT,
  sala_id         INT NOT NULL,
  usuario_id      BIGINT NOT NULL,
  titulo          VARCHAR(200) NOT NULL,
  descricao       VARCHAR(500) DEFAULT NULL,
  inicio          DATETIME NOT NULL,
  fim             DATETIME NOT NULL,
  status          ENUM('pendente','confirmada','expirada','cancelada','concluida') DEFAULT 'pendente',
  confirmacao_prazo  DATETIME NOT NULL,
  confirmada_em      DATETIME DEFAULT NULL,
  cancelada_em       DATETIME DEFAULT NULL,
  motivo_cancel      VARCHAR(255) DEFAULT NULL,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (sala_id)    REFERENCES recepcao_salas(id) ON DELETE CASCADE,
  FOREIGN KEY (usuario_id) REFERENCES users(id),
  INDEX idx_reserva_sala_periodo (sala_id, inicio, fim, status),
  INDEX idx_reserva_status_prazo (status, confirmacao_prazo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------- 5) ENVIOS (drop + recreate com BIGINT) ----------
DROP TABLE IF EXISTS recepcao_envios;
CREATE TABLE recepcao_envios (
  id                  INT PRIMARY KEY AUTO_INCREMENT,
  remetente_id        BIGINT NOT NULL,
  destino             VARCHAR(255) NOT NULL,
  destinatario        VARCHAR(150) NOT NULL,
  valor_mercadoria    DECIMAL(12,2) DEFAULT 0,
  codigo_correios     VARCHAR(30) DEFAULT NULL,
  status_correios     VARCHAR(120) DEFAULT NULL,
  status_data         DATETIME DEFAULT NULL,
  status_local        VARCHAR(180) DEFAULT NULL,
  ultima_atualizacao  DATETIME DEFAULT NULL,
  observacoes         VARCHAR(500) DEFAULT NULL,
  created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (remetente_id) REFERENCES users(id),
  INDEX idx_envio_codigo (codigo_correios),
  INDEX idx_envio_remetente (remetente_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------- VERIFICAÇÃO ----------
SELECT
  (SELECT COUNT(*) FROM information_schema.tables
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'unidades_cpe')      AS unidades_cpe,
  (SELECT COUNT(*) FROM information_schema.tables
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'recepcao_salas')    AS recepcao_salas,
  (SELECT COUNT(*) FROM information_schema.tables
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'recepcao_reservas') AS recepcao_reservas,
  (SELECT COUNT(*) FROM information_schema.tables
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'recepcao_envios')   AS recepcao_envios,
  (SELECT COUNT(*) FROM information_schema.columns
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'unit_id') AS users_unit_id;
-- Todas as colunas devem retornar 1.
