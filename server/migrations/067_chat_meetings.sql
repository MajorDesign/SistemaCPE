-- =====================================================================
-- 067_chat_meetings.sql
-- Salas de reuniao temporarias estilo Google Meet/Jitsi com link externo.
-- Suporta participantes internos (logados no sistema) E externos (guests
-- que abrem o link sem login, identificados por nome + guest_token).
--
-- Fluxo:
--   1. Host (qualquer user logado) cria sala -> codigo + URL gerados
--   2. Compartilha o link
--   3. Externo abre o link -> digita nome -> entra na SALA DE ESPERA
--   4. Host ve a lista de "aguardando" e clica "Aprovar"
--   5. Externo entra de fato. WebRTC mesh igual ao chat-voice.
--   6. Host pode "Encerrar sala" a qualquer momento.
--
-- WebRTC mesh sem TURN: funciona em mesma rede / IPs publicos. CGNAT
-- pesado pode bloquear. Avisar isso na UI.
-- =====================================================================

USE `cpe_chat`;

CREATE TABLE IF NOT EXISTS `chat_meeting_rooms` (
  `id`            BIGINT       NOT NULL AUTO_INCREMENT,
  `codigo`        VARCHAR(16)  NOT NULL,
  `nome`          VARCHAR(120) NOT NULL,
  `criado_por`    BIGINT       NOT NULL COMMENT 'soft ref cpe_plus.users.id (host)',
  `criado_em`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `encerrada_em`  DATETIME     NULL COMMENT 'NULL = sala ativa; setado quando host encerra',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_meeting_codigo` (`codigo`),
  INDEX `idx_meeting_host` (`criado_por`),
  INDEX `idx_meeting_ativa` (`encerrada_em`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Participantes transient (rastreio em tempo real de quem esta na sala
-- ou aguardando). Mistura users internos (user_id != NULL) e guests
-- externos (user_id IS NULL, guest_name preenchido).
--
-- status:
--   - 'aguardando' : guest pediu pra entrar, esperando host aprovar
--                    (users internos pulam direto pra 'dentro')
--   - 'dentro'     : aprovado e participando ativamente
--   - 'rejeitado'  : host rejeitou (entrada bloqueada)
CREATE TABLE IF NOT EXISTS `chat_meeting_participants` (
  `meeting_id`  BIGINT       NOT NULL,
  `peer_id`     VARCHAR(40)  NOT NULL COMMENT 'UUID gerado client-side pra signaling WebRTC',
  `user_id`     BIGINT       NULL COMMENT 'soft ref cpe_plus.users.id (NULL pra guests)',
  `guest_name`  VARCHAR(80)  NULL COMMENT 'preenchido pra guests externos',
  `guest_token` VARCHAR(64)  NULL COMMENT 'token aleatorio pra autenticar guest no WS',
  `status`      ENUM('aguardando','dentro','rejeitado') NOT NULL DEFAULT 'aguardando',
  `mic_on`      TINYINT(1)   NOT NULL DEFAULT 1,
  `cam_on`      TINYINT(1)   NOT NULL DEFAULT 0,
  `share_on`    TINYINT(1)   NOT NULL DEFAULT 0,
  `entrou_em`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`meeting_id`, `peer_id`),
  INDEX `idx_meetpart_user` (`user_id`),
  INDEX `idx_meetpart_guest_token` (`guest_token`),
  INDEX `idx_meetpart_status` (`status`),
  CONSTRAINT `fk_meetpart_meeting`
    FOREIGN KEY (`meeting_id`) REFERENCES `chat_meeting_rooms`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
