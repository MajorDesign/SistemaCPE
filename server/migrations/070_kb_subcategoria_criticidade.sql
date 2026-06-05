-- =====================================================================
-- 070_kb_subcategoria_criticidade.sql
-- Adiciona estrutura visual rica aos artigos da Base de Conhecimento:
--   - subcategoria: refinamento livre da categoria (ex: "Redes" dentro de TI)
--   - criticidade: nivel de importancia/urgencia do artigo (badge colorido)
--   - capa_icon:  emoji ou bootstrap-icon mostrado em destaque na capa
--   - capa_cor:   cor primaria da capa em HEX (gradient da capa)
-- =====================================================================

USE `cpe_plus`;

ALTER TABLE `kb_articles`
  ADD COLUMN `subcategoria` VARCHAR(80) NULL COMMENT 'refinamento livre da categoria' AFTER `categoria`,
  ADD COLUMN `criticidade`  ENUM('baixa','media','alta','critica') NOT NULL DEFAULT 'media' COMMENT 'badge colorido na capa' AFTER `subcategoria`,
  ADD COLUMN `capa_icon`    VARCHAR(40) NULL DEFAULT 'bi-book' COMMENT 'bootstrap-icon classe ou emoji' AFTER `criticidade`,
  ADD COLUMN `capa_cor`     VARCHAR(7)  NULL DEFAULT '#FFC107' COMMENT 'cor HEX primaria da capa' AFTER `capa_icon`,
  ADD INDEX `idx_kb_criticidade` (`criticidade`);
