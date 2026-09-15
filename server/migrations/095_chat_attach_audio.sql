-- =========================================================
-- 095_chat_attach_audio.sql — chat_attachments aceita audio
-- =========================================================
-- DB: cpe_chat
--
-- Bug detectado por scripts/e2e-audio-upload.mjs (13/14 passing):
-- coluna tipo era ENUM('image'), MySQL convertia 'audio' pra ''.
-- Aditiva; muda ENUM e adiciona duracao_s (nullable, pra imagens fica NULL).

USE cpe_chat;

ALTER TABLE chat_attachments
  MODIFY COLUMN tipo ENUM('image','audio','file') NOT NULL DEFAULT 'image';

ALTER TABLE chat_attachments
  ADD COLUMN duracao_s DECIMAL(6,2) NULL AFTER tamanho;

-- Retro-corrige: attachments que ficaram com tipo='' por causa do bug
-- viram 'audio' se o mime bater com padrao audio.
UPDATE chat_attachments
   SET tipo='audio'
 WHERE tipo=''
   AND (mime LIKE 'audio/%' OR arquivo LIKE '%.webm' OR arquivo LIKE '%.mp3' OR arquivo LIKE '%.m4a' OR arquivo LIKE '%.ogg');

-- Corrige tb registros orfaos: se ficou vazio e nao e audio, joga em 'file'
UPDATE chat_attachments SET tipo='file' WHERE tipo='';
