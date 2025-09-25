import os
import json
import uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify
import base64

# ---  Importações de  dependências - --
try:
    from firebase_admin import credentials, firestore, initialize_app, auth
    import firebase_admin
except ImportError:
    firebase_admin = None

try:
    from confluent_kafka import Producer
except ImportError:
    Producer = None


try:
    from sqlalchemy import create_engine, Column, String, MetaData, text, func
    from sqlalchemy.orm import sessionmaker, declarative_base
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.dialects.postgresql import JSON
    from geoalchemy2 import Geography
    from geoalchemy2.shape import to_shape
    from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
except ImportError:
    SQLAlchemyError = None
    declarative_base = None
    create_engine = None
    Column = String = MetaData = sessionmaker = Geography = to_shape = text = func = None
    urlparse = urlunparse = parse_qs = urlencode = None
    JSON = None

from flask_cors import CORS

# --- Variáveis globais para erros de inicialização -- 
firebase_init_error = None
postgres_init_error = None
kafka_producer_init_error = None # Renamed for clarity    
db_init_error = None

# --- Configuração do Flask ---
app = Flask(__name__)
CORS(app, supports_credentials=True, origins=['https://frontend-tester-1foc8lpkl-jeanmnorhens-projects.vercel.app'])

# --- Configuração do Firebase ---
db = None
if firebase_admin:
    try:
        base64_sdk = os.environ.get('FIREBASE_ADMIN_SDK_BASE64')
        if base64_sdk:
            decoded_sdk = base64.b64decode(base64_sdk).decode('utf-8')
            cred_dict = json.loads(decoded_sdk)
            cred = credentials.Certificate(cred_dict)
            if not firebase_admin._apps:
                initialize_app(cred)
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

# --- Configuração do PostgreSQL (PostGIS) ---
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
                    pass

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
    class UserLocation(Base):
        __tablename__ = 'user_locations'
        user_id = Column(String, primary_key=True)
        location = Column(Geography(geometry_type='POINT', srid=4326), nullable=False)

    class UserStoreRole(Base):
        __tablename__ = 'user_store_roles'
        user_id = Column(String, primary_key=True)
        store_id = Column(String, primary_key=True)
        role = Column(String, nullable=False)  # Ex: 'owner', 'employee'
        shifts = Column(JSON)  # Ex: ["manha", "tarde"]

    class StoreLocation(Base):
        __tablename__ = 'store_locations'
        store_id = Column(String, primary_key=True)
        location = Column(Geography(geometry_type='POINT', srid=4326), nullable=False)

    class Critica(Base):
        __tablename__ = 'criticas'
        id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
        produto_id = Column(String, nullable=False)
        tipo_critica = Column(String, nullable=False)
        comentario = Column(String)
        status = Column(String, default='PENDENTE') # PENDENTE, RESOLVIDA, REJEITADA
        criado_em = Column(String, default=lambda: datetime.now(timezone.utc).isoformat())


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
        print("Tabelas do banco de dados verificadas/criadas com sucesso.")
    except Exception as e:
        db_init_error = str(e)
        print(f"Erro ao criar tabelas do banco de dados: {e}")

# --- Configuração do Kafka Producer ---
producer = None
if Producer:
    try:
        kafka_conf = {
            'bootstrap.servers': os.environ.get('KAFKA_BOOTSTRAP_SERVER'),
            'security.protocol': 'SASL_SSL',
            'sasl.mechanisms': 'PLAIN',
            'sasl.username': os.environ.get('KAFKA_API_KEY'),
            'sasl.password': os.environ.get('KAFKA_API_SECRET')
        }
        if kafka_conf['bootstrap.servers']:
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

def publish_event(topic, event_type, user_id, data, changes=None):
    if not producer:
        print("Produtor Kafka não está inicializado. Evento não publicado.")
        return
    event = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "data": data,
        "source_service": "servico-usuarios"
    }
    if changes:
        event["changes"] = changes
    try:
        event_value = json.dumps(event, default=str)
        producer.produce(topic, key=user_id, value=event_value, callback=delivery_report)
        producer.poll(0)
        print(f"Evento '{event_type}' para o usuário {user_id} publicado no tópico {topic}.")
    except Exception as e:
        print(f"Erro ao publicar evento Kafka: {e}")

# --- Rotas da API ---

