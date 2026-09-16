-- =========================================================
-- 097_ticket_setores_envolvidos.sql
-- =========================================================
-- Sprint "Memoria de setores envolvidos" (2026-09-16):
--   Ate hoje, um ticket carrega apenas o group_id ATUAL. Quando ele e
--   encaminhado (ex: faturamento -> financeiro), o setor original perde
--   acesso — o UPDATE sobrescreve a coluna e ninguem mais consegue voltar
--   pra consultar o historico. Se quem cuidou do chamado sai da empresa
--   e e desativado, ninguem mais no setor original consegue ver.
--
--   Esta migration adiciona uma tabela de LINHA DO TEMPO de setores
--   envolvidos, populada em cada criacao/encaminhamento. A regra de
--   visibilidade (user_pode_ver_ticket) usa esta tabela pra ampliar o
--   acesso pros setores que ja participaram do ticket, mesmo apos ele
--   ter saido de la.
--
-- Ver: docs/REGRAS_NEGOCIO.md "Memoria de setores envolvidos".
-- Aditiva. Backfill retroativo popula o setor atual como historico inicial.

USE cpe_plus;

CREATE TABLE IF NOT EXISTS ticket_setores_envolvidos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  ticket_id BIGINT UNSIGNED NOT NULL,
  group_id INT NOT NULL,
  entrou_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  saiu_em TIMESTAMP NULL,
  motivo VARCHAR(400) NULL,
  encaminhado_por INT NULL COMMENT 'user_id que encaminhou pra este setor (NULL na criacao)',
  KEY idx_tse_ticket (ticket_id),
  KEY idx_tse_group (group_id),
  KEY idx_tse_group_saiu (group_id, saiu_em),
  CONSTRAINT fk_tse_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Backfill retroativo: cria uma linha "aberta" (saiu_em=NULL) por ticket
-- existente que ainda nao tenha registro. Assim a linha do tempo dos
-- antigos comeca com o estado corrente e vai crescendo a partir dos
-- proximos encaminhamentos.
INSERT INTO ticket_setores_envolvidos (ticket_id, group_id, entrou_em, saiu_em)
SELECT t.id, t.group_id, t.created_at, NULL
  FROM tickets t
 WHERE t.group_id IS NOT NULL
   AND NOT EXISTS (
     SELECT 1 FROM ticket_setores_envolvidos tse WHERE tse.ticket_id = t.id
   );
