"""
Script para criar usuário admin com senha customizada
Uso: python create_admin.py
"""

import hashlib
import mysql.connector
import sys
import uuid
from datetime import datetime

# =========================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# =========================================

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",  # Sem senha
    "database": "cpe_plus",
}

# =========================================
# CORES PARA TERMINAL
# =========================================

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

# =========================================
# FUNÇÕES
# =========================================

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")

def hash_password(password: str) -> str:
    """Gera hash SHA256 da senha"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_db_connection():
    """Conecta ao banco de dados"""
    try:
        print_info("Conectando ao banco de dados...")
        conn = mysql.connector.connect(**DB_CONFIG)
        print_success("Conexão estabelecida!")
        return conn
    except mysql.connector.Error as err:
        print_error(f"Erro ao conectar: {err}")
        sys.exit(1)

def user_exists(cursor, email: str = None, username: str = None) -> bool:
    """Verifica se usuário já existe por email ou username"""
    if email:
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        return cursor.fetchone() is not None
    elif username:
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        return cursor.fetchone() is not None
    return False

def generate_unique_username(cursor, base_username: str) -> str:
    """Gera um username único adicionando timestamp se necessário"""
    username = base_username
    counter = 1
    
    while user_exists(cursor, username=username):
        # Se username existe, adiciona um número
        username = f"{base_username}{counter}"
        counter += 1
        
        if counter > 1000:  # Proteção infinita
            # Se ainda não funcionar, usa UUID
            username = f"{base_username}_{uuid.uuid4().hex[:8]}"
            break
    
    return username

def create_admin_user(email: str, password: str, name: str = "Administrador"):
    """Cria novo usuário admin"""
    
    print("\n" + "=" * 80)
    print_info("CRIANDO NOVO USUÁRIO ADMIN")
    print("=" * 80)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # ✅ Verificar se email já existe
        print_info(f"Verificando se email já existe: {email}")
        if user_exists(cursor, email=email):
            print_warning(f"Email já registrado: {email}")
            print_info("Deletando usuário anterior...")
            cursor.execute("DELETE FROM users WHERE email = %s", (email,))
            conn.commit()
            print_success("Usuário anterior deletado!")
        
        # ✅ Gerar username único
        base_username = email.split('@')[0]
        print_info(f"Verificando disponibilidade do username: {base_username}")
        
        username = generate_unique_username(cursor, base_username)
        
        if username != base_username:
            print_warning(f"Username '{base_username}' já existe!")
            print_success(f"Usando username alternativo: {username}")
        else:
            print_success(f"Username disponível: {username}")
        
        # ✅ Gerar hash da senha
        print_info("Gerando hash da senha...")
        password_hash = hash_password(password)
        print_success(f"Hash gerado: {password_hash[:50]}...")
        
        # ✅ Inserir novo usuário
        print_info("Inserindo novo usuário no banco de dados...")
        insert_query = """
            INSERT INTO users (name, email, username, password_hash, role, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """
        
        cursor.execute(insert_query, (
            name,                           # name
            email,                          # email
            username,                       # username (gerado dinamicamente)
            password_hash,                  # password_hash
            "ADMIN",                        # role
            1                               # is_active
        ))
        
        conn.commit()
        new_user_id = cursor.lastrowid
        
        print_success(f"Usuário criado com sucesso!")
        print("=" * 80)
        print(f"{Colors.BOLD}Dados do novo usuário:{Colors.END}")
        print(f"  • ID: {new_user_id}")
        print(f"  • Nome: {name}")
        print(f"  • Email: {email}")
        print(f"  • Username: {username}")
        print(f"  • Senha: {password}")
        print(f"  • Hash: {password_hash}")
        print(f"  • Role: ADMIN")
        print(f"  • Status: ✓ Ativo")
        print(f"  • Criado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("=" * 80 + "\n")
        
        # ✅ Verificar criação
        cursor.execute("SELECT * FROM users WHERE id = %s", (new_user_id,))
        user = cursor.fetchone()
        
        if user:
            print_success("✅ Usuário verificado no banco de dados!")
            print(f"\n{Colors.BOLD}🔐 Você já pode fazer login com:{Colors.END}")
            print(f"   Email: {email}")
            print(f"   Senha: {password}")
            return True
        else:
            print_error("Erro ao verificar criação do usuário")
            return False
        
    except Exception as err:
        print_error(f"Erro ao criar usuário: {err}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cursor.close()
        conn.close()

# =========================================
# MAIN
# =========================================

if __name__ == "__main__":
    print("\n")
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "CPE CONTROL - CRIAR USUÁRIO ADMIN" + " " * 25 + "║")
    print("╚" + "═" * 78 + "╝")
    print(f"{Colors.END}\n")
    
    # Dados do novo usuário
    email = "admin@cpetecnologia.com.br"
    password = "Cpe@7482"
    name = "Administrador CPE"
    
    print_info(f"Criando usuário com dados:")
    print(f"  • Email: {email}")
    print(f"  • Senha: {password}")
    print(f"  • Nome: {name}\n")
    
    # Criar usuário
    sucesso = create_admin_user(
        email=email,
        password=password,
        name=name
    )
    
    if sucesso:
        print_success("🎉 Tudo pronto! Você já pode fazer login!")
        sys.exit(0)
    else:
        print_error("❌ Algo deu errado. Verifique os logs acima.")
        sys.exit(1)