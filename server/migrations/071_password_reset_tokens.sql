-- =====================================================================
-- 071_password_reset_tokens.sql
-- Tabela para tokens de "Esqueci minha senha".
-- Cada solicitacao gera um token de 64 chars (uuid4 hex) com expiracao
-- de 1 hora. Token e single-use: marca used_at ao trocar a senha.
-- =====================================================================

USE `cpe_plus`;

CREATE TABLE IF NOT EXISTS `password_reset_tokens` (
  `id`         INT          NOT NULL AUTO_INCREMENT,
  `user_id`    INT          NOT NULL COMMENT 'FK soft pra users.id',
  `token`      CHAR(64)     NOT NULL COMMENT 'hex de uuid4 (sem traços)',
  `expires_at` DATETIME     NOT NULL COMMENT 'criado_em + 1h',
  `criado_em`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `used_at`    DATETIME     NULL     DEFAULT NULL COMMENT 'preenchido quando o token e usado',
  `ip_origem`  VARCHAR(45)  NULL     DEFAULT NULL COMMENT 'IP que solicitou (audit)',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_token` (`token`),
  INDEX `idx_user` (`user_id`),
  INDEX `idx_expires` (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
