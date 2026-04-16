-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1:3306
-- Tempo de geração: 14/04/2026 às 21:02
-- Versão do servidor: 9.1.0
-- Versão do PHP: 8.3.14

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Banco de dados: `cpe_plus`
--

-- --------------------------------------------------------

--
-- Estrutura para tabela `categorias`
--

DROP TABLE IF EXISTS `categorias`;
CREATE TABLE IF NOT EXISTS `categorias` (
  `id` int UNSIGNED NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `nome` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descricao` text COLLATE utf8mb4_unicode_ci,
  `sla_minutos` int UNSIGNED DEFAULT NULL COMMENT 'SLA em minutos. NULL = sem SLA definido.',
  `sla_primeira_resposta_minutos` int UNSIGNED DEFAULT NULL,
  `ativo` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_group_nome` (`group_id`,`nome`),
  KEY `idx_group_id` (`group_id`),
  KEY `idx_ativo` (`ativo`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `categorias`
--

INSERT INTO `categorias` (`id`, `group_id`, `nome`, `descricao`, `sla_minutos`, `sla_primeira_resposta_minutos`, `ativo`, `created_at`, `updated_at`) VALUES
(1, 5, 'Notas a cancelar', 'categoria destinado a notas a cancelar', 2880, 120, 1, '2026-04-08 12:45:57', '2026-04-09 17:54:06'),
(2, 5, 'notas ja emitida', 'teste emição', 10, NULL, 1, '2026-04-08 13:19:44', '2026-04-08 13:22:25'),
(3, 3, 'notas ja emitida', 'tsetes', 1440, NULL, 1, '2026-04-08 17:34:56', '2026-04-08 17:34:56'),
(4, 1, 'suporte simples', 'suporte rapido', 4330, 1440, 1, '2026-04-08 20:46:47', '2026-04-09 17:49:27'),
(5, 1, 'testse t222', 'teste 22', 10, NULL, 0, '2026-04-09 12:49:39', '2026-04-09 17:45:09');

-- --------------------------------------------------------

--
-- Estrutura para tabela `categorias_task`
--

DROP TABLE IF EXISTS `categorias_task`;
CREATE TABLE IF NOT EXISTS `categorias_task` (
  `id` int NOT NULL AUTO_INCREMENT,
  `espaco_id` int DEFAULT NULL,
  `group_id` int DEFAULT NULL,
  `nome` varchar(100) NOT NULL,
  `cor` varchar(7) DEFAULT '#6554c0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_espaco` (`espaco_id`)
<<<<<<< HEAD
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
=======
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
>>>>>>> 296c60d546f50bc39f8894d961744045aa1e7d96

-- --------------------------------------------------------

--
-- Estrutura para tabela `comentarios_task`
--

DROP TABLE IF EXISTS `comentarios_task`;
CREATE TABLE IF NOT EXISTS `comentarios_task` (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `tarefa_id` bigint UNSIGNED NOT NULL,
  `etapa_id` bigint UNSIGNED DEFAULT NULL,
  `autor_id` bigint NOT NULL,
  `texto` text NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_tarefa` (`tarefa_id`)
<<<<<<< HEAD
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
=======
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
>>>>>>> 296c60d546f50bc39f8894d961744045aa1e7d96

--
-- Despejando dados para a tabela `comentarios_task`
--

INSERT INTO `comentarios_task` (`id`, `tarefa_id`, `etapa_id`, `autor_id`, `texto`, `created_at`) VALUES
(2, 6, NULL, 20, 'Urgente! Precisa ser resolvido com prioridade.', '2026-04-14 17:11:33'),
(4, 6, NULL, 20, 'teste comentario', '2026-04-14 17:18:43'),
(13, 7, NULL, 20, '123\n<img src=\"/SistemaCPE/web/assests/uploads/tasks/2cb73532cca448da9786b1c92c4f77fc.jpg\" style=\"max-width:100%;border-radius:6px;\">', '2026-04-14 18:13:40');

-- --------------------------------------------------------

--
-- Estrutura para tabela `convites_espaco_task`
--

DROP TABLE IF EXISTS `convites_espaco_task`;
CREATE TABLE IF NOT EXISTS `convites_espaco_task` (
  `id` int NOT NULL AUTO_INCREMENT,
  `espaco_id` int NOT NULL,
  `group_id` int NOT NULL,
  `convidado_por` int NOT NULL,
  `status` enum('pendente','aceito','recusado') COLLATE utf8mb4_unicode_ci DEFAULT 'pendente',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `respondido_em` datetime DEFAULT NULL,
  `respondido_por` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_convite` (`espaco_id`,`group_id`,`status`),
  KEY `idx_group` (`group_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `convites_espaco_task`
--

INSERT INTO `convites_espaco_task` (`id`, `espaco_id`, `group_id`, `convidado_por`, `status`, `created_at`, `respondido_em`, `respondido_por`) VALUES
(2, 4, 5, 20, 'pendente', '2026-04-14 10:27:19', NULL, NULL),
(3, 4, 10, 20, 'aceito', '2026-04-14 10:27:42', '2026-04-14 10:32:58', 27),
(4, 6, 5, 20, 'pendente', '2026-04-14 11:06:24', NULL, NULL),
(5, 6, 10, 20, 'aceito', '2026-04-14 11:33:33', '2026-04-14 11:37:00', 27),
(6, 6, 3, 20, 'aceito', '2026-04-14 14:55:22', '2026-04-14 14:55:29', 20);

-- --------------------------------------------------------

--
-- Estrutura para tabela `cpe_grupo`
--

DROP TABLE IF EXISTS `cpe_grupo`;
CREATE TABLE IF NOT EXISTS `cpe_grupo` (
  `id` int NOT NULL AUTO_INCREMENT,
  `department_id` int NOT NULL,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_group_per_dept` (`department_id`,`name`),
  KEY `idx_department` (`department_id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `cpe_grupo`
--

INSERT INTO `cpe_grupo` (`id`, `department_id`, `name`, `description`, `created_at`, `updated_at`) VALUES
(1, 1, 'Suporte', 'Suporte da CPE', '2026-04-01 13:08:58', '2026-04-01 13:08:58'),
(3, 2, 'assistencia', 'Assistência Técnica da CPE', '2026-04-01 13:08:58', '2026-04-07 17:38:25'),
(4, 3, 'Financeiro', 'Departamento Financeiro', '2026-04-01 13:08:58', '2026-04-01 13:08:58'),
(5, 3, 'Faturamento', 'Setor de Faturamento', '2026-04-01 13:08:58', '2026-04-01 13:08:58'),
(7, 1, 'teste', NULL, '2026-04-07 17:44:09', '2026-04-07 17:44:09'),
(9, 4, 'Estoque', 'Estoque', '2026-04-13 21:29:02', '2026-04-13 21:29:02'),
(10, 4, 'faturamento', NULL, '2026-04-14 13:25:35', '2026-04-14 13:25:35');

-- --------------------------------------------------------

--
-- Estrutura para tabela `departments`
--

DROP TABLE IF EXISTS `departments`;
CREATE TABLE IF NOT EXISTS `departments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `idx_name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `departments`
--

INSERT INTO `departments` (`id`, `name`, `description`, `created_at`, `updated_at`) VALUES
(1, 'TI', 'Departamento de Tecnologia da Informação', '2026-03-03 21:31:31', '2026-03-03 21:31:31'),
(2, 'RH', 'Departamento de Recursos Humanos', '2026-03-03 21:31:31', '2026-03-03 21:31:31'),
(3, 'Financeiro', 'Departamento Financeiro', '2026-03-03 21:31:31', '2026-03-03 21:31:31'),
(4, 'Administrativo', 'Departamento Administrativo', '2026-03-03 21:31:31', '2026-03-03 21:31:31');

-- --------------------------------------------------------

--
-- Estrutura para tabela `documents`
--

DROP TABLE IF EXISTS `documents`;
CREATE TABLE IF NOT EXISTS `documents` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `content` longtext,
  `visibility` enum('INTERNAL','SECTOR','PRIVATE','TI','RESTRICTED') NOT NULL DEFAULT 'INTERNAL',
  `sector` varchar(120) DEFAULT NULL,
  `owner_user_id` bigint NOT NULL,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_docs_owner` (`owner_user_id`)
<<<<<<< HEAD
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
=======
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
>>>>>>> 296c60d546f50bc39f8894d961744045aa1e7d96

-- --------------------------------------------------------

--
-- Estrutura para tabela `espacos_task`
--

DROP TABLE IF EXISTS `espacos_task`;
CREATE TABLE IF NOT EXISTS `espacos_task` (
  `id` int UNSIGNED NOT NULL AUTO_INCREMENT,
  `nome` varchar(255) NOT NULL,
  `chave` varchar(20) NOT NULL,
  `template` varchar(50) DEFAULT 'tarefa',
  `gerenciado_por` enum('equipe','responsavel') DEFAULT 'equipe',
  `group_id` int DEFAULT NULL,
  `criador_id` bigint NOT NULL,
  `cor` varchar(7) DEFAULT '#6554c0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_group` (`group_id`),
  KEY `idx_criador` (`criador_id`)
<<<<<<< HEAD
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
=======
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
>>>>>>> 296c60d546f50bc39f8894d961744045aa1e7d96

--
-- Despejando dados para a tabela `espacos_task`
--

INSERT INTO `espacos_task` (`id`, `nome`, `chave`, `template`, `gerenciado_por`, `group_id`, `criador_id`, `cor`, `created_at`) VALUES
(2, 'Teste de Tarefa', 'TDT', 'tarefa', 'equipe', NULL, 15, '#6554c0', '2026-04-13 18:15:16'),
(3, 'teste de tarefa', 'TDT', 'tarefa', 'equipe', NULL, 15, '#974f0c', '2026-04-13 18:16:12'),
(4, 'Processo de venda', 'PDV', 'tarefa', 'equipe', 3, 20, '#974f0c', '2026-04-13 20:51:47'),
(6, 'Processo de venda novo', 'PDVN', 'tarefa', 'equipe', 3, 20, '#974f0c', '2026-04-14 14:05:42');

-- --------------------------------------------------------

--
-- Estrutura para tabela `espaco_grupos_task`
--

DROP TABLE IF EXISTS `espaco_grupos_task`;
CREATE TABLE IF NOT EXISTS `espaco_grupos_task` (
  `espaco_id` int NOT NULL,
  `group_id` int NOT NULL,
  `adicionado_em` datetime DEFAULT CURRENT_TIMESTAMP,
  `adicionado_por` int DEFAULT NULL,
  PRIMARY KEY (`espaco_id`,`group_id`)
<<<<<<< HEAD
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
=======
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
>>>>>>> 296c60d546f50bc39f8894d961744045aa1e7d96

--
-- Despejando dados para a tabela `espaco_grupos_task`
--

INSERT INTO `espaco_grupos_task` (`espaco_id`, `group_id`, `adicionado_em`, `adicionado_por`) VALUES
(3, 5, '2026-04-13 17:08:10', 15),
(4, 9, '2026-04-13 18:55:58', 20),
(4, 10, '2026-04-14 10:32:58', 27),
(6, 10, '2026-04-14 11:37:00', 27),
(6, 3, '2026-04-14 14:55:29', 20),
(4, 3, '2026-04-14 14:58:45', 20);

-- --------------------------------------------------------

--
-- Estrutura para tabela `espaco_grupo_sla_task`
--

DROP TABLE IF EXISTS `espaco_grupo_sla_task`;
CREATE TABLE IF NOT EXISTS `espaco_grupo_sla_task` (
  `espaco_id` int NOT NULL,
  `group_id` int NOT NULL,
  `status_id` int NOT NULL,
  `sla_minutos` int NOT NULL DEFAULT '60',
  PRIMARY KEY (`espaco_id`,`group_id`,`status_id`)
<<<<<<< HEAD
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
=======
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
>>>>>>> 296c60d546f50bc39f8894d961744045aa1e7d96

--
-- Despejando dados para a tabela `espaco_grupo_sla_task`
--

INSERT INTO `espaco_grupo_sla_task` (`espaco_id`, `group_id`, `status_id`, `sla_minutos`) VALUES
(3, 5, 7, 10),
(3, 5, 8, 6),
(3, 5, 9, 5),
(3, 5, 10, 0),
(3, 5, 11, 17),
(6, 3, 20, 60),
(6, 3, 21, 90),
(6, 3, 22, 0),
(6, 3, 23, 0),
(6, 10, 20, 120),
(6, 10, 21, 120),
(6, 10, 22, 0),
(6, 10, 23, 0);

-- --------------------------------------------------------

--
-- Estrutura para tabela `espaco_membros_task`
--

DROP TABLE IF EXISTS `espaco_membros_task`;
CREATE TABLE IF NOT EXISTS `espaco_membros_task` (
  `id` int UNSIGNED NOT NULL AUTO_INCREMENT,
  `espaco_id` int UNSIGNED NOT NULL,
  `usuario_id` bigint NOT NULL,
  `funcao` enum('administrador','membro','visualizador') DEFAULT 'membro',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_eu` (`espaco_id`,`usuario_id`),
  KEY `idx_espaco` (`espaco_id`),
  KEY `idx_usuario` (`usuario_id`)
<<<<<<< HEAD
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
=======
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
>>>>>>> 296c60d546f50bc39f8894d961744045aa1e7d96

--
-- Despejando dados para a tabela `espaco_membros_task`
--

INSERT INTO `espaco_membros_task` (`id`, `espaco_id`, `usuario_id`, `funcao`, `created_at`) VALUES
(2, 2, 15, 'administrador', '2026-04-13 18:15:16'),
(3, 2, 2, 'administrador', '2026-04-13 18:15:16'),
(4, 2, 3, 'membro', '2026-04-13 18:15:16'),
(5, 3, 15, 'administrador', '2026-04-13 18:16:12'),
(6, 3, 20, 'administrador', '2026-04-13 18:16:12'),
(7, 3, 19, 'membro', '2026-04-13 18:16:12'),
(8, 4, 20, 'administrador', '2026-04-13 20:51:47'),
(10, 6, 20, 'administrador', '2026-04-14 14:05:42');

-- --------------------------------------------------------

--
-- Estrutura para tabela `etapas_task`
--

DROP TABLE IF EXISTS `etapas_task`;
CREATE TABLE IF NOT EXISTS `etapas_task` (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `tarefa_id` bigint UNSIGNED NOT NULL,
  `group_id` int NOT NULL,
  `titulo` varchar(255) NOT NULL,
  `descricao` text,
  `status_id` int UNSIGNED DEFAULT NULL,
  `responsavel_id` bigint DEFAULT NULL,
  `tempo_estimado` int DEFAULT '0',
  `prazo` datetime DEFAULT NULL,
  `ordem` int DEFAULT '0',
  `concluida_em` datetime DEFAULT NULL,
  `concluida_por` bigint DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_tarefa` (`tarefa_id`),
  KEY `idx_group` (`group_id`)
<<<<<<< HEAD
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
=======
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
>>>>>>> 296c60d546f50bc39f8894d961744045aa1e7d96

-- --------------------------------------------------------

--
-- Estrutura para tabela `historico_task`
--

DROP TABLE IF EXISTS `historico_task`;
CREATE TABLE IF NOT EXISTS `historico_task` (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `tarefa_id` bigint UNSIGNED NOT NULL,
  `etapa_id` bigint UNSIGNED DEFAULT NULL,
  `usuario_id` bigint NOT NULL,
  `acao` varchar(100) NOT NULL,
  `detalhe` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_tarefa` (`tarefa_id`)
<<<<<<< HEAD
) ENGINE=InnoDB AUTO_INCREMENT=64 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
=======
) ENGINE=InnoDB AUTO_INCREMENT=64 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
>>>>>>> 296c60d546f50bc39f8894d961744045aa1e7d96

--
-- Despejando dados para a tabela `historico_task`
--

INSERT INTO `historico_task` (`id`, `tarefa_id`, `etapa_id`, `usuario_id`, `acao`, `detalhe`, `created_at`) VALUES
(1, 1, NULL, 15, 'criou', 'Tarefa criada: separar o pedido', '2026-04-13 18:45:13'),
(2, 2, NULL, 15, 'criou', 'Tarefa criada: separar o pedido', '2026-04-13 18:45:52'),
(3, 2, NULL, 15, 'atualizou', 'editou', '2026-04-13 18:46:29'),
(4, 2, NULL, 15, 'atualizou', 'editou', '2026-04-13 18:46:30'),
(5, 2, NULL, 15, 'atualizou', 'editou', '2026-04-13 18:46:36'),
(6, 2, NULL, 15, 'atualizou', 'editou', '2026-04-13 18:46:52'),
(7, 2, NULL, 15, 'atualizou_tempo', 'gasto=2h restante=None', '2026-04-13 18:47:04'),
(8, 2, NULL, 15, 'atualizou_tempo', 'gasto=None restante=None', '2026-04-13 18:47:11'),
(9, 2, NULL, 15, 'comentou', NULL, '2026-04-13 18:47:21'),
(10, 1, NULL, 15, 'atualizou', 'status: 2', '2026-04-13 20:06:12'),
(11, 2, NULL, 20, 'atualizou', 'status: 9', '2026-04-13 20:26:42'),
(12, 2, NULL, 20, 'atualizou', 'editou', '2026-04-13 20:26:56'),
(13, 3, NULL, 20, 'criou', 'Tarefa criada: Criar nota para o pedido', '2026-04-13 20:28:20'),
(14, 3, NULL, 20, 'atualizou', 'editou', '2026-04-13 20:28:24'),
(15, 3, NULL, 20, 'finalizou', 'Tarefa finalizada', '2026-04-13 20:28:33'),
(16, 3, NULL, 20, 'atualizou', 'status: 9', '2026-04-13 20:28:39'),
(17, 4, NULL, 20, 'criou', 'Tarefa criada: Aguardando venda', '2026-04-13 20:54:44'),
(18, 5, NULL, 20, 'criou', 'Tarefa criada: enviar para estoque', '2026-04-14 14:09:12'),
(19, 5, NULL, 20, 'atualizou', 'editou', '2026-04-14 14:38:14'),
(20, 5, NULL, 20, 'atualizou', 'editou', '2026-04-14 14:39:11'),
(21, 5, NULL, 20, 'atualizou', 'editou', '2026-04-14 14:39:21'),
(22, 5, NULL, 20, 'atualizou', 'status: 21', '2026-04-14 14:39:30'),
(23, 5, NULL, 20, 'atualizou', 'status: 22', '2026-04-14 14:39:55'),
(24, 5, NULL, 20, 'atualizou', 'status: 21', '2026-04-14 14:39:56'),
(25, 5, NULL, 20, 'atualizou', 'status: 20', '2026-04-14 14:39:57'),
(26, 5, NULL, 20, 'atualizou', 'status: 21', '2026-04-14 14:40:37'),
(27, 5, NULL, 20, 'atualizou', 'status: 22', '2026-04-14 16:47:21'),
(28, 5, NULL, 20, 'finalizou', 'Tarefa finalizada', '2026-04-14 16:47:25'),
(29, 6, NULL, 20, 'criou', 'Tarefa criada: Faturar o pedido', '2026-04-14 16:48:11'),
(30, 6, NULL, 20, 'atualizou', 'editou', '2026-04-14 16:48:23'),
(31, 6, NULL, 20, 'atualizou', 'editou', '2026-04-14 16:48:30'),
(32, 6, NULL, 20, 'atualizou', 'editou', '2026-04-14 16:49:20'),
(33, 6, NULL, 20, 'atualizou', 'editou', '2026-04-14 17:01:31'),
(34, 6, NULL, 20, 'atualizou', 'editou', '2026-04-14 17:10:14'),
(35, 6, NULL, 20, 'atualizou', 'status: 21', '2026-04-14 17:11:16'),
(36, 6, NULL, 20, 'comentou', NULL, '2026-04-14 17:11:33'),
(37, 6, NULL, 20, 'atualizou', 'prioridade: urgente', '2026-04-14 17:12:15'),
(38, 6, NULL, 20, 'atualizou', 'editou', '2026-04-14 17:13:31'),
(39, 6, NULL, 20, 'comentou', NULL, '2026-04-14 17:17:59'),
(40, 6, NULL, 20, 'comentou', NULL, '2026-04-14 17:18:43'),
(41, 6, NULL, 20, 'comentou', NULL, '2026-04-14 17:18:57'),
(42, 6, NULL, 20, 'comentou', 'teste', '2026-04-14 17:19:52'),
(43, 6, NULL, 20, 'comentou', 'teste', '2026-04-14 17:19:53'),
(44, 6, NULL, 20, 'comentou', 'teste', '2026-04-14 17:19:54'),
(45, 6, NULL, 20, 'comentou', 'teste', '2026-04-14 17:19:55'),
(46, 6, NULL, 20, 'comentou', 'teste', '2026-04-14 17:19:56'),
(47, 6, NULL, 20, 'comentou', 'teste', '2026-04-14 17:19:57'),
(48, 6, NULL, 20, 'comentou', 'teste final', '2026-04-14 17:23:29'),
(49, 6, NULL, 20, 'atualizou', 'editou', '2026-04-14 17:52:14'),
(50, 7, NULL, 27, 'criou', 'Tarefa criada: pegar o pedido', '2026-04-14 18:04:14'),
(51, 7, NULL, 27, 'atualizou', 'editou', '2026-04-14 18:04:18'),
(52, 7, NULL, 20, 'comentou', '123\n<img src=\"/SistemaCPE/web/assests/uploads/tasks/2cb73532cca448da9786b1c92c4f', '2026-04-14 18:13:40'),
(53, 5, NULL, 20, 'reabriu', 'Tarefa reaberta', '2026-04-14 18:22:57'),
(54, 7, NULL, 20, 'atualizou', 'status: 22', '2026-04-14 19:25:57'),
(56, 5, NULL, 15, 'atualizou', 'status: 22', '2026-04-14 20:09:59'),
(57, 6, NULL, 15, 'atualizou', 'editou', '2026-04-14 20:10:53'),
(58, 6, NULL, 15, 'atualizou', 'editou', '2026-04-14 20:10:54'),
(59, 6, NULL, 15, 'atualizou', 'título: Faturar o pedido', '2026-04-14 20:20:51'),
(60, 6, NULL, 15, 'atualizou', 'editou', '2026-04-14 20:21:13'),
(61, 6, NULL, 20, 'atualizou', 'título: Faturar o pedido', '2026-04-14 20:34:42'),
(62, 6, NULL, 20, 'atualizou', 'título: Faturar o pedido', '2026-04-14 20:48:32'),
(63, 6, NULL, 20, 'atualizou', 'status: 20', '2026-04-14 20:48:53');

-- --------------------------------------------------------

--
-- Estrutura para tabela `notificacoes`
--

DROP TABLE IF EXISTS `notificacoes`;
CREATE TABLE IF NOT EXISTS `notificacoes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ticket_id` int DEFAULT NULL,
  `usuario_id` int DEFAULT NULL,
  `mensagem` varchar(255) DEFAULT NULL,
  `tipo` varchar(50) DEFAULT NULL,
  `lido` tinyint(1) DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_usuario_lido` (`usuario_id`,`lido`) COMMENT 'Busca rápida de notificações não lidas por usuário',
  KEY `idx_usuario_criado` (`usuario_id`,`created_at`) COMMENT 'Timeline de notificações por data',
  KEY `idx_ticket_id` (`ticket_id`) COMMENT 'Buscar notificações de um ticket específico'
<<<<<<< HEAD
) ENGINE=MyISAM AUTO_INCREMENT=169 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
=======
) ENGINE=MyISAM AUTO_INCREMENT=169 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
>>>>>>> 296c60d546f50bc39f8894d961744045aa1e7d96

--
-- Despejando dados para a tabela `notificacoes`
--

INSERT INTO `notificacoes` (`id`, `ticket_id`, `usuario_id`, `mensagem`, `tipo`, `lido`, `created_at`, `updated_at`) VALUES
(112, 23, 20, 'Status alterado para 3', 'status_alterado', 1, '2026-04-08 19:50:14', '2026-04-08 20:22:49'),
(12, 7, 17, 'Ticket atribuído a 15', 'atribuido', 0, '2026-03-30 18:11:35', '2026-03-30 18:11:35'),
(111, 24, 20, 'Status alterado para 3', 'status_alterado', 1, '2026-04-08 19:50:08', '2026-04-08 20:22:47'),
(18, 8, 17, 'Novo ticket: \"novo teste de notificação tarde\" de Sistema', 'ticket_criado', 0, '2026-03-30 18:31:28', '2026-03-30 18:31:28'),
(109, 25, 17, 'Comentário interno no ticket #FAT-2026-00004: teste', 'comentario_interno', 0, '2026-04-08 17:33:22', '2026-04-08 17:33:22'),
(9, 7, 17, 'Novo ticket: \"novo ticket de teste\" de Sistema', 'ticket_criado', 0, '2026-03-30 18:11:21', '2026-03-30 18:11:21'),
(110, 25, 20, 'Status alterado para 3', 'status_alterado', 1, '2026-04-08 19:50:03', '2026-04-08 20:22:47'),
(33, 9, 17, 'Ticket atribuído a 15', 'atribuido', 0, '2026-03-30 18:53:49', '2026-03-30 18:53:49'),
(79, 19, 17, 'Novo ticket: \"segundo teste de ticket 2\" de Sistema', 'ticket_criado', 0, '2026-03-31 22:14:58', '2026-03-31 22:14:58'),
(108, 25, 20, 'Seu chamado foi assumido por Usuário #15', 'ticket_atribuido', 1, '2026-04-08 17:32:47', '2026-04-08 17:32:59'),
(21, 8, 17, 'Ticket atribuído a 15', 'atribuido', 0, '2026-03-30 18:31:53', '2026-03-30 18:31:53'),
(101, 21, 20, 'Seu chamado foi assumido por Usuário #23', 'ticket_atribuido', 1, '2026-04-07 19:19:25', '2026-04-07 19:20:08'),
(30, 9, 17, 'Novo ticket: \"trocar mouse e teclado\" de Sistema', 'ticket_criado', 0, '2026-03-30 18:52:31', '2026-03-30 18:52:31'),
(105, 24, 20, 'Status alterado para 3', 'status_alterado', 1, '2026-04-08 14:16:26', '2026-04-08 14:46:05'),
(106, 22, 20, 'Seu chamado foi assumido por Usuário #15', 'ticket_atribuido', 1, '2026-04-08 14:53:18', '2026-04-08 14:53:32'),
(102, 21, 23, 'Nova resposta no ticket #SUP-2026-00006: camila atende ok', 'nova_resposta', 1, '2026-04-07 19:20:36', '2026-04-07 19:20:55'),
(99, 21, 20, 'Nova resposta no ticket #SUP-2026-00006: teste 222', 'nova_resposta', 1, '2026-04-07 18:51:45', '2026-04-07 19:20:02'),
(100, 21, 20, 'Ticket encaminhado para \'assistencia\' por Administrador: ', 'ticket_encaminhado', 1, '2026-04-07 18:59:43', '2026-04-07 19:20:02'),
(96, 21, 20, 'Nova resposta no ticket #SUP-2026-00006: teste 222', 'nova_resposta', 1, '2026-04-07 18:28:42', '2026-04-07 18:28:49'),
(97, 21, 17, 'Ticket atribuído a 15', 'atribuido', 0, '2026-04-07 18:51:27', '2026-04-07 18:51:27'),
(43, 10, 17, 'Novo ticket: \"teste de ticket id\" de Sistema', 'ticket_criado', 0, '2026-03-30 22:08:22', '2026-03-30 22:08:22'),
(92, 20, 20, 'Nova resposta no ticket #ASS-2026-00001: resposta teste', 'nova_resposta', 1, '2026-04-07 17:56:42', '2026-04-07 17:57:25'),
(93, 20, 20, 'Nova resposta no ticket #ASS-2026-00001: ok ok ok', 'nova_resposta', 1, '2026-04-07 17:57:39', '2026-04-07 17:57:47'),
(46, 11, 17, 'Novo ticket: \"chamado\" de Sistema', 'ticket_criado', 0, '2026-03-30 22:14:09', '2026-03-30 22:14:09'),
(82, 19, 17, 'Ticket atribuído a 15', 'atribuido', 0, '2026-03-31 22:15:27', '2026-03-31 22:15:27'),
(49, 11, 17, 'Ticket atribuído a 15', 'atribuido', 0, '2026-03-30 22:15:39', '2026-03-30 22:15:39'),
(104, 24, 20, 'Seu chamado foi assumido por Usuário #15', 'ticket_atribuido', 1, '2026-04-08 13:23:08', '2026-04-08 13:23:24'),
(52, 13, 17, 'Novo ticket: \"teste ticket alfa numerico\" de Sistema', 'ticket_criado', 0, '2026-03-30 22:46:33', '2026-03-30 22:46:33'),
(70, 18, 17, 'Ticket atribuído a 19', 'atribuido', 0, '2026-03-31 20:36:31', '2026-03-31 20:36:31'),
(55, 14, 17, 'Novo ticket: \"novo teste de geração de ticket alfa\" de Sistema', 'ticket_criado', 0, '2026-03-30 22:47:18', '2026-03-30 22:47:18'),
(130, 30, 20, 'Seu chamado foi resolvido por Usuário #19. Caso não esteja satisfeito, você pode reabri-lo.', 'ticket_resolvido', 1, '2026-04-10 12:23:20', '2026-04-10 12:26:40'),
(103, 23, 20, 'Seu chamado foi assumido por Usuário #15', 'ticket_atribuido', 1, '2026-04-08 13:20:27', '2026-04-08 13:21:18'),
(58, 15, 17, 'Novo ticket: \"segundo teste de ticket 2\" de Sistema', 'ticket_criado', 0, '2026-03-31 13:53:14', '2026-03-31 13:53:14'),
(94, 21, 17, 'Novo ticket: \"segundo teste de ticket3\" de Sistema', 'ticket_criado', 0, '2026-04-07 18:23:18', '2026-04-07 18:23:18'),
(61, 16, 17, 'Novo ticket: \"Teste final do sistema\" de Sistema', 'ticket_criado', 0, '2026-03-31 14:34:45', '2026-03-31 14:34:45'),
(67, 18, 17, 'Novo ticket: \"novo teste 1234\" de Sistema', 'ticket_criado', 0, '2026-03-31 20:36:13', '2026-03-31 20:36:13'),
(64, 17, 17, 'Novo ticket: \"tests 1111\" de Sistema', 'ticket_criado', 0, '2026-03-31 15:20:32', '2026-03-31 15:20:32'),
(107, 23, 20, 'Seu chamado foi assumido por Usuário #15', 'ticket_atribuido', 1, '2026-04-08 14:53:24', '2026-04-08 14:53:34'),
(129, 30, 20, 'Nova resposta no ticket #SUP-2026-00010: primeira resposta', 'nova_resposta', 1, '2026-04-09 20:46:56', '2026-04-10 12:26:33'),
(126, 29, 20, 'Status alterado para 4', 'status_alterado', 1, '2026-04-09 20:07:48', '2026-04-10 12:26:33'),
(124, 29, 20, 'Status alterado para 1', 'status_alterado', 1, '2026-04-09 18:01:22', '2026-04-10 12:26:33'),
(117, 27, 24, 'Seu chamado foi assumido por Usuário #15', 'ticket_atribuido', 1, '2026-04-08 20:37:18', '2026-04-08 21:04:16'),
(118, 27, 22, 'Usuário #15 devolveu o chamado para a fila', 'ticket_devolvido', 0, '2026-04-08 20:37:50', '2026-04-08 20:37:50'),
(119, 28, 24, 'Seu chamado foi assumido por Usuário #19', 'ticket_atribuido', 1, '2026-04-08 20:48:30', '2026-04-08 21:04:16'),
(128, 30, 20, 'Seu chamado foi assumido por Usuário #19', 'ticket_atribuido', 1, '2026-04-09 20:46:04', '2026-04-10 12:26:33'),
(120, 28, 24, 'Nova resposta no ticket #SUP-2026-00008: ok ook oki', 'nova_resposta', 1, '2026-04-08 20:54:24', '2026-04-08 21:04:16'),
(121, 28, 24, 'Status alterado para 4', 'status_alterado', 0, '2026-04-08 21:04:51', '2026-04-08 21:04:51'),
(122, 28, 17, 'Comentário interno no ticket #SUP-2026-00008: teste', 'comentario_interno', 0, '2026-04-08 22:04:04', '2026-04-08 22:04:04'),
(123, 29, 20, 'Seu chamado foi assumido por Usuário #19', 'ticket_atribuido', 1, '2026-04-09 17:56:03', '2026-04-10 12:26:33'),
(127, 29, 20, 'Status alterado para 5', 'status_alterado', 1, '2026-04-09 20:09:22', '2026-04-10 12:26:33'),
(131, 21, 20, 'Status alterado para 4', 'status_alterado', 1, '2026-04-10 13:03:14', '2026-04-14 13:29:57'),
(132, 21, 20, 'Seu chamado foi resolvido por Usuário #23. Caso não esteja satisfeito, você pode reabri-lo.', 'ticket_resolvido', 1, '2026-04-10 13:03:15', '2026-04-14 13:29:57'),
(133, 31, 17, 'Novo chamado de camila: ultimo teste', 'ticket_criado', 0, '2026-04-10 13:03:59', '2026-04-10 13:03:59'),
(134, 31, 19, 'Novo chamado de camila: ultimo teste', 'ticket_criado', 1, '2026-04-10 13:03:59', '2026-04-10 13:04:51'),
(135, 31, 22, 'Novo chamado de camila: ultimo teste', 'ticket_criado', 0, '2026-04-10 13:03:59', '2026-04-10 13:03:59'),
(136, 31, 23, 'Seu chamado foi assumido por Usuário #19', 'ticket_atribuido', 1, '2026-04-10 13:04:53', '2026-04-10 13:35:26'),
(137, 31, 23, 'Nova resposta no ticket #SUP-2026-00011: teste de primeiro atendimento', 'nova_resposta', 1, '2026-04-10 13:05:10', '2026-04-10 13:35:26'),
(138, 31, 23, 'Status alterado para 3', 'status_alterado', 1, '2026-04-10 13:05:22', '2026-04-10 13:35:26'),
(139, 31, 23, 'Status alterado para 2', 'status_alterado', 1, '2026-04-10 13:06:09', '2026-04-10 13:35:26'),
(140, 31, 23, 'Seu chamado foi resolvido por Usuário #19. Caso não esteja satisfeito, você pode reabri-lo.', 'ticket_resolvido', 1, '2026-04-10 13:06:35', '2026-04-10 13:35:26'),
(141, 32, 20, 'Novo chamado de jonathan: teste de chamado para assistencia', 'ticket_criado', 1, '2026-04-10 13:12:17', '2026-04-14 13:29:57'),
(142, 32, 23, 'Novo chamado de jonathan: teste de chamado para assistencia', 'ticket_criado', 1, '2026-04-10 13:12:17', '2026-04-10 13:35:26'),
(143, 32, 24, 'Novo chamado de jonathan: teste de chamado para assistencia', 'ticket_criado', 0, '2026-04-10 13:12:17', '2026-04-10 13:12:17'),
(144, 32, 19, 'Seu chamado foi assumido por Usuário #23', 'ticket_atribuido', 1, '2026-04-10 13:12:32', '2026-04-10 17:26:26'),
(145, 33, 20, 'Novo chamado de jonathan: novo teste para assistencia 2', 'ticket_criado', 1, '2026-04-10 13:35:19', '2026-04-14 13:29:57'),
(146, 33, 23, 'Novo chamado de jonathan: novo teste para assistencia 2', 'ticket_criado', 1, '2026-04-10 13:35:19', '2026-04-10 13:35:32'),
(147, 33, 24, 'Novo chamado de jonathan: novo teste para assistencia 2', 'ticket_criado', 0, '2026-04-10 13:35:19', '2026-04-10 13:35:19'),
(148, 33, 19, 'Seu chamado foi assumido por Usuário #23', 'ticket_atribuido', 1, '2026-04-10 13:35:34', '2026-04-10 17:26:26'),
(149, 33, 19, 'Nova resposta no ticket #ASS-2026-00001: primeira resposta', 'nova_resposta', 1, '2026-04-10 13:36:07', '2026-04-10 17:26:26'),
(150, 34, 17, 'Novo chamado de camila: teste de avaliação', 'ticket_criado', 0, '2026-04-10 17:40:32', '2026-04-10 17:40:32'),
(151, 34, 19, 'Novo chamado de camila: teste de avaliação', 'ticket_criado', 1, '2026-04-10 17:40:32', '2026-04-13 19:02:00'),
(152, 34, 22, 'Novo chamado de camila: teste de avaliação', 'ticket_criado', 0, '2026-04-10 17:40:32', '2026-04-10 17:40:32'),
(153, 34, 23, 'Seu chamado foi assumido por Usuário #19', 'ticket_atribuido', 0, '2026-04-10 17:40:42', '2026-04-10 17:40:42'),
(154, 34, 23, 'Nova resposta no ticket #SUP-2026-00012: novo teste de avaliação', 'nova_resposta', 0, '2026-04-10 17:40:57', '2026-04-10 17:40:57'),
(155, 34, 19, 'Nova resposta no ticket #SUP-2026-00012: teste de avaliação', 'nova_resposta', 1, '2026-04-10 17:41:26', '2026-04-13 19:02:00'),
(156, 34, 23, 'Seu chamado foi resolvido por Usuário #19. Caso não esteja satisfeito, você pode reabri-lo.', 'ticket_resolvido', 0, '2026-04-10 17:41:48', '2026-04-10 17:41:48'),
(157, 34, 23, '📋 Avalie o atendimento do chamado SUP-2026-00012. Sua opinião é importante! Você tem 7 dias para avaliar.', 'avaliacao_pendente', 0, '2026-04-10 17:41:48', '2026-04-10 17:41:48'),
(158, 33, 17, 'Comentário interno no ticket #ASS-2026-00001: teste', 'comentario_interno', 0, '2026-04-10 17:56:53', '2026-04-10 17:56:53'),
(159, NULL, 22, 'Seu grupo foi convidado para participar do quadro \"Processo de venda\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 0, '2026-04-14 13:13:49', '2026-04-14 13:13:49'),
(160, NULL, 27, 'Seu grupo foi convidado para participar do quadro \"Processo de venda\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 1, '2026-04-14 13:27:42', '2026-04-14 14:06:45'),
(161, NULL, 20, 'O grupo \"faturamento\" aceitou o convite para o quadro \"Processo de venda\".', 'convite_aceito_task', 1, '2026-04-14 13:32:58', '2026-04-14 13:52:52'),
(162, NULL, 27, 'Seu grupo foi convidado para participar do quadro \"Processo de venda novo\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 1, '2026-04-14 14:33:33', '2026-04-14 14:36:38'),
(163, NULL, 28, 'Seu grupo foi convidado para participar do quadro \"Processo de venda novo\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 0, '2026-04-14 14:33:33', '2026-04-14 14:33:33'),
(164, NULL, 20, 'O grupo \"faturamento\" aceitou o convite para o quadro \"Processo de venda novo\".', 'convite_aceito_task', 1, '2026-04-14 14:37:00', '2026-04-14 17:55:26'),
(165, NULL, 20, 'Seu grupo foi convidado para participar do quadro \"Processo de venda novo\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 1, '2026-04-14 17:55:22', '2026-04-14 17:55:27'),
(166, NULL, 23, 'Seu grupo foi convidado para participar do quadro \"Processo de venda novo\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 0, '2026-04-14 17:55:22', '2026-04-14 17:55:22'),
(167, NULL, 24, 'Seu grupo foi convidado para participar do quadro \"Processo de venda novo\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 0, '2026-04-14 17:55:22', '2026-04-14 17:55:22'),
(168, NULL, 20, 'O grupo \"assistencia\" aceitou o convite para o quadro \"Processo de venda novo\".', 'convite_aceito_task', 1, '2026-04-14 17:55:29', '2026-04-14 18:15:16');

-- --------------------------------------------------------

--
-- Estrutura para tabela `page_permissions`
--

DROP TABLE IF EXISTS `page_permissions`;
CREATE TABLE IF NOT EXISTS `page_permissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `page_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Nome da página (ex: CHAT, USERS)',
  `allowed_roles` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Roles separados por vírgula (ex: ADMIN,TI)',
  `updated_by` int DEFAULT NULL COMMENT 'ID do admin que alterou',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_page_name` (`page_name`),
  KEY `idx_page_name` (`page_name`)
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `page_permissions`
--

INSERT INTO `page_permissions` (`id`, `page_name`, `allowed_roles`, `updated_by`, `updated_at`) VALUES
(1, 'DASHBOARD', 'USER,RESPONSAVEL_GRUPO,ADMIN,TI,MANAGER', NULL, '2026-04-06 22:28:35'),
(2, 'TICKETS', 'USER,RESPONSAVEL_GRUPO,ADMIN,TI,MANAGER', NULL, '2026-04-06 22:28:35'),
(3, 'CHAT', 'USER,RESPONSAVEL_GRUPO,ADMIN,TI,MANAGER', NULL, '2026-04-06 22:28:35'),
(4, 'TASKS', 'USER,RESPONSAVEL_GRUPO,ADMIN,TI,MANAGER', NULL, '2026-04-06 22:28:35'),
(5, 'PROJECTS', 'USER,RESPONSAVEL_GRUPO,ADMIN,TI,MANAGER', NULL, '2026-04-06 22:28:35'),
(6, 'KNOWLEDGE_BASE', 'USER,RESPONSAVEL_GRUPO,ADMIN,TI,MANAGER', NULL, '2026-04-06 22:28:35'),
(7, 'DOWNLOAD_AGENTS', 'USER,RESPONSAVEL_GRUPO,ADMIN,TI,MANAGER', NULL, '2026-04-06 22:28:35'),
(8, 'GROUPS', 'ADMIN,TI,MANAGER', NULL, '2026-04-06 22:28:35'),
(9, 'REGISTRATIONS', 'ADMIN,TI,MANAGER', NULL, '2026-04-06 22:28:35'),
(10, 'REPORTS', 'ADMIN,TI,MANAGER', NULL, '2026-04-06 22:28:35'),
(11, 'BILLING', 'ADMIN,MANAGER', NULL, '2026-04-06 22:28:35'),
(12, 'USERS', 'ADMIN,TI', NULL, '2026-04-06 22:28:35'),
(13, 'INVENTORY', 'ADMIN,TI', NULL, '2026-04-06 22:28:35'),
(14, 'PASSWORD_VAULT', 'ADMIN,TI', NULL, '2026-04-06 22:28:35'),
(15, 'SETTINGS', 'ADMIN', NULL, '2026-04-06 22:28:35'),
(16, 'PERMISSIONS', 'ADMIN', NULL, '2026-04-06 22:28:35'),
(17, 'AVALIACOES', 'RESPONSAVEL_GRUPO,ADMIN,TI,MANAGER', NULL, '2026-04-10 17:15:03');

-- --------------------------------------------------------

--
-- Estrutura para tabela `passwords`
--

DROP TABLE IF EXISTS `passwords`;
CREATE TABLE IF NOT EXISTS `passwords` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `client` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `link` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `observation` text COLLATE utf8mb4_unicode_ci,
  `group_id` int DEFAULT NULL,
  `is_public` tinyint(1) DEFAULT '0',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_exclusive` tinyint(1) DEFAULT '0',
  `allowed_group_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_group_id` (`group_id`),
  KEY `idx_allowed_group` (`allowed_group_id`),
  KEY `idx_is_exclusive` (`is_exclusive`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `passwords`
--

INSERT INTO `passwords` (`id`, `user_id`, `client`, `email`, `description`, `password`, `link`, `observation`, `group_id`, `is_public`, `created_at`, `updated_at`, `is_exclusive`, `allowed_group_id`) VALUES
(1, 1, 'tese', 'admin@cpe.com.br', 'teste', '22223333', 'https://github.com/cpeinfra-cmyk/cpenavigator', 'teste22', NULL, 0, '2026-03-07 07:17:57', '2026-03-07 07:17:57', 0, NULL),
(2, 1, 'teste 55', 'admin@cpe.com.br', 'teste 44', 'd3d5t7gas1436', 'https://github.com/cpeinfra-cmyk/cpenavigator', '3d3t', NULL, 0, '2026-03-07 16:27:31', '2026-03-07 16:27:31', 0, NULL),
(4, 1, 'Jon', 'admin@cpe.com.br', 'teste jon', 'jon123', 'https://github.com/login/oauth/authorize', 'teste jon', NULL, 0, '2026-03-10 14:57:10', '2026-03-10 14:57:10', 0, NULL);

-- --------------------------------------------------------

--
-- Estrutura para tabela `status_task`
--

DROP TABLE IF EXISTS `status_task`;
CREATE TABLE IF NOT EXISTS `status_task` (
  `id` int UNSIGNED NOT NULL AUTO_INCREMENT,
  `group_id` int DEFAULT NULL,
  `espaco_id` int UNSIGNED DEFAULT NULL,
  `nome` varchar(100) NOT NULL,
  `cor` varchar(7) DEFAULT '#6b7280',
  `icone` varchar(50) DEFAULT 'bi-circle',
  `ordem` int DEFAULT '0',
  `is_final` tinyint(1) DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_group` (`group_id`)
<<<<<<< HEAD
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
=======
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
>>>>>>> 296c60d546f50bc39f8894d961744045aa1e7d96

--
-- Despejando dados para a tabela `status_task`
--

INSERT INTO `status_task` (`id`, `group_id`, `espaco_id`, `nome`, `cor`, `icone`, `ordem`, `is_final`, `created_at`) VALUES
(4, NULL, 2, 'A Fazer', '#6b7280', 'bi-circle', 0, 0, '2026-04-13 18:15:16'),
(5, NULL, 2, 'Fazendo', '#f59e0b', 'bi-arrow-right-circle', 1, 0, '2026-04-13 18:15:16'),
(6, NULL, 2, 'Feito', '#10b981', 'bi-check-circle', 2, 1, '2026-04-13 18:15:16'),
(7, NULL, 3, 'A Fazer', '#6b7280', 'bi-circle', 0, 0, '2026-04-13 18:16:12'),
(8, NULL, 3, 'Fazendo', '#f59e0b', 'bi-arrow-right-circle', 1, 0, '2026-04-13 18:16:12'),
(9, NULL, 3, 'Feito', '#10b981', 'bi-check-circle', 2, 1, '2026-04-13 18:16:12'),
(10, NULL, 3, 'Teste', '#8b5cf6', 'bi-eye', 2, 0, '2026-04-13 20:14:04'),
(11, NULL, 3, 'estoque fazendo', '#0052cc', 'bi-circle', 4, 0, '2026-04-13 20:15:52'),
(12, 3, 4, 'A Fazer', '#6b7280', 'bi-circle', 0, 0, '2026-04-13 20:51:47'),
(13, 3, 4, 'Fazendo conferencia de NF-e', '#f59e0b', 'bi-arrow-right-circle', 2, 0, '2026-04-13 20:51:47'),
(14, 3, 4, 'Feito', '#10b981', 'bi-check-circle', 3, 1, '2026-04-13 20:51:47'),
(15, 3, 4, 'Emitindo NF-e', '#cc00bb', 'bi-calendar', 1, 0, '2026-04-13 20:52:38'),
(20, 3, 6, 'A Fazer (pegue o seu ticket)', '#1a1a1a', 'bi-circle', 0, 0, '2026-04-14 14:05:42'),
(21, 3, 6, 'Fazendo', '#f59e0b', 'bi-arrow-right-circle', 1, 0, '2026-04-14 14:05:42'),
(22, 3, 6, 'Feito', '#10b981', 'bi-check-circle', 2, 1, '2026-04-14 14:05:42'),
(23, 3, 6, 'Primeira venda confirmada', '#0052cc', 'bi-circle', 3, 0, '2026-04-14 14:06:02');

-- --------------------------------------------------------

--
-- Estrutura para tabela `subcategorias`
--

DROP TABLE IF EXISTS `subcategorias`;
CREATE TABLE IF NOT EXISTS `subcategorias` (
  `id` int UNSIGNED NOT NULL AUTO_INCREMENT,
  `categoria_id` int UNSIGNED NOT NULL,
  `nome` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descricao` text COLLATE utf8mb4_unicode_ci,
  `sla_minutos` int UNSIGNED DEFAULT NULL,
  `sla_primeira_resposta_minutos` int UNSIGNED DEFAULT NULL,
  `ativo` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_categoria_nome` (`categoria_id`,`nome`),
  KEY `idx_categoria_id` (`categoria_id`),
  KEY `idx_ativo` (`ativo`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `subcategorias`
--

INSERT INTO `subcategorias` (`id`, `categoria_id`, `nome`, `descricao`, `sla_minutos`, `sla_primeira_resposta_minutos`, `ativo`, `created_at`, `updated_at`) VALUES
(1, 1, 'notas já canceladas', 'notas que já foram canceladas', NULL, NULL, 1, '2026-04-08 12:46:25', '2026-04-08 12:46:25'),
(2, 3, 'testes', 'test se', 20, 3, 1, '2026-04-08 17:35:08', '2026-04-10 13:14:53'),
(3, 4, 'tesete', NULL, NULL, NULL, 0, '2026-04-09 17:50:18', '2026-04-09 17:50:36'),
(4, 4, 'teste 22', NULL, NULL, NULL, 1, '2026-04-09 17:51:13', '2026-04-09 17:51:13'),
(5, 2, 'notas ok', 'notas ok ok', 300, 60, 1, '2026-04-09 17:54:27', '2026-04-09 17:54:27');

-- --------------------------------------------------------

--
-- Estrutura para tabela `subtarefas_task`
--

DROP TABLE IF EXISTS `subtarefas_task`;
CREATE TABLE IF NOT EXISTS `subtarefas_task` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tarefa_id` int NOT NULL,
  `titulo` varchar(500) NOT NULL,
  `concluida` tinyint(1) DEFAULT '0',
  `concluida_em` datetime DEFAULT NULL,
  `criador_id` int DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_tarefa` (`tarefa_id`)
<<<<<<< HEAD
) ENGINE=MyISAM AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
=======
) ENGINE=MyISAM AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
>>>>>>> 296c60d546f50bc39f8894d961744045aa1e7d96

--
-- Despejando dados para a tabela `subtarefas_task`
--

INSERT INTO `subtarefas_task` (`id`, `tarefa_id`, `titulo`, `concluida`, `concluida_em`, `criador_id`, `created_at`) VALUES
(1, 2, 'indo separar', 1, '2026-04-13 20:26:31', 15, '2026-04-13 15:46:07'),
(2, 1, 'Verificar estoque', 1, '2026-04-13 20:25:44', 15, '2026-04-13 17:23:41'),
(3, 1, 'Separar itens', 0, NULL, 15, '2026-04-13 17:23:41'),
(4, 5, 'ainda falta embrulhar', 1, '2026-04-14 18:17:29', 20, '2026-04-14 11:49:13'),
(5, 5, 'falta alguém levar la depois de embrulhado', 1, '2026-04-14 18:17:30', 20, '2026-04-14 11:49:34'),
(6, 6, 'pegar o numero com alguém', 1, '2026-04-14 17:11:03', 20, '2026-04-14 14:10:34');

-- --------------------------------------------------------

--
-- Estrutura para tabela `tarefas_task`
--

DROP TABLE IF EXISTS `tarefas_task`;
CREATE TABLE IF NOT EXISTS `tarefas_task` (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `numero` varchar(20) DEFAULT NULL,
  `titulo` varchar(255) NOT NULL,
  `descricao` text,
  `prioridade` enum('baixa','media','alta','urgente') DEFAULT 'media',
  `status_id` int UNSIGNED DEFAULT NULL,
  `group_id` int DEFAULT NULL,
  `espaco_id` int UNSIGNED DEFAULT NULL,
  `criador_id` bigint NOT NULL,
  `responsavel_id` bigint DEFAULT NULL,
  `tempo_estimado` int DEFAULT '0',
  `prazo` datetime DEFAULT NULL,
  `concluida_em` datetime DEFAULT NULL,
  `concluida_por` bigint DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `start_date` datetime DEFAULT NULL,
  `tempo_gasto` varchar(50) DEFAULT NULL,
  `tempo_restante` varchar(50) DEFAULT NULL,
  `relator_id` int DEFAULT NULL,
  `cor_card` varchar(7) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `numero` (`numero`),
  KEY `idx_group` (`group_id`),
  KEY `idx_status` (`status_id`),
  KEY `idx_responsavel` (`responsavel_id`)
<<<<<<< HEAD
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
=======
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
>>>>>>> 296c60d546f50bc39f8894d961744045aa1e7d96

--
-- Despejando dados para a tabela `tarefas_task`
--

INSERT INTO `tarefas_task` (`id`, `numero`, `titulo`, `descricao`, `prioridade`, `status_id`, `group_id`, `espaco_id`, `criador_id`, `responsavel_id`, `tempo_estimado`, `prazo`, `concluida_em`, `concluida_por`, `created_at`, `updated_at`, `start_date`, `tempo_gasto`, `tempo_restante`, `relator_id`, `cor_card`) VALUES
(1, 'TASK-1', 'separar o pedido', NULL, 'media', 2, NULL, 1, 15, NULL, 0, NULL, NULL, NULL, '2026-04-13 18:45:13', '2026-04-13 20:06:12', NULL, NULL, NULL, 15, NULL),
(2, 'TDT-1', 'separar o pedido', NULL, 'media', 9, NULL, 3, 15, 19, 0, '2026-04-17 15:46:00', NULL, NULL, '2026-04-13 18:45:52', '2026-04-13 20:26:42', '2026-04-13 15:47:00', '2h', NULL, 15, NULL),
(3, 'TDT-2', 'Criar nota para o pedido', NULL, 'media', 9, 3, 3, 20, 20, 0, NULL, '2026-04-13 20:28:33', 20, '2026-04-13 20:28:20', '2026-04-13 20:28:39', NULL, NULL, NULL, 20, NULL),
(4, 'PDV-1', 'Aguardando venda', NULL, 'media', 12, 3, 4, 20, NULL, 0, NULL, NULL, NULL, '2026-04-13 20:54:44', '2026-04-13 20:54:44', NULL, NULL, NULL, 20, NULL),
(5, 'PDVN-1', 'enviar para estoque', NULL, 'media', 22, 3, 6, 20, 24, 2, NULL, NULL, NULL, '2026-04-14 14:09:12', '2026-04-14 20:09:59', NULL, NULL, NULL, 20, NULL),
(6, 'PDVN-2', 'Faturar o pedido', 'Preciso faturar o numero do <b>pedido</b>', 'urgente', 20, 3, 6, 20, 15, 0, '2026-04-15 13:48:00', NULL, NULL, '2026-04-14 16:48:11', '2026-04-14 20:48:53', NULL, NULL, NULL, 20, '#000000'),
(7, 'PDVN-3', 'pegar o pedido', NULL, 'media', 22, 10, 6, 27, 27, 0, NULL, NULL, NULL, '2026-04-14 18:04:14', '2026-04-14 19:25:57', NULL, NULL, NULL, 27, NULL);

-- --------------------------------------------------------

--
-- Estrutura para tabela `tarefa_categorias_task`
--

DROP TABLE IF EXISTS `tarefa_categorias_task`;
CREATE TABLE IF NOT EXISTS `tarefa_categorias_task` (
  `tarefa_id` int NOT NULL,
  `categoria_id` int NOT NULL,
  PRIMARY KEY (`tarefa_id`,`categoria_id`)
<<<<<<< HEAD
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
=======
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
>>>>>>> 296c60d546f50bc39f8894d961744045aa1e7d96

-- --------------------------------------------------------

--
-- Estrutura para tabela `tarefa_historico_status_task`
--

DROP TABLE IF EXISTS `tarefa_historico_status_task`;
CREATE TABLE IF NOT EXISTS `tarefa_historico_status_task` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tarefa_id` int NOT NULL,
  `status_id` int DEFAULT NULL,
  `status_nome` varchar(100) DEFAULT NULL,
  `status_cor` varchar(7) DEFAULT NULL,
  `responsavel_id` int DEFAULT NULL,
  `responsavel_group_id` int DEFAULT NULL,
  `entrou_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `saiu_em` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_tarefa` (`tarefa_id`),
  KEY `idx_status` (`status_id`)
<<<<<<< HEAD
) ENGINE=MyISAM AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
=======
) ENGINE=MyISAM AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
>>>>>>> 296c60d546f50bc39f8894d961744045aa1e7d96

--
-- Despejando dados para a tabela `tarefa_historico_status_task`
--

INSERT INTO `tarefa_historico_status_task` (`id`, `tarefa_id`, `status_id`, `status_nome`, `status_cor`, `responsavel_id`, `responsavel_group_id`, `entrou_em`, `saiu_em`) VALUES
(1, 1, 2, NULL, NULL, NULL, NULL, '2026-04-13 20:06:12', NULL),
(2, 2, 9, 'Feito', '#10b981', 19, 1, '2026-04-13 20:26:43', NULL),
(3, 3, 7, 'A Fazer', '#6b7280', NULL, 3, '2026-04-13 20:28:21', '2026-04-13 20:28:40'),
(4, 3, 9, 'Feito', '#10b981', 20, 3, '2026-04-13 20:28:40', NULL),
(5, 4, 12, 'A Fazer', '#6b7280', NULL, 3, '2026-04-13 20:54:44', NULL),
(6, 5, 20, 'A Fazer', '#6b7280', NULL, 3, '2026-04-14 14:09:12', '2026-04-14 14:39:30'),
(7, 5, 21, 'Fazendo', '#f59e0b', 24, 3, '2026-04-14 14:39:30', '2026-04-14 14:39:56'),
(8, 5, 22, 'Feito', '#10b981', 24, 3, '2026-04-14 14:39:56', '2026-04-14 14:39:57'),
(9, 5, 21, 'Fazendo', '#f59e0b', 24, 3, '2026-04-14 14:39:57', '2026-04-14 14:39:57'),
(10, 5, 20, 'A Fazer', '#6b7280', 24, 3, '2026-04-14 14:39:57', '2026-04-14 14:40:37'),
(11, 5, 21, 'Fazendo', '#f59e0b', 24, 3, '2026-04-14 14:40:37', '2026-04-14 16:47:21'),
(12, 5, 22, 'Feito', '#10b981', 24, 3, '2026-04-14 16:47:21', '2026-04-14 18:22:58'),
(13, 6, 20, 'A Fazer', '#d10099', NULL, 3, '2026-04-14 16:48:11', '2026-04-14 17:11:17'),
(14, 6, 21, 'Fazendo', '#f59e0b', NULL, NULL, '2026-04-14 17:11:17', '2026-04-14 20:48:54'),
(15, 7, 21, 'Fazendo', '#f59e0b', NULL, 10, '2026-04-14 18:04:15', '2026-04-14 19:25:57'),
(16, 5, 21, 'Fazendo', '#f59e0b', 24, 3, '2026-04-14 18:22:58', '2026-04-14 20:10:00'),
(17, 7, 22, 'Feito', '#10b981', 27, 10, '2026-04-14 19:25:57', NULL),
(18, 8, 20, 'A Fazer (pegue o seu ticket)', '#1a1a1a', NULL, 3, '2026-04-14 19:45:10', NULL),
(19, 5, 22, 'Feito', '#10b981', 24, 3, '2026-04-14 20:10:00', NULL),
(20, 6, 20, 'A Fazer (pegue o seu ticket)', '#1a1a1a', 15, NULL, '2026-04-14 20:48:54', NULL);

-- --------------------------------------------------------

--
-- Estrutura para tabela `tarefa_membros_task`
--

DROP TABLE IF EXISTS `tarefa_membros_task`;
CREATE TABLE IF NOT EXISTS `tarefa_membros_task` (
  `tarefa_id` int NOT NULL,
  `usuario_id` int NOT NULL,
  PRIMARY KEY (`tarefa_id`,`usuario_id`)
<<<<<<< HEAD
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
=======
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
>>>>>>> 296c60d546f50bc39f8894d961744045aa1e7d96

-- --------------------------------------------------------

--
-- Estrutura para tabela `templates_espaco_task`
--

DROP TABLE IF EXISTS `templates_espaco_task`;
CREATE TABLE IF NOT EXISTS `templates_espaco_task` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descricao` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cor` varchar(7) COLLATE utf8mb4_unicode_ci DEFAULT '#6554c0',
  `criador_id` int NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_criador` (`criador_id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `templates_espaco_task`
--

INSERT INTO `templates_espaco_task` (`id`, `nome`, `descricao`, `cor`, `criador_id`, `created_at`) VALUES
(3, 'Processo de venda novo', NULL, '#974f0c', 20, '2026-04-14 11:44:01');

-- --------------------------------------------------------

--
-- Estrutura para tabela `template_statuses_task`
--

DROP TABLE IF EXISTS `template_statuses_task`;
CREATE TABLE IF NOT EXISTS `template_statuses_task` (
  `id` int NOT NULL AUTO_INCREMENT,
  `template_id` int NOT NULL,
  `nome` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `cor` varchar(7) COLLATE utf8mb4_unicode_ci DEFAULT '#6b7280',
  `icone` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT 'bi-circle',
  `ordem` int DEFAULT '0',
  `is_final` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_template` (`template_id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `template_statuses_task`
--

INSERT INTO `template_statuses_task` (`id`, `template_id`, `nome`, `cor`, `icone`, `ordem`, `is_final`) VALUES
(9, 3, 'A Fazer', '#6b7280', 'bi-circle', 0, 0),
(10, 3, 'Fazendo', '#f59e0b', 'bi-arrow-right-circle', 1, 0),
(11, 3, 'Feito', '#10b981', 'bi-check-circle', 2, 1),
(12, 3, 'Primeira venda confirmada', '#0052cc', 'bi-circle', 3, 0);

-- --------------------------------------------------------

--
-- Estrutura para tabela `tickets`
--

DROP TABLE IF EXISTS `tickets`;
CREATE TABLE IF NOT EXISTS `tickets` (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `numero` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `id_alfanumerica` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `solicitante_id` bigint NOT NULL,
  `responsavel_id` bigint DEFAULT NULL,
  `group_id` int NOT NULL,
  `categoria_id` int UNSIGNED DEFAULT NULL,
  `subcategoria_id` int UNSIGNED DEFAULT NULL,
  `status_id` int UNSIGNED NOT NULL,
  `prioridade_id` int UNSIGNED NOT NULL,
  `assunto` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descricao_inicial` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `origem` enum('portal','email','whatsapp','telefone','api','interno') COLLATE utf8mb4_unicode_ci DEFAULT 'portal',
  `sla_primeira_resposta_em` datetime DEFAULT NULL,
  `sla_resolucao_em` datetime DEFAULT NULL,
  `primeira_resposta_em` datetime DEFAULT NULL,
  `resolvido_em` datetime DEFAULT NULL,
  `fechado_em` datetime DEFAULT NULL,
  `ultimo_evento_em` datetime DEFAULT CURRENT_TIMESTAMP,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `reopen_count` tinyint UNSIGNED NOT NULL DEFAULT '0' COMMENT 'Quantas vezes o chamado foi reaberto pelo solicitante',
  PRIMARY KEY (`id`),
  UNIQUE KEY `numero` (`numero`),
  UNIQUE KEY `uk_numero` (`numero`),
  UNIQUE KEY `id_alfanumerica` (`id_alfanumerica`),
  KEY `idx_solicitante_id` (`solicitante_id`),
  KEY `idx_responsavel_id` (`responsavel_id`),
  KEY `idx_group_id` (`group_id`),
  KEY `idx_categoria_id` (`categoria_id`),
  KEY `idx_subcategoria_id` (`subcategoria_id`),
  KEY `idx_status_id` (`status_id`),
  KEY `idx_prioridade_id` (`prioridade_id`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_ultimo_evento_em` (`ultimo_evento_em`),
  KEY `idx_origem` (`origem`),
  KEY `idx_comp_group_status` (`group_id`,`status_id`,`created_at`),
  KEY `idx_comp_responsavel_status` (`responsavel_id`,`status_id`,`created_at`),
  KEY `idx_comp_status_criacao` (`status_id`,`created_at`),
  KEY `idx_id_alfanumerica` (`id_alfanumerica`)
) ENGINE=InnoDB AUTO_INCREMENT=35 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `tickets`
--

INSERT INTO `tickets` (`id`, `numero`, `id_alfanumerica`, `solicitante_id`, `responsavel_id`, `group_id`, `categoria_id`, `subcategoria_id`, `status_id`, `prioridade_id`, `assunto`, `descricao_inicial`, `origem`, `sla_primeira_resposta_em`, `sla_resolucao_em`, `primeira_resposta_em`, `resolvido_em`, `fechado_em`, `ultimo_evento_em`, `created_at`, `updated_at`, `reopen_count`) VALUES
(15, 'SUP-2026-00001', NULL, 15, 15, 1, NULL, NULL, 3, 2, 'segundo teste de ticket 2', 'teste numercao', '', NULL, NULL, NULL, NULL, NULL, '2026-03-31 10:53:14', '2026-03-31 13:53:14', '2026-04-08 19:50:55', 0),
(16, 'SUP-2026-00002', NULL, 15, 15, 1, NULL, NULL, 2, 2, 'Teste final do sistema', 'Deve gerar ID alfanumérica', 'portal', NULL, NULL, NULL, NULL, NULL, '2026-03-31 11:34:45', '2026-03-31 14:34:45', '2026-04-08 19:50:46', 0),
(17, 'SUP-2026-00003', NULL, 15, NULL, 1, NULL, NULL, 1, 2, 'tests 1111', 'tetset1111', '', NULL, NULL, NULL, NULL, NULL, '2026-03-31 12:20:32', '2026-03-31 15:20:32', '2026-03-31 15:20:32', 0),
(18, 'SUP-2026-00004', 'SU0018N6T4', 15, 19, 1, NULL, NULL, 1, 2, 'novo teste 1234', 'teste 1235456', '', NULL, NULL, NULL, NULL, NULL, '2026-03-31 17:36:13', '2026-03-31 20:36:13', '2026-03-31 20:36:30', 0),
(19, 'SUP-2026-00005', 'SU0019N6T0', 19, 15, 1, NULL, NULL, 3, 1, 'segundo teste de ticket 2', 'teste 222', '', NULL, NULL, NULL, NULL, NULL, '2026-03-31 19:14:58', '2026-03-31 22:14:58', '2026-04-08 19:51:01', 0),
(21, 'SUP-2026-00006', 'SU0021N6T7', 20, 23, 3, NULL, NULL, 4, 2, 'segundo teste de ticket3', 'estou realizando um teste novo de ticket', '', NULL, NULL, '2026-04-07 15:28:42', '2026-04-10 10:03:15', NULL, '2026-04-07 15:23:18', '2026-04-07 18:23:18', '2026-04-10 13:03:15', 0),
(22, 'FAT-2026-00001', 'FA0022N6T0', 20, 15, 5, 1, 1, 2, 2, 'revisar nota cancelada', 'quero muito ver se essa nota aqui já foi cancelada 44888215855589325', '', NULL, NULL, NULL, NULL, NULL, '2026-04-08 09:48:45', '2026-04-08 12:48:45', '2026-04-08 14:53:18', 0),
(23, 'FAT-2026-00002', 'FA0023N6T6', 20, 15, 5, 2, NULL, 3, 2, 'tests222', '222teste', '', NULL, NULL, NULL, NULL, NULL, '2026-04-08 10:20:16', '2026-04-08 13:20:16', '2026-04-08 19:50:14', 0),
(24, 'FAT-2026-00003', 'FA0024N6T2', 20, 15, 5, 2, NULL, 3, 2, 'novotetst', 'testaset', '', NULL, NULL, NULL, NULL, NULL, '2026-04-08 10:22:48', '2026-04-08 13:22:48', '2026-04-08 19:50:08', 0),
(25, 'FAT-2026-00004', 'FA0025N6T8', 20, 15, 5, 2, NULL, 3, 2, 'segundo teste de ticket 2', 'testes', '', NULL, NULL, NULL, NULL, NULL, '2026-04-08 13:14:32', '2026-04-08 16:14:32', '2026-04-08 19:50:03', 0),
(27, 'SUP-2026-00007', 'SU0027N6T3', 24, NULL, 1, NULL, NULL, 1, 2, 'Teste natalia', 'Ticket natalia', '', NULL, NULL, NULL, NULL, NULL, '2026-04-08 17:22:08', '2026-04-08 20:22:08', '2026-04-08 20:37:50', 0),
(28, 'SUP-2026-00008', 'SU0028N6T9', 24, 19, 1, 4, NULL, 4, 2, 'novo teste da natalia', 'nati teste', '', NULL, NULL, NULL, NULL, NULL, '2026-04-08 17:47:13', '2026-04-08 20:47:13', '2026-04-08 21:04:51', 0),
(29, 'SUP-2026-00009', 'SU0029N6T5', 20, 19, 1, 4, NULL, 5, 2, 'teste para o suporte', 'teste para o suporte', '', NULL, NULL, NULL, NULL, NULL, '2026-04-09 14:55:18', '2026-04-09 17:55:18', '2026-04-09 20:09:22', 0),
(30, 'SUP-2026-00010', 'SU0030N6T6', 20, 19, 1, 4, 4, 4, 4, 'novo teste de agora', 'novo teste de agora para testar', '', NULL, NULL, '2026-04-09 17:46:56', '2026-04-10 09:23:20', NULL, '2026-04-09 17:40:09', '2026-04-09 20:40:09', '2026-04-10 12:23:20', 0),
(31, 'SUP-2026-00011', 'SU0031N6T2', 23, 19, 1, 4, 4, 4, 2, 'ultimo teste', 'ultimo teste da assistencia para o suporte', '', NULL, NULL, '2026-04-10 10:05:10', '2026-04-10 10:06:35', NULL, '2026-04-10 10:03:59', '2026-04-10 13:03:59', '2026-04-10 13:06:35', 0),
(33, 'ASS-2026-00001', 'AS0033N6T2', 19, 23, 3, 3, 2, 2, 3, 'novo teste para assistencia 2', 'novo teste para assistencia 2', '', NULL, NULL, NULL, NULL, NULL, '2026-04-10 10:35:19', '2026-04-10 13:35:19', '2026-04-10 13:35:34', 0),
(34, 'SUP-2026-00012', 'SU0034N6T0', 23, 19, 1, 4, 4, 4, 4, 'teste de avaliação', 'teste de avaliação', '', NULL, NULL, '2026-04-10 14:40:57', '2026-04-10 14:41:48', NULL, '2026-04-10 14:40:31', '2026-04-10 17:40:31', '2026-04-10 17:41:48', 0);

-- --------------------------------------------------------

--
-- Estrutura para tabela `ticket_anexos`
--

DROP TABLE IF EXISTS `ticket_anexos`;
CREATE TABLE IF NOT EXISTS `ticket_anexos` (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `ticket_id` bigint UNSIGNED NOT NULL,
  `interacao_id` bigint UNSIGNED DEFAULT NULL,
  `nome_original` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `caminho_arquivo` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `mime_type` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tamanho_bytes` bigint UNSIGNED DEFAULT NULL,
  `enviado_por` bigint NOT NULL,
  `ativo` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_ticket_id` (`ticket_id`),
  KEY `idx_interacao_id` (`interacao_id`),
  KEY `idx_enviado_por` (`enviado_por`),
  KEY `idx_ativo` (`ativo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `ticket_avaliacoes`
--

DROP TABLE IF EXISTS `ticket_avaliacoes`;
CREATE TABLE IF NOT EXISTS `ticket_avaliacoes` (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `ticket_id` bigint UNSIGNED NOT NULL,
  `solicitante_id` bigint NOT NULL,
  `responsavel_id` bigint DEFAULT NULL,
  `group_id` int DEFAULT NULL,
  `estrelas` tinyint UNSIGNED DEFAULT NULL,
  `comentario` text COLLATE utf8mb4_unicode_ci,
  `popup_count` tinyint UNSIGNED NOT NULL DEFAULT '0',
  `avaliado_em` datetime DEFAULT NULL,
  `expira_em` datetime NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_ticket` (`ticket_id`)
) ;

--
-- Despejando dados para a tabela `ticket_avaliacoes`
--

INSERT INTO `ticket_avaliacoes` (`id`, `ticket_id`, `solicitante_id`, `responsavel_id`, `group_id`, `estrelas`, `comentario`, `popup_count`, `avaliado_em`, `expira_em`, `created_at`) VALUES
(1, 34, 23, 19, 1, 10, 'teste ok', 2, '2026-04-10 14:43:07', '2026-04-17 14:41:48', '2026-04-10 14:41:48');

-- --------------------------------------------------------

--
-- Estrutura para tabela `ticket_interacoes`
--

DROP TABLE IF EXISTS `ticket_interacoes`;
CREATE TABLE IF NOT EXISTS `ticket_interacoes` (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `ticket_id` bigint UNSIGNED NOT NULL,
  `usuario_id` bigint NOT NULL,
  `tipo` enum('mensagem','nota_interna','alteracao_status','atribuicao','sistema','encaminhamento','devolucao','sla_iniciado','sla_pausado','sla_retomado','sla_concluido','sla_estourado','reabertura','resolucao') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'mensagem',
  `publico` tinyint(1) DEFAULT '1',
  `mensagem` longtext COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_ticket_id` (`ticket_id`),
  KEY `idx_usuario_id` (`usuario_id`),
  KEY `idx_tipo` (`tipo`),
  KEY `idx_publico` (`publico`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_comp_ticket_created` (`ticket_id`,`created_at`),
  KEY `idx_ticket_publico_criacao` (`ticket_id`,`publico`,`created_at`) COMMENT 'Carregar interações públicas/privadas de um ticket'
) ENGINE=InnoDB AUTO_INCREMENT=101 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `ticket_interacoes`
--

INSERT INTO `ticket_interacoes` (`id`, `ticket_id`, `usuario_id`, `tipo`, `publico`, `mensagem`, `created_at`, `updated_at`) VALUES
(42, 15, 15, '', 1, 'Teste após adicionar updated_at', '2026-03-31 14:33:29', '2026-03-31 14:33:29'),
(43, 17, 15, '', 1, 'testes', '2026-03-31 17:36:37', '2026-03-31 17:36:37'),
(44, 18, 15, '', 1, 'comentario para o usuario', '2026-03-31 20:37:00', '2026-03-31 20:37:00'),
(45, 18, 15, 'nota_interna', 0, 'Comentario interno', '2026-03-31 20:37:07', '2026-03-31 20:37:07'),
(46, 18, 15, 'nota_interna', 0, 'interno 2', '2026-03-31 20:38:31', '2026-03-31 20:38:31'),
(47, 18, 15, '', 1, 'para o usuario 2', '2026-03-31 20:39:13', '2026-03-31 20:39:13'),
(48, 18, 15, 'nota_interna', 0, 'comentario interno 3', '2026-03-31 21:52:10', '2026-03-31 21:52:10'),
(49, 18, 15, '', 1, 'comum 1', '2026-03-31 21:52:47', '2026-03-31 21:52:47'),
(50, 19, 15, 'nota_interna', 0, 'pedir autorizaççao', '2026-03-31 22:15:59', '2026-03-31 22:15:59'),
(51, 19, 15, '', 1, 'ok recebido', '2026-03-31 22:16:26', '2026-03-31 22:16:26'),
(52, 19, 19, '', 1, '123', '2026-04-01 17:38:21', '2026-04-01 17:38:21'),
(53, 19, 19, '', 1, '123', '2026-04-01 17:43:45', '2026-04-01 17:43:45'),
(54, 19, 15, '', 1, '23456', '2026-04-01 17:44:35', '2026-04-01 17:44:35'),
(55, 19, 19, '', 1, 'okok', '2026-04-01 17:44:48', '2026-04-01 17:44:48'),
(59, 21, 15, '', 1, 'teste 222', '2026-04-07 18:28:42', '2026-04-07 18:28:42'),
(60, 21, 15, '', 1, 'teste 222', '2026-04-07 18:51:45', '2026-04-07 18:51:45'),
(61, 21, 15, '', 1, '🔀 Ticket encaminhado para o grupo \'assistencia\' por Administrador', '2026-04-07 18:59:42', '2026-04-07 18:59:42'),
(62, 21, 23, 'atribuicao', 1, '🙋 Usuário #23 assumiu o atendimento deste chamado.', '2026-04-07 19:19:25', '2026-04-07 19:19:25'),
(63, 21, 20, '', 1, 'camila atende ok', '2026-04-07 19:20:36', '2026-04-07 19:20:36'),
(64, 23, 15, 'atribuicao', 1, '🙋 Usuário #15 assumiu o atendimento deste chamado.', '2026-04-08 13:20:27', '2026-04-08 13:20:27'),
(65, 23, 15, 'sla_iniciado', 1, '⏱️ Contagem de SLA iniciada.', '2026-04-08 13:20:27', '2026-04-08 13:20:27'),
(66, 23, 15, 'devolucao', 1, '↩️ Usuário #15 devolveu o chamado para a fila — Motivo: testse.', '2026-04-08 13:21:40', '2026-04-08 13:21:40'),
(67, 23, 15, 'sla_pausado', 1, '⏸️ SLA pausado — Motivo: testse.', '2026-04-08 13:21:40', '2026-04-08 13:21:40'),
(68, 24, 15, 'atribuicao', 1, '🙋 Usuário #15 assumiu o atendimento deste chamado.', '2026-04-08 13:23:08', '2026-04-08 13:23:08'),
(69, 24, 15, 'sla_iniciado', 1, '⏱️ Contagem de SLA iniciada.', '2026-04-08 13:23:08', '2026-04-08 13:23:08'),
(70, 22, 15, 'atribuicao', 1, '🙋 Usuário #15 assumiu o atendimento deste chamado.', '2026-04-08 14:53:18', '2026-04-08 14:53:18'),
(71, 23, 15, 'atribuicao', 1, '🙋 Usuário #15 assumiu o atendimento deste chamado.', '2026-04-08 14:53:24', '2026-04-08 14:53:24'),
(72, 23, 15, 'sla_iniciado', 1, '⏱️ Contagem de SLA iniciada.', '2026-04-08 14:53:24', '2026-04-08 14:53:24'),
(73, 25, 15, 'atribuicao', 1, '🙋 Usuário #15 assumiu o atendimento deste chamado.', '2026-04-08 17:32:47', '2026-04-08 17:32:47'),
(74, 25, 15, 'sla_iniciado', 1, '⏱️ Contagem de SLA iniciada.', '2026-04-08 17:32:47', '2026-04-08 17:32:47'),
(75, 25, 15, 'nota_interna', 0, 'teste', '2026-04-08 17:33:22', '2026-04-08 17:33:22'),
(76, 15, 15, 'atribuicao', 1, '🙋 Usuário #15 assumiu o atendimento deste chamado.', '2026-04-08 19:50:44', '2026-04-08 19:50:44'),
(77, 16, 15, 'atribuicao', 1, '🙋 Usuário #15 assumiu o atendimento deste chamado.', '2026-04-08 19:50:46', '2026-04-08 19:50:46'),
(78, 27, 15, 'atribuicao', 1, '🙋 Usuário #15 assumiu o atendimento deste chamado.', '2026-04-08 20:37:18', '2026-04-08 20:37:18'),
(79, 27, 15, 'devolucao', 1, '↩️ Usuário #15 devolveu o chamado para a fila.', '2026-04-08 20:37:50', '2026-04-08 20:37:50'),
(80, 28, 19, 'atribuicao', 1, '🙋 Usuário #19 assumiu o atendimento deste chamado.', '2026-04-08 20:48:30', '2026-04-08 20:48:30'),
(81, 28, 19, 'sla_iniciado', 1, '⏱️ Contagem de SLA iniciada.', '2026-04-08 20:48:30', '2026-04-08 20:48:30'),
(82, 28, 19, '', 1, 'ok ook oki', '2026-04-08 20:54:24', '2026-04-08 20:54:24'),
(83, 28, 15, 'nota_interna', 0, 'teste', '2026-04-08 22:04:04', '2026-04-08 22:04:04'),
(84, 29, 19, 'atribuicao', 1, '🙋 Usuário #19 assumiu o atendimento deste chamado.', '2026-04-09 17:56:03', '2026-04-09 17:56:03'),
(85, 29, 20, '', 1, 'okok teste', '2026-04-09 18:07:35', '2026-04-09 18:07:35'),
(86, 30, 19, 'atribuicao', 1, '🙋 Usuário #19 assumiu o atendimento deste chamado.', '2026-04-09 20:46:04', '2026-04-09 20:46:04'),
(87, 30, 19, '', 1, 'primeira resposta', '2026-04-09 20:46:56', '2026-04-09 20:46:56'),
(88, 30, 19, 'resolucao', 1, '✅ Chamado finalizado por Usuário #19.', '2026-04-10 12:23:20', '2026-04-10 12:23:20'),
(89, 21, 23, 'resolucao', 1, '✅ Chamado finalizado por Usuário #23.', '2026-04-10 13:03:15', '2026-04-10 13:03:15'),
(90, 31, 19, 'atribuicao', 1, '🙋 Usuário #19 assumiu o atendimento deste chamado.', '2026-04-10 13:04:53', '2026-04-10 13:04:53'),
(91, 31, 19, '', 1, 'teste de primeiro atendimento', '2026-04-10 13:05:10', '2026-04-10 13:05:10'),
(92, 31, 19, 'resolucao', 1, '✅ Chamado finalizado por Usuário #19.', '2026-04-10 13:06:35', '2026-04-10 13:06:35'),
(94, 33, 23, 'atribuicao', 1, '🙋 Usuário #23 assumiu o atendimento deste chamado.', '2026-04-10 13:35:34', '2026-04-10 13:35:34'),
(95, 33, 23, '', 1, 'primeira resposta', '2026-04-10 13:36:07', '2026-04-10 13:36:07'),
(96, 34, 19, 'atribuicao', 1, '🙋 Usuário #19 assumiu o atendimento deste chamado.', '2026-04-10 17:40:42', '2026-04-10 17:40:42'),
(97, 34, 19, '', 1, 'novo teste de avaliação', '2026-04-10 17:40:57', '2026-04-10 17:40:57'),
(98, 34, 23, '', 1, 'teste de avaliação', '2026-04-10 17:41:26', '2026-04-10 17:41:26'),
(99, 34, 19, 'resolucao', 1, '✅ Chamado finalizado por Usuário #19.', '2026-04-10 17:41:48', '2026-04-10 17:41:48'),
(100, 33, 15, 'nota_interna', 0, 'teste', '2026-04-10 17:56:53', '2026-04-10 17:56:53');

-- --------------------------------------------------------

--
-- Estrutura para tabela `ticket_prioridades`
--

DROP TABLE IF EXISTS `ticket_prioridades`;
CREATE TABLE IF NOT EXISTS `ticket_prioridades` (
  `id` int UNSIGNED NOT NULL AUTO_INCREMENT,
  `nome` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nivel` tinyint NOT NULL,
  `descricao` text COLLATE utf8mb4_unicode_ci,
  `cor_hex` varchar(7) COLLATE utf8mb4_unicode_ci DEFAULT '#667eea',
  `sla_horas` int DEFAULT '48',
  `ativo` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nome` (`nome`),
  UNIQUE KEY `nivel` (`nivel`),
  KEY `idx_nivel` (`nivel`),
  KEY `idx_ativo` (`ativo`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `ticket_prioridades`
--

INSERT INTO `ticket_prioridades` (`id`, `nome`, `nivel`, `descricao`, `cor_hex`, `sla_horas`, `ativo`, `created_at`, `updated_at`) VALUES
(1, 'Baixa', 1, 'Prioridade baixa', '#17a2b8', 48, 1, '2026-03-20 17:30:17', '2026-03-20 17:30:17'),
(2, 'Média', 2, 'Prioridade média', '#ffc107', 48, 1, '2026-03-20 17:30:17', '2026-03-20 17:30:17'),
(3, 'Alta', 3, 'Prioridade alta', '#fd7e14', 48, 1, '2026-03-20 17:30:17', '2026-03-20 17:30:17'),
(4, 'Crítica', 4, 'Prioridade crítica', '#dc3545', 48, 1, '2026-03-20 17:30:17', '2026-03-20 17:30:17');

-- --------------------------------------------------------

--
-- Estrutura para tabela `ticket_sla`
--

DROP TABLE IF EXISTS `ticket_sla`;
CREATE TABLE IF NOT EXISTS `ticket_sla` (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `ticket_id` bigint UNSIGNED NOT NULL,
  `categoria_id` int UNSIGNED NOT NULL,
  `sla_minutos` int UNSIGNED NOT NULL COMMENT 'SLA copiado da categoria no momento da abertura',
  `sla_primeira_resposta_minutos` int UNSIGNED DEFAULT NULL,
  `primeira_resposta_em` datetime DEFAULT NULL,
  `iniciado_em` datetime DEFAULT NULL COMMENT 'Quando o atendimento come├ºou (usu├írio assumiu)',
  `pausado_em` datetime DEFAULT NULL COMMENT 'Quando foi pausado pela ├║ltima vez',
  `minutos_pausados` int UNSIGNED NOT NULL DEFAULT '0' COMMENT 'Total de minutos j├í pausados (acumulado)',
  `status` enum('aguardando','em_andamento','pausado','concluido','estourado') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'aguardando',
  `estourou_em` datetime DEFAULT NULL COMMENT 'Momento exato em que o SLA estourou',
  `concluido_em` datetime DEFAULT NULL COMMENT 'Momento em que foi conclu├¡do dentro do prazo',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_ticket_sla` (`ticket_id`),
  KEY `idx_status` (`status`),
  KEY `idx_categoria_id` (`categoria_id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Rastreamento de SLA por ticket';

--
-- Despejando dados para a tabela `ticket_sla`
--

INSERT INTO `ticket_sla` (`id`, `ticket_id`, `categoria_id`, `sla_minutos`, `sla_primeira_resposta_minutos`, `primeira_resposta_em`, `iniciado_em`, `pausado_em`, `minutos_pausados`, `status`, `estourou_em`, `concluido_em`, `created_at`, `updated_at`) VALUES
(1, 23, 2, 1440, NULL, NULL, '2026-04-08 10:20:28', NULL, 91, 'em_andamento', NULL, NULL, '2026-04-08 13:20:16', '2026-04-08 14:53:24'),
(2, 24, 2, 10, NULL, NULL, '2026-04-08 10:23:09', NULL, 0, 'em_andamento', NULL, NULL, '2026-04-08 13:22:48', '2026-04-08 13:23:08'),
(3, 25, 2, 10, NULL, NULL, '2026-04-08 14:32:48', NULL, 0, 'em_andamento', NULL, NULL, '2026-04-08 16:14:32', '2026-04-08 17:32:47'),
(4, 28, 4, 10, NULL, NULL, '2026-04-08 17:48:31', NULL, 0, 'concluido', NULL, '2026-04-08 18:04:51', '2026-04-08 20:47:13', '2026-04-08 21:04:51'),
(5, 29, 4, 4330, 1440, NULL, '2026-04-09 14:55:18', NULL, 0, 'concluido', NULL, '2026-04-09 17:07:49', '2026-04-09 17:55:18', '2026-04-09 20:07:48'),
(6, 30, 4, 4330, 1440, '2026-04-09 17:46:56', '2026-04-09 17:40:09', NULL, 0, 'concluido', NULL, '2026-04-10 09:23:21', '2026-04-09 20:40:09', '2026-04-10 12:23:20'),
(7, 31, 4, 4330, 1440, '2026-04-10 10:05:10', '2026-04-10 10:03:59', NULL, 0, 'concluido', NULL, '2026-04-10 10:06:36', '2026-04-10 13:03:59', '2026-04-10 13:06:35'),
(8, 32, 3, 1440, NULL, NULL, '2026-04-10 10:12:17', NULL, 0, 'em_andamento', NULL, NULL, '2026-04-10 13:12:17', '2026-04-10 13:12:17'),
(9, 33, 3, 20, 3, '2026-04-10 10:36:07', '2026-04-10 10:35:19', NULL, 0, 'em_andamento', NULL, NULL, '2026-04-10 13:35:19', '2026-04-10 13:36:07'),
(10, 34, 4, 4330, 1440, '2026-04-10 14:40:57', '2026-04-10 14:40:31', NULL, 0, 'concluido', NULL, '2026-04-10 14:41:48', '2026-04-10 17:40:31', '2026-04-10 17:41:48');

-- --------------------------------------------------------

--
-- Estrutura para tabela `ticket_status`
--

DROP TABLE IF EXISTS `ticket_status`;
CREATE TABLE IF NOT EXISTS `ticket_status` (
  `id` int UNSIGNED NOT NULL AUTO_INCREMENT,
  `nome` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `descricao` text COLLATE utf8mb4_unicode_ci,
  `ordem` tinyint NOT NULL DEFAULT '0',
  `finalizador` tinyint(1) DEFAULT '0',
  `cor_hex` varchar(7) COLLATE utf8mb4_unicode_ci DEFAULT '#667eea',
  `ativo` tinyint(1) DEFAULT '1',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `nome` (`nome`),
  KEY `idx_ordem` (`ordem`),
  KEY `idx_finalizador` (`finalizador`),
  KEY `idx_ativo` (`ativo`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `ticket_status`
--

INSERT INTO `ticket_status` (`id`, `nome`, `descricao`, `ordem`, `finalizador`, `cor_hex`, `ativo`, `created_at`, `updated_at`) VALUES
(1, 'Aberto', 'Ticket recém aberto', 0, 0, '#667eea', 1, '2026-03-20 17:24:13', '2026-03-20 17:24:13'),
(2, 'Em Andamento', 'Ticket sendo atendido', 0, 0, '#667eea', 1, '2026-03-20 17:24:13', '2026-03-20 17:24:13'),
(3, 'Aguardando', 'Aguardando resposta do usuário', 0, 0, '#667eea', 1, '2026-03-20 17:24:13', '2026-03-20 17:24:13'),
(4, 'Resolvido', 'Problema resolvido', 0, 0, '#667eea', 1, '2026-03-20 17:24:13', '2026-03-20 17:24:13'),
(5, 'Fechado', 'Ticket encerrado', 0, 0, '#667eea', 1, '2026-03-20 17:24:13', '2026-03-20 17:24:13');

-- --------------------------------------------------------

--
-- Estrutura para tabela `users`
--

DROP TABLE IF EXISTS `users`;
CREATE TABLE IF NOT EXISTS `users` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(120) NOT NULL,
  `email` varchar(190) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` enum('USER','TI','ADMIN','RESPONSAVEL_GRUPO') DEFAULT 'USER',
  `sector` varchar(120) DEFAULT NULL,
  `unit` varchar(120) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `username` varchar(50) DEFAULT NULL,
  `department_id` int DEFAULT NULL,
  `group_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `username` (`username`),
  KEY `idx_department` (`department_id`),
  KEY `idx_group` (`group_id`)
<<<<<<< HEAD
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
=======
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
>>>>>>> 296c60d546f50bc39f8894d961744045aa1e7d96

--
-- Despejando dados para a tabela `users`
--

INSERT INTO `users` (`id`, `name`, `email`, `password_hash`, `role`, `sector`, `unit`, `is_active`, `created_at`, `username`, `department_id`, `group_id`) VALUES
(15, 'Administrador', 'admin@cpe.com.br', '$2b$12$cUzgsKcnlFpM4RLi4s6ice887vhB4RqDprqSCAeeTLpCiyhnjLkZ.', 'ADMIN', NULL, NULL, 1, '2026-03-18 21:01:36', 'admin', NULL, NULL),
(17, 'Manager System', 'manager@cpe.com.br', '$2b$12$e5owWqUGPxvGMQdM3dUVDe2O0k0vqCqRVJr.qiHqnINNk.G9K2i3O', 'TI', NULL, NULL, 1, '2026-03-18 21:01:36', 'manager', NULL, 1),
(19, 'jonathan', 'jonathan2@cpe.com.br', '$2b$12$gAsoH/SsdblwHN.kd9djQeFMXb3Kep0q8rUbfe0kNSYbPTlw.X2Xa', 'USER', NULL, NULL, 1, '2026-03-18 21:43:48', 'jonathan.lopes2', NULL, 1),
(20, 'fernanda', 'fernandateste@cpe.com.br', '$2b$12$14PTC6nIsDE1TBi9/tOGZuDT2WmTMAB3R6mdqXCZ6mMGnahe8k4Xe', 'RESPONSAVEL_GRUPO', NULL, NULL, 1, '2026-03-18 22:19:27', 'fernanda.teste', NULL, 3),
(22, 'jose', 'jose@cpe.com.br', '$2b$12$lstGgaNJYVLuzX9bI4fci.WZ8mXCHpZzyknSfeqhyztfJtmefYKii', 'RESPONSAVEL_GRUPO', NULL, NULL, 1, '2026-04-02 20:10:25', 'jose.jose', NULL, 1),
(23, 'camila', 'camila@cpe.com.br', '$2b$12$N61JAIvgCTDXXI/H.B0ryuKI8vxcr8FayHrj5DxrXHAkreSiKg3km', 'USER', NULL, NULL, 1, '2026-04-07 18:34:51', 'camila.teste', NULL, 3),
(24, 'Natalia', 'nataliateste@cpe.com.br', '$2b$12$dgxPx/f02y8Tunam4JQ4Mus3rwIalJZDtzA6.OX/rfEbPGFVrJr62', 'USER', NULL, NULL, 1, '2026-04-08 20:12:31', 'natalia.teste', NULL, 3),
(25, 'Edson Cardoso', 'edson.teste@cpe.com.br', '$2b$12$Yo0zLMdHTveMBBgHF/e98u9VUNZ8a5LwmuseMVtyNk1g0I/WJo0ZC', 'RESPONSAVEL_GRUPO', NULL, NULL, 1, '2026-04-13 21:57:09', 'edson.teste', NULL, 9),
(26, 'Jean Teste', 'jean.teste@cpe.com.br', '$2b$12$UNTpfhH21Ipc0eE1TLEgouNLRfFeAAePyw.WmF1WkSkeXPDcqLA/6', 'USER', NULL, NULL, 1, '2026-04-13 21:57:38', 'jean.teste', NULL, 9),
(27, 'viviane - faturamento', 'viviane.teste@cpe.com.br', '$2b$12$wrzip7RZG2TmkMeS7QHNc.Giln4yz2RguDiR83k5MB9dM2vq6iJri', 'RESPONSAVEL_GRUPO', NULL, NULL, 1, '2026-04-14 13:26:22', 'viviane.teste', NULL, 10),
(28, 'Vanessa melo', 'vanessa.teste@cpe.com.br', '$2b$12$fSAaiz3DDTQ5JBMDNqtss.Y3j4sP2NtbLhMPGzEI3NhLxWXstJLzq', 'USER', NULL, NULL, 1, '2026-04-14 13:26:53', 'vanessa.teste', NULL, 10);

-- --------------------------------------------------------

--
-- Estrutura para tabela `user_access_exceptions`
--

DROP TABLE IF EXISTS `user_access_exceptions`;
CREATE TABLE IF NOT EXISTS `user_access_exceptions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL COMMENT 'Usuário afetado',
  `page_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Nome da página',
  `exception_type` enum('block','allow') COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'block = bloquear, allow = permitir',
  `reason` text COLLATE utf8mb4_unicode_ci COMMENT 'Motivo da exceção',
  `created_by` int DEFAULT NULL COMMENT 'Admin que criou',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_user_page_type` (`user_id`,`page_name`,`exception_type`),
  KEY `idx_uae_user_id` (`user_id`),
  KEY `idx_uae_page_name` (`page_name`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estrutura stand-in para view `vw_historico_notificacoes`
-- (Veja abaixo para a visão atual)
--
DROP VIEW IF EXISTS `vw_historico_notificacoes`;
CREATE TABLE IF NOT EXISTS `vw_historico_notificacoes` (
`created_at` timestamp
,`id` int
,`lido` tinyint(1)
,`mensagem` varchar(255)
,`ticket_assunto` varchar(255)
,`ticket_id` int
,`ticket_numero` varchar(20)
,`tipo` varchar(50)
,`updated_at` timestamp
,`usuario_id` int
,`usuario_nome` varchar(120)
);

-- --------------------------------------------------------

--
-- Estrutura stand-in para view `vw_notificacoes_nao_lidas`
-- (Veja abaixo para a visão atual)
--
DROP VIEW IF EXISTS `vw_notificacoes_nao_lidas`;
CREATE TABLE IF NOT EXISTS `vw_notificacoes_nao_lidas` (
`atribuidos` bigint
,`finalizados` bigint
,`respondidos` bigint
,`total_nao_lidas` bigint
,`transferidos` bigint
,`ultima_notificacao` timestamp
,`usuario_id` bigint
,`usuario_nome` varchar(120)
);

-- --------------------------------------------------------

--
-- Estrutura para view `vw_historico_notificacoes`
--
DROP TABLE IF EXISTS `vw_historico_notificacoes`;

DROP VIEW IF EXISTS `vw_historico_notificacoes`;
CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vw_historico_notificacoes`  AS SELECT `n`.`id` AS `id`, `n`.`ticket_id` AS `ticket_id`, `t`.`numero` AS `ticket_numero`, `t`.`assunto` AS `ticket_assunto`, `n`.`usuario_id` AS `usuario_id`, `u`.`name` AS `usuario_nome`, `n`.`mensagem` AS `mensagem`, `n`.`tipo` AS `tipo`, `n`.`lido` AS `lido`, `n`.`created_at` AS `created_at`, `n`.`updated_at` AS `updated_at` FROM ((`notificacoes` `n` join `tickets` `t` on((`n`.`ticket_id` = `t`.`id`))) join `users` `u` on((`n`.`usuario_id` = `u`.`id`))) ORDER BY `n`.`created_at` DESC ;

-- --------------------------------------------------------

--
-- Estrutura para view `vw_notificacoes_nao_lidas`
--
DROP TABLE IF EXISTS `vw_notificacoes_nao_lidas`;

DROP VIEW IF EXISTS `vw_notificacoes_nao_lidas`;
CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vw_notificacoes_nao_lidas`  AS SELECT `u`.`id` AS `usuario_id`, `u`.`name` AS `usuario_nome`, count(`n`.`id`) AS `total_nao_lidas`, count((case when (`n`.`tipo` = 'atribuido') then 1 end)) AS `atribuidos`, count((case when (`n`.`tipo` = 'respondido') then 1 end)) AS `respondidos`, count((case when (`n`.`tipo` = 'transferido') then 1 end)) AS `transferidos`, count((case when (`n`.`tipo` = 'finalizado') then 1 end)) AS `finalizados`, max(`n`.`created_at`) AS `ultima_notificacao` FROM (`users` `u` left join `notificacoes` `n` on(((`u`.`id` = `n`.`usuario_id`) and (`n`.`lido` = false)))) GROUP BY `u`.`id`, `u`.`name` ORDER BY `total_nao_lidas` DESC ;

--
-- Restrições para tabelas despejadas
--

--
-- Restrições para tabelas `categorias`
--
ALTER TABLE `categorias`
  ADD CONSTRAINT `fk_categorias_group` FOREIGN KEY (`group_id`) REFERENCES `cpe_grupo` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `cpe_grupo`
--
ALTER TABLE `cpe_grupo`
  ADD CONSTRAINT `cpe_grupo_ibfk_1` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `passwords`
--
ALTER TABLE `passwords`
  ADD CONSTRAINT `fk_passwords_group` FOREIGN KEY (`group_id`) REFERENCES `cpe_grupo` (`id`) ON DELETE SET NULL;

--
-- Restrições para tabelas `subcategorias`
--
ALTER TABLE `subcategorias`
  ADD CONSTRAINT `fk_subcategorias_categoria` FOREIGN KEY (`categoria_id`) REFERENCES `categorias` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `template_statuses_task`
--
ALTER TABLE `template_statuses_task`
  ADD CONSTRAINT `template_statuses_task_ibfk_1` FOREIGN KEY (`template_id`) REFERENCES `templates_espaco_task` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `tickets`
--
ALTER TABLE `tickets`
  ADD CONSTRAINT `fk_tickets_categoria` FOREIGN KEY (`categoria_id`) REFERENCES `categorias` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `fk_tickets_group` FOREIGN KEY (`group_id`) REFERENCES `cpe_grupo` (`id`) ON DELETE RESTRICT,
  ADD CONSTRAINT `fk_tickets_prioridade` FOREIGN KEY (`prioridade_id`) REFERENCES `ticket_prioridades` (`id`) ON DELETE RESTRICT,
  ADD CONSTRAINT `fk_tickets_responsavel` FOREIGN KEY (`responsavel_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `fk_tickets_solicitante` FOREIGN KEY (`solicitante_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT,
  ADD CONSTRAINT `fk_tickets_status` FOREIGN KEY (`status_id`) REFERENCES `ticket_status` (`id`) ON DELETE RESTRICT,
  ADD CONSTRAINT `fk_tickets_subcategoria` FOREIGN KEY (`subcategoria_id`) REFERENCES `subcategorias` (`id`) ON DELETE SET NULL;

--
-- Restrições para tabelas `ticket_anexos`
--
ALTER TABLE `ticket_anexos`
  ADD CONSTRAINT `fk_anexos_interacao` FOREIGN KEY (`interacao_id`) REFERENCES `ticket_interacoes` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `fk_anexos_ticket` FOREIGN KEY (`ticket_id`) REFERENCES `tickets` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_anexos_usuario` FOREIGN KEY (`enviado_por`) REFERENCES `users` (`id`) ON DELETE RESTRICT;

--
-- Restrições para tabelas `ticket_interacoes`
--
ALTER TABLE `ticket_interacoes`
  ADD CONSTRAINT `fk_interacoes_ticket` FOREIGN KEY (`ticket_id`) REFERENCES `tickets` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_interacoes_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `users` (`id`) ON DELETE RESTRICT;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
