from dotenv import load_dotenv
load_dotenv(dotenv_path='.env.local')

import os
import json
import uuid
import requests
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
import base64

# --- Importações de dependências ---1
try:
    import firebase_admin
    from firebase_admin import credentials, auth, firestore
except ImportError:
    firebase_admin = None

try:
    from confluent_kafka import Producer
except ImportError:
    Producer = None

try:
    from sqlalchemy import create_engine, Column, String, MetaData, text
    from sqlalchemy.orm import sessionmaker, declarative_base
    from sqlalchemy.exc import SQLAlchemyError
    from geoalchemy2 import Geography
    from geoalchemy2.shape import to_shape
    from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
except ImportError:
    SQLAlchemyError = None
    declarative_base = None
    create_engine = None
    Column = String = MetaData = sessionmaker = Geography = to_shape = text = None
    urlparse = urlunparse = parse_qs = urlencode = None

# --- Variáveis globais para erros de inicialização ---
firebase_init_error = None
postgres_init_error = None
kafka_producer_init_error = None # Renamed for clarity
db_init_error = None

# --- Configuração do Flask ---
app = Flask(__name__)
CORS(app, supports_credentials=True, origins=['http://localhost:3000', 'https://frontend-tester-1foc8lpkl-jeanmnorhens-projects.vercel.app'])

# --- Configuração do Firebase (PADRONIZADO) ---
db = None
if firebase_admin:
    try:
        base64_sdk = os.environ.get('FIREBASE_ADMIN_SDK_BASE64')
        if base64_sdk:
            decoded_sdk = base64.b64decode(base64_sdk).decode('utf-8')
            cred_dict = json.loads(decoded_sdk)
            cred = credentials.Certificate(cred_dict)
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("Firebase inicializado com sucesso.")
        else:
            firebase_init_error = "Variável de ambiente FIREBASE_ADMIN_SDK_BASE64 não encontrada."
            print(firebase_init_error)
    except Exception as e:
        firebase_init_error = str(e)
        print(f"Erro ao inicializar Firebase: {e}")
else:
    firebase_init_error = "Biblioteca firebase_admin não encontrada."

# --- Configuração do PostgreSQL (PostGIS) (PADRONIZADO) ---
db_session = None
engine = None
if create_engine:
    try:
        db_url = os.environ.get('POSTGRES_POSTGRES_URL')
        if db_url:
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql://", 1)
            
            cleaned_url = db_url
            if urlparse:
                try:
                    parsed_url = urlparse(db_url)
                    query_params = parse_qs(parsed_url.query)
                    query_params.pop('supa', None)
                    new_query = urlencode(query_params, doseq=True)
                    cleaned_url = urlunparse(parsed_url._replace(query=new_query))
                except Exception:
                    pass # Usa a URL original se o parse falhar

            engine = create_engine(cleaned_url)
            Session = sessionmaker(bind=engine)
            db_session = Session()
            print("Conexão com PostgreSQL (PostGIS) estabelecida com sucesso.")
        else:
            postgres_init_error = "Variável de ambiente POSTGRES_POSTGRES_URL não encontrada."
            print(postgres_init_error)
    except Exception as e:
        postgres_init_error = str(e)
        print(f"Erro ao conectar com PostgreSQL: {e}")
else:
    postgres_init_error = "SQLAlchemy não encontrado."

# --- Definição do Modelo de Dados Geoespacial ---
Base = declarative_base() if declarative_base else object

if Base != object and Geography:
    class StoreLocation(Base):
        __tablename__ = 'store_locations'
        store_id = Column(String, primary_key=True)
        location = Column(Geography(geometry_type='POINT', srid=4326), nullable=False)

def init_db():
    global db_init_error
    if not engine:
        db_init_error = "Engine do PostgreSQL não inicializada."
        print(db_init_error)
        return
    if not Base:
        db_init_error = "Declarative base do SQLAlchemy não pôde ser criada."
        print(db_init_error)
        return
    try:
        Base.metadata.create_all(engine)
        print("Tabela 'store_locations' verificada/criada com sucesso.")
    except Exception as e:
        db_init_error = str(e)
        print(f"Erro ao criar tabela 'store_locations': {e}")

