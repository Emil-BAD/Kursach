import secrets

# Генерируем ключ длиной 64 символа
jwt_secret_key = secrets.token_urlsafe(48)  # 48 байт ≈ 64 символа в Base64
print(jwt_secret_key)