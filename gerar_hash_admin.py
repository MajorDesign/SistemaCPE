import bcrypt

print("\n" + "=" * 80)
print("GERADOR DE HASH PARA ADMIN")
print("=" * 80)

# Senha real do admin
senha = 'Cpe@7482'

# Gerar hash
print(f"\nGerando hash para: {senha}")
salt = bcrypt.gensalt(rounds=12)
hash_bytes = bcrypt.hashpw(senha.encode('utf-8'), salt)
hash_string = hash_bytes.decode('utf-8')

print(f"\nHash gerado: {hash_string}")
print(f"Tamanho: {len(hash_string)} caracteres")

# Validar
validacao = bcrypt.checkpw(senha.encode('utf-8'), hash_bytes)
print(f"Validacao: {'OK' if validacao else 'ERRO'}")

# Gerar SQL
print("\n" + "=" * 80)
print("SQL PARA COPIAR E COLAR NO phpMyAdmin")
print("=" * 80 + "\n")

sql = f"UPDATE users SET password_hash = '{hash_string}' WHERE username = 'admin';"
print(sql)

print("\n" + "=" * 80)
print("DEPOIS DE ATUALIZAR, TESTE COM:")
print("=" * 80)
print(f"\nUsuario: admin")
print(f"Senha:   {senha}")

print("\n" + "=" * 80 + "\n")