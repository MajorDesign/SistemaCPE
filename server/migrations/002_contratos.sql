-- Migração: tabelas de Contratos e Termos
-- Executar via MySQL/phpMyAdmin no banco cpe_plus

CREATE TABLE IF NOT EXISTS contrato_pastas (
    id          INT           NOT NULL AUTO_INCREMENT,
    group_id    INT           NOT NULL,
    parent_id   INT           NULL DEFAULT NULL,
    nome        VARCHAR(255)  NOT NULL,
    is_root     TINYINT(1)    NOT NULL DEFAULT 0,
    created_by  INT           NULL DEFAULT NULL,
    created_at  TIMESTAMP     NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_group  (group_id),
    INDEX idx_parent (parent_id),
    CONSTRAINT fk_contr_pasta_group  FOREIGN KEY (group_id)  REFERENCES cpe_grupo(id)      ON DELETE CASCADE,
    CONSTRAINT fk_contr_pasta_parent FOREIGN KEY (parent_id) REFERENCES contrato_pastas(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS contratos (
    id            INT           NOT NULL AUTO_INCREMENT,
    pasta_id      INT           NOT NULL,
    nome          VARCHAR(255)  NOT NULL,
    descricao     TEXT          NULL,
    arquivo_path  VARCHAR(500)  NOT NULL,
    tipo          VARCHAR(10)   NOT NULL,
    tamanho_bytes INT           NOT NULL DEFAULT 0,
    uploaded_by   BIGINT        NULL DEFAULT NULL,
    created_at    TIMESTAMP     NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_pasta    (pasta_id),
    INDEX idx_uploader (uploaded_by),
    CONSTRAINT fk_contr_pasta_id FOREIGN KEY (pasta_id)   REFERENCES contrato_pastas(id) ON DELETE CASCADE,
    CONSTRAINT fk_contr_user     FOREIGN KEY (uploaded_by) REFERENCES users(id)          ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Pasta raiz para cada grupo existente (apenas se ainda não tiver uma)
INSERT INTO contrato_pastas (group_id, parent_id, nome, is_root, created_by)
SELECT g.id, NULL, g.name, 1, NULL
FROM cpe_grupo g
WHERE NOT EXISTS (
    SELECT 1 FROM contrato_pastas p
    WHERE p.group_id = g.id AND p.is_root = 1
);
