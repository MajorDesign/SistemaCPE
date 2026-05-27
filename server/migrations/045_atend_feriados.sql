-- =====================================================================
-- Migration 045 - Feriados das agendas de atendimento
-- =====================================================================
-- Feriado trava o dia inteiro de uma agenda (sem horarios, sem agendamento).
--   agenda_id NULL  -> feriado nacional, vale para TODAS as agendas
--   agenda_id setado -> feriado estadual/municipal, vale so para aquela unidade
-- Os feriados nacionais brasileiros de 2026/2027/2028 ja vem cadastrados.
-- =====================================================================

CREATE TABLE IF NOT EXISTS `atend_feriados` (
  `id`         INT          NOT NULL AUTO_INCREMENT,
  `data`       DATE         NOT NULL,
  `nome`       VARCHAR(150) NOT NULL,
  `agenda_id`  INT          DEFAULT NULL
               COMMENT 'NULL = feriado nacional (todas as agendas)',
  `tipo`       ENUM('nacional','estadual','municipal','outro')
               NOT NULL DEFAULT 'nacional',
  `created_by` INT          DEFAULT NULL,
  `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_feriado_data` (`data`),
  KEY `idx_feriado_agenda` (`agenda_id`),
  CONSTRAINT `fk_feriado_agenda`
    FOREIGN KEY (`agenda_id`) REFERENCES `atend_agendas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  COMMENT='Feriados que travam o dia das agendas de atendimento';

-- Feriados nacionais brasileiros (agenda_id NULL = valem para todas) -----
INSERT INTO `atend_feriados` (`data`, `nome`, `tipo`) VALUES
  -- 2026
  ('2026-01-01', 'Confraternizacao Universal',     'nacional'),
  ('2026-02-17', 'Carnaval',                       'nacional'),
  ('2026-04-03', 'Sexta-feira Santa',              'nacional'),
  ('2026-04-21', 'Tiradentes',                     'nacional'),
  ('2026-05-01', 'Dia do Trabalho',                'nacional'),
  ('2026-06-04', 'Corpus Christi',                 'nacional'),
  ('2026-09-07', 'Independencia do Brasil',        'nacional'),
  ('2026-10-12', 'Nossa Senhora Aparecida',        'nacional'),
  ('2026-11-02', 'Finados',                        'nacional'),
  ('2026-11-15', 'Proclamacao da Republica',       'nacional'),
  ('2026-11-20', 'Dia da Consciencia Negra',       'nacional'),
  ('2026-12-25', 'Natal',                          'nacional'),
  -- 2027
  ('2027-01-01', 'Confraternizacao Universal',     'nacional'),
  ('2027-02-09', 'Carnaval',                       'nacional'),
  ('2027-03-26', 'Sexta-feira Santa',              'nacional'),
  ('2027-04-21', 'Tiradentes',                     'nacional'),
  ('2027-05-01', 'Dia do Trabalho',                'nacional'),
  ('2027-05-27', 'Corpus Christi',                 'nacional'),
  ('2027-09-07', 'Independencia do Brasil',        'nacional'),
  ('2027-10-12', 'Nossa Senhora Aparecida',        'nacional'),
  ('2027-11-02', 'Finados',                        'nacional'),
  ('2027-11-15', 'Proclamacao da Republica',       'nacional'),
  ('2027-11-20', 'Dia da Consciencia Negra',       'nacional'),
  ('2027-12-25', 'Natal',                          'nacional'),
  -- 2028
  ('2028-01-01', 'Confraternizacao Universal',     'nacional'),
  ('2028-02-29', 'Carnaval',                       'nacional'),
  ('2028-04-14', 'Sexta-feira Santa',              'nacional'),
  ('2028-04-21', 'Tiradentes',                     'nacional'),
  ('2028-05-01', 'Dia do Trabalho',                'nacional'),
  ('2028-06-15', 'Corpus Christi',                 'nacional'),
  ('2028-09-07', 'Independencia do Brasil',        'nacional'),
  ('2028-10-12', 'Nossa Senhora Aparecida',        'nacional'),
  ('2028-11-02', 'Finados',                        'nacional'),
  ('2028-11-15', 'Proclamacao da Republica',       'nacional'),
  ('2028-11-20', 'Dia da Consciencia Negra',       'nacional'),
  ('2028-12-25', 'Natal',                          'nacional');
