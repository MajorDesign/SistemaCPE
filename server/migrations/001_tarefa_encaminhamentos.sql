-- Migração: tabela de encaminhamentos entre grupos para tarefas
-- Executar via MySQL/phpMyAdmin no banco do SistemaCPE

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
