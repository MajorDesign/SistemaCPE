-- =========================================================
-- 099_discord_links.sql
-- =========================================================
-- Sprint "Bot Discord" (2026-09-22):
--   Bot do Discord (novo servico CPEControlBot no CPEDC22) precisa
--   saber "esse Discord user esta linkado a qual user do CPE Control"
--   pra abrir e consultar chamados em nome dele.
--
--   Fluxo de vinculacao:
--   1. User no Discord: /vincular email:jonathan.lopes@cpetecnologia.com.br
--   2. Bot chama POST /api/discord/link/challenge {discord_id, email}
--      -> backend valida email existe em users, gera codigo 6 digitos,
--         insere em discord_link_challenges (TTL 15min), envia email
--   3. User confere email, volta ao Discord: /vincular-confirmar 123456
--   4. Bot chama POST /api/discord/link/verify {discord_id, code}
--      -> backend consuma challenge (marca used_at) e insere/atualiza
--         discord_links
--
-- Aditiva. Zero impacto em dados existentes.

USE cpe_plus;

-- users.id e BIGINT(20) signed neste schema (nao INT UNSIGNED como
-- assumimos inicialmente). FK exige tipos identicos, entao usamos BIGINT.
CREATE TABLE IF NOT EXISTS `discord_links` (
  `discord_id`  VARCHAR(32)   NOT NULL COMMENT 'Snowflake do user no Discord (18-20 digitos)',
  `user_id`     BIGINT(20)    NOT NULL COMMENT 'FK users.id — a quem o Discord user esta vinculado',
  `verified_at` DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_seen`   DATETIME      NULL COMMENT 'Ultima interacao do bot com este user (updated pelo POST /session)',
  PRIMARY KEY (`discord_id`),
  UNIQUE KEY `uk_discord_user` (`user_id`),
  CONSTRAINT `fk_discord_user`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Vinculo Discord user -> CPE Control user (1:1)';

CREATE TABLE IF NOT EXISTS `discord_link_challenges` (
  `code`       VARCHAR(6)   NOT NULL COMMENT 'Codigo numerico de 6 digitos (gerado pelo backend)',
  `discord_id` VARCHAR(32)  NOT NULL,
  `email`      VARCHAR(190) NOT NULL COMMENT 'Email do CPE user pra quem o codigo foi enviado',
  `expires_at` DATETIME     NOT NULL COMMENT 'TTL 15min a partir de created_at',
  `used_at`    DATETIME     NULL,
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`code`),
  KEY `idx_discord`   (`discord_id`),
  KEY `idx_expires`   (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Codigos temporarios pra vincular Discord user -> CPE user';