# --- Configuração do Kafka Producer ---
producer = None
if Producer:
    try:
        kafka_bootstrap_server = os.environ.get('KAFKA_BOOTSTRAP_SERVER')
        if kafka_bootstrap_server:
            kafka_api_key = os.environ.get('KAFKA_API_KEY')
            if kafka_api_key:
                # Cloud Kafka configuration
                print("Configurando produtor Kafka para ambiente de nuvem (SASL)...")
                kafka_conf = {
                    'bootstrap.servers': kafka_bootstrap_server,
                    'security.protocol': 'SASL_SSL',
                    'sasl.mechanisms': 'PLAIN',
                    'sasl.username': kafka_api_key,
                    'sasl.password': os.environ.get('KAFKA_API_SECRET')
                }
            else:
                # Local Docker Kafka configuration
                print("Configurando produtor Kafka para ambiente local (sem SASL)...")
                kafka_conf = {
                    'bootstrap.servers': kafka_bootstrap_server
                }
            producer = Producer(kafka_conf)
            print("Produtor Kafka inicializado com sucesso.")
        else:
            kafka_producer_init_error = "Variáveis de ambiente do Kafka não encontradas."
            print(kafka_producer_init_error)
    except Exception as e:
        kafka_producer_init_error = str(e)
        print(f"Erro ao inicializar Produtor Kafka: {e}")
else:
    kafka_producer_init_error = "Biblioteca confluent_kafka não encontrada."

def delivery_report(err, msg):
    if err is not None:
        print(f'Falha ao entregar mensagem Kafka: {err}')
    else:
        print(f'Mensagem Kafka entregue em {msg.topic()} [{msg.partition()}]')

def publish_event(topic, event_type, store_id, data, changes=None):
    if not producer:
        print("Produtor Kafka não está inicializado. Evento não publicado.")
        return
    event = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "store_id": store_id,
        "data": data,
        "source_service": "servico-lojas"
    }
    if changes:
        event["changes"] = changes
    try:
        event_value = json.dumps(event, default=str)
        producer.produce(topic, key=store_id, value=event_value, callback=delivery_report)
        producer.poll(0)
        print(f"Evento '{event_type}' para a loja {store_id} publicado no tópico {topic}.")
    except Exception as e:
        print(f"Erro ao publicar evento Kafka: {e}")

def check_permission(user_id, store_id):
    """Chama o servico-usuarios para verificar se um usuário tem permissão para gerenciar uma loja."""
    servico_usuarios_url = os.environ.get('SERVICO_USUARIOS_URL')
    if not servico_usuarios_url:
        print("ERRO: SERVICO_USUARIOS_URL não configurado.")
        return False, {"error": "URL do serviço de permissões não configurada."}

    try:
        response = requests.get(
            f"{servico_usuarios_url}/api/permissions/check",
            params={'user_id': user_id, 'store_id': store_id},
            timeout=5
        )
        if response.status_code == 200:
            return response.json().get('allow', False), response.json()
        else:
            return False, response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao contatar o serviço de permissões: {e}")
        return False, {"error": "Falha ao contatar o serviço de permissões."}

# --- Rotas da API ---

# Final workflow trigger test
@app.route('/api/stores', methods=['GET'])
def list_all_stores():
    if not db or not db_session:
        return jsonify({"error": "Dependências de banco de dados não inicializadas."}), 503

    try:
        stores_ref = db.collection('stores')
        docs = stores_ref.stream()
        
        all_stores = []
        for doc in docs:
            store_data = doc.to_dict()
            store_data['id'] = doc.id
            
            # Fetch location from PostGIS
            location_record = db_session.query(StoreLocation).filter_by(store_id=doc.id).first()
            if location_record and to_shape:
                point = to_shape(location_record.location)
                store_data['location'] = {'latitude': point.y, 'longitude': point.x}
            
            all_stores.append(store_data)
            
        return jsonify({"stores": all_stores}), 200
    except Exception as e:
        return jsonify({"error": f"Erro ao listar lojas: {e}"}), 500

