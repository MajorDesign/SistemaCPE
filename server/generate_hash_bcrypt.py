from passlib.hash import bcrypt

new_password = "Cpe@7482"
hashed_password = bcrypt.hash(new_password)

print("Hash da nova senha:", hashed_password)
