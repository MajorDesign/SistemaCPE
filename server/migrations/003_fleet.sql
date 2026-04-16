-- ============================================================
-- MÓDULO DE FROTAS - Migration 003
-- Data: 2026-04-15
-- Descrição: Tabelas para gestão de frota de veículos,
--            checklists de saída/retorno e registros de custos
-- ============================================================

USE cpe_plus;

-- ============================================================
-- GRUPO DE FROTAS
-- ============================================================
-- Inserir grupo Frotas na tabela cpe_grupo
INSERT IGNORE INTO cpe_grupo (name, description) VALUES ('Frotas', 'Grupo responsável pela gestão da frota de veículos');

-- ============================================================
-- TABELA: fleet_vehicles (Cadastro de veículos)
-- ============================================================
CREATE TABLE IF NOT EXISTS fleet_vehicles (
  id          INT PRIMARY KEY AUTO_INCREMENT,
  placa       VARCHAR(10)  NOT NULL UNIQUE COMMENT 'Ex: ABC-1234 ou ABC1D23',
  modelo      VARCHAR(100) NOT NULL,
  tipo        ENUM('carro','pickup','van','caminhao','moto') DEFAULT 'carro',
  ano         INT,
  cor         VARCHAR(50),
  unidade     VARCHAR(100) COMMENT 'Ex: CPE BH, CPE SP, CPE PE',
  status      ENUM('ativo','em_viagem','manutencao','inativo') DEFAULT 'ativo',
  created_by  BIGINT,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABELA: fleet_vehicle_photos (Histórico de fotos de referência)
-- ============================================================
-- A primeira foto enviada é a foto de referência.
-- Quando substituída, o registro antigo mantém is_current=0
-- e registra quem substituiu, quando e por quê (auditoria).
CREATE TABLE IF NOT EXISTS fleet_vehicle_photos (
  id                       INT PRIMARY KEY AUTO_INCREMENT,
  vehicle_id               INT NOT NULL,
  foto_path                VARCHAR(500) NOT NULL,
  is_current               TINYINT(1) DEFAULT 1 COMMENT '1=foto atual, 0=histórico',
  substituida_por_user_id  BIGINT       COMMENT 'Usuário que fez a substituição',
  motivo_substituicao      TEXT         COMMENT 'Motivo da troca de foto',
  created_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (vehicle_id)              REFERENCES fleet_vehicles(id) ON DELETE CASCADE,
  FOREIGN KEY (substituida_por_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABELA: fleet_checklists (Checklists de saída e retorno)
-- ============================================================
-- Cada registro representa uma saída completa (saída + retorno).
-- O checklist digital representa o formulário físico da CPE.
CREATE TABLE IF NOT EXISTS fleet_checklists (
  id          INT PRIMARY KEY AUTO_INCREMENT,
  vehicle_id  INT NOT NULL,
  condutor_id BIGINT NOT NULL,
  destino     VARCHAR(200),

  -- SAÍDA
  data_saida              DATE,
  horario_saida           TIME,
  km_saida                INT,
  nivel_combustivel_saida TINYINT COMMENT '0=E, 8=F (8 níveis)',
  liberador_id            BIGINT  COMMENT 'Quem liberou o veículo',
  assinatura_liberador    MEDIUMTEXT COMMENT 'Base64 do canvas de assinatura',
  assinatura_condutor_saida MEDIUMTEXT,

  -- RETORNO
  data_retorno              DATE,
  horario_retorno           TIME,
  km_retorno                INT,
  nivel_combustivel_retorno TINYINT,
  recebedor_id              BIGINT COMMENT 'Quem recebeu o veículo de volta',
  assinatura_recebedor      MEDIUMTEXT,
  assinatura_condutor_retorno MEDIUMTEXT,

  observacoes TEXT,

  -- STATUS DO CHECKLIST
  status ENUM(
    'aguardando_aprovacao',
    'aprovado',
    'em_viagem',
    'retornado',
    'cancelado'
  ) DEFAULT 'aguardando_aprovacao',

  aprovado_por BIGINT,
  aprovado_em  TIMESTAMP NULL,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  FOREIGN KEY (vehicle_id)   REFERENCES fleet_vehicles(id),
  FOREIGN KEY (condutor_id)  REFERENCES users(id),
  FOREIGN KEY (liberador_id) REFERENCES users(id) ON DELETE SET NULL,
  FOREIGN KEY (recebedor_id) REFERENCES users(id) ON DELETE SET NULL,
  FOREIGN KEY (aprovado_por) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABELA: fleet_checklist_problems (Itens com problema)
-- ============================================================
-- Registra quais itens do checklist apresentaram problema.
-- Items possíveis: Farol Esq, Farol Dir, Luz de freio,
-- Lanterna Esq, Lanterna Dir, Ar condicionado,
-- Seta Esq, Seta Dir, Limpador parabrisa,
-- Vidros elétricos, Rádio, Indicadores painel,
-- Buzina, Limpeza exterior, Limpeza interior, Outros
CREATE TABLE IF NOT EXISTS fleet_checklist_problems (
  id                   INT PRIMARY KEY AUTO_INCREMENT,
  checklist_id         INT NOT NULL,
  item_nome            VARCHAR(100) NOT NULL,
  descricao_adicional  TEXT COMMENT 'Usado para o item "Outros"',
  foto_path            VARCHAR(500),
  created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (checklist_id) REFERENCES fleet_checklists(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- TABELA: fleet_trips (Registros de viagens e custos)
-- ============================================================
-- Registra os custos de cada utilização do veículo
-- (equivalente às linhas da planilha atual).
CREATE TABLE IF NOT EXISTS fleet_trips (
  id                   INT PRIMARY KEY AUTO_INCREMENT,
  vehicle_id           INT NOT NULL,
  checklist_id         INT  COMMENT 'Checklist associado (opcional)',
  condutor_id          BIGINT,
  unidade              VARCHAR(100) COMMENT 'Ex: CPE BH, CPE SP',
  descricao            VARCHAR(200),
  data_saida           DATE NOT NULL,
  data_retorno         DATE,
  km_inicial           INT DEFAULT 0,
  km_final             INT DEFAULT 0,
  custo_aluguel        DECIMAL(10,2) DEFAULT 0,
  custo_telemetria     DECIMAL(10,2) DEFAULT 0,
  custo_estacionamento DECIMAL(10,2) DEFAULT 0,
  custo_pedagio        DECIMAL(10,2) DEFAULT 0,
  custo_manutencao     DECIMAL(10,2) DEFAULT 0,
  custo_combustivel    DECIMAL(10,2) DEFAULT 0,
  custo_outros         DECIMAL(10,2) DEFAULT 0,
  observacoes          TEXT,
  created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (vehicle_id)   REFERENCES fleet_vehicles(id),
  FOREIGN KEY (checklist_id) REFERENCES fleet_checklists(id) ON DELETE SET NULL,
  FOREIGN KEY (condutor_id)  REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- DADOS DE DEMONSTRAÇÃO
-- ============================================================

-- Veículos
INSERT IGNORE INTO fleet_vehicles (placa, modelo, tipo, ano, cor, unidade, status) VALUES
('ABC-1234', 'HB20',    'carro',   2022, 'Branco', 'CPE BH', 'ativo'),
('DEF-5678', 'Strada',  'pickup',  2021, 'Prata',  'CPE SP', 'ativo'),
('GHI-9012', 'Spin',    'van',     2023, 'Branco', 'CPE BH', 'ativo'),
('JKL-3456', 'Corolla', 'carro',   2020, 'Preto',  'CPE PE', 'ativo'),
('MNO-7890', 'S10',     'pickup',  2022, 'Prata',  'CPE BA', 'ativo'),
('PQR-1122', 'Onix',    'carro',   2023, 'Vermelho','CPE SP','ativo');

-- Viagens de demonstração (dados de jan-abr 2026)
INSERT IGNORE INTO fleet_trips
  (vehicle_id, unidade, data_saida, data_retorno, km_inicial, km_final,
   custo_aluguel, custo_telemetria, custo_pedagio, custo_combustivel, custo_outros)
SELECT v.id, v.unidade,
  DATE_SUB(CURDATE(), INTERVAL 90 DAY), DATE_SUB(CURDATE(), INTERVAL 85 DAY),
  45000, 45700, 2386.95, 81.00, 14.95, 0, 0
FROM fleet_vehicles v WHERE v.placa = 'ABC-1234' LIMIT 1;

INSERT IGNORE INTO fleet_trips
  (vehicle_id, unidade, data_saida, data_retorno, km_inicial, km_final,
   custo_aluguel, custo_telemetria, custo_pedagio, custo_combustivel, custo_manutencao)
SELECT v.id, v.unidade,
  DATE_SUB(CURDATE(), INTERVAL 60 DAY), DATE_SUB(CURDATE(), INTERVAL 55 DAY),
  31870, 32870, 3670.44, 81.00, 14.95, 578.18, 0
FROM fleet_vehicles v WHERE v.placa = 'DEF-5678' LIMIT 1;

INSERT IGNORE INTO fleet_trips
  (vehicle_id, unidade, data_saida, data_retorno, km_inicial, km_final,
   custo_aluguel, custo_telemetria, custo_pedagio, custo_combustivel)
SELECT v.id, v.unidade,
  DATE_SUB(CURDATE(), INTERVAL 30 DAY), DATE_SUB(CURDATE(), INTERVAL 25 DAY),
  8430, 9170, 2119.47, 81.00, 14.95, 0
FROM fleet_vehicles v WHERE v.placa = 'GHI-9012' LIMIT 1;
