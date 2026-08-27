-- ============================================================
-- Migration 090: multi-grupo por usuario
-- ============================================================
-- Contexto: hoje `users.group_id` limita cada usuario a UM unico
-- grupo. Precisamos permitir que um mesmo user participe de N grupos,
-- com role independente por grupo:
--   - Giselle Lins e RESPONSAVEL_GRUPO em "Gente e Gestao" E
--     RESPONSAVEL_GRUPO em "Financeiro"
--   - Outros podem ser RESPONSAVEL num grupo e USER em outro
--
-- Regras de negocio (ver docs/PLANO_MULTIGRUPO.md):
--   - Apenas role global ADMIN pode adicionar/remover grupos de um user
--   - ADMIN e TI seguem GLOBAIS (users.role); nao viram por-grupo
--   - Todo user precisa ter exatamente 1 grupo com is_primary=1
--   - users.group_id continua existindo como cache do grupo primario
--     (retrocompat + queries antigas), sincronizado pela aplicacao
--
-- Truque do is_primary UNIQUE:
--   MariaDB/MySQL nao suportam UNIQUE parcial (WHERE is_primary=1),
--   mas UNIQUE ignora NULL. Entao is_primary e NULLABLE: NULL = nao
--   primary, 1 = primary. UNIQUE(user_id, is_primary) bloqueia 2
--   registros (user_id, 1) mas permite N registros (user_id, NULL).

CREATE TABLE IF NOT EXISTS user_groups (
  user_id      BIGINT       NOT NULL COMMENT 'FK users.id',
  group_id     INT          NOT NULL COMMENT 'FK cpe_grupo.id',
  role_in_grp  ENUM('USER','RESPONSAVEL_GRUPO') NOT NULL DEFAULT 'USER'
               COMMENT 'papel do user NESTE grupo (nao afeta role global)',
  is_primary   TINYINT(1)   NULL DEFAULT NULL
               COMMENT 'NULL=nao primary, 1=primary (UNIQUE ignora NULL)',
  added_by     BIGINT       NULL COMMENT 'quem adicionou (users.id)',
  added_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,

  PRIMARY KEY (user_id, group_id),
  UNIQUE KEY  uk_user_primary (user_id, is_primary),
  KEY         idx_group (group_id),

  CONSTRAINT fk_ug_user     FOREIGN KEY (user_id)  REFERENCES users(id)     ON DELETE CASCADE,
  CONSTRAINT fk_ug_group    FOREIGN KEY (group_id) REFERENCES cpe_grupo(id) ON DELETE CASCADE,
  CONSTRAINT fk_ug_added_by FOREIGN KEY (added_by) REFERENCES users(id)     ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------------------------------------------
-- Backfill: cada user que tem users.group_id vira 1 linha (primary)
-- ----------------------------------------------------------------
INSERT IGNORE INTO user_groups (user_id, group_id, role_in_grp, is_primary, added_by, added_at)
SELECT
  u.id,
  u.group_id,
  CASE WHEN u.role = 'RESPONSAVEL_GRUPO' THEN 'RESPONSAVEL_GRUPO' ELSE 'USER' END,
  1,          -- is_primary=1 pro grupo atual do user
  NULL,       -- added_by: nao rastreamos historico anterior
  u.created_at
FROM users u
WHERE u.group_id IS NOT NULL;
