-- =====================================================================
-- 069_knowledge_base.sql
-- Base de conhecimento por SETOR (cpe_grupo). Cada artigo pertence a
-- um grupo (USER ve so do proprio grupo; ADMIN/TI/MANAGER ve tudo).
--
-- conteudo: markdown (renderizado no frontend via marked.js)
-- categoria: alinhada com os templates engineer-grade
-- views/helpful/unhelpful: metricas leves de relevancia
-- =====================================================================

USE `cpe_plus`;

CREATE TABLE IF NOT EXISTS `kb_articles` (
  `id`             INT          NOT NULL AUTO_INCREMENT,
  `group_id`       INT          NOT NULL COMMENT 'soft ref cpe_grupo.id — setor dono do artigo',
  `titulo`         VARCHAR(255) NOT NULL,
  `resumo`         VARCHAR(500) NULL COMMENT 'resumo curto, derivado das primeiras linhas se vazio',
  `conteudo`       LONGTEXT     NOT NULL COMMENT 'corpo em markdown',
  `categoria`      ENUM('procedimento','tutorial','troubleshooting','faq','politica','onboarding','outros')
                                NOT NULL DEFAULT 'outros',
  `tags`           VARCHAR(255) NULL COMMENT 'separadas por virgula',
  `autor_id`       INT          NOT NULL COMMENT 'soft ref users.id',
  `publicado`      TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '0 = rascunho',
  `views`          INT          NOT NULL DEFAULT 0,
  `helpful`        INT          NOT NULL DEFAULT 0,
  `unhelpful`      INT          NOT NULL DEFAULT 0,
  `criado_em`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `atualizado_em`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_kb_group_pub`  (`group_id`, `publicado`),
  INDEX `idx_kb_categoria`  (`categoria`),
  INDEX `idx_kb_autor`      (`autor_id`),
  FULLTEXT INDEX `ft_kb_busca` (`titulo`, `resumo`, `conteudo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