@app.route("/api/stores", methods=["POST"])
def create_store():
    if not db or not db_session:
        return jsonify({"error": "Dependências de banco de dados não inicializadas."}), 503

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization token is required"}), 401

    try:
        id_token = auth_header.split('Bearer ')[1]
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
    except Exception as e:
        return jsonify({"error": "Invalid or expired token", "details": str(e)}), 401

    store_data = request.get_json()
    if not store_data or not store_data.get('name'):
        return jsonify({"error": "Store name is required"}), 400
    
    store_id = str(uuid.uuid4())
    firestore_data = store_data.copy()
    location_data = firestore_data.pop('location', None)
    # O campo owner_uid não é mais salvo diretamente no documento da loja.
    # firestore_data['owner_uid'] = uid 
    firestore_data['created_at'] = firestore.SERVER_TIMESTAMP
    firestore_data['updated_at'] = firestore.SERVER_TIMESTAMP

    try:
        # Etapa 1: Preparar dados para os bancos de dados
        if location_data and 'latitude' in location_data and 'longitude' in location_data:
            lat = location_data['latitude']
            lon = location_data['longitude']
            wkt_point = f'POINT({lon} {lat})'
            new_location = StoreLocation(store_id=store_id, location=wkt_point)
            db_session.add(new_location)

        db.collection('stores').document(store_id).set(firestore_data)

        # Etapa 2: Chamar servico-usuarios para atribuir o papel de 'owner'
        servico_usuarios_url = os.environ.get('SERVICO_USUARIOS_URL')
        internal_secret = os.environ.get('INTERNAL_SERVICE_SECRET')
        if not servico_usuarios_url or not internal_secret:
            raise Exception("URL do serviço de usuários ou segredo interno não configurado.")

        role_payload = {'user_id': uid, 'store_id': store_id, 'role': 'owner'}
        headers = {'Authorization': f'Bearer {internal_secret}', 'Content-Type': 'application/json'}
        
        response = requests.post(f"{servico_usuarios_url}/internal/roles", json=role_payload, headers=headers, timeout=5)
        response.raise_for_status() # Lança uma exceção para status de erro (4xx ou 5xx)

        # Etapa 3: Se tudo deu certo, commitar a transação no banco de dados local
        db_session.commit()

        # Etapa 4: Publicar evento de sucesso
        publish_event('eventos_lojas', 'StoreCreated', store_id, store_data)
        return jsonify({"message": "Store created successfully", "storeId": store_id}), 201

    except Exception as e:
        # Se qualquer etapa falhar, reverter a transação do banco de dados
        db_session.rollback()
        # Tentar deletar o documento no Firestore se ele já foi criado
        db.collection('stores').document(store_id).delete()
        print(f"ERRO na criação da loja: {e}")
        return jsonify({"error": f"Erro ao criar loja ou atribuir papel: {e}"}), 500

@app.route('/api/stores/<store_id>', methods=['GET'])
def get_store(store_id):
    if not db or not db_session:
        return jsonify({"error": "Dependências de banco de dados não inicializadas."}), 503

    try:
        store_doc = db.collection('stores').document(store_id).get()
        if not store_doc.exists:
            return jsonify({"error": "Loja não encontrada."}), 404
        store_data = store_doc.to_dict()
        store_data['id'] = store_doc.id

        location_record = db_session.query(StoreLocation).filter_by(store_id=store_id).first()
        print(f"DEBUG: location_record in get_store: {location_record}") # Depuração
        if location_record:
            print("DEBUG: Inside if location_record block") # Depuração
            point = to_shape(location_record.location)
            store_data['location'] = {'latitude': point.y, 'longitude': point.x}

        return jsonify(store_data), 200
    except Exception as e:
        return jsonify({"error": f"Erro ao buscar loja: {e}"}), 500

@app.route('/api/stores/<store_id>', methods=['PUT'])
def update_store(store_id):
    if not db or not db_session:
        return jsonify({"error": "Dependências de banco de dados não inicializadas."}), 503

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization token is required"}), 401

    try:
        id_token = auth_header.split('Bearer ')[1]
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
    except Exception as e:
        return jsonify({"error": "Invalid or expired token", "details": str(e)}), 401

    update_data = request.get_json()
    if not update_data:
        return jsonify({"error": "Dados para atualização são obrigatórios."}), 400

    store_ref = db.collection('stores').document(store_id)
    
    try:
        store_doc = store_ref.get()
        if not store_doc.exists:
            return jsonify({"error": "Loja não encontrada."}), 404
        
        allowed, reason = check_permission(uid, store_id)
        if not allowed:
            return jsonify({"error": "User is not authorized to update this store", "details": reason}), 403

        firestore_data = update_data.copy()
        location_data = firestore_data.pop('location', None)
        firestore_data['updated_at'] = firestore.SERVER_TIMESTAMP

        if location_data and 'latitude' in location_data and 'longitude' in location_data:
            lat = location_data['latitude']
            lon = location_data['longitude']
            wkt_point = f'POINT({lon} {lat})'
            
            location_record = db_session.query(StoreLocation).filter_by(store_id=store_id).first()
            if location_record:
                location_record.location = wkt_point
            else:
                new_location = StoreLocation(store_id=store_id, location=wkt_point)
                db_session.add(new_location)

        if firestore_data:
            store_ref.update(firestore_data)

        db_session.commit()

        publish_event('eventos_lojas', 'StoreUpdated', store_id, update_data)
        return jsonify({"message": "Loja atualizada com sucesso.", "storeId": store_id}), 200

    except SQLAlchemyError as e:
        db_session.rollback()
        return jsonify({"error": f"Erro no banco de dados geoespacial: {e}"}), 500
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": f"Erro ao atualizar loja: {e}"}), 500

