-- =====================================================================
-- Migration 032 — Anexos de imagem em tickets
--
-- Armazena imagens (até ~250kb cada) anexadas a tickets ou comentários
-- diretamente no banco como BLOB. Sem dependência de filesystem.
--
-- Regras:
--   - Se interacao_id IS NULL → anexo da criação do ticket (descrição inicial)
--   - Se interacao_id NOT NULL → anexo vinculado a uma resposta/comentário
--
-- Idempotente: pode rodar múltiplas vezes sem erro.
-- =====================================================================

CREATE TABLE IF NOT EXISTS `ticket_attachments` (
  `id`            INT          NOT NULL AUTO_INCREMENT,
  `ticket_id`     INT          NOT NULL,
  `interacao_id`  INT          DEFAULT NULL  COMMENT 'NULL = anexo da criação; preenchido = anexo de uma interação/resposta',
  `filename`      VARCHAR(255) NOT NULL,
  `mime_type`     VARCHAR(100) NOT NULL,
  `size_bytes`    INT          NOT NULL,
  `content`       LONGBLOB     NOT NULL       COMMENT 'Binário da imagem',
  `uploaded_by`   INT          NOT NULL,
  `uploaded_at`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_ticket`    (`ticket_id`),
  KEY `idx_interacao` (`interacao_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
