-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Tempo de geração: 01/05/2026 às 00:21
-- Versão do servidor: 10.4.32-MariaDB
-- Versão do PHP: 8.2.12

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

CREATE TABLE `categorias` (
  `id` int(10) UNSIGNED NOT NULL,
  `group_id` int(11) NOT NULL,
  `nome` varchar(255) NOT NULL,
  `descricao` text DEFAULT NULL,
  `sla_minutos` int(10) UNSIGNED DEFAULT NULL COMMENT 'SLA em minutos. NULL = sem SLA definido.',
  `sla_primeira_resposta_minutos` int(10) UNSIGNED DEFAULT NULL,
  `ativo` tinyint(1) DEFAULT 1,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `categorias`
--

INSERT INTO `categorias` (`id`, `group_id`, `nome`, `descricao`, `sla_minutos`, `sla_primeira_resposta_minutos`, `ativo`, `created_at`, `updated_at`) VALUES
(1, 5, 'Notas a cancelar', 'categoria destinado a notas a cancelar', 2880, 120, 1, '2026-04-08 12:45:57', '2026-04-09 17:54:06'),
(2, 5, 'notas ja emitida', 'teste emição', 10, NULL, 1, '2026-04-08 13:19:44', '2026-04-08 13:22:25'),
(3, 3, 'notas ja emitida', 'tsetes', 1440, NULL, 1, '2026-04-08 17:34:56', '2026-04-08 17:34:56'),
(4, 1, 'suporte simples', 'suporte rapido', 5770, 1440, 1, '2026-04-08 20:46:47', '2026-04-16 20:34:24'),
(5, 1, 'testse t222', 'teste 22', 10, NULL, 0, '2026-04-09 12:49:39', '2026-04-09 17:45:09'),
(6, 9, 'separar pedidos', NULL, 1440, 60, 1, '2026-04-22 17:05:02', '2026-04-22 17:05:02');

-- --------------------------------------------------------

--
-- Estrutura para tabela `categorias_task`
--

CREATE TABLE `categorias_task` (
  `id` int(11) NOT NULL,
  `espaco_id` int(11) DEFAULT NULL,
  `group_id` int(11) DEFAULT NULL,
  `nome` varchar(100) NOT NULL,
  `cor` varchar(7) DEFAULT '#6554c0',
  `created_at` datetime DEFAULT current_timestamp()
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `categorias_task`
--

INSERT INTO `categorias_task` (`id`, `espaco_id`, `group_id`, `nome`, `cor`, `created_at`) VALUES
(1, 8, 3, 'exemplo 1', '#ffc107', '2026-04-21 19:55:23'),
(2, 8, 3, 'exemplo 2', '#474747', '2026-04-21 19:55:38'),
(3, 8, 3, 'exemplo 3', '#605534', '2026-04-21 20:04:58'),
(4, 8, 9, 'exemplo 4', '#ffc107', '2026-04-21 20:19:48');

-- --------------------------------------------------------

--
-- Estrutura para tabela `cofre_senhas`
--

CREATE TABLE `cofre_senhas` (
  `id` int(11) NOT NULL,
  `cofre_user_id` int(11) NOT NULL,
  `cofre_client` varchar(255) NOT NULL,
  `cofre_email` varchar(255) DEFAULT NULL,
  `cofre_description` varchar(500) NOT NULL,
  `cofre_password` text NOT NULL,
  `cofre_link` varchar(500) DEFAULT NULL,
  `cofre_observation` text DEFAULT NULL,
  `cofre_group_id` int(11) DEFAULT NULL,
  `cofre_is_public` tinyint(1) DEFAULT 0,
  `cofre_is_exclusive` tinyint(1) DEFAULT 0,
  `cofre_allowed_group_id` int(11) DEFAULT NULL,
  `cofre_created_at` datetime DEFAULT current_timestamp(),
  `cofre_updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `cofre_senhas`
--

INSERT INTO `cofre_senhas` (`id`, `cofre_user_id`, `cofre_client`, `cofre_email`, `cofre_description`, `cofre_password`, `cofre_link`, `cofre_observation`, `cofre_group_id`, `cofre_is_public`, `cofre_is_exclusive`, `cofre_allowed_group_id`, `cofre_created_at`, `cofre_updated_at`) VALUES
(1, 1, 'tese', 'admin@cpe.com.br', 'teste', '22223333', 'https://github.com/cpeinfra-cmyk/cpenavigator', 'teste22', NULL, 0, 0, NULL, '2026-03-07 07:17:57', '2026-03-07 07:17:57'),
(2, 1, 'teste 55', 'admin@cpe.com.br', 'teste 44', 'd3d5t7gas1436', 'https://github.com/cpeinfra-cmyk/cpenavigator', '3d3t', NULL, 0, 0, NULL, '2026-03-07 16:27:31', '2026-03-07 16:27:31'),
(4, 1, 'Jon', 'admin@cpe.com.br', 'teste jon', 'jon123', 'https://github.com/login/oauth/authorize', 'teste jon', NULL, 0, 0, NULL, '2026-03-10 14:57:10', '2026-03-10 14:57:10'),
(5, 25, 'google', 'edson.teste@cpe.com.br', 'Senha teste Google', 'Senhadificil123', 'https://app.seedprod.com/login', NULL, 9, 0, 0, 9, '2026-04-23 17:52:36', '2026-04-23 17:52:36'),
(6, 25, 'google2', 'edson.teste@cpe.com.br', 'Senha teste Google', '1232131231232131', '123', '123', 9, 0, 1, 9, '2026-04-23 17:53:08', '2026-04-23 17:53:08');

-- --------------------------------------------------------

--
-- Estrutura para tabela `comentarios_task`
--

CREATE TABLE `comentarios_task` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `tarefa_id` bigint(20) UNSIGNED NOT NULL,
  `etapa_id` bigint(20) UNSIGNED DEFAULT NULL,
  `autor_id` bigint(20) NOT NULL,
  `texto` text NOT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `comentarios_task`
--

INSERT INTO `comentarios_task` (`id`, `tarefa_id`, `etapa_id`, `autor_id`, `texto`, `created_at`) VALUES
(2, 6, NULL, 20, 'Urgente! Precisa ser resolvido com prioridade.', '2026-04-14 17:11:33'),
(4, 6, NULL, 20, 'teste comentario', '2026-04-14 17:18:43'),
(13, 7, NULL, 20, '123\n<img src=\"/SistemaCPE/web/assests/uploads/tasks/2cb73532cca448da9786b1c92c4f77fc.jpg\" style=\"max-width:100%;border-radius:6px;\">', '2026-04-14 18:13:40');

-- --------------------------------------------------------

--
-- Estrutura para tabela `contratos`
--

CREATE TABLE `contratos` (
  `id` int(11) NOT NULL,
  `pasta_id` int(11) NOT NULL,
  `nome` varchar(255) NOT NULL,
  `descricao` text DEFAULT NULL,
  `arquivo_path` varchar(500) NOT NULL,
  `tipo` varchar(10) NOT NULL,
  `tamanho_bytes` int(11) NOT NULL DEFAULT 0,
  `uploaded_by` bigint(20) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `contratos`
--

INSERT INTO `contratos` (`id`, `pasta_id`, `nome`, `descricao`, `arquivo_path`, `tipo`, `tamanho_bytes`, `uploaded_by`, `created_at`) VALUES
(4, 20, 'Termo de Responsabilidade - Jonathan Dos Santos Lopes', 'Notebook A70 ION | SN: AVNB23400202 | Placa-mãe: Avell Avell A70 ION | RAM: 64 GB | Storage: 954 GB', '/SistemaCPE/web/uploads/contratos/termo_1493c6fd5933.pdf', 'pdf', 34756, 15, '2026-04-27 14:19:31');

-- --------------------------------------------------------

--
-- Estrutura para tabela `contrato_pastas`
--

CREATE TABLE `contrato_pastas` (
  `id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  `parent_id` int(11) DEFAULT NULL,
  `nome` varchar(255) NOT NULL,
  `is_root` tinyint(1) NOT NULL DEFAULT 0,
  `created_by` int(11) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `contrato_pastas`
--

INSERT INTO `contrato_pastas` (`id`, `group_id`, `parent_id`, `nome`, `is_root`, `created_by`, `created_at`) VALUES
(1, 1, NULL, 'Suporte', 1, NULL, '2026-04-22 20:56:08'),
(2, 7, NULL, 'teste', 1, NULL, '2026-04-22 20:56:08'),
(3, 3, NULL, 'assistencia', 1, NULL, '2026-04-22 20:56:08'),
(4, 5, NULL, 'Faturamento', 1, NULL, '2026-04-22 20:56:08'),
(5, 4, NULL, 'Financeiro', 1, NULL, '2026-04-22 20:56:08'),
(6, 9, NULL, 'Estoque', 1, NULL, '2026-04-22 20:56:08'),
(7, 10, NULL, 'faturamento', 1, NULL, '2026-04-22 20:56:08'),
(8, 13, NULL, 'Frotas', 1, NULL, '2026-04-22 20:56:08'),
(16, 9, 6, 'exemplo 1', 0, 25, '2026-04-22 20:56:52'),
(19, 14, NULL, 'Suporte ti', 1, NULL, '2026-04-23 14:16:07'),
(20, 14, 19, 'Termos Notebooks 2026', 0, 15, '2026-04-23 14:16:34');

-- --------------------------------------------------------

--
-- Estrutura para tabela `convites_espaco_task`
--

CREATE TABLE `convites_espaco_task` (
  `id` int(11) NOT NULL,
  `espaco_id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  `convidado_por` int(11) NOT NULL,
  `status` enum('pendente','aceito','recusado') DEFAULT 'pendente',
  `created_at` datetime DEFAULT current_timestamp(),
  `respondido_em` datetime DEFAULT NULL,
  `respondido_por` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `convites_espaco_task`
--

INSERT INTO `convites_espaco_task` (`id`, `espaco_id`, `group_id`, `convidado_por`, `status`, `created_at`, `respondido_em`, `respondido_por`) VALUES
(2, 4, 5, 20, 'pendente', '2026-04-14 10:27:19', NULL, NULL),
(3, 4, 10, 20, 'aceito', '2026-04-14 10:27:42', '2026-04-14 10:32:58', 27),
(4, 6, 5, 20, 'pendente', '2026-04-14 11:06:24', NULL, NULL),
(5, 6, 10, 20, 'aceito', '2026-04-14 11:33:33', '2026-04-14 11:37:00', 27),
(6, 6, 3, 20, 'aceito', '2026-04-14 14:55:22', '2026-04-14 14:55:29', 20),
(7, 6, 9, 15, 'recusado', '2026-04-16 13:44:55', '2026-04-21 17:28:22', 25),
(10, 7, 3, 25, 'aceito', '2026-04-21 18:55:19', '2026-04-21 18:58:33', 20),
(11, 8, 3, 25, 'aceito', '2026-04-21 18:56:49', '2026-04-21 18:58:31', 20),
(12, 8, 10, 25, 'aceito', '2026-04-22 14:52:20', '2026-04-22 14:53:30', 27);

-- --------------------------------------------------------

--
-- Estrutura para tabela `cpe_grupo`
--

CREATE TABLE `cpe_grupo` (
  `id` int(11) NOT NULL,
  `department_id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `description` text DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
(10, 4, 'faturamento', NULL, '2026-04-14 13:25:35', '2026-04-14 13:25:35'),
(13, 6, 'Frotas', 'Responsáveis pela gestão e aprovação da frota', '2026-04-15 18:49:51', '2026-04-15 18:49:51'),
(14, 1, 'Suporte ti', NULL, '2026-04-23 14:16:07', '2026-04-23 14:16:07');

-- --------------------------------------------------------

--
-- Estrutura para tabela `departments`
--

CREATE TABLE `departments` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `description` text DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `departments`
--

INSERT INTO `departments` (`id`, `name`, `description`, `created_at`, `updated_at`) VALUES
(1, 'TI', 'Departamento de Tecnologia da Informação', '2026-03-03 21:31:31', '2026-03-03 21:31:31'),
(2, 'RH', 'Departamento de Recursos Humanos', '2026-03-03 21:31:31', '2026-03-03 21:31:31'),
(3, 'Financeiro', 'Departamento Financeiro', '2026-03-03 21:31:31', '2026-03-03 21:31:31'),
(4, 'Administrativo', 'Departamento Administrativo', '2026-03-03 21:31:31', '2026-03-03 21:31:31'),
(6, 'Frotas', 'Departamento de Gestão da Frota de Veículos', '2026-04-15 18:49:51', '2026-04-15 18:49:51');

-- --------------------------------------------------------

--
-- Estrutura para tabela `documents`
--

CREATE TABLE `documents` (
  `id` bigint(20) NOT NULL,
  `title` varchar(255) NOT NULL,
  `content` longtext DEFAULT NULL,
  `visibility` enum('INTERNAL','SECTOR','PRIVATE','TI','RESTRICTED') NOT NULL DEFAULT 'INTERNAL',
  `sector` varchar(120) DEFAULT NULL,
  `owner_user_id` bigint(20) NOT NULL,
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `espacos_task`
--

CREATE TABLE `espacos_task` (
  `id` int(10) UNSIGNED NOT NULL,
  `nome` varchar(255) NOT NULL,
  `chave` varchar(20) NOT NULL,
  `template` varchar(50) DEFAULT 'tarefa',
  `gerenciado_por` enum('equipe','responsavel') DEFAULT 'equipe',
  `group_id` int(11) DEFAULT NULL,
  `criador_id` bigint(20) NOT NULL,
  `cor` varchar(7) DEFAULT '#6554c0',
  `created_at` timestamp NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `espacos_task`
--

INSERT INTO `espacos_task` (`id`, `nome`, `chave`, `template`, `gerenciado_por`, `group_id`, `criador_id`, `cor`, `created_at`) VALUES
(2, 'Teste de Tarefa', 'TDT', 'tarefa', 'equipe', NULL, 15, '#6554c0', '2026-04-13 18:15:16'),
(3, 'teste de tarefa', 'TDT', 'tarefa', 'equipe', NULL, 15, '#974f0c', '2026-04-13 18:16:12'),
(4, 'Processo de venda', 'PDV', 'tarefa', 'equipe', 3, 20, '#974f0c', '2026-04-13 20:51:47'),
(6, 'Processo de venda novo', 'PDVN', 'tarefa', 'equipe', 3, 20, '#974f0c', '2026-04-14 14:05:42'),
(7, 'Processo de venda teste final', 'PDVTF', 'tarefa', 'equipe', 9, 25, '#974f0c', '2026-04-21 21:21:02'),
(8, '123 projeto', '1P', 'gestao', 'equipe', 9, 25, '#ffc107', '2026-04-21 21:56:30');

-- --------------------------------------------------------

--
-- Estrutura para tabela `espaco_grupos_task`
--

CREATE TABLE `espaco_grupos_task` (
  `espaco_id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  `adicionado_em` datetime DEFAULT current_timestamp(),
  `adicionado_por` int(11) DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `espaco_grupos_task`
--

INSERT INTO `espaco_grupos_task` (`espaco_id`, `group_id`, `adicionado_em`, `adicionado_por`) VALUES
(3, 5, '2026-04-13 17:08:10', 15),
(4, 9, '2026-04-13 18:55:58', 20),
(4, 10, '2026-04-14 10:32:58', 27),
(6, 10, '2026-04-14 11:37:00', 27),
(6, 3, '2026-04-14 14:55:29', 20),
(4, 3, '2026-04-14 14:58:45', 20),
(7, 9, '2026-04-21 18:21:02', 25),
(8, 9, '2026-04-21 18:56:30', 25),
(8, 3, '2026-04-21 18:58:31', 20),
(7, 3, '2026-04-21 18:58:33', 20),
(8, 10, '2026-04-22 14:53:30', 27);

-- --------------------------------------------------------

--
-- Estrutura para tabela `espaco_grupo_sla_task`
--

CREATE TABLE `espaco_grupo_sla_task` (
  `espaco_id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  `status_id` int(11) NOT NULL,
  `sla_minutos` int(11) NOT NULL DEFAULT 60
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
(6, 10, 23, 0),
(4, 9, 12, 60),
(4, 9, 15, 0),
(4, 9, 13, 0),
(4, 9, 14, 0),
(7, 9, 24, 0),
(7, 9, 25, 0),
(7, 9, 26, 0),
(7, 9, 27, 0),
(8, 3, 28, 0),
(8, 3, 29, 90),
(8, 3, 30, 0),
(8, 3, 31, 0),
(8, 9, 28, 0),
(8, 9, 29, 60),
(8, 9, 30, 30),
(8, 9, 31, 0);

-- --------------------------------------------------------

--
-- Estrutura para tabela `espaco_membros_task`
--

CREATE TABLE `espaco_membros_task` (
  `id` int(10) UNSIGNED NOT NULL,
  `espaco_id` int(10) UNSIGNED NOT NULL,
  `usuario_id` bigint(20) NOT NULL,
  `funcao` enum('administrador','membro','visualizador') DEFAULT 'membro',
  `created_at` timestamp NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
(10, 6, 20, 'administrador', '2026-04-14 14:05:42'),
(11, 7, 25, 'administrador', '2026-04-21 21:21:02'),
(12, 7, 20, 'membro', '2026-04-21 21:21:02'),
(13, 8, 25, 'administrador', '2026-04-21 21:56:30'),
(14, 8, 20, 'membro', '2026-04-21 21:56:30');

-- --------------------------------------------------------

--
-- Estrutura para tabela `etapas_task`
--

CREATE TABLE `etapas_task` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `tarefa_id` bigint(20) UNSIGNED NOT NULL,
  `group_id` int(11) NOT NULL,
  `titulo` varchar(255) NOT NULL,
  `descricao` text DEFAULT NULL,
  `status_id` int(10) UNSIGNED DEFAULT NULL,
  `responsavel_id` bigint(20) DEFAULT NULL,
  `tempo_estimado` int(11) DEFAULT 0,
  `prazo` datetime DEFAULT NULL,
  `ordem` int(11) DEFAULT 0,
  `concluida_em` datetime DEFAULT NULL,
  `concluida_por` bigint(20) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `fleet_checklists`
--

CREATE TABLE `fleet_checklists` (
  `id` int(11) NOT NULL,
  `vehicle_id` int(11) NOT NULL,
  `condutor_id` bigint(20) NOT NULL,
  `destino` varchar(200) DEFAULT NULL,
  `data_saida` date DEFAULT NULL,
  `horario_saida` time DEFAULT NULL,
  `km_saida` int(11) DEFAULT NULL,
  `nivel_combustivel_saida` tinyint(4) DEFAULT NULL COMMENT '0=E, 8=F (8 níveis)',
  `liberador_id` bigint(20) DEFAULT NULL COMMENT 'Quem liberou o veículo',
  `assinatura_liberador` mediumtext DEFAULT NULL COMMENT 'Base64 do canvas de assinatura',
  `assinatura_condutor_saida` mediumtext DEFAULT NULL,
  `data_retorno` date DEFAULT NULL,
  `horario_retorno` time DEFAULT NULL,
  `km_retorno` int(11) DEFAULT NULL,
  `nivel_combustivel_retorno` tinyint(4) DEFAULT NULL,
  `recebedor_id` bigint(20) DEFAULT NULL COMMENT 'Quem recebeu o veículo de volta',
  `assinatura_recebedor` mediumtext DEFAULT NULL,
  `assinatura_condutor_retorno` mediumtext DEFAULT NULL,
  `observacoes` text DEFAULT NULL,
  `status` enum('aguardando_vistoria','aguardando_aprovacao','aprovado','em_viagem','devolvido','retornado','retornado_com_avaria','cancelado') DEFAULT 'aguardando_vistoria',
  `aprovado_por` bigint(20) DEFAULT NULL,
  `aprovado_em` timestamp NULL DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `retorno_obs` text DEFAULT NULL,
  `assinatura_vistoriador_retorno` mediumtext DEFAULT NULL,
  `recusa_justificativa` text DEFAULT NULL,
  `recusa_por` bigint(20) DEFAULT NULL,
  `recusa_em` timestamp NULL DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `fleet_checklists`
--

INSERT INTO `fleet_checklists` (`id`, `vehicle_id`, `condutor_id`, `destino`, `data_saida`, `horario_saida`, `km_saida`, `nivel_combustivel_saida`, `liberador_id`, `assinatura_liberador`, `assinatura_condutor_saida`, `data_retorno`, `horario_retorno`, `km_retorno`, `nivel_combustivel_retorno`, `recebedor_id`, `assinatura_recebedor`, `assinatura_condutor_retorno`, `observacoes`, `status`, `aprovado_por`, `aprovado_em`, `created_at`, `updated_at`, `retorno_obs`, `assinatura_vistoriador_retorno`, `recusa_justificativa`, `recusa_por`, `recusa_em`) VALUES
(1, 4, 25, 'Av barão 1550', '2026-04-15', '18:16:00', 4500, 4, 20, 'data:image/png;base64,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', 'data:image/png;base64,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', '2026-04-15', '18:17:00', 4520, 4, 15, 'data:image/png;base64,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', 'data:image/png;base64,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', '', 'retornado', 15, '2026-04-15 21:17:11', '2026-04-15 21:17:05', '2026-04-15 21:18:33', NULL, NULL, NULL, NULL, NULL);
INSERT INTO `fleet_checklists` (`id`, `vehicle_id`, `condutor_id`, `destino`, `data_saida`, `horario_saida`, `km_saida`, `nivel_combustivel_saida`, `liberador_id`, `assinatura_liberador`, `assinatura_condutor_saida`, `data_retorno`, `horario_retorno`, `km_retorno`, `nivel_combustivel_retorno`, `recebedor_id`, `assinatura_recebedor`, `assinatura_condutor_retorno`, `observacoes`, `status`, `aprovado_por`, `aprovado_em`, `created_at`, `updated_at`, `retorno_obs`, `assinatura_vistoriador_retorno`, `recusa_justificativa`, `recusa_por`, `recusa_em`) VALUES
(2, 4, 25, 'AV afonso pena', '2026-04-15', '18:29:00', 4500, 3, 15, 'data:image/png;base64,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', 'data:image/png;base64,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', '2026-04-15', '18:55:00', 45800, 8, 15, 'data:image/png;base64,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', 'data:image/png;base64,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', '', 'retornado', 15, '2026-04-15 21:30:44', '2026-04-15 21:30:28', '2026-04-15 21:38:11', NULL, NULL, NULL, NULL, NULL),
(3, 4, 25, 'ali', '2026-04-16', '09:12:00', 48000, 4, 15, 'data:image/png;base64,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', 'data:image/png;base64,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', '2026-04-16', '09:17:00', 45900, 2, 15, 'data:image/png;base64,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', NULL, '', 'retornado', 15, '2026-04-16 12:16:40', '2026-04-16 12:12:51', '2026-04-16 12:19:43', '', 'data:image/png;base64,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', NULL, NULL, NULL);
INSERT INTO `fleet_checklists` (`id`, `vehicle_id`, `condutor_id`, `destino`, `data_saida`, `horario_saida`, `km_saida`, `nivel_combustivel_saida`, `liberador_id`, `assinatura_liberador`, `assinatura_condutor_saida`, `data_retorno`, `horario_retorno`, `km_retorno`, `nivel_combustivel_retorno`, `recebedor_id`, `assinatura_recebedor`, `assinatura_condutor_retorno`, `observacoes`, `status`, `aprovado_por`, `aprovado_em`, `created_at`, `updated_at`, `retorno_obs`, `assinatura_vistoriador_retorno`, `recusa_justificativa`, `recusa_por`, `recusa_em`) VALUES
(4, 4, 25, 'ali pertinho', '2026-04-16', '10:14:00', 5000, 8, 15, 'data:image/png;base64,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', 'data:image/png;base64,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', '2026-04-16', '11:13:00', 5030, 4, 15, 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAY4AAABkCAYAAACRrNcsAAAPlUlEQVR4AeydW2gkWR3Gu6u6c5sJMTOTdCcxG8GA7AqrEGFABEXxSZQVfFEUQfRpH8TnRUGRfd6nfVl88QKCDyvqo6govggyrOIiYxiHSTK5zuhkZrKTpLtqv+90V6X6kqQn6a6uc+pr6p9z6nbq//+d5Hx1zqlUewV9REAEREAEROA5CEg4ngOWDhUBERABESgUJBz6LRCBrBCQHyJgCQEJhyUVJTdFQAREICsEJBxZqQn5IQIiIAKWEMiBcFhSE3JTBERABCwhIOGwpKLkpgiIgAhkhYCEIys1IT9EIAcEFKIbBCQcbtSjohABERCB1AhIOFJDrQuJgAiIgBsEJBwu1KNiEAEREIEUCUg4UoStS4mACIiACwQkHC7UomIQARHICoFc+CHhyEU1K0gREAER6B8BCUf/WKokERABEcgFAQlHLqrZ/iAVgQiIQHYISDiyUxfyRAREQASsICDhsKKa5KQIiIAIZIWAvo8jOzUhT0RABETAEgLqcVhSUXJTBERABLJCQMKRlZqQH3knoPhFwBoCEg5rqkqOioAIiEA2CEg4slEP8kIEREAErCHgvHBYUxNyVAREQAQsISDhsKSi5KYIiIAIZIWAhCMrNSE/RMB5AgrQFQISDldqUnGIgAiIQEoEJBwpgdZlREAERMAVAhIO+2tSEYiACIhAqgQkHKni1sVEQAREwH4CEg7761ARiIAIZIVATvyQcOSkohXm8AlMT0//Z25urg4L5ufnw0EZyg9hAa1arQaweqVSqd24ceNw+BTkgQsEJBwu1KJiyBSB69evH6LRrkMYWgRifHx8uVgserDiIB1G+QWYWTzPK8I8H58RfODTWYJFkTEGoanPzMwcT05O3h+kryrbTgISDjvrLWdeZzNcNqxoiCkOtLhBHh0dHUGrzb+t8wQiRGR9tRCfZplIGktjUyN/zk+KjDHojFcul0sQjjnEGMfGPESRvZn6OWVpt8ME+MvtcHgKTQQuR+DmzZtfQUNZQ4NJcaDFjWi5XC6hdIoDDdnuCxpuLhwu+ub9+/eLCfOQ76ttbm5G5cXXwbY4j+tRGPbhUABvkYRJ4SpggzHsO3WBKHLxwCRiQS4BhsJ+cepJ2uEUAQmHU9WpYC5KAOKwjYawY3hpbW3tV2glfZRLcaAhe7KwoW2umQa4VqvV2TgnDQ23ByvdunXrp81jh5qsr69PwR8fPtKvSGiYFrHdGPbFYoMRrnfgcA1mxAYpY0USL+RSxHFfA0OKiXojMRr3MoxIwkEKslwSgFjwTpkNXQhxmAUE/j2wEUS2dWkXCOytsXFlQ8sUxobX29nZYS8Eu91Z7t69+3HEV4YZsUHKWIsTExNTiDISE2TjxQPbcHp6+nfxFmWcIsA/FKcCUjAicBYBTFz/q1qtGsGAWHQVieb50AqzHKKhTN6Fs9GklZvH5TZZXV3dB5tITIjzGMQMD6wUxsfHv7CwsHBgNuiHUwQkHE5Vp4I5jQDugDlPEY6Ojr7keV4sGGzoAnyOjo4eohGMh2eQN8M46FGMnVZmX7c7UNjGxsYIeJFtPJQFvuMOhKYQ2ghIONqAaNUtAhCMqHfBeYpkcCH04m9s6La2tvy9vb3ryZ3KX5wARRdna54DEFxdJByu1qziKnCiFkMmvAOOaeAOOETDxp6FB8G4Ge9Qpq8EwNi5uZ6+ArK8MMeFw/LakfsXJgDR4KStOR9iwfQYjRnnKvQ7TxoDtiT/AV9KxQ+BgP6IhgBdl0yFQNzT4HAURGMklavqIgUMD3KYKuIfz3cIjTsEJBzu1KUiaRJI3u2WSqXfNjcrSYEA2WN4MG5XINhxPoXL6xIpEVClpgRal0mVgLnb5RDVvXv3vpTqlXN6MfQyzEMICN+wR1o4Ojpiz4NZmWMEJByOVajCOSFQLpc/cbKmXL8JoDf3Y/YwYPwHylgwmtcJ9vb2NEHehOFaIuGwvUbl/6kE0Nv4+6k7tePCBCqVyjHFYnZ29jUUkhSM8NmzZwcYnuJTa+2PP+NQLa4QkHC4UpOKo4MAG7eOjdpwYQIYjuK7vELf91t6EkEQxI84P3z48MqFL6ATrSEg4bCmquRorwRqtVo8to7Gjk/1fL3Xc3VcJwEIsJm/SE5686ggaAjG1taW2hECKRRy81MVnpuqzk+gfNEgJsaNeKCx4z8C/iw/0V8+0mq1yp6FEQuIBoU3ORzF164HHI6SYFyeta0lSDhsrTn5fSaBzc3NUhAERjx4YLMBZFaWIDAzM8N3eMUiQU4ePjikRSywHmL+4j0KBthq/gJA8rxIOPJc+5bEflE3cUdcquMTnZ/3YSvEz0ntFpEol8sUgXaRMMjQawshvuxdLEIwPMxfTJgd+pF7AhKO3P8KuA1ge3u7dHx8bF4/Eg1bVSqVuCfiUvTLy8tvoccQ9SAoEDTzfSPYzkdmOandVSTAgUNSITobfFU6n4oyr2eB+FJY1rFfiwjEBCQcMQplXCWwu7vr4+7ZiAdj9H3fY0M6OTn5LtdtsJWVlYmFhYUj+B3NP7SIAraHBwcH30YsbOgpDpFhU+cCHmENH/QkjEgg5XeMePx2wM6jtUUEIgKNVMLR4KCfjhPguDway1oyTAjHixi+iQUluS/t/NTU1GP2hOgPRKBDFOD/U/jPL4/i3+yZotDmu+lJ4NwA4hCJhOlN7OzssLy2w7UqAucT4C/h+UfpCBFwgAAaX379KRvdWCwwfFVEQ83hnKBarR4PIszx8fHvzs7O1ikKTeP1WuzKlStXfd/36A98oI9IeloiYaiPjY39PCkOzbzpSSB29kR6KlAHicB5BCQc5xHSfucIoEHl152ycWajG8VX9DyvRBFB485GnXf9N6Kdp6WLi4sfRk/hCOfweBrPbbHp6ek3SqWSEQUKA6y9uK7rmJjm5DR9DHDOE/gd9xgS+UgYSnfu3PlG14K0UQT6TEDC0WegeSgOjWRLw8jGtptFxzXTACkb1jjFHT7H62u4Gz8Etx/BUl3Q+EIrvO/gomyckTQWNNLMUFh2GRf8DmmYY+iIu16vr/q+X8Y5PJ7Gc3sxXtMYphqOr169+kH40yIMmJjml01RGPyNjY3JXgrVMSKQBgEJRxqUHbrG8vLyDBrJniKKjmumSIpsWIv8oIAiW22kPu7GR9BAfx8WN8xsqJPrg8rjrv4t+EC/kHRf4G+BhnmC7ge0beVxMNNbgLAET58+fb1dFLBOQTCGuYaR27dvb7QVo1URyCwBp4Ujs9Qtdmx1dXUXjS0fZzV3ywila4pjWrajIcWhvS9sqHs/OjNH8kmlY8wnmMln9hi2t7f9R48e8WWAmXFSjojAZQlIOC5LMIfno0EsJe+Yu+VxjLmbjvaxMUW+ZSimfX1/f/8AAoORG/OuKU5gt4gPUKe2DuEL4Ij5utmkn0dHR//HPrhJV+BR61JE76nc3jvCkBxjaT1SayJgMQEJh8WV55rrT548uQKBKWPohsLECewW8UEDnto6hM+HHx1fN7u3tzeNfR78NCI4MTExxeEoKgmsa5VgqOovXXfkaqOCdYmAhMOl2lQsqRPA0N0+h6MODw9/CeHo1g0JHz9+/OnUHdMFRWCABCQcA4Srot0igCGnhxiGqiM1T4chzyfEzBNXY2NjX8Vkf8ckO0TjT25RUDQiUChIOOz+LZD3fSYAUTiIBAFp/JQX8xCGaVwOiVdEaoyT+DSs83XjJsEP9jxCviMLwvFZrGsRAacISDicqk4F0yuBpaWlP87NzfG/xdl7ML2GpjiMowxoAXUBubYFw1HtAhFgmGoT8y98korzHvE8DN+R1Xa6VkXACQISDieqUUGcRQC9CPPGWAhF3INAb+AzVAd0H4xCIN9SBAUCG0JOfAdB8C6FgcZJcRrykUD4Dx48mMexWvJOIEfxSzhyVNmuhwqB4H96c97B9CLYg6BBHPieJmiD0YgODBAG6EQY+r7/VwgCew1x74ET31tbWx/tOEkbRCDHBCQcOa58W0O/du3aT9B74OtKKBKmF4F1fpcE3y1FgeiqEFAHhsz/6H4PAvEizIgEhIGP13pra2uf4gEyERCBswlIOM7mo71DIlCpVO7D6tVqleJAi+chxsbGvgV14O8ukoZGINPuKQUiwJDUm5FARENMEAp+k92/20/QugiIQG8E+MfX25E6SgT6ROCFF174DYaQnqGXwCElmuk1YFucYthoDoZRJg+aYBbzvqguLpgnmDDctBcJRDPlCwJ9TFC/2uUcbRIBEbgEAQnHJeDp1PMJQBweQBBMjwGpEYZarfZFnDlKOUDa6DIgc85iBAKT1fWmMJhhJuTNJDV6ETPnnK/dIiAClyQQnS7hiEgo7QuBpaWldyAQRiggGiHE4RoKRtKpD5xzSJgRBqzvQwwiUUimRiAwWV1CeVpEQASGSEDCMUT4Llx6cXHx7UgokPKf3l5GXEYo8MP8zwPEwCzoadQw5/CPSBg455AwIwxYn8L5WkRABDJMQMKR4crJomvVavWHmLQ2PQoKBYaOXoGf0IiTHgVUooA5h3BiYuJVCAEfbTVPLe3s7JQx5/AxHK8lSUB5EbCMgITDsgpL292VlZVXIBQ1DjtRKKAQP8CkNZIToaBPFArYH9iboFhgzsFbXV19k/tkIiACbhGQcLhVn/2I5kMQikMIhXnaCSLwNoTCh1KYsqMUK/y/iXg+gkIB+xy2axEBEXCcgMPC4XjN9Tk89iaa9l8IxQgEorVL0bhe8okmb319XfMRDS76KQK5IiDhyFV1P3+wnK9InOU3xcU8Vqv8vG0c2IvMix0vLCz8L2+GkYI/J/5eB5aVcAwMrRsFo+fhRiCKggTYixyK4eJpX7eEm54P5M3A+ZOwgS8SjoEjtuMCEIgnNM/z9j0Y8rtIN/thKOs2yvmnzBsaA9TB78H/13kxxPs67Ht5M9TvS2m0OBKONChbcI2NjY1JGuctaMjPIp3vh6Gsj6Ccl2XrQ2OAOvg8+H85L4Z4X4O9kUO7nUZzI+FIg/KgrqFyRUAERGAIBCQcQ4CuS4qACIiAzQQkHDbXnnwXARHICoFc+SHhyFV1K1gREAERuDwBCcflGaoEERABEcgVAQlHrqrbvmDlsQiIQPYISDiyVyfySAREQAQyTUDCkenqkXMiIAIikBUCJ35IOE5YKCcCIiACItADAQlHD5B0iAiIgAiIwAkBCccJC+VEYBgEdE0RsI6AhMO6KpPDIiACIjBcAhKO4fLX1UVABETAOgLOCod1NSGHRUAERMASAhIOSypKboqACIhAVghIOLJSE/JDBJwloMBcIyDhcK1GFY8IiIAIDJiAhGPAgFW8CIiACLhG4H0AAAD//4grNOQAAAAGSURBVAMAzVCjffVnka4AAAAASUVORK5CYII=', 'data:image/png;base64,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', '', 'retornado', 15, '2026-04-16 13:50:57', '2026-04-16 13:15:10', '2026-04-16 14:16:27', '', 'data:image/png;base64,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', 'O km que você esta me devolvendo não condiz favor corrigir', 15, '2026-04-16 14:12:01');
INSERT INTO `fleet_checklists` (`id`, `vehicle_id`, `condutor_id`, `destino`, `data_saida`, `horario_saida`, `km_saida`, `nivel_combustivel_saida`, `liberador_id`, `assinatura_liberador`, `assinatura_condutor_saida`, `data_retorno`, `horario_retorno`, `km_retorno`, `nivel_combustivel_retorno`, `recebedor_id`, `assinatura_recebedor`, `assinatura_condutor_retorno`, `observacoes`, `status`, `aprovado_por`, `aprovado_em`, `created_at`, `updated_at`, `retorno_obs`, `assinatura_vistoriador_retorno`, `recusa_justificativa`, `recusa_por`, `recusa_em`) VALUES
(5, 4, 25, 'vou ali pertinho', '2026-04-16', '11:19:00', 5030, 4, 15, 'data:image/png;base64,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', 'data:image/png;base64,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', '2026-04-16', '11:24:00', 5050, 0, 15, 'data:image/png;base64,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', 'data:image/png;base64,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', '', 'retornado_com_avaria', 15, '2026-04-16 14:24:00', '2026-04-16 14:20:39', '2026-04-16 14:26:29', '', 'data:image/png;base64,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', NULL, NULL, NULL);
INSERT INTO `fleet_checklists` (`id`, `vehicle_id`, `condutor_id`, `destino`, `data_saida`, `horario_saida`, `km_saida`, `nivel_combustivel_saida`, `liberador_id`, `assinatura_liberador`, `assinatura_condutor_saida`, `data_retorno`, `horario_retorno`, `km_retorno`, `nivel_combustivel_retorno`, `recebedor_id`, `assinatura_recebedor`, `assinatura_condutor_retorno`, `observacoes`, `status`, `aprovado_por`, `aprovado_em`, `created_at`, `updated_at`, `retorno_obs`, `assinatura_vistoriador_retorno`, `recusa_justificativa`, `recusa_por`, `recusa_em`) VALUES
(6, 4, 25, 'AV parana', '2026-04-16', '13:25:00', 5050, 7, 15, 'data:image/png;base64,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', 'data:image/png;base64,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', '2026-04-16', '13:31:00', 5050, 0, 15, 'data:image/png;base64,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', 'data:image/png;base64,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', 'Carro precisa lavar ', 'retornado', 15, '2026-04-16 16:28:48', '2026-04-16 16:28:05', '2026-04-16 16:32:59', 'Olha o cara passou na minha frente e eu bati ', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAY0AAABkCAYAAAB6m2wvAAAJyElEQVR4AezdP28jRRzGcY/tJIBMBEpyyeUU6Rp0DdW9hGto6aBBdHQIiYKGlo6GgoYKGiQoeQGIV3AlAqXOJXFyUcJdyJHYXvP8Jl7Hzm1ye/Z6Pbv7jbze9Xr/zHzmpEczY/vqNf4QQAABBBBIKUBopITiMAQQQACBWo3Q4F8BAqEJUB4EAhYgNAJuHIqGAAIIhCZAaITWIpQHAQQQCFigoqERcItQNAQQQCBgAUIj4MahaAgggEBoAoRGaC1CeRCoqADVLoYAoVGMdqKUCCCAQBAChEYQzUAhEEAAgWIIEBrFaKdsSslVEEAAgSkFCI0pATkdAQQQqJIAoVGl1qauCCAQmkDhykNoFK7JKDACCCAwPwFCY3723BkBBBAonAChUbgmo8CvK8DxCCCQnQChkZ0lV0IAAQRKL0BolL6JqSACCCCQnUA2oZFdebgSAggggEDAAoRGwI1D0RBAAIHQBAiN0FqE8iCQjQBXQWAmAoTGTFi5KAIIIFBOAUKjnO1KrRBAAIGZCBAaU7ByKgIIIFA1AUKjai1OfRFAAIEpBAiNKfA4FQEEQhOgPLMWIDRmLcz1EUAAgRIJEBolasxQq3Lnzp1ISzfU8lEuBBBIL0BopLfiyEuB13re3Nx8q9lsOi0Nbffv3r3bJ0Bei5CDEQhKgNAIqjnKVxiFRKff7w8r5pyrxQGiEIm09FZWVs6HB7CBAAJBCxAaQTdP8Qv3+PHjzt7enjs/P+8pPK7S47JqTqv60tLSosKjP7psbGxECpxodXWVYS0h8UDgVoEc3yQ0csSu8q2Ojo6aCo/67u6uO9FfFEUJGXIlVK/Xnf0tLi76Ya04UBQkFi6RhYqWztUZbCGAQB4ChEYeytxjTODs7Ozd/f39ukLEWYjY0ul0rEdhQeJ7I9oYOyd+oSCxTWehoqUZh4nmSSK90dTCAwEEZihAaMwQl0unFzg8PFxQeFiQ+N7IaKD0er1/u92u75ooTBJDRfMkTgHS0WKT7dH6+npv0BP5NH0pbjuS9xBAwAQIDVNgCVqg3W63Dg4OGgqSsVBRT+O3OERGK6DeiGs0Gnq7bj2RnyxI4mUwvNVXoPg5E+uhKGC6W1tb+6PXYBsBBJIFCI1kF/YWQGBnZ+dDCxL1UPww18XFRU/FTuyJaL9/KFD8WomiTWcfBbaAaag3sx4HS7weBIwPF+2zSfkzfzJPCFRYIKTQqHAzUPUsBJ4+fdpUgFwf3vpKgaDRrcvhrSiKLFSGHRRt3HhrpYq9p5WzT3k5Tcq/GQcJn+oyGpYqChAaVWz1atX5Ww1vLcTDWzYBb8GiHorvncRr7XNKlueakPdzJ1HkV8oUy5haTRtezTnLj5oFSCMOkLW1Nevh+Pd5QqDsAoRG2VuY+qUWULAsa0Lez51YuChQbA5lGC4KlNMo8j0Vf03nLgNkYWGhruEr/1FgBUnv4cOH3/gDyvBEHRC4JkBoXAPhJQI3CShQ3rYwsV6Jeh7dKLoKkME5Tn91HfP1IET8hLsm3fk+yQCIVfEFCI3ityE1mIOAeiELCgc/fzI6AX+9KDbhrqWpHoh9FNj3RhQiDGddh+J1YQQIjbk3FQUousDoBHyr1fo+0p96IpeTIYPKqQdSs0Uv7YuJ8XCWDxKFSKTztvUeDwSCFyA0gm8iClgkge3t7c/VA/HzIjaMZYvmQuJvuw8n1OM6WZCoJ+KWl5ffsyEt65FYiGibH3GMkVgHJUBoBNUcFKaMApoLib/t7jSs5SfWVU//8Sytx4IkDhHt9z/iaCFiX0DU60daeOQkwG1uFiA0brbhHQRmJqAeyLA3YkFydnZ2Hg9paT28r4XI4CdSflfvw0+sK0Ss5zI8hg0E8hQgNPLU5l4I3CBwcnLyhsLDT6xr7V68ePGHwmNsXsROtaEshcjwl3/VE+F/RTQYltwECI3cqLnRmAAvbhU4Pj5+pPDwIaJeiev1evYrvi+FiHoi9lMoPkQUIP319fXo/v3779x6cd5EYAoBQmMKPE5FIC+BdrvdUHj4EHn27NmfCR/Q8p/OajQa7uLi4nhkKMtC5Ie8ysl9yi9AaJS/jalhyQROT0/f3x/5/0g6nc6RDWVpGavpYCjLQuQz64VoLsSGsvwydiAvELgUSPVMaKRi4iAEwhU4PDxctaEsLf6TWeqF2JcH/VBWHCQaxqppLsSGsuxXfZ0FyPLy8hfh1oqShSpAaITaMpQLgQkF1AsZ+7XfbrebGCCtVus79UCilZWVv2v8IZBSgNBICcVhCGQhMI9rHBwc+LkQTaar49H33wvRhi+KeiBuaWnpgXoeXU2i/6fl+cbGxoF/kycEEgQIjQQUdiFQRgELDxvCihcFh++BWF01dKU59MaSnloKkjXbx4JAkgChkaTCPgQqIKDwqKv38Y/C43rvo6bexi8VIKCKEwiULzQmQOAUBKoq0G6331F4+J83UXj8GjvU6/WP4m3WCIwKEBqjGmwjUGEBTaB/HEXRMDju3bv3V4U5qPoNAoTGDTDsRqCKAhYc6mXsWd3V83hg6wwWLlEiAUKjRI1JVRDIQmBnZ2dT17FJcre5ucnchjB4XAkQGlcWbCGAwEBAvYyfB5sfDNasEPAChIZnKP4TNUAgSwFNjn+i6+04537UmgcCQwFCY0jBBgIIjArs7u5uPXny5MvRfWwjQGjwbwABBBCYiUA5L0polLNdqRUCCCAwEwFCYyasXBQBBBAopwChUc52rUqtqCcCCOQsQGjkDM7tEEAAgSILEBpFbj3KjgACCOQs8MrQyLk83A4BBBBAIGABQiPgxqFoCCCAQGgChEZoLUJ5EHilAAcgMD8BQmN+9twZAQQQKJwAoVG4JqPACCCAwPwECI1ke/YigAACCCQIEBoJKOxCAAEEEEgWIDSSXdiLAAKhCVCeIAQIjSCagUIggAACxRAgNIrRTpQSAQQQCEKA0AiiGUIpBOVAAAEEbhcgNG734V0EEEAAgREBQmMEg00EEEAgNIHQykNohNYilAcBBBAIWIDQCLhxKBoCCCAQmgChEVqLUJ78BbgjAgikFiA0UlNxIAIIIIAAocG/AQQQQACB1AI5hUbq8nAgAggggEDAAoRGwI1D0RBAAIHQBAiN0FqE8iCQkwC3QWASAUJjEjXOQQABBCoqQGhUtOGpNgIIIDCJAKExiVraczgOAQQQKJkAoVGyBqU6CCCAwCwFCI1Z6nJtBBAITYDyTClAaEwJyOkIIIBAlQQIjSq1NnVFAAEEphQgNKYE5PSXBdiDAALlFSA0ytu21AwBBBDIXIDQyJyUCyKAAAKhCWRXHkIjO0uuhAACCJRegNAofRNTQQQQQCA7gf8BAAD//ybHThkAAAAGSURBVAMAM2Lk5xvTYlwAAAAASUVORK5CYII=', 'cara explica melhor como voce relou', 15, '2026-04-16 16:31:35');
INSERT INTO `fleet_checklists` (`id`, `vehicle_id`, `condutor_id`, `destino`, `data_saida`, `horario_saida`, `km_saida`, `nivel_combustivel_saida`, `liberador_id`, `assinatura_liberador`, `assinatura_condutor_saida`, `data_retorno`, `horario_retorno`, `km_retorno`, `nivel_combustivel_retorno`, `recebedor_id`, `assinatura_recebedor`, `assinatura_condutor_retorno`, `observacoes`, `status`, `aprovado_por`, `aprovado_em`, `created_at`, `updated_at`, `retorno_obs`, `assinatura_vistoriador_retorno`, `recusa_justificativa`, `recusa_por`, `recusa_em`) VALUES
(7, 4, 25, 'yiulandia', '2026-04-16', '15:36:00', 5060, 8, 15, 'data:image/png;base64,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', 'data:image/png;base64,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', '2026-04-16', '16:21:00', 5070, 3, 15, 'data:image/png;base64,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', 'data:image/png;base64,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', '', 'retornado', 15, '2026-04-16 19:19:44', '2026-04-16 18:43:08', '2026-04-16 19:24:05', '', 'data:image/png;base64,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', NULL, NULL, NULL);
INSERT INTO `fleet_checklists` (`id`, `vehicle_id`, `condutor_id`, `destino`, `data_saida`, `horario_saida`, `km_saida`, `nivel_combustivel_saida`, `liberador_id`, `assinatura_liberador`, `assinatura_condutor_saida`, `data_retorno`, `horario_retorno`, `km_retorno`, `nivel_combustivel_retorno`, `recebedor_id`, `assinatura_recebedor`, `assinatura_condutor_retorno`, `observacoes`, `status`, `aprovado_por`, `aprovado_em`, `created_at`, `updated_at`, `retorno_obs`, `assinatura_vistoriador_retorno`, `recusa_justificativa`, `recusa_por`, `recusa_em`) VALUES
(8, 4, 25, 'addd', '2026-04-16', '17:08:00', 5070, 8, 15, 'data:image/png;base64,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', 'data:image/png;base64,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', '2026-04-16', '17:15:00', 5090, 8, 15, 'data:image/png;base64,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', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAY0AAABkCAYAAAB6m2wvAAAO20lEQVR4Aeyde4wkRR3H57G7x8Hy0n3ezO69FB8IiBhEjfEdMVECiQ8UH/iOkT/OBxpNTOAPJSEIKokJCKIBJcHEYDBRgxFNjKgE9AKoIHDc3e7e7C4syinsMjM9fn99003f7c7t7Dy7uz6X+k1Vd1dX1+9TO/Xtqpruy2X4BwEIQAACEGiSAKLRJCiyQQACEIBAJoNo8FcAgbgRoD4QiDEBRCPGjUPVIAABCMSNAKIRtxahPhCAAARiTMBR0Yhxi1A1CEAAAjEmgGjEuHGoGgQgAIG4EUA04tYi1AcCjhLA7WQQQDSS0U7UEgIQgEAsCCAasWgGKgEBCEAgGQQQjWS0U2dqSSkQgAAE2iSAaLQJkNMhAAEIuEQA0XCptfEVAhCIG4HE1QfRSFyTUWEIQAAC/SOAaPSPPVeGAAQgkDgCiEbimowKb5QA+SEAgc4RQDQ6x5KSIAABCKSeAKKR+ibGQQhAAAKdI9AZ0ehcfSgJAhCAAARiTADRiHHjUDUIQAACcSOAaMStRagPBDpDgFIg0BUCiEZXsFIoBCAAgXQSQDTS2a54BQEIQKArBBCNNrByKgQgAAHXCCAarrU4/kIAAhBogwCi0QY8ToUABOJGgPp0mwCi0W3CfSh/YmLi4kKhcNeWLVsWJicny7Ka0i1ZcK5iT3awWCzuVtmf7oNbXBICEIgBAUQjBo3QySqYOORyuZtqtdqbVO5oNpsdkCnZWgjOVWxh2PO801X2dXYdiUggRFWlEZTWEHMWBBJFANFIVHNtuLKezljyPO8Pij84NzeX3Yjl8/lrqtXqHp27LKvJLIQmFQnSOaVDQZGA1CL237GxsZ8FGYkhAIFkE0A0kt1+DWtfF4e84heWSqU3KL61YeYGB/bv3/+F+fn5HTp3sywnC0VHgnKVBOUxnbpKUCQgmYgdNzAwcEFERExQlsfHx+/WuQQIQCBhBBCNhDVYXKorQblUgrJTQrJKUDQ99mvV81lZGCIiYoKySaJzTlRItA5Tlj2kE06RESAAgY0Q6GFeRKOHsF251MzMzLkSk2Nl4chE6yA/kf8HFYfTXFEhkdAMyE7RWslDgZhIRKoakcyNjo5+XOcSIACBGBBANGLQCC5U4cCBAxdJRE5QHE5zaXrrConIUzJPljEzFoGYSERyGpFMDg4O3hgVEqWfGhkZucbyYhCAQG8JIBq95d2Lq/l38rpj/0cvLtbONTS99TWJyAtkeVnWbNOmTZ+SaBxQubaIr+hQ0D6b1sqYkCh90tDQ0C75aOsj9guucrFY/O2hnN36pFwIQMAIIBpGIUXmed7l9Tv2l+qO/OqkubZnz54bZmdnt2hUYov4/vTW8PDw2RIL+xVX5Uh/JCC2a0B+vzkQEfldkYg8YAcwCECgswQQjc7y7HtppVLpcnWwf7GKqEPdtX379nFLJ9kefvjhe7ROYr/iGpSY+EKyvLx8ovy0qS3fNfkaxkrnJSKnmoiYSUSqEpH9fgY+IACBtgjESTTacoSTnyegO/XXaOs/sqw6138pTl1YWlp6WkJiU1u+iGiN41UaYT1tjiq2KDSJSE4iUqwLiDc1NfXD8CAJCEBgQwQQjQ3hSk7mSqXyTnWenjrM49VZpv6ZiN27d/9VayIn2khEsdzOvl8f/xODwxpN+7JagP+omNh6yL7DDrIBAQisSwDRWBdRMjMsLCzcrembH9drf446yS/X005EGm3dJhs2ATEhKZfLN8px/0cCiv0gAZnS1JUtpNsDiv4+Po4gwCYEjiCAaBwBJE2b6jQ/ojtte2rbfs56hXzbLHMyLC4uflLi4f/cV0wqMp+DhMPiTRJVEw9vYmLiY7YDgwAE1iaAaKzNJTV7dae9U84sq3PM6a76caWdD2IyKMtqncPWfaI8shqd/UCcTEDuix4gDQEIHCKAaBzi0MfP7l9agrHLrqJ4THfUv7Q0lsmUSqWTNPowofhTMPIwLuJk0ZliVSsWi0cKix3DIOAsAUTDgabXNNV16hTvMlcVn6spmEssjR0iMDMz81obeQwMDLxPo4/DHirU9gkmHmK26hmRQ2fzCQG3CCAajrS3OsW3SDCesLtoTcF8yxG3N+Tmvn37fqrRh/9QoTgdtjguZnkTD7NCobC0oYLJnDgCVLgxAUSjMZvUHRkaGjpbTtmd9JA6P9Y3BKNR0OjM3t6b1fF9EltFzwdtn2zrHs/vIQUBdwggGu60dWbv3r171OFdW3d5q6Zcfl5PEzUgoDWPrRqlZSuVylfEbkXWICe7IeAGAUTDjXYOvVQHuEsdn/9eJk25nKcRxyfCg71MJOxaCwsLV4rdMfl8/jtB1bVI7uxPmAMGxO4RQDTca/OMOr/TInP233UQQcsua9HcRNd/4265XD7YckGcCIGEEkA0Etpw7VZbo40P1Ms4VqONR+ppouYI+E+Wa6SWby47uSCQCAJNVRLRaApT+jJprv52CUewprGzUCjclj4vu+uRRmvdvQClQyCGBBCNGDZKr6qkaarzda0Fmb1m5D1TU1MXWhpbl4D9qsqY+SOOdXOTAQIpIoBopKgxW3GlWq2epvOs87O3v35facI6BIIRhmLjtk7uww+zBYGkE0A0kt6CbdZ/fn5+QdNUX68XM6z1jX/W00RrENixY8dng90SjQeDNDEEXCGAaLjS0kfxU9NU35Bw3F/P8hKtb9xcTxMdQWB5efnbtku8MrOzs6dbGoOASwTSJxoutV4HfZVwWAe4YkWqQ2Rtw0CsbUO2W6MMizAIOEcA0XCuyRs77HneO3TU5ukHNE3Fa0YEIxomJibsFSz+Lq0F/dFP8AEBxwggGo41+NHcLZVKv9fxi2T2RtetEo6/KU2oE8jlcv6vpiSuNa0Fvb6+m2h9AuRIEQFEI0WN2QlX5ubmbtXUy+dUlo04zpBw3Km08yE6ypC48r1x/i/CXQD88bvb9g091wLv9VrX+FI9w9smJydvqaediySaI7JaMMoQlyedg4DDEIgQQDQiMJKc7HTdtTB+tcq8TGbvWbpIwnGNpV0y+WxrGItRn8VlJLpNGgKuEUA0XGvxDfirqarLlf0qmQnHLnWiX7V02m18fPwBG11oms5fwzB/bR1DPMJt24dBwEUCiIaLrb4Bn9VRXqrs35OZcHyzUChcbOk0moTCpqK8fD5/auCfpqMyYpBlHSMgQtw8gXTmRDTS2a4d9Uqdpi2M/8gKVSd6k0Yc9tNc20yNyadgKiocTVQqlT9rOircTo2zOAKBNgggGm3Ac+lUCYeNMG43nzVt86vp6enwbtz2JdVGR0eXNMKoyadQHCSMNfmbXVhYOCepflFvCHSLAKLRLbIpLFcd6QVy625Zplwu3z81NbXF0n20li8tofCnogYHB0+OFiIfsxpd8L2IQiENgQgBvhwRGCTXJ6BO9XXK9YjdmVer1T3btm07SduJCmtNRWl08Zh8C0cbiXKIykKghwQQjR7CTsul1Lm+WL48IRtaWVnZd9ZZZw0qHfug0cWKbM2pKI0udsbeASoIgRgQWFc0YlBHqhBDAhKOUVVrWSOO49Xhzikd26B1i2slFrbQ7b9sMKiofGAqKoBBDIEmCSAaTYIi22oC6nQ31/eOFAqFR+vpWEU2FaV1i0tUqejU05Oqe3RbhwkQgEAzBBCNZiiRpyGBeuc7pzWBHbqbf3Z6evqwheWGJ3b5gMSirPqEU1Gqn13R/1WU6pzwp7rNFQwC/SGAaPSHe6quqk64IIfulR1TqVSWJiYmXq50X4LE4hmZicVApAI1TaFlVU/+3iNQSEKgFQJ8iVqhxjmrCKhDfrV23iHL5HK5BzVd9VZL98rGxsYO1kcWm7XO4l/WRhflcnlWdePv3CfCBwTaJ8CXaW2G7G2BgDrn89RhX2+nqsP+je74P2Tpbpqu4T+cNzAwMBxcR9e2ZMVGF4uLi0XbwCAAgc4QQDQ6w5FS6gRmZ2c/o6S96NDeVXWz7v7t3VXa1dlQLBbnJRg2DRWuoZhYVKtVz8RCApaInwF3lgqlQaD7BBCN7jN27grqsC9TB27iYb5fqc7dXrNu6bZNZT0uIap5njemUU1Ynrb9dYv5+fl8uJNEugjgTSwIIBqxaIb0VUJ3+9erU3+3eab48+rob7V0qzY9Pf13CYaNLLZGyzCxkEjxFtooFNIQ6CIBRKOLcF0vWlNVv9CIwxbI7T8yulCL47/btm3bMetx0dTTHRIIT0JjVlNcq1QqL5P4hKeqXP/ns7yyPERCAgI9IYBo9ARzUi7S+XpqxHHv4ODgGSp5tzr6Nz733HO7x8fHt2vbDxKI+yQKJg5mvkBo9PAuCYQ9fGfm5ws+VIYvFiqXv90ACjEEekiAL14PYbt6qb179x7QFNIr5f+zslPy+fxjEopAIM7UPhMHMyVXBxMKLXA/ozJ47cdqPOyBQE8JIBo9xZ2Ki0UfmmvokKai/i1h8BT74qB0TZmD144ouWYwfajlcrlHTSACs1GFFriPW/MMdkIg5QTi5h6iEbcWiXF9RkZGjlfn77+eQ3EoBmul1fufKFeyihU1Djp+ZyAOinMmEDMzMy9qfAZHIACBfhJANPpJP2HXHhoaCp+J2GDVbZTxtETBXuXhm8Tiw1aG1i7eLtG5ytIYBCAQfwKIRvzbKDY1VKe/X519xkxpv/NvMs4pn408Ql80orhFG/Y/Aa4o/uLk5ORtivsTuCoEINA0AUSjaVRkFAH/ATp1+A0XrZWn6SAhuV2Z7VmOOY043qsRxw3aJkAAAjEmgGjEuHFcqJqE407P886Xrw/KZmQECEAgxgR6JBoxJkDV+k6gVCrdI/F4heyyvleGCkAAAkclgGgcFQ8HIQABCEAgSgDRiNIgDQGHCOAqBFohgGi0Qo1zIAABCDhKANFwtOFxGwIQgEArBBCNVqg1ew75IAABCKSMAKKRsgbFHQhAAALdJIBodJMuZUMAAnEjQH3aJIBotAmQ0yEAAQi4RADRcKm18RUCEIBAmwQQjTYBcvpqAuyBAATSSwDRSG/b4hkEIACBjhNANDqOlAIhAAEIxI1A5+qDaHSOJSVBAAIQSD0BRCP1TYyDEIAABDpH4P8AAAD//5eNZ3QAAAAGSURBVAMA5gHlBRfX7JsAAAAASUVORK5CYII=', '', 'retornado', 15, '2026-04-16 20:10:34', '2026-04-16 20:09:25', '2026-04-16 20:15:52', '', 'data:image/png;base64,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', NULL, NULL, NULL);
INSERT INTO `fleet_checklists` (`id`, `vehicle_id`, `condutor_id`, `destino`, `data_saida`, `horario_saida`, `km_saida`, `nivel_combustivel_saida`, `liberador_id`, `assinatura_liberador`, `assinatura_condutor_saida`, `data_retorno`, `horario_retorno`, `km_retorno`, `nivel_combustivel_retorno`, `recebedor_id`, `assinatura_recebedor`, `assinatura_condutor_retorno`, `observacoes`, `status`, `aprovado_por`, `aprovado_em`, `created_at`, `updated_at`, `retorno_obs`, `assinatura_vistoriador_retorno`, `recusa_justificativa`, `recusa_por`, `recusa_em`) VALUES
(9, 4, 15, 'ali', '2026-04-22', '14:13:00', 5090, 8, 25, 'data:image/png;base64,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', 'data:image/png;base64,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', '2026-04-22', '14:18:00', 5100, 8, 25, 'data:image/png;base64,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', 'data:image/png;base64,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', '', 'retornado', 25, '2026-04-22 17:18:32', '2026-04-22 17:14:53', '2026-04-22 17:19:29', '', 'data:image/png;base64,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', NULL, NULL, NULL),
(10, 4, 25, '456', '2026-04-22', '17:21:00', 5101, 8, NULL, NULL, 'data:image/png;base64,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', NULL, NULL, NULL, NULL, NULL, NULL, NULL, '', 'aguardando_vistoria', NULL, NULL, '2026-04-22 20:21:44', '2026-04-22 20:21:44', NULL, NULL, NULL, NULL, NULL);

-- --------------------------------------------------------

--
-- Estrutura para tabela `fleet_checklist_photos`
--

CREATE TABLE `fleet_checklist_photos` (
  `id` int(11) NOT NULL,
  `checklist_id` int(11) NOT NULL,
  `angulo` varchar(50) DEFAULT 'frente',
  `foto_path` varchar(500) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `fleet_checklist_photos`
--

INSERT INTO `fleet_checklist_photos` (`id`, `checklist_id`, `angulo`, `foto_path`, `created_at`) VALUES
(1, 3, 'frente', '/SistemaCPE/web/uploads/fleet/cl3_frente_96e114c4.png', '2026-04-16 12:12:51'),
(2, 3, 'parachoque_traseiro', '/SistemaCPE/web/uploads/fleet/cl3_parachoque_traseiro_ef58fee8.png', '2026-04-16 12:12:51'),
(3, 4, 'frente', '/SistemaCPE/web/uploads/fleet/cl4_frente_2d141d45.png', '2026-04-16 13:15:10'),
(4, 4, 'parachoque_dianteiro', '/SistemaCPE/web/uploads/fleet/cl4_parachoque_dianteiro_a7d15d12.png', '2026-04-16 13:15:10'),
(5, 4, 'parachoque_traseiro', '/SistemaCPE/web/uploads/fleet/cl4_parachoque_traseiro_5ea593a5.png', '2026-04-16 13:15:10'),
(6, 5, 'frente', '/SistemaCPE/web/uploads/fleet/cl5_frente_55445252.png', '2026-04-16 14:20:39'),
(7, 5, 'parachoque_dianteiro', '/SistemaCPE/web/uploads/fleet/cl5_parachoque_dianteiro_73c777e0.png', '2026-04-16 14:20:39'),
(8, 5, 'parachoque_traseiro', '/SistemaCPE/web/uploads/fleet/cl5_parachoque_traseiro_fa2a460b.png', '2026-04-16 14:20:39'),
(9, 5, 'avaria_retorno', '/SistemaCPE/web/uploads/fleet/cl5_avaria_retorno_9ad6a49f.jpg', '2026-04-16 14:26:00'),
(14, 7, 'problema', '/SistemaCPE/web/uploads/fleet/cl7_problema_7454c09b.png', '2026-04-16 18:43:08'),
(15, 7, 'arranhado_lat_d_pchq_t', '/SistemaCPE/web/uploads/fleet/cl7_arranhado_lat_d_pchq_t_43a35e92.png', '2026-04-16 18:43:08'),
(16, 8, 'problema', '/SistemaCPE/web/uploads/fleet/cl8_problema_63111233.png', '2026-04-16 20:09:25'),
(17, 8, 'arranhado_lat_d_pchq_t', '/SistemaCPE/web/uploads/fleet/cl8_arranhado_lat_d_pchq_t_a8984165.png', '2026-04-16 20:09:25');

-- --------------------------------------------------------

--
-- Estrutura para tabela `fleet_checklist_problems`
--

CREATE TABLE `fleet_checklist_problems` (
  `id` int(11) NOT NULL,
  `checklist_id` int(11) NOT NULL,
  `item_nome` varchar(100) NOT NULL,
  `descricao_adicional` text DEFAULT NULL COMMENT 'Usado para o item "Outros"',
  `foto_path` varchar(500) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `fase` enum('saida','retorno') DEFAULT 'saida'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `fleet_checklist_problems`
--

INSERT INTO `fleet_checklist_problems` (`id`, `checklist_id`, `item_nome`, `descricao_adicional`, `foto_path`, `created_at`, `fase`) VALUES
(1, 5, 'Farol Esq', 'não vi o carro e bati ', NULL, '2026-04-16 14:26:00', 'retorno'),
(3, 7, 'Arranhado/Risco', '[{\"hotspot\":\"lat_d_pchq_t\",\"label\":\"Pchq Tras.\",\"photoUrl\":\"/SistemaCPE/web/uploads/fleet/cl7_arranhado_lat_d_pchq_t_43a35e92.png\"}]', NULL, '2026-04-16 18:43:08', 'saida'),
(4, 8, 'Arranhado/Risco', '[{\"hotspot\":\"lat_d_pchq_t\",\"label\":\"Pchq Tras.\",\"photoUrl\":\"/SistemaCPE/web/uploads/fleet/cl8_arranhado_lat_d_pchq_t_a8984165.png\"}]', NULL, '2026-04-16 20:09:25', 'saida');

-- --------------------------------------------------------

--
-- Estrutura para tabela `fleet_km_alerts`
--

CREATE TABLE `fleet_km_alerts` (
  `id` int(11) NOT NULL,
  `vehicle_id` int(11) NOT NULL,
  `tipo` varchar(100) NOT NULL,
  `km_limite` int(11) NOT NULL,
  `notificado` tinyint(1) DEFAULT 0,
  `created_by` bigint(20) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `fleet_maintenance`
--

CREATE TABLE `fleet_maintenance` (
  `id` int(11) NOT NULL,
  `vehicle_id` int(11) NOT NULL,
  `tipo` varchar(100) NOT NULL DEFAULT 'Outro',
  `descricao` text DEFAULT NULL,
  `data_entrada` date DEFAULT NULL,
  `data_conclusao` date DEFAULT NULL,
  `km_atual` int(11) DEFAULT NULL,
  `custo` decimal(10,2) DEFAULT 0.00,
  `fornecedor` varchar(200) DEFAULT NULL,
  `status` enum('agendado','em_andamento','concluido','cancelado') DEFAULT 'agendado',
  `observacoes` text DEFAULT NULL,
  `trip_id` int(11) DEFAULT NULL,
  `created_by` bigint(20) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `fleet_maintenance`
--

INSERT INTO `fleet_maintenance` (`id`, `vehicle_id`, `tipo`, `descricao`, `data_entrada`, `data_conclusao`, `km_atual`, `custo`, `fornecedor`, `status`, `observacoes`, `trip_id`, `created_by`, `created_at`, `updated_at`) VALUES
(1, 4, 'Alinhamento', 'bla bla bla ', '2026-04-16', '2026-04-17', 48000, 12000.00, 'mm', 'concluido', '', NULL, 15, '2026-04-16 12:57:00', '2026-04-16 13:14:21'),
(2, 4, 'Troca de Pastilha de Freio', 'troca de pastilha ', '2026-04-23', '2026-04-24', 5, 250.00, 'mm', 'concluido', '', NULL, 25, '2026-04-16 16:36:14', '2026-04-22 17:13:19');

-- --------------------------------------------------------

--
-- Estrutura para tabela `fleet_maintenance_files`
--

CREATE TABLE `fleet_maintenance_files` (
  `id` int(11) NOT NULL,
  `maintenance_id` int(11) NOT NULL,
  `file_path` varchar(500) NOT NULL,
  `nome_arquivo` varchar(200) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `fleet_maintenance_types`
--

CREATE TABLE `fleet_maintenance_types` (
  `id` int(11) NOT NULL,
  `name` varchar(100) NOT NULL,
  `created_by` bigint(20) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `fleet_maintenance_types`
--

INSERT INTO `fleet_maintenance_types` (`id`, `name`, `created_by`, `created_at`) VALUES
(1, 'Troca de Oleo', NULL, '2026-04-16 12:45:18'),
(2, 'Troca de Pneu', NULL, '2026-04-16 12:45:18'),
(3, 'Revisao', NULL, '2026-04-16 12:45:18'),
(4, 'Troca de Filtro', NULL, '2026-04-16 12:45:18'),
(5, 'Alinhamento', NULL, '2026-04-16 12:45:18'),
(6, 'Balanceamento', NULL, '2026-04-16 12:45:18'),
(7, 'Funilaria/Pintura', NULL, '2026-04-16 12:45:18'),
(8, 'Eletrica', NULL, '2026-04-16 12:45:18'),
(9, 'Troca de Correia', NULL, '2026-04-16 12:45:18'),
(10, 'Troca de Pastilha de Freio', NULL, '2026-04-16 12:45:18'),
(11, 'Lavagem/Higienizacao', NULL, '2026-04-16 12:45:18');

-- --------------------------------------------------------

--
-- Estrutura para tabela `fleet_reservations`
--

CREATE TABLE `fleet_reservations` (
  `id` int(11) NOT NULL,
  `vehicle_id` int(11) NOT NULL,
  `solicitante_id` bigint(20) NOT NULL,
  `destino` varchar(200) NOT NULL,
  `data_reserva` date NOT NULL,
  `horario_inicio` time NOT NULL,
  `horario_fim` time NOT NULL,
  `status` enum('pendente','aprovado','rejeitado','cancelado','concluido') DEFAULT 'pendente',
  `aprovador_id` bigint(20) DEFAULT NULL,
  `aprovado_em` timestamp NULL DEFAULT NULL,
  `motivo_rejeicao` text DEFAULT NULL,
  `notif_lida` tinyint(1) DEFAULT 0,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `fleet_reservations`
--

INSERT INTO `fleet_reservations` (`id`, `vehicle_id`, `solicitante_id`, `destino`, `data_reserva`, `horario_inicio`, `horario_fim`, `status`, `aprovador_id`, `aprovado_em`, `motivo_rejeicao`, `notif_lida`, `created_at`, `updated_at`) VALUES
(1, 4, 25, 'vila velha', '2026-04-16', '18:00:00', '19:00:00', 'aprovado', 15, '2026-04-16 20:05:11', NULL, 1, '2026-04-16 19:50:58', '2026-04-22 21:02:55'),
(2, 4, 25, 'ali', '2026-04-17', '08:00:00', '18:00:00', 'aprovado', 15, '2026-04-16 20:08:23', NULL, 1, '2026-04-16 20:08:06', '2026-04-22 21:02:55');

-- --------------------------------------------------------

--
-- Estrutura para tabela `fleet_trips`
--

CREATE TABLE `fleet_trips` (
  `id` int(11) NOT NULL,
  `vehicle_id` int(11) NOT NULL,
  `checklist_id` int(11) DEFAULT NULL COMMENT 'Checklist associado (opcional)',
  `condutor_id` bigint(20) DEFAULT NULL,
  `unidade` varchar(100) DEFAULT NULL COMMENT 'Ex: CPE BH, CPE SP',
  `descricao` varchar(200) DEFAULT NULL,
  `data_saida` date NOT NULL,
  `data_retorno` date DEFAULT NULL,
  `km_inicial` int(11) DEFAULT 0,
  `km_final` int(11) DEFAULT 0,
  `custo_aluguel` decimal(10,2) DEFAULT 0.00,
  `custo_telemetria` decimal(10,2) DEFAULT 0.00,
  `custo_estacionamento` decimal(10,2) DEFAULT 0.00,
  `custo_pedagio` decimal(10,2) DEFAULT 0.00,
  `custo_manutencao` decimal(10,2) DEFAULT 0.00,
  `custo_combustivel` decimal(10,2) DEFAULT 0.00,
  `custo_lavagem` decimal(10,2) DEFAULT 0.00,
  `custo_outros` decimal(10,2) DEFAULT 0.00,
  `observacoes` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `fleet_trips`
--

INSERT INTO `fleet_trips` (`id`, `vehicle_id`, `checklist_id`, `condutor_id`, `unidade`, `descricao`, `data_saida`, `data_retorno`, `km_inicial`, `km_final`, `custo_aluguel`, `custo_telemetria`, `custo_estacionamento`, `custo_pedagio`, `custo_manutencao`, `custo_combustivel`, `custo_lavagem`, `custo_outros`, `observacoes`, `created_at`, `updated_at`) VALUES
(1, 1, NULL, NULL, 'CPE BH', NULL, '2026-01-15', '2026-01-20', 45000, 45700, 2386.95, 81.00, 0.00, 14.95, 0.00, 0.00, 0.00, 0.00, NULL, '2026-04-15 18:45:47', '2026-04-15 18:45:47'),
(2, 2, NULL, NULL, 'CPE SP', NULL, '2026-02-14', '2026-02-19', 31870, 32870, 3670.44, 81.00, 0.00, 14.95, 0.00, 578.18, 0.00, 0.00, NULL, '2026-04-15 18:45:47', '2026-04-15 18:45:47'),
(3, 3, NULL, NULL, 'CPE BH', NULL, '2026-03-16', '2026-03-21', 8430, 9170, 2119.47, 81.00, 0.00, 14.95, 0.00, 0.00, 0.00, 0.00, NULL, '2026-04-15 18:45:47', '2026-04-15 18:45:47');

-- --------------------------------------------------------

--
-- Estrutura para tabela `fleet_vehicles`
--

CREATE TABLE `fleet_vehicles` (
  `id` int(11) NOT NULL,
  `placa` varchar(10) NOT NULL COMMENT 'Ex: ABC-1234 ou ABC1D23',
  `modelo` varchar(100) NOT NULL,
  `tipo` enum('carro','pickup','van','caminhao','moto') DEFAULT 'carro',
  `ano` int(11) DEFAULT NULL,
  `cor` varchar(50) DEFAULT NULL,
  `unidade` varchar(100) DEFAULT NULL COMMENT 'Ex: CPE BH, CPE SP, CPE PE',
  `status` enum('ativo','em_viagem','manutencao','revisao','inativo') DEFAULT 'ativo',
  `created_by` bigint(20) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `km_atual` int(11) DEFAULT 0 COMMENT 'KM atual do hodometro',
  `avaria_descricao` text DEFAULT NULL,
  `avaria_em` timestamp NULL DEFAULT NULL,
  `avaria_corrigida_em` timestamp NULL DEFAULT NULL,
  `avaria_corrigida_por` bigint(20) DEFAULT NULL,
  `avaria_correcao_obs` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `fleet_vehicles`
--

INSERT INTO `fleet_vehicles` (`id`, `placa`, `modelo`, `tipo`, `ano`, `cor`, `unidade`, `status`, `created_by`, `created_at`, `updated_at`, `km_atual`, `avaria_descricao`, `avaria_em`, `avaria_corrigida_em`, `avaria_corrigida_por`, `avaria_correcao_obs`) VALUES
(1, 'ABC-1234', 'HB20', 'carro', 2022, 'Branco', 'CPE BH', 'ativo', NULL, '2026-04-15 18:45:47', '2026-04-15 18:45:47', 0, NULL, NULL, NULL, NULL, NULL),
(2, 'DEF-5678', 'Strada', 'pickup', 2021, 'Prata', 'CPE SP', 'ativo', NULL, '2026-04-15 18:45:47', '2026-04-15 18:45:47', 0, NULL, NULL, NULL, NULL, NULL),
(3, 'GHI-9012', 'Spin', 'van', 2023, 'Branco', 'CPE BH', 'ativo', NULL, '2026-04-15 18:45:47', '2026-04-15 18:45:47', 0, NULL, NULL, NULL, NULL, NULL),
(4, 'JKL-3456', 'Corolla', 'carro', 2020, 'Preto', 'CPE PE', 'ativo', NULL, '2026-04-15 18:45:47', '2026-04-22 17:19:29', 5100, NULL, NULL, '2026-04-16 14:49:08', 15, 'Foi realizada a troca do farol que foi quebrado'),
(5, 'MNO-7890', 'S10', 'pickup', 2022, 'Prata', 'CPE BA', 'ativo', NULL, '2026-04-15 18:45:47', '2026-04-15 18:45:47', 0, NULL, NULL, NULL, NULL, NULL),
(6, 'PQR-1122', 'Onix', 'carro', 2023, 'Vermelho', 'CPE SP', 'ativo', NULL, '2026-04-15 18:45:47', '2026-04-15 18:45:47', 0, NULL, NULL, NULL, NULL, NULL);

-- --------------------------------------------------------

--
-- Estrutura para tabela `fleet_vehicle_history`
--

CREATE TABLE `fleet_vehicle_history` (
  `id` int(11) NOT NULL,
  `vehicle_id` int(11) NOT NULL,
  `evento` varchar(100) NOT NULL,
  `descricao` text DEFAULT NULL,
  `status_anterior` varchar(50) DEFAULT NULL,
  `status_novo` varchar(50) DEFAULT NULL,
  `user_id` bigint(20) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `fleet_vehicle_history`
--

INSERT INTO `fleet_vehicle_history` (`id`, `vehicle_id`, `evento`, `descricao`, `status_anterior`, `status_novo`, `user_id`, `created_at`) VALUES
(1, 4, 'Vistoria de retorno', 'Checklist #4 — OK', 'em_viagem', 'ativo', 15, '2026-04-16 14:16:27'),
(2, 4, 'Vistoria de retorno', 'Checklist #5 — Com avaria', 'em_viagem', 'manutencao', 15, '2026-04-16 14:26:29'),
(3, 4, 'Avaria corrigida', 'Foi realizada a troca do farol que foi quebrado', 'manutencao', 'ativo', 15, '2026-04-16 14:49:08'),
(4, 4, 'Vistoria de retorno', 'Checklist #6 — OK', 'em_viagem', 'ativo', 15, '2026-04-16 16:32:59'),
(5, 4, 'Manutencao/Reparo', 'ficar para reparo do farol ', 'ativo', 'manutencao', 25, '2026-04-16 16:33:55'),
(6, 4, 'Liberado para uso', 'Status anterior: manutencao', 'manutencao', 'ativo', 25, '2026-04-16 16:36:38'),
(7, 4, 'Vistoria de retorno', 'Checklist #7 — OK', 'em_viagem', 'ativo', 15, '2026-04-16 19:24:05'),
(8, 4, 'Vistoria de retorno', 'Checklist #8 — OK', 'em_viagem', 'ativo', 15, '2026-04-16 20:15:52'),
(9, 4, 'Vistoria de retorno', 'Checklist #9 — OK', 'em_viagem', 'ativo', 25, '2026-04-22 17:19:29');

-- --------------------------------------------------------

--
-- Estrutura para tabela `fleet_vehicle_photos`
--

CREATE TABLE `fleet_vehicle_photos` (
  `id` int(11) NOT NULL,
  `vehicle_id` int(11) NOT NULL,
  `foto_path` varchar(500) NOT NULL,
  `angulo` varchar(50) DEFAULT 'frente',
  `is_current` tinyint(1) DEFAULT 1 COMMENT '1=foto atual, 0=histórico',
  `substituida_por_user_id` bigint(20) DEFAULT NULL COMMENT 'Usuário que fez a substituição',
  `motivo_substituicao` text DEFAULT NULL COMMENT 'Motivo da troca de foto',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Despejando dados para a tabela `fleet_vehicle_photos`
--

INSERT INTO `fleet_vehicle_photos` (`id`, `vehicle_id`, `foto_path`, `angulo`, `is_current`, `substituida_por_user_id`, `motivo_substituicao`, `created_at`) VALUES
(4, 4, '/SistemaCPE/web/uploads/fleet/cl6_frente_4c27877b.png', 'frente', 1, 15, NULL, '2026-04-16 16:32:59'),
(5, 4, '/SistemaCPE/web/uploads/fleet/cl6_parachoque_dianteiro_026bc08d.png', 'parachoque_dianteiro', 1, 15, NULL, '2026-04-16 16:32:59'),
(6, 4, '/SistemaCPE/web/uploads/fleet/cl6_parachoque_traseiro_8455b197.png', 'parachoque_traseiro', 1, 15, NULL, '2026-04-16 16:32:59');

-- --------------------------------------------------------

--
-- Estrutura para tabela `historico_task`
--

CREATE TABLE `historico_task` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `tarefa_id` bigint(20) UNSIGNED NOT NULL,
  `etapa_id` bigint(20) UNSIGNED DEFAULT NULL,
  `usuario_id` bigint(20) NOT NULL,
  `acao` varchar(100) NOT NULL,
  `detalhe` text DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
(63, 6, NULL, 20, 'atualizou', 'status: 20', '2026-04-14 20:48:53'),
(64, 6, NULL, 15, 'atualizou', 'status: 21', '2026-04-15 17:36:57'),
(65, 6, NULL, 15, 'atualizou', 'status: 20', '2026-04-15 21:06:45'),
(66, 6, NULL, 15, 'atualizou', 'status: 21', '2026-04-16 16:44:38'),
(69, 10, NULL, 25, 'criou', 'Tarefa criada: novo teste', '2026-04-21 22:21:24'),
(70, 10, NULL, 25, 'atualizou', 'editou', '2026-04-21 22:21:27'),
(71, 10, NULL, 25, 'atualizou', 'status: 31', '2026-04-21 22:21:37'),
(72, 10, NULL, 15, 'encaminhou', 'Encaminhada para grupo 3', '2026-04-21 22:28:33'),
(73, 10, NULL, 20, 'atualizou', 'editou', '2026-04-21 22:30:01'),
(74, 10, NULL, 20, 'atualizou', 'status: 29', '2026-04-21 22:30:19'),
(75, 10, NULL, 20, 'finalizou', 'Tarefa finalizada', '2026-04-21 22:44:44'),
(76, 10, NULL, 20, 'reabriu', 'Tarefa reaberta', '2026-04-21 22:47:39'),
(77, 10, NULL, 20, 'finalizou', 'Tarefa finalizada', '2026-04-21 22:47:50'),
(78, 11, NULL, 20, 'criou', 'Tarefa criada: contador de tempo planejado', '2026-04-21 22:48:32'),
(79, 11, NULL, 20, 'atualizou', 'editou', '2026-04-21 22:49:02'),
(80, 11, NULL, 20, 'atualizou', 'editou', '2026-04-21 23:05:21'),
(81, 11, NULL, 20, 'atualizou', 'status: Concluído', '2026-04-21 23:12:25'),
(82, 11, NULL, 20, 'encaminhou', 'Encaminhada para grupo 9', '2026-04-21 23:12:28'),
(83, 11, NULL, 25, 'atualizou', 'editou', '2026-04-21 23:19:51'),
(84, 11, NULL, 15, 'atualizou', 'status: Concluído', '2026-04-22 15:08:56'),
(85, 11, NULL, 15, 'finalizou', 'Tarefa finalizada', '2026-04-22 15:09:00'),
(86, 4, NULL, 15, 'atualizou', 'editou', '2026-04-22 17:03:56'),
(87, 12, NULL, 15, 'criou', 'Tarefa criada: teste 01', '2026-04-22 17:16:20'),
(88, 12, NULL, 15, 'atualizou', 'editou', '2026-04-22 17:16:29'),
(89, 12, NULL, 15, 'atualizou', 'editou', '2026-04-22 17:16:47'),
(90, 12, NULL, 25, 'atualizou', 'editou', '2026-04-22 17:49:06'),
(91, 11, NULL, 25, 'reabriu', 'Tarefa reaberta', '2026-04-22 17:49:28'),
(92, 11, NULL, 25, 'finalizou', 'Tarefa finalizada', '2026-04-22 17:49:33'),
(93, 12, NULL, 25, 'atualizou', 'editou', '2026-04-22 17:55:19'),
(94, 12, NULL, 25, 'atualizou', 'editou', '2026-04-22 17:56:59'),
(95, 12, NULL, 25, 'atualizou', 'editou', '2026-04-22 18:33:28'),
(96, 12, NULL, 25, 'atualizou', 'editou', '2026-04-22 18:35:25'),
(97, 12, NULL, 25, 'atualizou', 'status: Em Andamento', '2026-04-22 18:40:26'),
(98, 12, NULL, 15, 'atualizou', 'status: Planejado', '2026-04-22 19:07:40'),
(99, 12, NULL, 25, 'atualizou', 'status: Concluído', '2026-04-22 19:08:58');

-- --------------------------------------------------------

--
-- Estrutura para tabela `notificacoes`
--

CREATE TABLE `notificacoes` (
  `id` int(11) NOT NULL,
  `ticket_id` int(11) DEFAULT NULL,
  `usuario_id` int(11) DEFAULT NULL,
  `mensagem` varchar(255) DEFAULT NULL,
  `tipo` varchar(50) DEFAULT NULL,
  `lido` tinyint(1) DEFAULT 0,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
(168, NULL, 20, 'O grupo \"assistencia\" aceitou o convite para o quadro \"Processo de venda novo\".', 'convite_aceito_task', 1, '2026-04-14 17:55:29', '2026-04-14 18:15:16'),
(169, NULL, 25, 'Seu grupo foi convidado para participar do quadro \"Processo de venda novo\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 1, '2026-04-16 16:44:55', '2026-04-21 20:13:54'),
(170, NULL, 26, 'Seu grupo foi convidado para participar do quadro \"Processo de venda novo\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 0, '2026-04-16 16:44:55', '2026-04-16 16:44:55'),
(171, NULL, 15, 'O grupo \"Estoque\" recusou o convite para o quadro \"Processo de venda novo\".', 'convite_recusado_task', 1, '2026-04-21 20:28:22', '2026-04-21 21:31:41'),
(172, NULL, 20, 'Seu grupo foi convidado para participar do quadro \"Processo de venda teste final\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 1, '2026-04-21 21:21:32', '2026-04-21 22:26:06'),
(173, NULL, 23, 'Seu grupo foi convidado para participar do quadro \"Processo de venda teste final\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 0, '2026-04-21 21:21:32', '2026-04-21 21:21:32'),
(174, NULL, 24, 'Seu grupo foi convidado para participar do quadro \"Processo de venda teste final\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 0, '2026-04-21 21:21:32', '2026-04-21 21:21:32'),
(175, NULL, 20, 'Seu grupo foi convidado para participar do quadro \"Processo de venda teste final\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 1, '2026-04-21 21:44:42', '2026-04-21 22:26:06'),
(176, NULL, 23, 'Seu grupo foi convidado para participar do quadro \"Processo de venda teste final\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 0, '2026-04-21 21:44:42', '2026-04-21 21:44:42'),
(177, NULL, 24, 'Seu grupo foi convidado para participar do quadro \"Processo de venda teste final\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 0, '2026-04-21 21:44:42', '2026-04-21 21:44:42'),
(178, NULL, 20, 'Seu grupo foi convidado para participar do quadro \"Processo de venda teste final\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 1, '2026-04-21 21:55:19', '2026-04-21 22:26:06'),
(179, NULL, 23, 'Seu grupo foi convidado para participar do quadro \"Processo de venda teste final\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 0, '2026-04-21 21:55:19', '2026-04-21 21:55:19'),
(180, NULL, 24, 'Seu grupo foi convidado para participar do quadro \"Processo de venda teste final\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 0, '2026-04-21 21:55:19', '2026-04-21 21:55:19'),
(181, NULL, 20, 'Você foi adicionado ao quadro \"123 projeto\". Acesse Tarefas para ver.', 'convite_task', 1, '2026-04-21 21:56:30', '2026-04-21 22:26:06'),
(182, NULL, 20, 'Seu grupo foi convidado para participar do quadro \"123 projeto\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 1, '2026-04-21 21:56:49', '2026-04-21 22:26:08'),
(183, NULL, 23, 'Seu grupo foi convidado para participar do quadro \"123 projeto\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 0, '2026-04-21 21:56:49', '2026-04-21 21:56:49'),
(184, NULL, 24, 'Seu grupo foi convidado para participar do quadro \"123 projeto\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 0, '2026-04-21 21:56:49', '2026-04-21 21:56:49'),
(185, NULL, 25, 'O grupo \"assistencia\" aceitou o convite para o quadro \"123 projeto\".', 'convite_aceito_task', 1, '2026-04-21 21:58:31', '2026-04-21 21:59:53'),
(186, NULL, 25, 'O grupo \"assistencia\" aceitou o convite para o quadro \"Processo de venda teste final\".', 'convite_aceito_task', 1, '2026-04-21 21:58:33', '2026-04-21 21:59:53'),
(187, 10, 20, 'Tarefa \"novo teste\" foi encaminhada para seu grupo.', 'encaminhamento_task', 1, '2026-04-21 22:28:33', '2026-04-21 22:29:46'),
(188, 10, 23, 'Tarefa \"novo teste\" foi encaminhada para seu grupo.', 'encaminhamento_task', 0, '2026-04-21 22:28:33', '2026-04-21 22:28:33'),
(189, 10, 24, 'Tarefa \"novo teste\" foi encaminhada para seu grupo.', 'encaminhamento_task', 0, '2026-04-21 22:28:33', '2026-04-21 22:28:33'),
(190, 11, 25, 'Tarefa \"contador de tempo planejado\" foi encaminhada para seu grupo.', 'encaminhamento_task', 1, '2026-04-21 23:12:28', '2026-04-21 23:13:04'),
(191, 11, 26, 'Tarefa \"contador de tempo planejado\" foi encaminhada para seu grupo.', 'encaminhamento_task', 0, '2026-04-21 23:12:28', '2026-04-21 23:12:28'),
(192, NULL, 27, 'Seu grupo foi convidado para participar do quadro \"123 projeto\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 0, '2026-04-22 17:52:20', '2026-04-22 17:52:20'),
(193, NULL, 28, 'Seu grupo foi convidado para participar do quadro \"123 projeto\". Acesse Tarefas para aceitar ou recusar.', 'convite_task', 0, '2026-04-22 17:52:20', '2026-04-22 17:52:20'),
(194, NULL, 25, 'O grupo \"faturamento\" aceitou o convite para o quadro \"123 projeto\".', 'convite_aceito_task', 1, '2026-04-22 17:53:30', '2026-04-22 17:53:38'),
(195, NULL, 15, 'Reserva criada para a sala. Confirme em até 40 min (reserva #1).', 'sucesso', 0, '2026-04-30 21:04:34', '2026-04-30 21:04:34'),
(196, NULL, 15, 'Reserva #1 confirmada com sucesso.', 'sucesso', 0, '2026-04-30 21:04:47', '2026-04-30 21:04:47'),
(197, NULL, 15, 'Reserva #1 foi cancelada.', 'aviso', 0, '2026-04-30 21:05:15', '2026-04-30 21:05:15'),
(198, NULL, 15, 'Reserva criada para a sala. Confirme em até 40 min (reserva #2).', 'sucesso', 0, '2026-04-30 21:20:53', '2026-04-30 21:20:53'),
(199, 2, 20, 'Você foi convidado para a reunião \"Reunião top 2\" em 01/05 00:00. Confirme presença na página de Recepção.', 'convite_reuniao', 0, '2026-04-30 21:20:53', '2026-04-30 21:20:53'),
(200, 2, 25, 'Você foi convidado para a reunião \"Reunião top 2\" em 01/05 00:00. Confirme presença na página de Recepção.', 'convite_reuniao', 1, '2026-04-30 21:20:53', '2026-04-30 21:21:18'),
(201, 2, 15, 'Edson Cardoso aceitou o convite para \"Reunião top 2\".', 'convite_aceito_reuniao', 0, '2026-04-30 21:21:22', '2026-04-30 21:21:22'),
(202, NULL, 15, 'Reserva #2 confirmada com sucesso.', 'sucesso', 0, '2026-04-30 21:21:37', '2026-04-30 21:21:37');

-- --------------------------------------------------------

--
-- Estrutura para tabela `page_permissions`
--

CREATE TABLE `page_permissions` (
  `id` int(11) NOT NULL,
  `page_name` varchar(50) NOT NULL COMMENT 'Nome da página (ex: CHAT, USERS)',
  `allowed_roles` text NOT NULL COMMENT 'Roles separados por vírgula (ex: ADMIN,TI)',
  `updated_by` int(11) DEFAULT NULL COMMENT 'ID do admin que alterou',
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
(14, 'PASSWORD_VAULT', 'USER,RESPONSAVEL_GRUPO,TI,MANAGER,ADMIN', NULL, '2026-04-23 18:39:48'),
(15, 'SETTINGS', 'ADMIN', NULL, '2026-04-06 22:28:35'),
(16, 'PERMISSIONS', 'ADMIN', NULL, '2026-04-06 22:28:35'),
(17, 'AVALIACOES', 'RESPONSAVEL_GRUPO,ADMIN,TI,MANAGER', NULL, '2026-04-10 17:15:03');

-- --------------------------------------------------------

--
-- Estrutura para tabela `passwords`
--

CREATE TABLE `passwords` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `client` varchar(255) NOT NULL,
  `email` varchar(255) DEFAULT NULL,
  `description` varchar(500) NOT NULL,
  `password` text NOT NULL,
  `link` varchar(500) DEFAULT NULL,
  `observation` text DEFAULT NULL,
  `group_id` int(11) DEFAULT NULL,
  `is_public` tinyint(1) DEFAULT 0,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `is_exclusive` tinyint(1) DEFAULT 0,
  `allowed_group_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `passwords`
--

INSERT INTO `passwords` (`id`, `user_id`, `client`, `email`, `description`, `password`, `link`, `observation`, `group_id`, `is_public`, `created_at`, `updated_at`, `is_exclusive`, `allowed_group_id`) VALUES
(1, 1, 'tese', 'admin@cpe.com.br', 'teste', '22223333', 'https://github.com/cpeinfra-cmyk/cpenavigator', 'teste22', NULL, 0, '2026-03-07 07:17:57', '2026-03-07 07:17:57', 0, NULL),
(2, 1, 'teste 55', 'admin@cpe.com.br', 'teste 44', 'd3d5t7gas1436', 'https://github.com/cpeinfra-cmyk/cpenavigator', '3d3t', NULL, 0, '2026-03-07 16:27:31', '2026-03-07 16:27:31', 0, NULL),
(4, 1, 'Jon', 'admin@cpe.com.br', 'teste jon', 'jon123', 'https://github.com/login/oauth/authorize', 'teste jon', NULL, 0, '2026-03-10 14:57:10', '2026-03-10 14:57:10', 0, NULL);

-- --------------------------------------------------------

--
-- Estrutura para tabela `recepcao_convidados`
--

CREATE TABLE `recepcao_convidados` (
  `id` int(11) NOT NULL,
  `reserva_id` int(11) NOT NULL,
  `usuario_id` bigint(20) NOT NULL,
  `status` enum('pendente','aceito','recusado') DEFAULT 'pendente',
  `respondido_em` datetime DEFAULT NULL,
  `convidado_por` bigint(20) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `recepcao_convidados`
--

INSERT INTO `recepcao_convidados` (`id`, `reserva_id`, `usuario_id`, `status`, `respondido_em`, `convidado_por`, `created_at`, `updated_at`) VALUES
(1, 2, 20, 'pendente', NULL, 15, '2026-04-30 21:20:53', '2026-04-30 21:20:53'),
(2, 2, 25, 'aceito', '2026-04-30 18:21:22', 15, '2026-04-30 21:20:53', '2026-04-30 21:21:22');

-- --------------------------------------------------------

--
-- Estrutura para tabela `recepcao_envios`
--

CREATE TABLE `recepcao_envios` (
  `id` int(11) NOT NULL,
  `remetente_id` bigint(20) NOT NULL,
  `destino` varchar(255) NOT NULL,
  `destinatario` varchar(150) NOT NULL,
  `valor_mercadoria` decimal(12,2) DEFAULT 0.00,
  `codigo_correios` varchar(30) DEFAULT NULL,
  `status_correios` varchar(120) DEFAULT NULL,
  `status_data` datetime DEFAULT NULL,
  `status_local` varchar(180) DEFAULT NULL,
  `ultima_atualizacao` datetime DEFAULT NULL,
  `observacoes` varchar(500) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `recepcao_envios`
--

INSERT INTO `recepcao_envios` (`id`, `remetente_id`, `destino`, `destinatario`, `valor_mercadoria`, `codigo_correios`, `status_correios`, `status_data`, `status_local`, `ultima_atualizacao`, `observacoes`, `created_at`, `updated_at`) VALUES
(1, 15, 'CPE PE', 'Mari', 16000.00, 'AD369661868BR', 'AD369661868BR', NULL, 'belo', '2026-04-30 18:45:17', 'teste de envio', '2026-04-30 21:28:39', '2026-04-30 21:45:17');

-- --------------------------------------------------------

--
-- Estrutura para tabela `recepcao_escritorios`
--

CREATE TABLE `recepcao_escritorios` (
  `id` int(11) NOT NULL,
  `unit_id` int(11) NOT NULL,
  `nome` varchar(120) NOT NULL,
  `ativo` tinyint(1) DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `recepcao_escritorios`
--

INSERT INTO `recepcao_escritorios` (`id`, `unit_id`, `nome`, `ativo`, `created_at`, `updated_at`) VALUES
(1, 1, 'Escrit├│rio Bar├úo', 1, '2026-04-30 21:23:57', '2026-04-30 21:23:57'),
(2, 1, 'Escrit├│rio Raja', 1, '2026-04-30 21:23:57', '2026-04-30 21:23:57');

-- --------------------------------------------------------

--
-- Estrutura para tabela `recepcao_reservas`
--

CREATE TABLE `recepcao_reservas` (
  `id` int(11) NOT NULL,
  `sala_id` int(11) NOT NULL,
  `usuario_id` bigint(20) NOT NULL,
  `titulo` varchar(200) NOT NULL,
  `descricao` varchar(500) DEFAULT NULL,
  `inicio` datetime NOT NULL,
  `fim` datetime NOT NULL,
  `status` enum('pendente','confirmada','expirada','cancelada','concluida') DEFAULT 'pendente',
  `confirmacao_prazo` datetime NOT NULL,
  `confirmada_em` datetime DEFAULT NULL,
  `cancelada_em` datetime DEFAULT NULL,
  `motivo_cancel` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `recepcao_reservas`
--

INSERT INTO `recepcao_reservas` (`id`, `sala_id`, `usuario_id`, `titulo`, `descricao`, `inicio`, `fim`, `status`, `confirmacao_prazo`, `confirmada_em`, `cancelada_em`, `motivo_cancel`, `created_at`, `updated_at`) VALUES
(1, 2, 15, 'Reunião top', NULL, '2026-04-30 18:30:00', '2026-04-30 19:30:00', 'cancelada', '2026-04-30 18:44:34', '2026-04-30 18:04:47', '2026-04-30 18:05:15', 'Cancelada pelo usuário', '2026-04-30 21:04:34', '2026-04-30 21:05:15'),
(2, 2, 15, 'Reunião top 2', 'Vai ser na barão viu pessoal', '2026-05-01 00:00:00', '2026-05-02 00:00:00', 'confirmada', '2026-04-30 19:00:53', '2026-04-30 18:21:37', NULL, NULL, '2026-04-30 21:20:53', '2026-04-30 21:21:37');

-- --------------------------------------------------------

--
-- Estrutura para tabela `recepcao_salas`
--

CREATE TABLE `recepcao_salas` (
  `id` int(11) NOT NULL,
  `unit_id` int(11) NOT NULL,
  `escritorio_id` int(11) DEFAULT NULL,
  `nome` varchar(120) NOT NULL,
  `tipo` enum('sala','auditorio') DEFAULT 'sala',
  `capacidade` int(11) DEFAULT NULL,
  `descricao` varchar(500) DEFAULT NULL,
  `cor` varchar(7) DEFAULT '#3b82f6',
  `ativa` tinyint(1) DEFAULT 1,
  `criado_por` bigint(20) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `recepcao_salas`
--

INSERT INTO `recepcao_salas` (`id`, `unit_id`, `escritorio_id`, `nome`, `tipo`, `capacidade`, `descricao`, `cor`, `ativa`, `criado_por`, `created_at`, `updated_at`) VALUES
(1, 1, NULL, 'Sala 1', 'sala', NULL, NULL, '#696969', 1, 15, '2026-04-30 21:03:19', '2026-04-30 21:03:19'),
(2, 1, NULL, 'Sala 2', 'sala', 5, NULL, '#19335c', 1, 15, '2026-04-30 21:04:12', '2026-04-30 21:04:12');

-- --------------------------------------------------------

--
-- Estrutura para tabela `status_task`
--

CREATE TABLE `status_task` (
  `id` int(10) UNSIGNED NOT NULL,
  `group_id` int(11) DEFAULT NULL,
  `espaco_id` int(10) UNSIGNED DEFAULT NULL,
  `nome` varchar(100) NOT NULL,
  `cor` varchar(7) DEFAULT '#6b7280',
  `icone` varchar(50) DEFAULT 'bi-circle',
  `ordem` int(11) DEFAULT 0,
  `is_final` tinyint(1) DEFAULT 0,
  `created_at` timestamp NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
(22, 3, 6, 'Feito', '#10b981', 'bi-check-circle', 3, 1, '2026-04-14 14:05:42'),
(23, 3, 6, 'Primeira venda confirmada', '#0052cc', 'bi-circle', 2, 0, '2026-04-14 14:06:02'),
(24, 9, 7, 'A Fazer', '#6b7280', 'bi-circle', 0, 0, '2026-04-21 21:21:02'),
(25, 9, 7, 'Fazendo', '#f59e0b', 'bi-arrow-right-circle', 1, 0, '2026-04-21 21:21:02'),
(26, 9, 7, 'Feito', '#10b981', 'bi-check-circle', 2, 1, '2026-04-21 21:21:02'),
(27, 9, 7, 'Primeira venda confirmada', '#0052cc', 'bi-circle', 3, 0, '2026-04-21 21:21:02'),
(28, 9, 8, 'Planejado', '#6b7280', 'bi-calendar', 0, 0, '2026-04-21 21:56:30'),
(29, 9, 8, 'Em Andamento', '#000000', 'bi-arrow-right-circle', 1, 0, '2026-04-21 21:56:30'),
(30, 9, 8, 'Bloqueado', '#ef4444', 'bi-x-circle', 2, 0, '2026-04-21 21:56:30'),
(31, 9, 8, 'Concluído', '#10b981', 'bi-check-circle', 3, 1, '2026-04-21 21:56:30');

-- --------------------------------------------------------

--
-- Estrutura para tabela `subcategorias`
--

CREATE TABLE `subcategorias` (
  `id` int(10) UNSIGNED NOT NULL,
  `categoria_id` int(10) UNSIGNED NOT NULL,
  `nome` varchar(255) NOT NULL,
  `descricao` text DEFAULT NULL,
  `sla_minutos` int(10) UNSIGNED DEFAULT NULL,
  `sla_primeira_resposta_minutos` int(10) UNSIGNED DEFAULT NULL,
  `ativo` tinyint(1) DEFAULT 1,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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

CREATE TABLE `subtarefas_task` (
  `id` int(11) NOT NULL,
  `tarefa_id` int(11) NOT NULL,
  `titulo` varchar(500) NOT NULL,
  `concluida` tinyint(1) DEFAULT 0,
  `concluida_em` datetime DEFAULT NULL,
  `criador_id` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp()
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `subtarefas_task`
--

INSERT INTO `subtarefas_task` (`id`, `tarefa_id`, `titulo`, `concluida`, `concluida_em`, `criador_id`, `created_at`) VALUES
(1, 2, 'indo separar', 1, '2026-04-13 20:26:31', 15, '2026-04-13 15:46:07'),
(2, 1, 'Verificar estoque', 1, '2026-04-13 20:25:44', 15, '2026-04-13 17:23:41'),
(3, 1, 'Separar itens', 0, NULL, 15, '2026-04-13 17:23:41'),
(4, 5, 'ainda falta embrulhar', 1, '2026-04-14 18:17:29', 20, '2026-04-14 11:49:13'),
(5, 5, 'falta alguém levar la depois de embrulhado', 1, '2026-04-14 18:17:30', 20, '2026-04-14 11:49:34'),
(6, 6, 'pegar o numero com alguém', 1, '2026-04-14 17:11:03', 20, '2026-04-14 14:10:34'),
(7, 11, 'teste de sub-tarefa 1', 0, NULL, 20, '2026-04-21 19:49:42'),
(8, 11, 'teste de sub tarefa 2', 0, NULL, 20, '2026-04-21 19:49:48'),
(9, 12, 'ters 01', 1, '2026-04-22 17:17:50', 25, '2026-04-22 14:17:39'),
(10, 12, 'comp', 0, NULL, 27, '2026-04-22 14:55:43');

-- --------------------------------------------------------

--
-- Estrutura para tabela `tarefas_task`
--

CREATE TABLE `tarefas_task` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `numero` varchar(20) DEFAULT NULL,
  `titulo` varchar(255) NOT NULL,
  `descricao` text DEFAULT NULL,
  `prioridade` enum('baixa','media','alta','urgente') DEFAULT 'media',
  `status_id` int(10) UNSIGNED DEFAULT NULL,
  `group_id` int(11) DEFAULT NULL,
  `espaco_id` int(10) UNSIGNED DEFAULT NULL,
  `criador_id` bigint(20) NOT NULL,
  `responsavel_id` bigint(20) DEFAULT NULL,
  `tempo_estimado` int(11) DEFAULT 0,
  `prazo` datetime DEFAULT NULL,
  `concluida_em` datetime DEFAULT NULL,
  `concluida_por` bigint(20) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `start_date` datetime DEFAULT NULL,
  `tempo_gasto` varchar(50) DEFAULT NULL,
  `tempo_restante` varchar(50) DEFAULT NULL,
  `relator_id` int(11) DEFAULT NULL,
  `cor_card` varchar(7) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `tarefas_task`
--

INSERT INTO `tarefas_task` (`id`, `numero`, `titulo`, `descricao`, `prioridade`, `status_id`, `group_id`, `espaco_id`, `criador_id`, `responsavel_id`, `tempo_estimado`, `prazo`, `concluida_em`, `concluida_por`, `created_at`, `updated_at`, `start_date`, `tempo_gasto`, `tempo_restante`, `relator_id`, `cor_card`) VALUES
(1, 'TASK-1', 'separar o pedido', NULL, 'media', 2, NULL, 1, 15, NULL, 0, NULL, NULL, NULL, '2026-04-13 18:45:13', '2026-04-13 20:06:12', NULL, NULL, NULL, 15, NULL),
(2, 'TDT-1', 'separar o pedido', NULL, 'media', 9, NULL, 3, 15, 19, 0, '2026-04-17 15:46:00', NULL, NULL, '2026-04-13 18:45:52', '2026-04-13 20:26:42', '2026-04-13 15:47:00', '2h', NULL, 15, NULL),
(3, 'TDT-2', 'Criar nota para o pedido', NULL, 'media', 9, 3, 3, 20, 20, 0, NULL, '2026-04-13 20:28:33', 20, '2026-04-13 20:28:20', '2026-04-13 20:28:39', NULL, NULL, NULL, 20, NULL),
(4, 'PDV-1', 'Aguardando venda', NULL, 'media', 12, 3, 4, 20, 15, 0, NULL, NULL, NULL, '2026-04-13 20:54:44', '2026-04-22 17:03:56', NULL, NULL, NULL, 20, NULL),
(5, 'PDVN-1', 'enviar para estoque', NULL, 'media', 22, 3, 6, 20, 24, 2, NULL, NULL, NULL, '2026-04-14 14:09:12', '2026-04-14 20:09:59', NULL, NULL, NULL, 20, NULL),
(6, 'PDVN-2', 'Faturar o pedido', 'Preciso faturar o numero do <b>pedido</b>', 'urgente', 21, 3, 6, 20, 15, 0, '2026-04-15 13:48:00', NULL, NULL, '2026-04-14 16:48:11', '2026-04-16 16:44:38', NULL, NULL, NULL, 20, '#000000'),
(7, 'PDVN-3', 'pegar o pedido', NULL, 'media', 22, 10, 6, 27, 27, 0, NULL, NULL, NULL, '2026-04-14 18:04:14', '2026-04-14 19:25:57', NULL, NULL, NULL, 27, NULL),
(10, '1P-1', 'novo teste', NULL, 'media', 31, 3, 8, 25, 20, 0, NULL, '2026-04-21 22:47:50', 20, '2026-04-21 22:21:24', '2026-04-21 22:47:50', NULL, NULL, NULL, 25, NULL),
(11, '1P-2', 'contador de tempo planejado', 'teste para contar tempo no status planejado&nbsp;', 'media', 31, 9, 8, 20, 25, 0, NULL, '2026-04-22 17:49:33', 25, '2026-04-21 22:48:32', '2026-04-22 17:49:33', NULL, NULL, NULL, 20, NULL),
(12, '1P-3', 'teste 01', NULL, 'media', 31, NULL, 8, 15, 25, 0, '2026-04-22 15:37:00', NULL, NULL, '2026-04-22 17:16:20', '2026-04-22 19:08:58', NULL, NULL, NULL, 15, NULL);

-- --------------------------------------------------------

--
-- Estrutura para tabela `tarefa_categorias_task`
--

CREATE TABLE `tarefa_categorias_task` (
  `tarefa_id` int(11) NOT NULL,
  `categoria_id` int(11) NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `tarefa_categorias_task`
--

INSERT INTO `tarefa_categorias_task` (`tarefa_id`, `categoria_id`) VALUES
(11, 1),
(11, 2),
(11, 3),
(11, 4),
(12, 1),
(12, 2),
(12, 4);

-- --------------------------------------------------------

--
-- Estrutura para tabela `tarefa_encaminhamentos_task`
--

CREATE TABLE `tarefa_encaminhamentos_task` (
  `id` int(11) NOT NULL,
  `tarefa_id` int(11) NOT NULL,
  `de_grupo_id` int(11) NOT NULL,
  `para_grupo_id` int(11) NOT NULL,
  `encaminhado_por` int(11) NOT NULL,
  `encaminhado_em` datetime NOT NULL DEFAULT current_timestamp(),
  `status_id_origem` int(11) DEFAULT NULL,
  `status_id_retorno` int(11) DEFAULT NULL,
  `devolvido_em` datetime DEFAULT NULL,
  `devolvido_por` int(11) DEFAULT NULL,
  `motivo_devolucao` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `tarefa_encaminhamentos_task`
--

INSERT INTO `tarefa_encaminhamentos_task` (`id`, `tarefa_id`, `de_grupo_id`, `para_grupo_id`, `encaminhado_por`, `encaminhado_em`, `status_id_origem`, `status_id_retorno`, `devolvido_em`, `devolvido_por`, `motivo_devolucao`) VALUES
(1, 10, 9, 3, 15, '2026-04-21 22:28:33', 31, 31, NULL, NULL, NULL),
(2, 11, 3, 9, 20, '2026-04-21 23:12:28', 31, 31, NULL, NULL, NULL);

-- --------------------------------------------------------

--
-- Estrutura para tabela `tarefa_historico_status_task`
--

CREATE TABLE `tarefa_historico_status_task` (
  `id` int(11) NOT NULL,
  `tarefa_id` int(11) NOT NULL,
  `status_id` int(11) DEFAULT NULL,
  `status_nome` varchar(100) DEFAULT NULL,
  `status_cor` varchar(7) DEFAULT NULL,
  `responsavel_id` int(11) DEFAULT NULL,
  `responsavel_group_id` int(11) DEFAULT NULL,
  `entrou_em` datetime NOT NULL DEFAULT current_timestamp(),
  `saiu_em` datetime DEFAULT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `tarefa_historico_status_task`
--

INSERT INTO `tarefa_historico_status_task` (`id`, `tarefa_id`, `status_id`, `status_nome`, `status_cor`, `responsavel_id`, `responsavel_group_id`, `entrou_em`, `saiu_em`) VALUES
(1, 1, 2, NULL, NULL, NULL, NULL, '2026-04-13 20:06:12', NULL),
(2, 2, 9, 'Feito', '#10b981', 19, 1, '2026-04-13 20:26:43', NULL),
(3, 3, 7, 'A Fazer', '#6b7280', NULL, 3, '2026-04-13 20:28:21', '2026-04-13 20:28:40'),
(4, 3, 9, 'Feito', '#10b981', 20, 3, '2026-04-13 20:28:40', NULL),
(5, 4, 12, 'A Fazer', '#6b7280', NULL, 3, '2026-04-13 20:54:44', '2026-04-22 17:03:56'),
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
(20, 6, 20, 'A Fazer (pegue o seu ticket)', '#1a1a1a', 15, NULL, '2026-04-14 20:48:54', '2026-04-15 17:36:57'),
(21, 6, 21, 'Fazendo', '#f59e0b', 15, NULL, '2026-04-15 17:36:57', '2026-04-15 21:06:45'),
(22, 6, 20, 'A Fazer (pegue o seu ticket)', '#1a1a1a', 15, NULL, '2026-04-15 21:06:45', '2026-04-16 16:44:38'),
(23, 6, 21, 'Fazendo', '#f59e0b', 15, NULL, '2026-04-16 16:44:38', NULL),
(24, 9, 28, 'Planejado', '#6b7280', NULL, 9, '2026-04-21 22:00:13', '2026-04-21 22:08:07'),
(25, 9, 31, 'Concluído', '#10b981', NULL, NULL, '2026-04-21 22:08:07', '2026-04-21 22:08:10'),
(26, 9, 12, 'A Fazer', '#6b7280', NULL, 3, '2026-04-21 22:08:10', '2026-04-21 22:16:52'),
(27, 9, 28, 'Planejado', '#6b7280', NULL, 3, '2026-04-21 22:16:52', '2026-04-21 22:17:01'),
(28, 9, 28, 'Planejado', '#6b7280', NULL, 3, '2026-04-21 22:17:01', '2026-04-21 22:17:13'),
(29, 9, 28, 'Planejado', '#6b7280', NULL, 3, '2026-04-21 22:17:13', '2026-04-21 22:21:08'),
(30, 9, 28, 'Planejado', '#6b7280', NULL, 3, '2026-04-21 22:21:08', '2026-04-21 22:21:14'),
(31, 9, 28, 'Planejado', '#6b7280', NULL, 3, '2026-04-21 22:21:14', NULL),
(32, 10, 28, 'Planejado', '#6b7280', NULL, 9, '2026-04-21 22:21:24', '2026-04-21 22:21:37'),
(33, 10, 31, 'Concluído', '#10b981', 25, 9, '2026-04-21 22:21:37', '2026-04-21 22:21:41'),
(34, 10, 28, 'Planejado', '#6b7280', NULL, 3, '2026-04-21 22:21:41', '2026-04-21 22:25:27'),
(35, 10, 28, 'Planejado', '#6b7280', NULL, 3, '2026-04-21 22:25:27', '2026-04-21 22:25:34'),
(36, 10, 28, 'Planejado', '#6b7280', NULL, 3, '2026-04-21 22:25:34', '2026-04-21 22:26:28'),
(37, 10, 28, 'Planejado', '#6b7280', NULL, 3, '2026-04-21 22:26:28', '2026-04-21 22:26:57'),
(38, 10, 28, 'Planejado', '#6b7280', NULL, 3, '2026-04-21 22:26:57', '2026-04-21 22:28:33'),
(39, 10, 28, 'Planejado', '#6b7280', NULL, 3, '2026-04-21 22:28:33', '2026-04-21 22:30:19'),
(40, 10, 29, 'Em Andamento', '#3b82f6', 20, 3, '2026-04-21 22:30:19', '2026-04-21 22:47:39'),
(41, 10, 28, 'Planejado', '#6b7280', NULL, 3, '2026-04-21 22:47:39', NULL),
(42, 11, 28, 'Planejado', '#6b7280', NULL, 3, '2026-04-21 22:48:32', '2026-04-21 23:12:25'),
(43, 11, 31, 'Concluído', '#10b981', 20, 3, '2026-04-21 23:12:25', '2026-04-21 23:12:28'),
(44, 11, 28, 'Planejado', '#6b7280', NULL, 9, '2026-04-21 23:12:28', '2026-04-22 15:08:56'),
(45, 11, 31, 'Concluído', '#10b981', 25, 9, '2026-04-22 15:08:56', '2026-04-22 17:49:28'),
(46, 4, 12, 'A Fazer', '#6b7280', 15, NULL, '2026-04-22 17:03:56', NULL),
(47, 12, 28, 'Planejado', '#6b7280', NULL, NULL, '2026-04-22 17:16:20', '2026-04-22 17:16:29'),
(48, 12, 28, 'Planejado', '#6b7280', 28, 10, '2026-04-22 17:16:29', '2026-04-22 17:16:47'),
(49, 12, 28, 'Planejado', '#6b7280', 25, 9, '2026-04-22 17:16:47', '2026-04-22 18:40:26'),
(50, 11, 28, 'Planejado', '#6b7280', NULL, 9, '2026-04-22 17:49:28', NULL),
(51, 12, 29, 'Em Andamento', '#000000', 25, 9, '2026-04-22 18:40:26', '2026-04-22 19:07:40'),
(52, 12, 28, 'Planejado', '#6b7280', 25, 9, '2026-04-22 19:07:40', '2026-04-22 19:08:58'),
(53, 12, 31, 'Concluído', '#10b981', 25, 9, '2026-04-22 19:08:58', NULL);

-- --------------------------------------------------------

--
-- Estrutura para tabela `tarefa_membros_task`
--

CREATE TABLE `tarefa_membros_task` (
  `tarefa_id` int(11) NOT NULL,
  `usuario_id` int(11) NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `templates_espaco_task`
--

CREATE TABLE `templates_espaco_task` (
  `id` int(11) NOT NULL,
  `nome` varchar(100) NOT NULL,
  `descricao` varchar(255) DEFAULT NULL,
  `cor` varchar(7) DEFAULT '#6554c0',
  `criador_id` int(11) NOT NULL,
  `created_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `templates_espaco_task`
--

INSERT INTO `templates_espaco_task` (`id`, `nome`, `descricao`, `cor`, `criador_id`, `created_at`) VALUES
(3, 'Processo de venda novo', NULL, '#974f0c', 20, '2026-04-14 11:44:01');

-- --------------------------------------------------------

--
-- Estrutura para tabela `template_statuses_task`
--

CREATE TABLE `template_statuses_task` (
  `id` int(11) NOT NULL,
  `template_id` int(11) NOT NULL,
  `nome` varchar(100) NOT NULL,
  `cor` varchar(7) DEFAULT '#6b7280',
  `icone` varchar(50) DEFAULT 'bi-circle',
  `ordem` int(11) DEFAULT 0,
  `is_final` tinyint(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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

CREATE TABLE `tickets` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `numero` varchar(20) NOT NULL,
  `id_alfanumerica` varchar(10) DEFAULT NULL,
  `solicitante_id` bigint(20) NOT NULL,
  `responsavel_id` bigint(20) DEFAULT NULL,
  `group_id` int(11) NOT NULL,
  `categoria_id` int(10) UNSIGNED DEFAULT NULL,
  `subcategoria_id` int(10) UNSIGNED DEFAULT NULL,
  `status_id` int(10) UNSIGNED NOT NULL,
  `prioridade_id` int(10) UNSIGNED NOT NULL,
  `assunto` varchar(255) NOT NULL,
  `descricao_inicial` longtext NOT NULL,
  `origem` enum('portal','email','whatsapp','telefone','api','interno') DEFAULT 'portal',
  `sla_primeira_resposta_em` datetime DEFAULT NULL,
  `sla_resolucao_em` datetime DEFAULT NULL,
  `primeira_resposta_em` datetime DEFAULT NULL,
  `resolvido_em` datetime DEFAULT NULL,
  `fechado_em` datetime DEFAULT NULL,
  `ultimo_evento_em` datetime DEFAULT current_timestamp(),
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `reopen_count` tinyint(3) UNSIGNED NOT NULL DEFAULT 0 COMMENT 'Quantas vezes o chamado foi reaberto pelo solicitante'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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

CREATE TABLE `ticket_anexos` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `ticket_id` bigint(20) UNSIGNED NOT NULL,
  `interacao_id` bigint(20) UNSIGNED DEFAULT NULL,
  `nome_original` varchar(255) NOT NULL,
  `caminho_arquivo` varchar(500) NOT NULL,
  `mime_type` varchar(100) DEFAULT NULL,
  `tamanho_bytes` bigint(20) UNSIGNED DEFAULT NULL,
  `enviado_por` bigint(20) NOT NULL,
  `ativo` tinyint(1) DEFAULT 1,
  `created_at` timestamp NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estrutura para tabela `ticket_avaliacoes`
--

CREATE TABLE `ticket_avaliacoes` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `ticket_id` bigint(20) UNSIGNED NOT NULL,
  `solicitante_id` bigint(20) NOT NULL,
  `responsavel_id` bigint(20) DEFAULT NULL,
  `group_id` int(11) DEFAULT NULL,
  `estrelas` tinyint(3) UNSIGNED DEFAULT NULL,
  `comentario` text DEFAULT NULL,
  `popup_count` tinyint(3) UNSIGNED NOT NULL DEFAULT 0,
  `avaliado_em` datetime DEFAULT NULL,
  `expira_em` datetime NOT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `ticket_avaliacoes`
--

INSERT INTO `ticket_avaliacoes` (`id`, `ticket_id`, `solicitante_id`, `responsavel_id`, `group_id`, `estrelas`, `comentario`, `popup_count`, `avaliado_em`, `expira_em`, `created_at`) VALUES
(1, 34, 23, 19, 1, 10, 'teste ok', 2, '2026-04-10 14:43:07', '2026-04-17 14:41:48', '2026-04-10 14:41:48');

-- --------------------------------------------------------

--
-- Estrutura para tabela `ticket_interacoes`
--

CREATE TABLE `ticket_interacoes` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `ticket_id` bigint(20) UNSIGNED NOT NULL,
  `usuario_id` bigint(20) NOT NULL,
  `tipo` enum('mensagem','nota_interna','alteracao_status','atribuicao','sistema','encaminhamento','devolucao','sla_iniciado','sla_pausado','sla_retomado','sla_concluido','sla_estourado','reabertura','resolucao') DEFAULT 'mensagem',
  `publico` tinyint(1) DEFAULT 1,
  `mensagem` longtext DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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

CREATE TABLE `ticket_prioridades` (
  `id` int(10) UNSIGNED NOT NULL,
  `nome` varchar(50) NOT NULL,
  `nivel` tinyint(4) NOT NULL,
  `descricao` text DEFAULT NULL,
  `cor_hex` varchar(7) DEFAULT '#667eea',
  `sla_horas` int(11) DEFAULT 48,
  `ativo` tinyint(1) DEFAULT 1,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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

CREATE TABLE `ticket_sla` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `ticket_id` bigint(20) UNSIGNED NOT NULL,
  `categoria_id` int(10) UNSIGNED NOT NULL,
  `sla_minutos` int(10) UNSIGNED NOT NULL COMMENT 'SLA copiado da categoria no momento da abertura',
  `sla_primeira_resposta_minutos` int(10) UNSIGNED DEFAULT NULL,
  `primeira_resposta_em` datetime DEFAULT NULL,
  `iniciado_em` datetime DEFAULT NULL COMMENT 'Quando o atendimento come├ºou (usu├írio assumiu)',
  `pausado_em` datetime DEFAULT NULL COMMENT 'Quando foi pausado pela ├║ltima vez',
  `minutos_pausados` int(10) UNSIGNED NOT NULL DEFAULT 0 COMMENT 'Total de minutos j├í pausados (acumulado)',
  `status` enum('aguardando','em_andamento','pausado','concluido','estourado') NOT NULL DEFAULT 'aguardando',
  `estourou_em` datetime DEFAULT NULL COMMENT 'Momento exato em que o SLA estourou',
  `concluido_em` datetime DEFAULT NULL COMMENT 'Momento em que foi conclu├¡do dentro do prazo',
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Rastreamento de SLA por ticket';

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

CREATE TABLE `ticket_status` (
  `id` int(10) UNSIGNED NOT NULL,
  `nome` varchar(50) NOT NULL,
  `descricao` text DEFAULT NULL,
  `ordem` tinyint(4) NOT NULL DEFAULT 0,
  `finalizador` tinyint(1) DEFAULT 0,
  `cor_hex` varchar(7) DEFAULT '#667eea',
  `ativo` tinyint(1) DEFAULT 1,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

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
-- Estrutura para tabela `unidades_cpe`
--

CREATE TABLE `unidades_cpe` (
  `id` int(11) NOT NULL,
  `nome` varchar(120) NOT NULL,
  `sigla` varchar(20) DEFAULT NULL,
  `cidade` varchar(120) DEFAULT NULL,
  `uf` char(2) DEFAULT NULL,
  `endereco` varchar(255) DEFAULT NULL,
  `ativo` tinyint(1) DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `unidades_cpe`
--

INSERT INTO `unidades_cpe` (`id`, `nome`, `sigla`, `cidade`, `uf`, `endereco`, `ativo`, `created_at`, `updated_at`) VALUES
(1, 'CPE Belo Horizonte', 'BH', 'Belo Horizonte', 'MG', NULL, 1, '2026-04-30 20:58:24', '2026-04-30 20:58:24'),
(2, 'CPE Sao paulo', 'SP', 'sao paulo', 'SP', NULL, 1, '2026-04-30 20:58:24', '2026-04-30 21:00:20');

-- --------------------------------------------------------

--
-- Estrutura para tabela `users`
--

CREATE TABLE `users` (
  `id` bigint(20) NOT NULL,
  `name` varchar(120) NOT NULL,
  `email` varchar(190) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` enum('USER','TI','ADMIN','RESPONSAVEL_GRUPO') DEFAULT 'USER',
  `sector` varchar(120) DEFAULT NULL,
  `unit` varchar(120) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `username` varchar(50) DEFAULT NULL,
  `department_id` int(11) DEFAULT NULL,
  `group_id` int(11) DEFAULT NULL,
  `unit_id` int(11) DEFAULT NULL,
  `vault_pin_hash` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `users`
--

INSERT INTO `users` (`id`, `name`, `email`, `password_hash`, `role`, `sector`, `unit`, `is_active`, `created_at`, `username`, `department_id`, `group_id`, `unit_id`, `vault_pin_hash`) VALUES
(15, 'Administrador', 'admin@cpe.com.br', '$2b$12$cUzgsKcnlFpM4RLi4s6ice887vhB4RqDprqSCAeeTLpCiyhnjLkZ.', 'ADMIN', NULL, NULL, 1, '2026-03-18 21:01:36', 'admin', NULL, NULL, NULL, '$2b$12$6mQswuezaxsxp5NbKnSuZOUuFExzN6JJ2yLGMMnddAeABJHhesKfG'),
(17, 'Manager System', 'manager@cpe.com.br', '$2b$12$e5owWqUGPxvGMQdM3dUVDe2O0k0vqCqRVJr.qiHqnINNk.G9K2i3O', 'TI', NULL, NULL, 1, '2026-03-18 21:01:36', 'manager', NULL, 1, NULL, NULL),
(19, 'jonathan', 'jonathan2@cpe.com.br', '$2b$12$gAsoH/SsdblwHN.kd9djQeFMXb3Kep0q8rUbfe0kNSYbPTlw.X2Xa', 'USER', NULL, NULL, 1, '2026-03-18 21:43:48', 'jonathan.lopes2', NULL, 1, NULL, NULL),
(20, 'fernanda', 'fernandateste@cpe.com.br', '$2b$12$14PTC6nIsDE1TBi9/tOGZuDT2WmTMAB3R6mdqXCZ6mMGnahe8k4Xe', 'RESPONSAVEL_GRUPO', NULL, NULL, 1, '2026-03-18 22:19:27', 'fernanda.teste', NULL, 3, NULL, NULL),
(22, 'jose', 'jose@cpe.com.br', '$2b$12$lstGgaNJYVLuzX9bI4fci.WZ8mXCHpZzyknSfeqhyztfJtmefYKii', 'RESPONSAVEL_GRUPO', NULL, NULL, 1, '2026-04-02 20:10:25', 'jose.jose', NULL, 1, NULL, NULL),
(23, 'camila', 'camila@cpe.com.br', '$2b$12$N61JAIvgCTDXXI/H.B0ryuKI8vxcr8FayHrj5DxrXHAkreSiKg3km', 'USER', NULL, NULL, 1, '2026-04-07 18:34:51', 'camila.teste', NULL, 3, NULL, NULL),
(24, 'Natalia', 'nataliateste@cpe.com.br', '$2b$12$dgxPx/f02y8Tunam4JQ4Mus3rwIalJZDtzA6.OX/rfEbPGFVrJr62', 'USER', NULL, NULL, 1, '2026-04-08 20:12:31', 'natalia.teste', NULL, 3, NULL, NULL),
(25, 'Edson Cardoso', 'edson.teste@cpe.com.br', '$2b$12$Yo0zLMdHTveMBBgHF/e98u9VUNZ8a5LwmuseMVtyNk1g0I/WJo0ZC', 'RESPONSAVEL_GRUPO', NULL, NULL, 1, '2026-04-13 21:57:09', 'edson.teste', NULL, 9, NULL, '$2b$12$ixMi.LzUXnrUUBNRdNkrSujV6hmeJfIIH21gjEHMebxc25q7ik8Gi'),
(26, 'Jean Teste', 'jean.teste@cpe.com.br', '$2b$12$UNTpfhH21Ipc0eE1TLEgouNLRfFeAAePyw.WmF1WkSkeXPDcqLA/6', 'USER', NULL, NULL, 1, '2026-04-13 21:57:38', 'jean.teste', NULL, 9, NULL, NULL),
(27, 'viviane - faturamento', 'viviane.teste@cpe.com.br', '$2b$12$wrzip7RZG2TmkMeS7QHNc.Giln4yz2RguDiR83k5MB9dM2vq6iJri', 'RESPONSAVEL_GRUPO', NULL, NULL, 1, '2026-04-14 13:26:22', 'viviane.teste', NULL, 10, NULL, NULL),
(28, 'Vanessa melo', 'vanessa.teste@cpe.com.br', '$2b$12$fSAaiz3DDTQ5JBMDNqtss.Y3j4sP2NtbLhMPGzEI3NhLxWXstJLzq', 'USER', NULL, NULL, 1, '2026-04-14 13:26:53', 'vanessa.teste', NULL, 10, NULL, NULL),
(29, 'fred.teste', 'fred.teste@cpe.com.br', '$2b$12$/LAlzHtsqzVs.eNpfKtMFO3xvKsTYAkHOyZn9KiDhLKs00MdlKG8m', 'RESPONSAVEL_GRUPO', NULL, NULL, 1, '2026-04-22 20:24:06', 'fred.teste', NULL, 13, NULL, NULL);

-- --------------------------------------------------------

--
-- Estrutura para tabela `user_access_exceptions`
--

CREATE TABLE `user_access_exceptions` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL COMMENT 'Usuário afetado',
  `page_name` varchar(50) NOT NULL COMMENT 'Nome da página',
  `exception_type` enum('block','allow') NOT NULL COMMENT 'block = bloquear, allow = permitir',
  `reason` text DEFAULT NULL COMMENT 'Motivo da exceção',
  `created_by` int(11) DEFAULT NULL COMMENT 'Admin que criou',
  `created_at` timestamp NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Despejando dados para a tabela `user_access_exceptions`
--

INSERT INTO `user_access_exceptions` (`id`, `user_id`, `page_name`, `exception_type`, `reason`, `created_by`, `created_at`) VALUES
(7, 25, 'REPORTS', 'allow', '', 15, '2026-04-22 17:36:02');

-- --------------------------------------------------------

--
-- Estrutura stand-in para view `vw_historico_notificacoes`
-- (Veja abaixo para a visão atual)
--
CREATE TABLE `vw_historico_notificacoes` (
`id` int(11)
,`ticket_id` int(11)
,`ticket_numero` varchar(20)
,`ticket_assunto` varchar(255)
,`usuario_id` int(11)
,`usuario_nome` varchar(120)
,`mensagem` varchar(255)
,`tipo` varchar(50)
,`lido` tinyint(1)
,`created_at` timestamp
,`updated_at` timestamp
);

-- --------------------------------------------------------

--
-- Estrutura stand-in para view `vw_notificacoes_nao_lidas`
-- (Veja abaixo para a visão atual)
--
CREATE TABLE `vw_notificacoes_nao_lidas` (
`usuario_id` bigint(20)
,`usuario_nome` varchar(120)
,`total_nao_lidas` bigint(21)
,`atribuidos` bigint(21)
,`respondidos` bigint(21)
,`transferidos` bigint(21)
,`finalizados` bigint(21)
,`ultima_notificacao` timestamp
);

-- --------------------------------------------------------

--
-- Estrutura para view `vw_historico_notificacoes`
--
DROP TABLE IF EXISTS `vw_historico_notificacoes`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vw_historico_notificacoes`  AS SELECT `n`.`id` AS `id`, `n`.`ticket_id` AS `ticket_id`, `t`.`numero` AS `ticket_numero`, `t`.`assunto` AS `ticket_assunto`, `n`.`usuario_id` AS `usuario_id`, `u`.`name` AS `usuario_nome`, `n`.`mensagem` AS `mensagem`, `n`.`tipo` AS `tipo`, `n`.`lido` AS `lido`, `n`.`created_at` AS `created_at`, `n`.`updated_at` AS `updated_at` FROM ((`notificacoes` `n` join `tickets` `t` on(`n`.`ticket_id` = `t`.`id`)) join `users` `u` on(`n`.`usuario_id` = `u`.`id`)) ORDER BY `n`.`created_at` DESC ;

-- --------------------------------------------------------

--
-- Estrutura para view `vw_notificacoes_nao_lidas`
--
DROP TABLE IF EXISTS `vw_notificacoes_nao_lidas`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vw_notificacoes_nao_lidas`  AS SELECT `u`.`id` AS `usuario_id`, `u`.`name` AS `usuario_nome`, count(`n`.`id`) AS `total_nao_lidas`, count(case when `n`.`tipo` = 'atribuido' then 1 end) AS `atribuidos`, count(case when `n`.`tipo` = 'respondido' then 1 end) AS `respondidos`, count(case when `n`.`tipo` = 'transferido' then 1 end) AS `transferidos`, count(case when `n`.`tipo` = 'finalizado' then 1 end) AS `finalizados`, max(`n`.`created_at`) AS `ultima_notificacao` FROM (`users` `u` left join `notificacoes` `n` on(`u`.`id` = `n`.`usuario_id` and `n`.`lido` = 0)) GROUP BY `u`.`id`, `u`.`name` ORDER BY count(`n`.`id`) DESC ;

--
-- Índices para tabelas despejadas
--

--
-- Índices de tabela `categorias`
--
ALTER TABLE `categorias`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uk_group_nome` (`group_id`,`nome`),
  ADD KEY `idx_group_id` (`group_id`),
  ADD KEY `idx_ativo` (`ativo`);

--
-- Índices de tabela `categorias_task`
--
ALTER TABLE `categorias_task`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_espaco` (`espaco_id`);

--
-- Índices de tabela `cofre_senhas`
--
ALTER TABLE `cofre_senhas`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_cofre_user` (`cofre_user_id`),
  ADD KEY `idx_cofre_group` (`cofre_group_id`),
  ADD KEY `idx_cofre_exclusive` (`cofre_is_exclusive`),
  ADD KEY `idx_cofre_allowed_group` (`cofre_allowed_group_id`);

--
-- Índices de tabela `comentarios_task`
--
ALTER TABLE `comentarios_task`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_tarefa` (`tarefa_id`);

--
-- Índices de tabela `contratos`
--
ALTER TABLE `contratos`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_pasta` (`pasta_id`),
  ADD KEY `idx_uploader` (`uploaded_by`);

--
-- Índices de tabela `contrato_pastas`
--
ALTER TABLE `contrato_pastas`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_group` (`group_id`),
  ADD KEY `idx_parent` (`parent_id`);

--
-- Índices de tabela `convites_espaco_task`
--
ALTER TABLE `convites_espaco_task`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_convite` (`espaco_id`,`group_id`,`status`),
  ADD KEY `idx_group` (`group_id`),
  ADD KEY `idx_status` (`status`);

--
-- Índices de tabela `cpe_grupo`
--
ALTER TABLE `cpe_grupo`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `unique_group_per_dept` (`department_id`,`name`),
  ADD KEY `idx_department` (`department_id`);

--
-- Índices de tabela `departments`
--
ALTER TABLE `departments`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `name` (`name`),
  ADD KEY `idx_name` (`name`);

--
-- Índices de tabela `documents`
--
ALTER TABLE `documents`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_docs_owner` (`owner_user_id`);

--
-- Índices de tabela `espacos_task`
--
ALTER TABLE `espacos_task`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_group` (`group_id`),
  ADD KEY `idx_criador` (`criador_id`);

--
-- Índices de tabela `espaco_grupos_task`
--
ALTER TABLE `espaco_grupos_task`
  ADD PRIMARY KEY (`espaco_id`,`group_id`);

--
-- Índices de tabela `espaco_grupo_sla_task`
--
ALTER TABLE `espaco_grupo_sla_task`
  ADD PRIMARY KEY (`espaco_id`,`group_id`,`status_id`);

--
-- Índices de tabela `espaco_membros_task`
--
ALTER TABLE `espaco_membros_task`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uk_eu` (`espaco_id`,`usuario_id`),
  ADD KEY `idx_espaco` (`espaco_id`),
  ADD KEY `idx_usuario` (`usuario_id`);

--
-- Índices de tabela `etapas_task`
--
ALTER TABLE `etapas_task`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_tarefa` (`tarefa_id`),
  ADD KEY `idx_group` (`group_id`);

--
-- Índices de tabela `fleet_checklists`
--
ALTER TABLE `fleet_checklists`
  ADD PRIMARY KEY (`id`),
  ADD KEY `vehicle_id` (`vehicle_id`),
  ADD KEY `condutor_id` (`condutor_id`),
  ADD KEY `liberador_id` (`liberador_id`),
  ADD KEY `recebedor_id` (`recebedor_id`),
  ADD KEY `aprovado_por` (`aprovado_por`);

--
-- Índices de tabela `fleet_checklist_photos`
--
ALTER TABLE `fleet_checklist_photos`
  ADD PRIMARY KEY (`id`),
  ADD KEY `checklist_id` (`checklist_id`);

--
-- Índices de tabela `fleet_checklist_problems`
--
ALTER TABLE `fleet_checklist_problems`
  ADD PRIMARY KEY (`id`),
  ADD KEY `checklist_id` (`checklist_id`);

--
-- Índices de tabela `fleet_km_alerts`
--
ALTER TABLE `fleet_km_alerts`
  ADD PRIMARY KEY (`id`),
  ADD KEY `vehicle_id` (`vehicle_id`),
  ADD KEY `created_by` (`created_by`);

--
-- Índices de tabela `fleet_maintenance`
--
ALTER TABLE `fleet_maintenance`
  ADD PRIMARY KEY (`id`),
  ADD KEY `vehicle_id` (`vehicle_id`),
  ADD KEY `created_by` (`created_by`);

--
-- Índices de tabela `fleet_maintenance_files`
--
ALTER TABLE `fleet_maintenance_files`
  ADD PRIMARY KEY (`id`),
  ADD KEY `maintenance_id` (`maintenance_id`);

--
-- Índices de tabela `fleet_maintenance_types`
--
ALTER TABLE `fleet_maintenance_types`
  ADD PRIMARY KEY (`id`),
  ADD KEY `created_by` (`created_by`);

--
-- Índices de tabela `fleet_reservations`
--
ALTER TABLE `fleet_reservations`
  ADD PRIMARY KEY (`id`),
  ADD KEY `solicitante_id` (`solicitante_id`),
  ADD KEY `aprovador_id` (`aprovador_id`),
  ADD KEY `idx_data_veiculo` (`vehicle_id`,`data_reserva`,`status`);

--
-- Índices de tabela `fleet_trips`
--
ALTER TABLE `fleet_trips`
  ADD PRIMARY KEY (`id`),
  ADD KEY `vehicle_id` (`vehicle_id`),
  ADD KEY `checklist_id` (`checklist_id`),
  ADD KEY `condutor_id` (`condutor_id`);

--
-- Índices de tabela `fleet_vehicles`
--
ALTER TABLE `fleet_vehicles`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `placa` (`placa`),
  ADD KEY `created_by` (`created_by`);

--
-- Índices de tabela `fleet_vehicle_history`
--
ALTER TABLE `fleet_vehicle_history`
  ADD PRIMARY KEY (`id`),
  ADD KEY `vehicle_id` (`vehicle_id`),
  ADD KEY `user_id` (`user_id`);

--
-- Índices de tabela `fleet_vehicle_photos`
--
ALTER TABLE `fleet_vehicle_photos`
  ADD PRIMARY KEY (`id`),
  ADD KEY `vehicle_id` (`vehicle_id`),
  ADD KEY `substituida_por_user_id` (`substituida_por_user_id`);

--
-- Índices de tabela `historico_task`
--
ALTER TABLE `historico_task`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_tarefa` (`tarefa_id`);

--
-- Índices de tabela `notificacoes`
--
ALTER TABLE `notificacoes`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_usuario_lido` (`usuario_id`,`lido`) COMMENT 'Busca rápida de notificações não lidas por usuário',
  ADD KEY `idx_usuario_criado` (`usuario_id`,`created_at`) COMMENT 'Timeline de notificações por data',
  ADD KEY `idx_ticket_id` (`ticket_id`) COMMENT 'Buscar notificações de um ticket específico';

--
-- Índices de tabela `page_permissions`
--
ALTER TABLE `page_permissions`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `unique_page_name` (`page_name`),
  ADD KEY `idx_page_name` (`page_name`);

--
-- Índices de tabela `passwords`
--
ALTER TABLE `passwords`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_user_id` (`user_id`),
  ADD KEY `idx_group_id` (`group_id`),
  ADD KEY `idx_allowed_group` (`allowed_group_id`),
  ADD KEY `idx_is_exclusive` (`is_exclusive`);

--
-- Índices de tabela `recepcao_convidados`
--
ALTER TABLE `recepcao_convidados`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uniq_reserva_usuario` (`reserva_id`,`usuario_id`),
  ADD KEY `convidado_por` (`convidado_por`),
  ADD KEY `idx_convidado_status` (`usuario_id`,`status`);

--
-- Índices de tabela `recepcao_envios`
--
ALTER TABLE `recepcao_envios`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_envio_codigo` (`codigo_correios`),
  ADD KEY `idx_envio_remetente` (`remetente_id`);

--
-- Índices de tabela `recepcao_escritorios`
--
ALTER TABLE `recepcao_escritorios`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uniq_unit_nome` (`unit_id`,`nome`);

--
-- Índices de tabela `recepcao_reservas`
--
ALTER TABLE `recepcao_reservas`
  ADD PRIMARY KEY (`id`),
  ADD KEY `usuario_id` (`usuario_id`),
  ADD KEY `idx_reserva_sala_periodo` (`sala_id`,`inicio`,`fim`,`status`),
  ADD KEY `idx_reserva_status_prazo` (`status`,`confirmacao_prazo`);

--
-- Índices de tabela `recepcao_salas`
--
ALTER TABLE `recepcao_salas`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_sala_unit` (`unit_id`,`ativa`),
  ADD KEY `idx_sala_escritorio` (`escritorio_id`);

--
-- Índices de tabela `status_task`
--
ALTER TABLE `status_task`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_group` (`group_id`);

--
-- Índices de tabela `subcategorias`
--
ALTER TABLE `subcategorias`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uk_categoria_nome` (`categoria_id`,`nome`),
  ADD KEY `idx_categoria_id` (`categoria_id`),
  ADD KEY `idx_ativo` (`ativo`);

--
-- Índices de tabela `subtarefas_task`
--
ALTER TABLE `subtarefas_task`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_tarefa` (`tarefa_id`);

--
-- Índices de tabela `tarefas_task`
--
ALTER TABLE `tarefas_task`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `numero` (`numero`),
  ADD KEY `idx_group` (`group_id`),
  ADD KEY `idx_status` (`status_id`),
  ADD KEY `idx_responsavel` (`responsavel_id`);

--
-- Índices de tabela `tarefa_categorias_task`
--
ALTER TABLE `tarefa_categorias_task`
  ADD PRIMARY KEY (`tarefa_id`,`categoria_id`);

--
-- Índices de tabela `tarefa_encaminhamentos_task`
--
ALTER TABLE `tarefa_encaminhamentos_task`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_tarefa_id` (`tarefa_id`),
  ADD KEY `idx_de_grupo` (`de_grupo_id`,`devolvido_em`),
  ADD KEY `idx_para_grupo` (`para_grupo_id`,`devolvido_em`);

--
-- Índices de tabela `tarefa_historico_status_task`
--
ALTER TABLE `tarefa_historico_status_task`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_tarefa` (`tarefa_id`),
  ADD KEY `idx_status` (`status_id`);

--
-- Índices de tabela `tarefa_membros_task`
--
ALTER TABLE `tarefa_membros_task`
  ADD PRIMARY KEY (`tarefa_id`,`usuario_id`);

--
-- Índices de tabela `templates_espaco_task`
--
ALTER TABLE `templates_espaco_task`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_criador` (`criador_id`);

--
-- Índices de tabela `template_statuses_task`
--
ALTER TABLE `template_statuses_task`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_template` (`template_id`);

--
-- Índices de tabela `tickets`
--
ALTER TABLE `tickets`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `numero` (`numero`),
  ADD UNIQUE KEY `uk_numero` (`numero`),
  ADD UNIQUE KEY `id_alfanumerica` (`id_alfanumerica`),
  ADD KEY `idx_solicitante_id` (`solicitante_id`),
  ADD KEY `idx_responsavel_id` (`responsavel_id`),
  ADD KEY `idx_group_id` (`group_id`),
  ADD KEY `idx_categoria_id` (`categoria_id`),
  ADD KEY `idx_subcategoria_id` (`subcategoria_id`),
  ADD KEY `idx_status_id` (`status_id`),
  ADD KEY `idx_prioridade_id` (`prioridade_id`),
  ADD KEY `idx_created_at` (`created_at`),
  ADD KEY `idx_ultimo_evento_em` (`ultimo_evento_em`),
  ADD KEY `idx_origem` (`origem`),
  ADD KEY `idx_comp_group_status` (`group_id`,`status_id`,`created_at`),
  ADD KEY `idx_comp_responsavel_status` (`responsavel_id`,`status_id`,`created_at`),
  ADD KEY `idx_comp_status_criacao` (`status_id`,`created_at`),
  ADD KEY `idx_id_alfanumerica` (`id_alfanumerica`);

--
-- Índices de tabela `ticket_anexos`
--
ALTER TABLE `ticket_anexos`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_ticket_id` (`ticket_id`),
  ADD KEY `idx_interacao_id` (`interacao_id`),
  ADD KEY `idx_enviado_por` (`enviado_por`),
  ADD KEY `idx_ativo` (`ativo`);

--
-- Índices de tabela `ticket_avaliacoes`
--
ALTER TABLE `ticket_avaliacoes`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uk_ticket` (`ticket_id`);

--
-- Índices de tabela `ticket_interacoes`
--
ALTER TABLE `ticket_interacoes`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_ticket_id` (`ticket_id`),
  ADD KEY `idx_usuario_id` (`usuario_id`),
  ADD KEY `idx_tipo` (`tipo`),
  ADD KEY `idx_publico` (`publico`),
  ADD KEY `idx_created_at` (`created_at`),
  ADD KEY `idx_comp_ticket_created` (`ticket_id`,`created_at`),
  ADD KEY `idx_ticket_publico_criacao` (`ticket_id`,`publico`,`created_at`) COMMENT 'Carregar interações públicas/privadas de um ticket';

--
-- Índices de tabela `ticket_prioridades`
--
ALTER TABLE `ticket_prioridades`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `nome` (`nome`),
  ADD UNIQUE KEY `nivel` (`nivel`),
  ADD KEY `idx_nivel` (`nivel`),
  ADD KEY `idx_ativo` (`ativo`);

--
-- Índices de tabela `ticket_sla`
--
ALTER TABLE `ticket_sla`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uk_ticket_sla` (`ticket_id`),
  ADD KEY `idx_status` (`status`),
  ADD KEY `idx_categoria_id` (`categoria_id`);

--
-- Índices de tabela `ticket_status`
--
ALTER TABLE `ticket_status`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `nome` (`nome`),
  ADD KEY `idx_ordem` (`ordem`),
  ADD KEY `idx_finalizador` (`finalizador`),
  ADD KEY `idx_ativo` (`ativo`);

--
-- Índices de tabela `unidades_cpe`
--
ALTER TABLE `unidades_cpe`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uniq_nome` (`nome`);

--
-- Índices de tabela `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`),
  ADD UNIQUE KEY `username` (`username`),
  ADD KEY `idx_department` (`department_id`),
  ADD KEY `idx_group` (`group_id`),
  ADD KEY `idx_users_unit` (`unit_id`);

--
-- Índices de tabela `user_access_exceptions`
--
ALTER TABLE `user_access_exceptions`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `unique_user_page_type` (`user_id`,`page_name`,`exception_type`),
  ADD KEY `idx_uae_user_id` (`user_id`),
  ADD KEY `idx_uae_page_name` (`page_name`);

--
-- AUTO_INCREMENT para tabelas despejadas
--

--
-- AUTO_INCREMENT de tabela `categorias`
--
ALTER TABLE `categorias`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT de tabela `categorias_task`
--
ALTER TABLE `categorias_task`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de tabela `cofre_senhas`
--
ALTER TABLE `cofre_senhas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT de tabela `comentarios_task`
--
ALTER TABLE `comentarios_task`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=14;

--
-- AUTO_INCREMENT de tabela `contratos`
--
ALTER TABLE `contratos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de tabela `contrato_pastas`
--
ALTER TABLE `contrato_pastas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=21;

--
-- AUTO_INCREMENT de tabela `convites_espaco_task`
--
ALTER TABLE `convites_espaco_task`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=13;

--
-- AUTO_INCREMENT de tabela `cpe_grupo`
--
ALTER TABLE `cpe_grupo`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=15;

--
-- AUTO_INCREMENT de tabela `departments`
--
ALTER TABLE `departments`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT de tabela `documents`
--
ALTER TABLE `documents`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `espacos_task`
--
ALTER TABLE `espacos_task`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=9;

--
-- AUTO_INCREMENT de tabela `espaco_membros_task`
--
ALTER TABLE `espaco_membros_task`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=15;

--
-- AUTO_INCREMENT de tabela `etapas_task`
--
ALTER TABLE `etapas_task`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `fleet_checklists`
--
ALTER TABLE `fleet_checklists`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=11;

--
-- AUTO_INCREMENT de tabela `fleet_checklist_photos`
--
ALTER TABLE `fleet_checklist_photos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=18;

--
-- AUTO_INCREMENT de tabela `fleet_checklist_problems`
--
ALTER TABLE `fleet_checklist_problems`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de tabela `fleet_km_alerts`
--
ALTER TABLE `fleet_km_alerts`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT de tabela `fleet_maintenance`
--
ALTER TABLE `fleet_maintenance`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de tabela `fleet_maintenance_files`
--
ALTER TABLE `fleet_maintenance_files`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `fleet_maintenance_types`
--
ALTER TABLE `fleet_maintenance_types`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=12;

--
-- AUTO_INCREMENT de tabela `fleet_reservations`
--
ALTER TABLE `fleet_reservations`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de tabela `fleet_trips`
--
ALTER TABLE `fleet_trips`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT de tabela `fleet_vehicles`
--
ALTER TABLE `fleet_vehicles`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT de tabela `fleet_vehicle_history`
--
ALTER TABLE `fleet_vehicle_history`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10;

--
-- AUTO_INCREMENT de tabela `fleet_vehicle_photos`
--
ALTER TABLE `fleet_vehicle_photos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT de tabela `historico_task`
--
ALTER TABLE `historico_task`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=100;

--
-- AUTO_INCREMENT de tabela `notificacoes`
--
ALTER TABLE `notificacoes`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=203;

--
-- AUTO_INCREMENT de tabela `page_permissions`
--
ALTER TABLE `page_permissions`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=19;

--
-- AUTO_INCREMENT de tabela `passwords`
--
ALTER TABLE `passwords`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de tabela `recepcao_convidados`
--
ALTER TABLE `recepcao_convidados`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de tabela `recepcao_envios`
--
ALTER TABLE `recepcao_envios`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT de tabela `recepcao_escritorios`
--
ALTER TABLE `recepcao_escritorios`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de tabela `recepcao_reservas`
--
ALTER TABLE `recepcao_reservas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de tabela `recepcao_salas`
--
ALTER TABLE `recepcao_salas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de tabela `status_task`
--
ALTER TABLE `status_task`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=32;

--
-- AUTO_INCREMENT de tabela `subcategorias`
--
ALTER TABLE `subcategorias`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT de tabela `subtarefas_task`
--
ALTER TABLE `subtarefas_task`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=11;

--
-- AUTO_INCREMENT de tabela `tarefas_task`
--
ALTER TABLE `tarefas_task`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=13;

--
-- AUTO_INCREMENT de tabela `tarefa_encaminhamentos_task`
--
ALTER TABLE `tarefa_encaminhamentos_task`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de tabela `tarefa_historico_status_task`
--
ALTER TABLE `tarefa_historico_status_task`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=54;

--
-- AUTO_INCREMENT de tabela `templates_espaco_task`
--
ALTER TABLE `templates_espaco_task`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT de tabela `template_statuses_task`
--
ALTER TABLE `template_statuses_task`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=13;

--
-- AUTO_INCREMENT de tabela `tickets`
--
ALTER TABLE `tickets`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=35;

--
-- AUTO_INCREMENT de tabela `ticket_anexos`
--
ALTER TABLE `ticket_anexos`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `ticket_avaliacoes`
--
ALTER TABLE `ticket_avaliacoes`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT de tabela `ticket_interacoes`
--
ALTER TABLE `ticket_interacoes`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=101;

--
-- AUTO_INCREMENT de tabela `ticket_prioridades`
--
ALTER TABLE `ticket_prioridades`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de tabela `ticket_sla`
--
ALTER TABLE `ticket_sla`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=11;

--
-- AUTO_INCREMENT de tabela `ticket_status`
--
ALTER TABLE `ticket_status`
  MODIFY `id` int(10) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT de tabela `unidades_cpe`
--
ALTER TABLE `unidades_cpe`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de tabela `users`
--
ALTER TABLE `users`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=30;

--
-- AUTO_INCREMENT de tabela `user_access_exceptions`
--
ALTER TABLE `user_access_exceptions`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- Restrições para tabelas despejadas
--

--
-- Restrições para tabelas `categorias`
--
ALTER TABLE `categorias`
  ADD CONSTRAINT `fk_categorias_group` FOREIGN KEY (`group_id`) REFERENCES `cpe_grupo` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `contratos`
--
ALTER TABLE `contratos`
  ADD CONSTRAINT `fk_contr_pasta_id` FOREIGN KEY (`pasta_id`) REFERENCES `contrato_pastas` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_contr_user` FOREIGN KEY (`uploaded_by`) REFERENCES `users` (`id`) ON DELETE SET NULL;

--
-- Restrições para tabelas `contrato_pastas`
--
ALTER TABLE `contrato_pastas`
  ADD CONSTRAINT `fk_contr_pasta_group` FOREIGN KEY (`group_id`) REFERENCES `cpe_grupo` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_contr_pasta_parent` FOREIGN KEY (`parent_id`) REFERENCES `contrato_pastas` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `cpe_grupo`
--
ALTER TABLE `cpe_grupo`
  ADD CONSTRAINT `cpe_grupo_ibfk_1` FOREIGN KEY (`department_id`) REFERENCES `departments` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `fleet_checklists`
--
ALTER TABLE `fleet_checklists`
  ADD CONSTRAINT `fleet_checklists_ibfk_1` FOREIGN KEY (`vehicle_id`) REFERENCES `fleet_vehicles` (`id`),
  ADD CONSTRAINT `fleet_checklists_ibfk_2` FOREIGN KEY (`condutor_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `fleet_checklists_ibfk_3` FOREIGN KEY (`liberador_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `fleet_checklists_ibfk_4` FOREIGN KEY (`recebedor_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `fleet_checklists_ibfk_5` FOREIGN KEY (`aprovado_por`) REFERENCES `users` (`id`) ON DELETE SET NULL;

--
-- Restrições para tabelas `fleet_checklist_photos`
--
ALTER TABLE `fleet_checklist_photos`
  ADD CONSTRAINT `fleet_checklist_photos_ibfk_1` FOREIGN KEY (`checklist_id`) REFERENCES `fleet_checklists` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `fleet_checklist_problems`
--
ALTER TABLE `fleet_checklist_problems`
  ADD CONSTRAINT `fleet_checklist_problems_ibfk_1` FOREIGN KEY (`checklist_id`) REFERENCES `fleet_checklists` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `fleet_km_alerts`
--
ALTER TABLE `fleet_km_alerts`
  ADD CONSTRAINT `fleet_km_alerts_ibfk_1` FOREIGN KEY (`vehicle_id`) REFERENCES `fleet_vehicles` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fleet_km_alerts_ibfk_2` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL;

--
-- Restrições para tabelas `fleet_maintenance`
--
ALTER TABLE `fleet_maintenance`
  ADD CONSTRAINT `fleet_maintenance_ibfk_1` FOREIGN KEY (`vehicle_id`) REFERENCES `fleet_vehicles` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fleet_maintenance_ibfk_2` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL;

--
-- Restrições para tabelas `fleet_maintenance_files`
--
ALTER TABLE `fleet_maintenance_files`
  ADD CONSTRAINT `fleet_maintenance_files_ibfk_1` FOREIGN KEY (`maintenance_id`) REFERENCES `fleet_maintenance` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `fleet_maintenance_types`
--
ALTER TABLE `fleet_maintenance_types`
  ADD CONSTRAINT `fleet_maintenance_types_ibfk_1` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL;

--
-- Restrições para tabelas `fleet_reservations`
--
ALTER TABLE `fleet_reservations`
  ADD CONSTRAINT `fleet_reservations_ibfk_1` FOREIGN KEY (`vehicle_id`) REFERENCES `fleet_vehicles` (`id`),
  ADD CONSTRAINT `fleet_reservations_ibfk_2` FOREIGN KEY (`solicitante_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `fleet_reservations_ibfk_3` FOREIGN KEY (`aprovador_id`) REFERENCES `users` (`id`) ON DELETE SET NULL;

--
-- Restrições para tabelas `fleet_trips`
--
ALTER TABLE `fleet_trips`
  ADD CONSTRAINT `fleet_trips_ibfk_1` FOREIGN KEY (`vehicle_id`) REFERENCES `fleet_vehicles` (`id`),
  ADD CONSTRAINT `fleet_trips_ibfk_2` FOREIGN KEY (`checklist_id`) REFERENCES `fleet_checklists` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `fleet_trips_ibfk_3` FOREIGN KEY (`condutor_id`) REFERENCES `users` (`id`) ON DELETE SET NULL;

--
-- Restrições para tabelas `fleet_vehicles`
--
ALTER TABLE `fleet_vehicles`
  ADD CONSTRAINT `fleet_vehicles_ibfk_1` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL;

--
-- Restrições para tabelas `fleet_vehicle_history`
--
ALTER TABLE `fleet_vehicle_history`
  ADD CONSTRAINT `fleet_vehicle_history_ibfk_1` FOREIGN KEY (`vehicle_id`) REFERENCES `fleet_vehicles` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fleet_vehicle_history_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL;

--
-- Restrições para tabelas `fleet_vehicle_photos`
--
ALTER TABLE `fleet_vehicle_photos`
  ADD CONSTRAINT `fleet_vehicle_photos_ibfk_1` FOREIGN KEY (`vehicle_id`) REFERENCES `fleet_vehicles` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fleet_vehicle_photos_ibfk_2` FOREIGN KEY (`substituida_por_user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL;

--
-- Restrições para tabelas `passwords`
--
ALTER TABLE `passwords`
  ADD CONSTRAINT `fk_passwords_group` FOREIGN KEY (`group_id`) REFERENCES `cpe_grupo` (`id`) ON DELETE SET NULL;

--
-- Restrições para tabelas `recepcao_convidados`
--
ALTER TABLE `recepcao_convidados`
  ADD CONSTRAINT `recepcao_convidados_ibfk_1` FOREIGN KEY (`reserva_id`) REFERENCES `recepcao_reservas` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `recepcao_convidados_ibfk_2` FOREIGN KEY (`usuario_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `recepcao_convidados_ibfk_3` FOREIGN KEY (`convidado_por`) REFERENCES `users` (`id`);

--
-- Restrições para tabelas `recepcao_envios`
--
ALTER TABLE `recepcao_envios`
  ADD CONSTRAINT `recepcao_envios_ibfk_1` FOREIGN KEY (`remetente_id`) REFERENCES `users` (`id`);

--
-- Restrições para tabelas `recepcao_escritorios`
--
ALTER TABLE `recepcao_escritorios`
  ADD CONSTRAINT `recepcao_escritorios_ibfk_1` FOREIGN KEY (`unit_id`) REFERENCES `unidades_cpe` (`id`) ON DELETE CASCADE;

--
-- Restrições para tabelas `recepcao_reservas`
--
ALTER TABLE `recepcao_reservas`
  ADD CONSTRAINT `recepcao_reservas_ibfk_1` FOREIGN KEY (`sala_id`) REFERENCES `recepcao_salas` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `recepcao_reservas_ibfk_2` FOREIGN KEY (`usuario_id`) REFERENCES `users` (`id`);

--
-- Restrições para tabelas `recepcao_salas`
--
ALTER TABLE `recepcao_salas`
  ADD CONSTRAINT `fk_sala_escritorio` FOREIGN KEY (`escritorio_id`) REFERENCES `recepcao_escritorios` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `recepcao_salas_ibfk_1` FOREIGN KEY (`unit_id`) REFERENCES `unidades_cpe` (`id`) ON DELETE CASCADE;

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
  ADD CONSTRAINT `fk_tickets_group` FOREIGN KEY (`group_id`) REFERENCES `cpe_grupo` (`id`),
  ADD CONSTRAINT `fk_tickets_prioridade` FOREIGN KEY (`prioridade_id`) REFERENCES `ticket_prioridades` (`id`),
  ADD CONSTRAINT `fk_tickets_responsavel` FOREIGN KEY (`responsavel_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `fk_tickets_solicitante` FOREIGN KEY (`solicitante_id`) REFERENCES `users` (`id`),
  ADD CONSTRAINT `fk_tickets_status` FOREIGN KEY (`status_id`) REFERENCES `ticket_status` (`id`),
  ADD CONSTRAINT `fk_tickets_subcategoria` FOREIGN KEY (`subcategoria_id`) REFERENCES `subcategorias` (`id`) ON DELETE SET NULL;

--
-- Restrições para tabelas `ticket_anexos`
--
ALTER TABLE `ticket_anexos`
  ADD CONSTRAINT `fk_anexos_interacao` FOREIGN KEY (`interacao_id`) REFERENCES `ticket_interacoes` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `fk_anexos_ticket` FOREIGN KEY (`ticket_id`) REFERENCES `tickets` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_anexos_usuario` FOREIGN KEY (`enviado_por`) REFERENCES `users` (`id`);

--
-- Restrições para tabelas `ticket_interacoes`
--
ALTER TABLE `ticket_interacoes`
  ADD CONSTRAINT `fk_interacoes_ticket` FOREIGN KEY (`ticket_id`) REFERENCES `tickets` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_interacoes_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `users` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
