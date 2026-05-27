-- =====================================================================
-- Migration 046 - Tipo da agenda de atendimento (fisica / online)
-- =====================================================================
-- Distingue agendas que representam uma UNIDADE FISICA (Salvador, BH...)
-- de uma agenda VIRTUAL ONLINE (atendimento remoto, sem unidade fisica).
--
-- No fluxo publico (agendar.html):
--   - Cliente escolhe primeiro: presencial ou online
--   - Presencial: ve os cards das agendas tipo='fisica' e escolhe a unidade
--   - Online: cai direto na primeira agenda tipo='online' (sem precisar
--     escolher unidade, pois nao importa pra atendimento remoto)
--
-- Decisao tomada com o usuario: criar UMA agenda 'CPETecnologia Online'
-- dedicada, em vez de agregar capacidade online de varias unidades.
-- =====================================================================

ALTER TABLE `atend_agendas`
  ADD COLUMN `tipo` ENUM('fisica','online') NOT NULL DEFAULT 'fisica'
      COMMENT 'fisica = unidade CPE | online = atendimento remoto'
      AFTER `unidade_id`,
  ADD KEY `idx_atend_agenda_tipo` (`tipo`);