@app.route('/users', methods=['POST'])
def create_user():
    # Teste de workflow 6
    if not db or not db_session:
        return jsonify({"error": "Dependências de banco de dados não inicializadas.", "health": get_health_status()}), 503

    user_data = request.json
    if not user_data or 'email' not in user_data or 'name' not in user_data:
        return jsonify({"error": "Email e nome são obrigatórios."}), 400

    user_id = str(uuid.uuid4())
    
    firestore_data = user_data.copy()
    location_data = firestore_data.pop('location', None)
    firestore_data['created_at'] = firestore.SERVER_TIMESTAMP
    firestore_data['updated_at'] = firestore.SERVER_TIMESTAMP

    try:
        if location_data and 'latitude' in location_data and 'longitude' in location_data:
            lat = location_data['latitude']
            lon = location_data['longitude']
            wkt_point = f'POINT({lon} {lat})'
            new_location = UserLocation(user_id=user_id, location=wkt_point)
            db_session.add(new_location)

        db.collection('users').document(user_id).set(firestore_data)
        db_session.commit()

        publish_event('eventos_usuarios', 'UserCreated', user_id, user_data)
        return jsonify({"id": user_id, "message": "Usuário criado com sucesso."}), 201

    except SQLAlchemyError as e:
        db_session.rollback()
        return jsonify({"error": f"Erro no banco de dados geoespacial: {e}"}), 500
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": f"Erro ao criar usuário: {e}"}), 500

@app.route('/users/<user_id>', methods=['GET'])
def get_user(user_id):
    if not db or not db_session:
        return jsonify({"error": "Dependências de banco de dados não inicializadas."}), 503

    try:
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            return jsonify({"error": "Usuário não encontrado."}), 404
        
        user_data = user_doc.to_dict()
        user_data['id'] = user_doc.id

        location_record = db_session.query(UserLocation).filter_by(user_id=user_id).first()
        if location_record and to_shape:
            point = to_shape(location_record.location)
            user_data['location'] = {'latitude': point.y, 'longitude': point.x}

        return jsonify(user_data), 200
    except Exception as e:
        return jsonify({"error": f"Erro ao buscar usuário: {e}"}), 500

