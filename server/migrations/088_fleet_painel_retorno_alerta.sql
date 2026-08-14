-- ============================================================
-- Migration 088: alerta de painel no checklist de retorno
-- ============================================================
-- Descricao: adiciona colunas pra armazenar o resultado da analise
-- automatica da foto do painel no checklist de RETORNO.
--
-- Contexto: quando o condutor tira a foto do painel no retorno, o
-- backend roda OCR (Tesseract) pra extrair o KM e comparar com
-- km_saida. Se o KM parece nao ter mudado ou a foto esta ilegivel,
-- grava um alerta aqui pro vistoriador ficar ciente. NAO bloqueia
-- o upload — so gera aviso.
--
-- retorno_painel_alerta: texto curto explicando o alerta (NULL = ok)
-- retorno_painel_km_ocr: KM que o OCR conseguiu extrair (NULL = ilegivel)

ALTER TABLE fleet_checklists
  ADD COLUMN retorno_painel_alerta VARCHAR(300) NULL
    COMMENT 'Alerta automatico sobre a foto do painel do retorno (NULL=ok)',
  ADD COLUMN retorno_painel_km_ocr INT NULL
    COMMENT 'KM extraido do painel via OCR (NULL=nao leu)';
