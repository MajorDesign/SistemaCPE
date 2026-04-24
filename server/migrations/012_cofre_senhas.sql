-- ============================================================
-- Migração 012: Cofre de Senhas
-- ============================================================
-- Cria a tabela do módulo Cofre de Senhas com prefixo cofre_
-- (tabela + colunas) para isolar este módulo de qualquer
-- outra tabela do sistema.
--
-- Os grupos são reutilizados de cpe_grupo (tabela de grupos do
-- sistema); não há tabela própria para grupos do cofre.
-- ============================================================

CREATE TABLE IF NOT EXISTS cofre_senhas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cofre_user_id INT NOT NULL,
    cofre_client VARCHAR(255) NOT NULL,
    cofre_email VARCHAR(255) DEFAULT NULL,
    cofre_description VARCHAR(500) NOT NULL,
    cofre_password TEXT NOT NULL,
    cofre_link VARCHAR(500) DEFAULT NULL,
    cofre_observation TEXT DEFAULT NULL,
    cofre_group_id INT DEFAULT NULL,
    cofre_is_public TINYINT(1) DEFAULT 0,
    cofre_is_exclusive TINYINT(1) DEFAULT 0,
    cofre_allowed_group_id INT DEFAULT NULL,
    cofre_created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    cofre_updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_cofre_user (cofre_user_id),
    KEY idx_cofre_group (cofre_group_id),
    KEY idx_cofre_exclusive (cofre_is_exclusive),
    KEY idx_cofre_allowed_group (cofre_allowed_group_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Migra dados da tabela antiga `passwords` (se existir e se
-- cofre_senhas estiver vazia).
DROP PROCEDURE IF EXISTS sp_migrar_passwords_para_cofre;

DELIMITER //
CREATE PROCEDURE sp_migrar_passwords_para_cofre()
BEGIN
    DECLARE v_passwords_existe INT DEFAULT 0;
    DECLARE v_cofre_vazio INT DEFAULT 0;

    SELECT COUNT(*) INTO v_passwords_existe
    FROM information_schema.tables
    WHERE table_schema = DATABASE() AND table_name = 'passwords';

    SELECT COUNT(*) INTO v_cofre_vazio FROM cofre_senhas;

    IF v_passwords_existe > 0 AND v_cofre_vazio = 0 THEN
        INSERT INTO cofre_senhas (
            id, cofre_user_id, cofre_client, cofre_email, cofre_description,
            cofre_password, cofre_link, cofre_observation, cofre_group_id,
            cofre_is_public, cofre_is_exclusive, cofre_allowed_group_id,
            cofre_created_at, cofre_updated_at
        )
        SELECT
            id, user_id, client, email, description,
            password, link, observation, group_id,
            is_public, is_exclusive, allowed_group_id,
            created_at, updated_at
        FROM passwords;
    END IF;
END //
DELIMITER ;

CALL sp_migrar_passwords_para_cofre();
DROP PROCEDURE IF EXISTS sp_migrar_passwords_para_cofre;
