-- =====================================================================
-- Migration 041 — Campos personalizados obrigatórios por categoria
--
-- Permite que cada categoria (ou subcategoria) defina campos extras que
-- o solicitante deve preencher ao abrir um ticket. Ex: a categoria
-- "Troca de equipamento" pode exigir "Patrimônio do equipamento".
--
-- categoria_campos      — definição dos campos (label, tipo, obrigatório)
-- ticket_campo_valores  — o que o usuário preencheu em cada ticket
--
-- Tipos suportados: texto, numero, data.
-- Idempotente.
-- =====================================================================

CREATE TABLE IF NOT EXISTS `categoria_campos` (
  `id`              INT          NOT NULL AUTO_INCREMENT,
  `categoria_id`    INT UNSIGNED DEFAULT NULL,
  `subcategoria_id` INT UNSIGNED DEFAULT NULL,
  `label`           VARCHAR(150) NOT NULL          COMMENT 'Rótulo do campo exibido no formulário',
  `tipo`            ENUM('texto','numero','data')  NOT NULL DEFAULT 'texto',
  `obrigatorio`     TINYINT(1)   NOT NULL DEFAULT 1,
  `ordem`           INT          NOT NULL DEFAULT 0,
  `ativo`           TINYINT(1)   NOT NULL DEFAULT 1,
  `created_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                 ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_categoria`    (`categoria_id`),
  KEY `idx_subcategoria` (`subcategoria_id`),
  KEY `idx_ativo`        (`ativo`),
  CONSTRAINT `fk_campo_categoria`
    FOREIGN KEY (`categoria_id`)    REFERENCES `categorias` (`id`)    ON DELETE CASCADE,
  CONSTRAINT `fk_campo_subcategoria`
    FOREIGN KEY (`subcategoria_id`) REFERENCES `subcategorias` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Campos personalizados que uma categoria/subcategoria exige no ticket';

CREATE TABLE IF NOT EXISTS `ticket_campo_valores` (
  `id`         INT             NOT NULL AUTO_INCREMENT,
  `ticket_id`  BIGINT UNSIGNED NOT NULL,
  `campo_id`   INT             NOT NULL,
  `valor`      TEXT            DEFAULT NULL,
  `created_at` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_ticket` (`ticket_id`),
  KEY `idx_campo`  (`campo_id`),
  CONSTRAINT `fk_valor_ticket`
    FOREIGN KEY (`ticket_id`) REFERENCES `tickets` (`id`)            ON DELETE CASCADE,
  CONSTRAINT `fk_valor_campo`
    FOREIGN KEY (`campo_id`)  REFERENCES `categoria_campos` (`id`)   ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Valores preenchidos pelo solicitante nos campos personalizados';
