from passlib.hash import argon2

# Substitua pela nova senha
new_password = "Cpe@7482"
hashed_password = argon2.hash(new_password)

print("Hash da nova senha:", hashed_password)
