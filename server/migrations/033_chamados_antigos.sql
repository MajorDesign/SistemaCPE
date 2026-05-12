-- =====================================================================
-- Migration 033 — Chamados Antigos (somente consulta)
--
-- Armazena chamados importados do sistema legado (CSV exportado).
-- A tabela é só de leitura na aplicação — popular via script:
--   python tools/import_chamados_antigos.py
--
-- Idempotente: pode rodar várias vezes.
-- =====================================================================

CREATE TABLE IF NOT EXISTS `chamados_antigos` (
  `id`              INT             NOT NULL AUTO_INCREMENT,
  `trackid`         VARCHAR(50)     NOT NULL    COMMENT 'ID alfanumérico no sistema legado',
  `nome_status`     VARCHAR(50)     DEFAULT NULL,
  `email`           VARCHAR(255)    DEFAULT NULL,
  `solicitante`     VARCHAR(255)    DEFAULT NULL,
  `categoria`       VARCHAR(150)    DEFAULT NULL,
  `prioridade`      VARCHAR(50)     DEFAULT NULL,
  `assunto`         VARCHAR(500)    DEFAULT NULL,
  `aberto_em`       DATETIME        DEFAULT NULL,
  `primeira_resp`   DATETIME        DEFAULT NULL,
  `duracao_pri_resp` INT            DEFAULT NULL  COMMENT 'Minutos até a primeira resposta',
  `fechado_em`      DATETIME        DEFAULT NULL,
  `fechado_por`     VARCHAR(255)    DEFAULT NULL,
  `atribuido_a`     VARCHAR(255)    DEFAULT NULL,
  `mensagem`        MEDIUMTEXT,
  `respondido_por`  VARCHAR(255)    DEFAULT NULL,
  `resposta`        MEDIUMTEXT,
  `dh_resposta`     DATETIME        DEFAULT NULL,
  `created_at`      DATETIME        DEFAULT CURRENT_TIMESTAMP COMMENT 'Data/hora da importação no SistemaCPE',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_trackid`  (`trackid`),
  KEY `idx_aberto_em`      (`aberto_em`),
  KEY `idx_email`          (`email`),
  KEY `idx_solicitante`    (`solicitante`),
  KEY `idx_categoria`      (`categoria`),
  KEY `idx_status`         (`nome_status`),
  FULLTEXT KEY `ft_busca`  (`assunto`, `mensagem`, `solicitante`, `email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
