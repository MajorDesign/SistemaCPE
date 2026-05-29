-- =====================================================================
-- 060_chat_push_subscriptions.sql
-- Web Push subscriptions (browser/PWA). Cada user pode ter varias
-- (desktop chrome, celular chrome, celular safari pwa, etc).
-- endpoint e UNIQUE pra suportar upsert idempotente.
-- =====================================================================

USE `cpe_chat`;

CREATE TABLE IF NOT EXISTS `chat_push_subscriptions` (
  `id`         BIGINT       NOT NULL AUTO_INCREMENT,
  `user_id`    BIGINT       NOT NULL COMMENT 'soft ref cpe_plus.users.id',
  `endpoint`   VARCHAR(512) NOT NULL COMMENT 'URL unica retornada pelo push service',
  `p256dh`     VARCHAR(255) NOT NULL,
  `auth`       VARCHAR(255) NOT NULL,
  `criado_em`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `ultimo_uso` DATETIME     NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_push_endpoint` (`endpoint`),
  INDEX `idx_push_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
