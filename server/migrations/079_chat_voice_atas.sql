-- ============================================================
-- MIGRATION 079: Ata de sessao em canal de voz do chat
-- Data: 2026-06-26
-- Descricao: Permite gravar ata por SESSAO do canal de voz (cada
-- vez que o canal esvazia e enche de novo eh uma nova ata). Quem
-- cria o canal define se a ata fica DISPONIVEL pra esse canal;
-- o primeiro user que entra decide se vai ATIVAR a gravacao da
-- sessao atual. So quem iniciou pode parar manualmente; auto-encerra
-- quando o canal esvazia.
--
-- Resumo via Gemini Free Tier (gemini-flash-latest).
-- ============================================================

USE cpe_chat;

-- 1) Flag no canal indicando se ata eh OFERECIDA pros usuarios
ALTER TABLE chat_channels
  ADD COLUMN ata_habilitada TINYINT(1) NOT NULL DEFAULT 0
  COMMENT 'Se 1, primeiro user que entra no canal recebe popup pra iniciar ata';

-- 2) Tabela de atas (1 linha por sessao)
CREATE TABLE IF NOT EXISTS chat_voice_atas (
  id                   INT          NOT NULL AUTO_INCREMENT,
  canal_id             INT          NOT NULL,
  canal_nome           VARCHAR(120) DEFAULT NULL,   -- snapshot pra exibir depois
  iniciada_por_user_id INT          NOT NULL,
  status               ENUM('gravando','gerando','pronta','erro') NOT NULL DEFAULT 'gravando',
  iniciada_em          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finalizada_em        TIMESTAMP    NULL,
  transcript_bruto     MEDIUMTEXT   NULL,    -- JSON array [{at, autor, texto, lang, peer_id}]
  ata_gerada           MEDIUMTEXT   NULL,    -- markdown final do LLM
  modelo_llm           VARCHAR(64)  NULL,
  erro_msg             VARCHAR(500) NULL,
  created_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_canal         (canal_id, iniciada_em),
  KEY idx_iniciada_por  (iniciada_por_user_id),
  KEY idx_status        (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
