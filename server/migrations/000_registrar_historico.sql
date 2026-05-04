-- =============================================================
-- Registra no _migrations_log todas as migrations que já foram
-- aplicadas manualmente no servidor antes do deploy automatizado.
-- Execute UMA VEZ no servidor de produção após criar a tabela
-- _migrations_log, antes de usar o deploy.sh.
-- =============================================================

USE cpe_plus;

CREATE TABLE IF NOT EXISTS _migrations_log (
  nome VARCHAR(100) PRIMARY KEY,
  aplicada_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Lista das migrations já aplicadas manualmente no servidor.
-- Ajuste conforme o histórico real do seu servidor de produção.
INSERT IGNORE INTO _migrations_log (nome) VALUES
  ('001_sla_primeira_resposta.sql'),
  ('001_tarefa_encaminhamentos.sql'),
  ('002_contratos.sql'),
  ('002_finalizar_reabrir.sql'),
  ('003_fleet.sql'),
  ('003_producao_sync.sql'),
  ('004_fleet_angulos.sql'),
  ('005_checklist_photos.sql'),
  ('006_checklist_workflow.sql'),
  ('007_devolucao_manutencao.sql'),
  ('008_maintenance_types_files.sql'),
  ('009_km_alerts.sql'),
  ('010_reservations.sql'),
  ('011_contratos.sql'),
  ('012_cofre_senhas.sql'),
  ('013_vault_pin.sql'),
  ('014_recepcao.sql'),
  ('014b_recepcao_fix.sql'),
  ('014c_recepcao_consolidada.sql'),
  ('015_recepcao_convidados.sql'),
  ('016_recepcao_escritorios.sql'),
  ('017_recepcao_envio_eventos.sql'),
  ('018_recepcao_cache_rastreio.sql'),
  ('019_recepcao_confirmacao_pre_reuniao.sql'),
  ('020_agenda_carbonio.sql'),
  ('021_agenda_lembretes.sql'),
  ('000_registrar_historico.sql');

SELECT nome, aplicada_em FROM _migrations_log ORDER BY aplicada_em;
