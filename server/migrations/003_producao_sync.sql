-- ============================================================
-- Migração 003: sincroniza o banco de produção com o estado de dev
-- (Aplica apenas o que ainda não existe; seguro para re-executar.)
-- ============================================================

-- -- 1) fleet_trips: coluna custo_lavagem (devolução com custos informados)
ALTER TABLE fleet_trips
    ADD COLUMN IF NOT EXISTS custo_lavagem DECIMAL(10,2) DEFAULT 0.00 AFTER custo_combustivel;

-- -- 2) fleet_maintenance: coluna trip_id (vincula manutenção concluída à trip criada)
ALTER TABLE fleet_maintenance
    ADD COLUMN IF NOT EXISTS trip_id INT NULL AFTER observacoes;

-- -- 3) tarefa_encaminhamentos_TASK (migração 001 — cria se ainda não existir)
CREATE TABLE IF NOT EXISTS tarefa_encaminhamentos_TASK (
    id               INT          NOT NULL AUTO_INCREMENT,
    tarefa_id        INT          NOT NULL,
    de_grupo_id      INT          NOT NULL,
    para_grupo_id    INT          NOT NULL,
    encaminhado_por  INT          NOT NULL,
    encaminhado_em   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status_id_origem INT          NULL DEFAULT NULL,
    status_id_retorno INT         NULL DEFAULT NULL,
    devolvido_em     DATETIME     NULL DEFAULT NULL,
    devolvido_por    INT          NULL DEFAULT NULL,
    motivo_devolucao TEXT         NULL DEFAULT NULL,
    PRIMARY KEY (id),
    INDEX idx_tarefa_id  (tarefa_id),
    INDEX idx_de_grupo   (de_grupo_id, devolvido_em),
    INDEX idx_para_grupo (para_grupo_id, devolvido_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -- 4) Contratos e Termos (migração 002 — cria se ainda não existir)
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

-- -- 5) Seed: uma pasta raiz de contratos para cada grupo (só se faltar)
INSERT INTO contrato_pastas (group_id, parent_id, nome, is_root, created_by)
SELECT g.id, NULL, g.name, 1, NULL
FROM cpe_grupo g
WHERE NOT EXISTS (
    SELECT 1 FROM contrato_pastas p
    WHERE p.group_id = g.id AND p.is_root = 1
);
