-- Migration 103: OTP de primeiro acesso.
--
-- Nova UX de auto-cadastro (2026-09-24): usuario com email @cpetecnologia.com.br
-- recebe codigo de 6 digitos por email e completa o cadastro sozinho, sem
-- passar por aprovacao manual do admin. Esta tabela guarda os OTPs pendentes.
--
-- Regras aplicadas pelo backend (routes/pre_cadastro.py):
--   * expires_at = created_at + 15 min
--   * attempts maximo = 5 (depois disso o OTP eh invalidado e user precisa
--     pedir outro codigo)
--   * used_at NOT NULL => codigo ja foi consumido, nao pode reusar
--   * Rate-limit de emissao: max 3 codigos por email/hora e 10 por IP/hora

-- ATENCAO MariaDB: DATETIME em vez de TIMESTAMP pra evitar o auto
-- ON UPDATE CURRENT_TIMESTAMP que o MariaDB adiciona no primeiro
-- TIMESTAMP NOT NULL da tabela — isso resetaria expires_at a cada
-- UPDATE de attempts, o que quebraria a validacao do OTP.

CREATE TABLE IF NOT EXISTS pre_cadastro_otp (
  id          BIGINT       NOT NULL AUTO_INCREMENT,
  email       VARCHAR(190) NOT NULL,
  code_hash   VARCHAR(64)  NOT NULL COMMENT 'sha256 hex do codigo de 6 digitos',
  attempts    INT          NOT NULL DEFAULT 0,
  expires_at  DATETIME     NOT NULL,
  used_at     DATETIME     NULL DEFAULT NULL,
  ip          VARCHAR(45)  NULL DEFAULT NULL,
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  INDEX idx_email_valid (email, used_at, expires_at),
  INDEX idx_created     (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
