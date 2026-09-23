-- =========================================================
-- 102_packages.sql
-- =========================================================
-- Sprint "Distribuicao de pacotes assinados" (2026-09-23):
--   Novo dominio /api/packages/* pra hospedar arquivos que os clientes
--   Windows (ex: script .bat da VPN) baixam com verificacao SHA256 +
--   token compartilhado.
--
--   Diferente do /api/agents (1 exe auto-instalavel por agente), aqui
--   um "pacote" e uma COLECAO de arquivos versionados juntos (ex:
--   OpenVPN_CPETecnologia.ovpn + CA-CPE-NEW.crt em uma versao).
--
--   Fluxo:
--   1. ADMIN publica nova versao via UI (upload multi-file) -> backend
--      calcula sha256, cria row em package_versions + N package_files,
--      atualiza packages.current_version_id.
--   2. Cliente .bat faz GET /api/packages/{slug}/manifest com token
--      -> recebe JSON {version, files:[{name,url,sha256,size}]}.
--   3. Baixa cada arquivo, confere hash, aplica.
--   4. Envia POST /api/packages/{slug}/log com o resultado.
--
--   Aditiva. Zero mudanca em dados existentes.

USE cpe_plus;

-- =========================================
-- CATALOGO DE PACOTES
-- =========================================
CREATE TABLE IF NOT EXISTS `packages` (
  `id`                    INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `slug`                  VARCHAR(64)  NOT NULL COMMENT 'ID legivel usado nas URLs (ex: vpn-openvpn)',
  `name`                  VARCHAR(120) NOT NULL,
  `description`           VARCHAR(500) NULL,
  `current_version_id`    INT UNSIGNED NULL COMMENT 'FK package_versions.id — versao servida no manifesto',
  `created_at`            DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`            DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                       ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_slug` (`slug`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================
-- VERSOES DE UM PACOTE (historico)
-- =========================================
CREATE TABLE IF NOT EXISTS `package_versions` (
  `id`             INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `package_id`     INT UNSIGNED NOT NULL,
  `version`        VARCHAR(50)  NOT NULL COMMENT 'Ex: 2026.09.23 ou 1.2.0 (livre; slug + version deve ser unico)',
  `notes`          TEXT         NULL     COMMENT 'Changelog opcional preenchido pelo admin ao publicar',
  `manifest_json`  MEDIUMTEXT   NOT NULL COMMENT 'JSON completo do manifesto entregue ao cliente',
  `created_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `created_by`     BIGINT       NULL     COMMENT 'FK users.id (admin que publicou)',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_pkg_version` (`package_id`, `version`),
  KEY `idx_pkg`     (`package_id`),
  CONSTRAINT `fk_ver_pkg`
    FOREIGN KEY (`package_id`) REFERENCES `packages` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- FK circular: packages.current_version_id → package_versions.id
-- Adicionada DEPOIS de package_versions existir. SET NULL se versao for
-- deletada (pouco provavel, mas evita orfanato).
ALTER TABLE `packages`
  ADD CONSTRAINT `fk_pkg_current_ver`
      FOREIGN KEY (`current_version_id`)
      REFERENCES `package_versions` (`id`) ON DELETE SET NULL;

-- =========================================
-- ARQUIVOS DE UMA VERSAO
-- =========================================
CREATE TABLE IF NOT EXISTS `package_files` (
  `id`          INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `version_id`  INT UNSIGNED NOT NULL,
  `filename`    VARCHAR(255) NOT NULL COMMENT 'Nome exposto ao cliente (ex: OpenVPN_CPETecnologia.ovpn)',
  `sha256`      CHAR(64)     NOT NULL COMMENT 'Hex lower-case do SHA256 do conteudo',
  `size_bytes` BIGINT UNSIGNED NOT NULL,
  `disk_path`   VARCHAR(500) NOT NULL COMMENT 'Path absoluto no disco (fora do web root)',
  `position`    INT          NOT NULL DEFAULT 0 COMMENT 'Ordem exibida na UI',
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_ver_filename` (`version_id`, `filename`),
  KEY `idx_version` (`version_id`),
  CONSTRAINT `fk_file_version`
    FOREIGN KEY (`version_id`) REFERENCES `package_versions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================
-- LOGS DE EXECUCAO (telemetria dos clientes .bat)
-- =========================================
CREATE TABLE IF NOT EXISTS `package_execution_logs` (
  `id`             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `package_slug`   VARCHAR(64)   NOT NULL,
  `version`        VARCHAR(50)   NULL     COMMENT 'Versao reportada pelo cliente (pode divergir da atual)',
  `computer`       VARCHAR(120)  NULL     COMMENT 'Hostname do PC que executou',
  `user_login`    VARCHAR(120)  NULL     COMMENT 'DOMAIN\\username reportado pelo bat',
  `success`        TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '1=SUCESSO, 0=FALHA/PARCIAL',
  `log_text`       MEDIUMTEXT    NULL     COMMENT 'Corpo completo do log txt',
  `client_ip`      VARCHAR(45)   NULL,
  `created_at`     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_slug_time` (`package_slug`, `created_at`),
  KEY `idx_success`   (`success`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Telemetria de execucao dos scripts cliente';

-- =========================================
-- SEED do pacote VPN (deixa ele pronto pra receber a 1a versao via UI)
-- =========================================
INSERT INTO `packages` (`slug`, `name`, `description`)
VALUES (
  'vpn-openvpn',
  'VPN OpenVPN — Perfil CPE',
  'Perfil OpenVPN + CA da cadeia nova. Instalador substitui a configuracao local no PC do usuario.'
)
ON DUPLICATE KEY UPDATE `updated_at` = CURRENT_TIMESTAMP;
