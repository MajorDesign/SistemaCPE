-- ============================================================
-- Migration 089: restricao de categorias por membro do grupo
-- ============================================================
-- Contexto: responsavel do grupo (RESPONSAVEL_GRUPO) pode restringir
-- quais categorias/subcategorias cada membro (USER) do grupo dele
-- consegue ver na lista de tickets.
--
-- Modelo:
--   - user_id       : membro do grupo (users.id, role=USER geralmente)
--   - group_id      : grupo (redundante com users.group_id, mas util
--                     pra filtro rapido e integridade caso o user
--                     mude de grupo — nova config nao vaza)
--   - categoria_id  : categoria alvo
--   - subcategoria_id: NULL = categoria toda; preenchido = so essa subcat
--
-- Regra de leitura (aplicada em obter_tickets):
--   - Se o USER tem 0 linhas aqui  -> ve tudo do grupo (default atual)
--   - Se tem 1+ linhas             -> so ve tickets que caem em alguma
--     das linhas dele + os proprios (solicitante_id = ele)
--
-- ADMIN, TI, MANAGER, RESPONSAVEL_GRUPO NAO sao afetados por esta
-- tabela — eles enxergam tudo do proprio escopo, sem filtro.

CREATE TABLE IF NOT EXISTS ticket_membro_categorias (
  id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id          BIGINT           NOT NULL COMMENT 'membro do grupo (users.id)',
  group_id         INT              NOT NULL COMMENT 'grupo do membro na hora da config',
  categoria_id     INT UNSIGNED     NOT NULL,
  subcategoria_id  INT UNSIGNED     NULL COMMENT 'NULL = categoria inteira',
  created_by       BIGINT           NOT NULL COMMENT 'quem configurou (responsavel/admin)',
  created_at       TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_tmc_user_cat_subcat (user_id, categoria_id, subcategoria_id),
  INDEX idx_tmc_group_user (group_id, user_id),
  INDEX idx_tmc_categoria  (categoria_id),
  INDEX idx_tmc_subcat     (subcategoria_id),
  CONSTRAINT fk_tmc_user     FOREIGN KEY (user_id)     REFERENCES users(id)     ON DELETE CASCADE,
  CONSTRAINT fk_tmc_group    FOREIGN KEY (group_id)    REFERENCES cpe_grupo(id) ON DELETE CASCADE,
  CONSTRAINT fk_tmc_cat      FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE CASCADE,
  CONSTRAINT fk_tmc_subcat   FOREIGN KEY (subcategoria_id) REFERENCES subcategorias(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