@app.route('/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    if not db or not db_session:
        return jsonify({"error": "Dependências de banco de dados não inicializadas."}), 503

    update_data = request.json
    if not update_data:
        return jsonify({"error": "Dados para atualização são obrigatórios."}), 400

    user_ref = db.collection('users').document(user_id)

    try:
        if not user_ref.get().exists:
            return jsonify({"error": "Usuário não encontrado."}), 404

        firestore_data = update_data.copy()
        location_data = firestore_data.pop('location', None)
        firestore_data['updated_at'] = firestore.SERVER_TIMESTAMP

        if location_data and 'latitude' in location_data and 'longitude' in location_data:
            lat = location_data['latitude']
            lon = location_data['longitude']
            wkt_point = f'POINT({lon} {lat})'
            
            location_record = db_session.query(UserLocation).filter_by(user_id=user_id).first()
            if location_record:
                location_record.location = wkt_point
            else:
                new_location = UserLocation(user_id=user_id, location=wkt_point)
                db_session.add(new_location)

        if firestore_data:
            user_ref.update(firestore_data)

        db_session.commit()

        publish_event('eventos_usuarios', 'UserUpdated', user_id, update_data)
        return jsonify({"message": "Usuário atualizado com sucesso.", "id": user_id}), 200

    except SQLAlchemyError as e:
        db_session.rollback()
        return jsonify({"error": f"Erro no banco de dados geoespacial: {e}"}), 500
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": f"Erro ao atualizar usuário: {e}"}), 500

@app.route('/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    if not db or not db_session:
        return jsonify({"error": "Dependências de banco de dados não inicializadas."}), 503

    user_ref = db.collection('users').document(user_id)

    try:
        if not user_ref.get().exists:
            return jsonify({"error": "Usuário não encontrado."}), 404

        location_record = db_session.query(UserLocation).filter_by(user_id=user_id).first()
        if location_record:
            db_session.delete(location_record)

        user_ref.delete()
        db_session.commit()

        publish_event('eventos_usuarios', 'UserDeleted', user_id, {"user_id": user_id})
        return '', 204

    except SQLAlchemyError as e:
        db_session.rollback()
        return jsonify({"error": f"Erro no banco de dados geoespacial: {e}"}), 500
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": f"Erro ao deletar usuário: {e}"}), 500

@app.route('/api/criticas', methods=['POST'])
def add_critica():
    """
    Recebe uma crítica de produto de um usuário e a salva no banco de dados.
    """
    if not db_session:
        return jsonify({"error": "Dependências de banco de dados não inicializadas."}), 503

    if not request.is_json:
        return jsonify({"error": "Missing JSON in request"}), 400

    data = request.get_json()
    produto_id = data.get('produto_id')
    tipo_critica = data.get('tipo_critica')
    comentario = data.get('comentario')

    if not all([produto_id, tipo_critica]):
        return jsonify({"error": "Missing required fields: produto_id, tipo_critica"}), 400

    try:
        new_critica = Critica(
            produto_id=produto_id,
            tipo_critica=tipo_critica,
            comentario=comentario,
            status='PENDENTE'
        )
        db_session.add(new_critica)
        db_session.commit()
        return jsonify({"id": new_critica.id, "message": "Crítica recebida e salva com sucesso!"}), 201
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": f"Erro ao salvar crítica: {e}"}), 500

@app.route('/api/criticas', methods=['GET'])
def get_criticas():
    """
    Retorna todas as críticas com status 'PENDENTE'.
    """
    if not db_session:
        return jsonify({"error": "Dependências de banco de dados não inicializadas."}), 503

    try:
        criticas_pendentes = db_session.query(Critica).filter_by(status='PENDENTE').all()
        result = []
        for critica in criticas_pendentes:
            result.append({
                "id": critica.id,
                "produto_id": critica.produto_id,
                "tipo_critica": critica.tipo_critica,
                "comentario": critica.comentario,
                "status": critica.status,
                "criado_em": critica.criado_em
            })
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": f"Erro ao buscar críticas: {e}"}), 500

# --- Funções Auxiliares de Autorização ---

def verify_owner(user_id, store_id):
    if not db_session:
        return False
    try:
        role_entry = db_session.query(UserStoreRole).filter_by(user_id=user_id, store_id=store_id).first()
        if role_entry and role_entry.role == 'owner':
            return True
        return False
    except Exception as e:
        print(f"Erro ao verificar proprietário: {e}")
        return False

# --- Rotas de Gerenciamento de Funcionários ---

@app.route('/api/stores/<store_id>/employees', methods=['POST'])
def add_employee(store_id):
    if not db or not db_session:
        return jsonify({"error": "Dependências de banco de dados não inicializadas."}), 503

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization token is required"}), 401
    try:
        id_token = auth_header.split('Bearer ')[1]
        decoded_token = auth.verify_id_token(id_token)
        requestor_uid = decoded_token['uid']
    except Exception as e:
        return jsonify({"error": "Invalid or expired token", "details": str(e)}), 401

    if not verify_owner(requestor_uid, store_id):
        return jsonify({"error": "Apenas o proprietário da loja pode adicionar funcionários."}), 403

    data = request.json
    if not data or not data.get('employee_id') or not isinstance(data.get('shifts'), list):
        return jsonify({"error": "employee_id e uma lista de shifts são obrigatórios."}), 400

    try:
        new_employee_role = UserStoreRole(
            user_id=data['employee_id'],
            store_id=store_id,
            role='employee',
            shifts=data['shifts']
        )
        db_session.merge(new_employee_role)
        db_session.commit()
        publish_event('eventos_funcionarios', 'EmployeeAdded', data['employee_id'], {"store_id": store_id, **data})
        return jsonify({"message": "Funcionário adicionado com sucesso."}), 201
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": f"Erro ao adicionar funcionário: {e}"}), 500

@app.route('/api/stores/<store_id>/employees', methods=['GET'])
def list_employees(store_id):
    if not db or not db_session:
        return jsonify({"error": "Dependências de banco de dados não inicializadas."}), 503

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization token is required"}), 401
    try:
        id_token = auth_header.split('Bearer ')[1]
        decoded_token = auth.verify_id_token(id_token)
        requestor_uid = decoded_token['uid']
    except Exception as e:
        return jsonify({"error": "Invalid or expired token", "details": str(e)}), 401

    if not verify_owner(requestor_uid, store_id):
        return jsonify({"error": "Apenas o proprietário da loja pode ver os funcionários."}), 403

    try:
        roles = db_session.query(UserStoreRole).filter_by(store_id=store_id).all()
        employees_details = []
        for role in roles:
            user_doc = db.collection('users').document(role.user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                employees_details.append({
                    "user_id": role.user_id,
                    "role": role.role,
                    "shifts": role.shifts,
                    "name": user_data.get('name'),
                    "email": user_data.get('email')
                })
        return jsonify(employees_details), 200
    except Exception as e:
        return jsonify({"error": f"Erro ao listar funcionários: {e}"}), 500

@app.route('/api/stores/<store_id>/employees/<employee_id>', methods=['DELETE'])
def remove_employee(store_id, employee_id):
    if not db or not db_session:
        return jsonify({"error": "Dependências de banco de dados não inicializadas."}), 503

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization token is required"}), 401
    try:
        id_token = auth_header.split('Bearer ')[1]
        decoded_token = auth.verify_id_token(id_token)
        requestor_uid = decoded_token['uid']
    except Exception as e:
        return jsonify({"error": "Invalid or expired token", "details": str(e)}), 401

    if not verify_owner(requestor_uid, store_id):
        return jsonify({"error": "Apenas o proprietário da loja pode remover funcionários."}), 403

    try:
        role_to_delete = db_session.query(UserStoreRole).filter_by(user_id=employee_id, store_id=store_id).first()
        if not role_to_delete:
            return jsonify({"error": "Vínculo de funcionário não encontrado."}), 404
        
        db_session.delete(role_to_delete)
        db_session.commit()
        publish_event('eventos_funcionarios', 'EmployeeRemoved', employee_id, {'store_id': store_id, 'employee_id': employee_id})
        return '', 204
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": f"Erro ao remover funcionário: {e}"}), 500

# --- Rotas Internas (Serviço-para-Serviço) ---

@app.route('/internal/roles', methods=['POST'])
def assign_role():
    if not db_session:
        return jsonify({"error": "Dependência do banco de dados não inicializada."}), 503

    # Esta rota deve ser protegida por um segredo compartilhado ou mTLS em produção
    # Por simplicidade, vamos usar um header com um segredo simples
    internal_secret = os.environ.get('INTERNAL_SERVICE_SECRET')
    auth_header = request.headers.get('Authorization')
    if not internal_secret or auth_header != f'Bearer {internal_secret}':
        return jsonify({"error": "Unauthorized internal service"}), 401

    data = request.json
    if not data or not data.get('user_id') or not data.get('store_id') or not data.get('role'):
        return jsonify({"error": "user_id, store_id, e role são obrigatórios."}), 400

    try:
        # Usar merge para inserir ou atualizar o papel (UPSERT)
        new_role = UserStoreRole(
            user_id=data['user_id'],
            store_id=data['store_id'],
            role=data['role'],
            shifts=data.get('shifts')  # Opcional, principalmente para funcionários
        )
        db_session.merge(new_role)
        db_session.commit()

        # Publicar evento para notificar outros sistemas (opcional, mas bom para auditoria)
        publish_event('eventos_funcionarios', 'UserRoleAssigned', data['user_id'], data)

        return jsonify({"message": f"Papel '{data['role']}' atribuído com sucesso."}), 201

    except SQLAlchemyError as e:
        db_session.rollback()
        return jsonify({"error": f"Erro no banco de dados ao atribuir papel: {e}"}), 500
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": f"Erro inesperado ao atribuir papel: {e}"}), 500


@app.route('/api/permissions/check', methods=['GET'])
def check_permission():
    user_id = request.args.get('user_id')
    store_id = request.args.get('store_id')

    if not user_id or not store_id:
        return jsonify({"allow": False, "reason": "user_id and store_id are required"}), 400

    if not db_session:
        return jsonify({"allow": False, "reason": "database dependency not available"}), 503

    try:
        role_entry = db_session.query(UserStoreRole).filter_by(user_id=user_id, store_id=store_id).first()

        if not role_entry:
            return jsonify({"allow": False, "reason": "not_associated"}), 403

        if role_entry.role == 'owner':
            return jsonify({"allow": True, "role": "owner"}), 200

        if role_entry.role == 'employee':
            # 1. Verificar Turno
            shifts = role_entry.shifts or []
            now_utc = datetime.now(timezone.utc)
            current_hour = now_utc.hour
            
            # Mapeamento de turnos para horas (exemplo)
            shift_hours = {
                "madrugada": range(0, 6),    # 00:00 - 05:59
                "manha": range(6, 12),     # 06:00 - 11:59
                "tarde": range(12, 18),    # 12:00 - 17:59
                "noite": range(18, 24)     # 18:00 - 23:59
            }

            in_shift = any(current_hour in shift_hours.get(s, range(-1,-1)) for s in shifts)
            if not in_shift:
                return jsonify({"allow": False, "reason": "outside_shift"}), 403

            # 2. Verificar Geofence (ex: 150 metros)
            GEOFENCE_RADIUS_METERS = 150
            is_within_geofence = db_session.query(func.ST_DWithin(
                UserLocation.location,
                StoreLocation.location,
                GEOFENCE_RADIUS_METERS
            )).filter(
                UserLocation.user_id == user_id,
                StoreLocation.store_id == store_id
            ).scalar()

            if not is_within_geofence:
                return jsonify({"allow": False, "reason": "outside_geofence"}), 403
            
            # Se passou em todas as verificações de funcionário
            return jsonify({"allow": True, "role": "employee"}), 200

        # Papel desconhecido
        return jsonify({"allow": False, "reason": "unknown_role"}), 403

    except Exception as e:
        return jsonify({"allow": False, "reason": f"internal_error: {e}"}), 500

# --- Health Check (para Vercel) ---
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
            "kafka_producer": kafka_producer_init_error # Renamed
        }
    }
    return status

@app.route('/health', methods=['GET'])
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
