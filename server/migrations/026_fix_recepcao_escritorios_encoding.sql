-- =====================================================================
-- Migration 026 — Corrige mojibake em recepcao_escritorios
--
-- Os escritórios cadastrados foram inseridos via terminal/phpMyAdmin
-- com encoding errado (UTF-8 lido como cp850), gerando "Escrit├│rio
-- Bar├úo" em vez de "Escritório Barão".
--
-- A conexão MySQL do FastAPI já está com utf8mb4 — novos cadastros
-- gravam corretamente. Este script só conserta os registros antigos.
--
-- IDEMPOTENTE: o UPDATE só atua quando o HEX atual bate exatamente
-- com o mojibake conhecido. Se já foi corrigido manualmente, não faz
-- nada.
--
-- Usamos UNHEX() em ambos os lados pra evitar problemas de encoding
-- na hora de carregar o script (alguns clientes mysql sob Windows
-- convertem caracteres acentuados a "?" no caminho da linha de
-- comando — UNHEX entrega bytes brutos que viram UTF-8 no banco).
-- =====================================================================

-- "Escrit├│rio Bar├úo" (mojibake)  →  "Escritório Barão" (UTF-8 correto)
UPDATE recepcao_escritorios
   SET nome = CONVERT(UNHEX('457363726974C3B372696F20426172C3A36F') USING utf8mb4)
 WHERE HEX(nome) = '457363726974E2949CE2948272696F20426172E2949CC3BA6F';

-- "Escrit├│rio Raja" (mojibake)  →  "Escritório Raja" (UTF-8 correto)
UPDATE recepcao_escritorios
   SET nome = CONVERT(UNHEX('457363726974C3B372696F2052616A61') USING utf8mb4)
 WHERE HEX(nome) = '457363726974E2949CE2948272696F2052616A61';
