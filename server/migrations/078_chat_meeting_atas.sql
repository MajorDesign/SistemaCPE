-- ============================================================
-- MIGRATION 078: Atas de reuniao com transcript + resumo via LLM
-- Data: 2026-06-26
-- Descricao: Permite gravar transcript de uma reuniao (frases ditas
-- por cada participante via Web Speech API + WebSocket) e, ao
-- encerrar, gerar resumo automatico via Gemini Free Tier.
--
-- Fluxo:
--   1. Host clica "Gravar Ata" -> INSERT status='gravando'
--   2. Cada meeting_caption recebido eh acumulado em memoria
--   3. Host clica "Encerrar Ata" -> UPDATE status='gerando',
--      transcript serializado em JSON, background task chama Gemini
--   4. Sucesso -> status='pronta' + ata_gerada (markdown)
--      Falha   -> status='erro' + erro_msg (transcript bruto fica)
--
-- Acesso: criador (host) sempre ve. Pra MVP, outros pedem o copy-paste.
-- ============================================================

USE cpe_chat;

CREATE TABLE IF NOT EXISTS chat_meeting_atas (
  id                 INT          NOT NULL AUTO_INCREMENT,
  meeting_id         INT          NOT NULL,
  meeting_code       VARCHAR(20)  NOT NULL,           -- snapshot p/ acesso pos-meeting
  meeting_nome       VARCHAR(200) DEFAULT NULL,        -- snapshot
  criada_por_user_id INT          NOT NULL,
  status             ENUM('gravando','gerando','pronta','erro') NOT NULL DEFAULT 'gravando',
  iniciada_em        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finalizada_em      TIMESTAMP    NULL,
  transcript_bruto   MEDIUMTEXT   NULL,                -- JSON array [{at, autor, texto, lang}]
  ata_gerada         MEDIUMTEXT   NULL,                -- markdown final do LLM
  modelo_llm         VARCHAR(64)  NULL,                -- ex: 'gemini-2.0-flash'
  erro_msg           VARCHAR(500) NULL,
  created_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_meeting     (meeting_id),
  KEY idx_criada_por  (criada_por_user_id),
  KEY idx_status      (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
