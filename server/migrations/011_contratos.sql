-- ============================================================
-- MÓDULO CONTRATOS E TERMOS - Migration 011
-- Data: 2026-04-16
-- ============================================================

USE cpe_plus;

-- Pastas (cada grupo ganha pasta raiz + pode ter subpastas)
CREATE TABLE IF NOT EXISTS contrato_pastas (
  id          INT PRIMARY KEY AUTO_INCREMENT,
  group_id    INT NOT NULL,
  parent_id   INT NULL,
  nome        VARCHAR(200) NOT NULL,
  is_root     TINYINT(1) DEFAULT 0 COMMENT '1=pasta raiz do grupo (nao pode excluir)',
  created_by  BIGINT,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (group_id)  REFERENCES cpe_grupo(id) ON DELETE CASCADE,
  FOREIGN KEY (parent_id) REFERENCES contrato_pastas(id) ON DELETE CASCADE,
  FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_group_parent (group_id, parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Contratos/arquivos
CREATE TABLE IF NOT EXISTS contratos (
  id              INT PRIMARY KEY AUTO_INCREMENT,
  pasta_id        INT NOT NULL,
  nome            VARCHAR(255) NOT NULL,
  descricao       TEXT,
  arquivo_path    VARCHAR(500) NOT NULL,
  tipo            VARCHAR(10) NOT NULL COMMENT 'pdf, doc, docx',
  tamanho_bytes   INT NOT NULL,
  uploaded_by     BIGINT NOT NULL,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (pasta_id)    REFERENCES contrato_pastas(id) ON DELETE CASCADE,
  FOREIGN KEY (uploaded_by) REFERENCES users(id),
  INDEX idx_pasta (pasta_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
