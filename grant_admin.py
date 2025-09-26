from dotenv import load_dotenv
load_dotenv(dotenv_path='services/servico-usuarios/.env.local')

import firebase_admin
from firebase_admin import credentials, auth
import os
import json
import base64

# Carregue suas credenciais do Firebase Admin SDK
# Certifique-se de que a variável de ambiente FIREBASE_ADMIN_SDK_BASE64 esteja configurada
base64_sdk = os.environ.get('FIREBASE_ADMIN_SDK_BASE64')
if not base64_sdk:
    print("Erro: Variável de ambiente FIREBASE_ADMIN_SDK_BASE64 não encontrada.")
    exit()

decoded_sdk = base64.b64decode(base64_sdk).decode('utf-8')
cred_dict = json.loads(decoded_sdk)
cred = credentials.Certificate(cred_dict)

# Inicialize o Firebase Admin SDK
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

# Email do usuário que você quer tornar admin
user_email = 'jeanmdasleite@gmail.com'

try:
    # 1. Obtenha o UID do usuário pelo email
    user = auth.get_user_by_email(user_email)
    uid = user.uid
    print(f"UID do usuário {user_email}: {uid}")

    # 2. Defina a custom claim 'admin: true'
    auth.set_custom_user_claims(uid, {'admin': True})
    print(f"Permissão de administrador concedida ao usuário {user_email} (UID: {uid}).")

    # Opcional: Verifique as claims atualizadas (pode levar alguns minutos para propagar)
    user = auth.get_user(uid)
    print(f"Claims atualizadas para {user_email}: {user.custom_claims}")

except Exception as e:
    print(f"Ocorreu um erro: {e}")