@app.route('/api/stores/<store_id>', methods=['DELETE'])
def delete_store(store_id):
    if not db or not db_session:
        return jsonify({"error": "Dependências de banco de dados não inicializadas."}), 503

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization token is required"}), 401

    try:
        id_token = auth_header.split('Bearer ')[1]
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
    except Exception as e:
        return jsonify({"error": "Invalid or expired token", "details": str(e)}), 401

    store_ref = db.collection('stores').document(store_id)

    try:
        store_doc = store_ref.get()
        if not store_doc.exists:
            return jsonify({"error": "Loja não encontrada."}), 404
        
        allowed, reason = check_permission(uid, store_id)
        if not allowed:
            return jsonify({"error": "User is not authorized to delete this store", "details": reason}), 403

        location_record = db_session.query(StoreLocation).filter_by(store_id=store_id).first()
        if location_record:
            db_session.delete(location_record)

        store_ref.delete()
        db_session.commit()

        publish_event('eventos_lojas', 'StoreDeleted', store_id, {"store_id": store_id})
        return '', 204

    except SQLAlchemyError as e:
        db_session.rollback()
        return jsonify({"error": f"Erro no banco de dados geoespacial: {e}"}), 500
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": f"Erro ao deletar loja: {e}"}), 500

def get_health_status():
    env_vars = {
        "FIREBASE_ADMIN_SDK_BASE64": "present" if os.environ.get('FIREBASE_ADMIN_SDK_BASE64') else "missing",
        "POSTGRES_POSTGRES_URL": "present" if os.environ.get('POSTGRES_POSTGRES_URL') else "missing",
        "KAFKA_BOOTSTRAP_SERVER": "present" if os.environ.get('KAFKA_BOOTSTRAP_SERVER') else "missing",
        "KAFKA_API_KEY": "present" if os.environ.get('KAFKA_API_KEY') else "missing",
        "KAFKA_API_SECRET": "present" if os.environ.get('KAFKA_API_SECRET') else "missing"
    }

    pg_status = "error"
    pg_query_error = None
    if db_session and text:
        try:
            db_session.execute(text('SELECT 1'))
            pg_status = "ok"
        except Exception as e:
            pg_query_error = str(e)
            pg_status = f"error during query: {pg_query_error}"

    status = {
        "environment_variables": env_vars,
        "dependencies": {
            "firestore": "ok" if db else "error",
            "kafka_producer": "ok" if producer else "error",
            "postgresql_connection": pg_status,
            "table_initialization": "ok" if not db_init_error else "error"
        },
        "initialization_errors": {
            "firestore": firebase_init_error,
            "postgresql_engine": postgres_init_error,
            "postgresql_table": db_init_error,
            "postgresql_query": pg_query_error,
            "kafka_producer": kafka_producer_init_error
        }
    }
    return status

@app.route('/api/health', methods=['GET'])
def health_check():
    status = get_health_status()
    
    all_ok = (
        all(value == "present" for value in status["environment_variables"].values()) and
        status["dependencies"]["firestore"] == "ok" and
        status["dependencies"]["kafka_producer"] == "ok" and
        status["dependencies"]["postgresql_connection"] == "ok" and
        status["dependencies"]["table_initialization"] == "ok"
    )
    http_status = 200 if all_ok else 503
    
    return jsonify(status), http_status

# --- Inicialização ---
init_db()

if __name__ == '__main__':
    app.run(debug=True)