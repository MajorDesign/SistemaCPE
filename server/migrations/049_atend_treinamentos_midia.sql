-- =====================================================================
-- Migration 049 - Treinamentos, descricoes, vendedor padrao e galeria
-- =====================================================================
-- Pedido do usuario:
--   1. Equipamento ganha campo descricao.
--   2. Curso ganha descricao + vendedor padrao (FK users OU nome livre).
--   3. Nova tabela `atend_treinamentos` (estrutura espelho de atend_servicos
--      pra catalogar treinamentos — presenciais/online).
--   4. Galeria de fotos (upload) + lista de videos (URLs) — polimorfica,
--      vale pra curso e pra treinamento.
--
-- Vendedor padrao do curso/treinamento e SOBRESCRITIVEL no agendamento:
-- a equipe pode trocar caso esteja de ferias, etc.
-- =====================================================================

-- 1) Descricao no equipamento ----------------------------------------
ALTER TABLE `atend_equipamentos`
  ADD COLUMN `descricao` TEXT NULL
      COMMENT 'Descricao do equipamento (visivel no cliente)'
      AFTER `nome`;

-- 2) Descricao + vendedor padrao no curso ----------------------------
ALTER TABLE `atend_servicos`
  ADD COLUMN `descricao` TEXT NULL
      COMMENT 'Descricao do curso (visivel no cliente)'
      AFTER `nome`,
  ADD COLUMN `vendedor_id` BIGINT NULL
      COMMENT 'FK users — vendedor padrao (sobrescritivel no agendamento)'
      AFTER `instrutor`,
  ADD COLUMN `vendedor_nome` VARCHAR(150) NULL
      COMMENT 'Nome livre do vendedor quando ele ainda nao tem cadastro'
      AFTER `vendedor_id`,
  ADD KEY `idx_servico_vendedor` (`vendedor_id`),
  ADD CONSTRAINT `fk_servico_vendedor`
      FOREIGN KEY (`vendedor_id`) REFERENCES `users`(`id`) ON DELETE SET NULL;

-- 3) Treinamentos -----------------------------------------------------
-- Estrutura espelho de atend_servicos. Pode ser agendado pelo publico
-- (mesma logica de capacidade presencial/online).
CREATE TABLE IF NOT EXISTS `atend_treinamentos` (
  `id`             INT          NOT NULL AUTO_INCREMENT,
  `agenda_id`      INT          NOT NULL,
  `nome`           VARCHAR(150) NOT NULL,
  `descricao`      TEXT         NULL,
  `duracao_min`    INT          NOT NULL DEFAULT 60,
  `cap_presencial` INT          NOT NULL DEFAULT 1,
  `cap_online`     INT          NOT NULL DEFAULT 1,
  `instrutor`      VARCHAR(150) NULL COMMENT 'Quem ministra',
  `vendedor_id`    BIGINT       NULL,
  `vendedor_nome`  VARCHAR(150) NULL,
  `ativo`          TINYINT(1)   NOT NULL DEFAULT 1,
  `ordem`          INT          NOT NULL DEFAULT 0,
  `created_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_treino_agenda` (`agenda_id`),
  KEY `idx_treino_vendedor` (`vendedor_id`),
  KEY `idx_treino_ativo` (`ativo`),
  CONSTRAINT `fk_treino_agenda`
    FOREIGN KEY (`agenda_id`) REFERENCES `atend_agendas`(`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_treino_vendedor`
    FOREIGN KEY (`vendedor_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Treinamentos oferecidos (similar a curso, mas categoria propria)';

-- 4) Galeria de fotos polimorfica ------------------------------------
-- entidade='servico'   -> entidade_id referencia atend_servicos.id
-- entidade='treinamento' -> entidade_id referencia atend_treinamentos.id
-- Sem FK (polimorfica), cleanup feito pela aplicacao quando a entidade e excluida.
CREATE TABLE IF NOT EXISTS `atend_midia_fotos` (
  `id`           INT          NOT NULL AUTO_INCREMENT,
  `entidade`     ENUM('servico','treinamento') NOT NULL,
  `entidade_id`  INT          NOT NULL,
  `arquivo`      VARCHAR(255) NOT NULL
                 COMMENT 'Caminho relativo: /SistemaCPE/web/uploads/atendimentos/<file>',
  `ordem`        INT          NOT NULL DEFAULT 0,
  `created_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_fotos_entidade` (`entidade`, `entidade_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Fotos de cursos/treinamentos (galeria publica)';

-- 5) Videos (links externos) -----------------------------------------
CREATE TABLE IF NOT EXISTS `atend_midia_videos` (
  `id`           INT          NOT NULL AUTO_INCREMENT,
  `entidade`     ENUM('servico','treinamento') NOT NULL,
  `entidade_id`  INT          NOT NULL,
  `url`          VARCHAR(500) NOT NULL COMMENT 'URL externa: YouTube, Vimeo, Drive...',
  `titulo`       VARCHAR(150) NULL,
  `ordem`        INT          NOT NULL DEFAULT 0,
  `created_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_videos_entidade` (`entidade`, `entidade_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Videos (links externos) de cursos/treinamentos';
