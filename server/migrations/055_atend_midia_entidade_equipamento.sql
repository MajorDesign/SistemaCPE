-- =====================================================================
-- 055_atend_midia_entidade_equipamento.sql
-- Inclui 'equipamento' no enum de atend_midia_fotos / atend_midia_videos.
-- Sem isso, INSERTs com entidade='equipamento' caem em string vazia ''
-- (MariaDB sem strict mode), e os GETs retornam vazio.
-- =====================================================================

ALTER TABLE `atend_midia_fotos`
  MODIFY `entidade` ENUM('servico','treinamento','equipamento') NOT NULL;

ALTER TABLE `atend_midia_videos`
  MODIFY `entidade` ENUM('servico','treinamento','equipamento') NOT NULL;

-- Reclassifica registros orfaos (criados antes desta migration quando o
-- backend ja mandava 'equipamento' mas o enum nao aceitava).
-- O nome de arquivo gerado pelo upload tem padrao "<entidade>_<id>_<hex>.<ext>",
-- entao da pra identificar com seguranca pelo prefixo "equipamento_".
UPDATE `atend_midia_fotos`
  SET `entidade` = 'equipamento'
  WHERE `entidade` = ''
    AND `arquivo` LIKE '%/equipamento\\_%';
