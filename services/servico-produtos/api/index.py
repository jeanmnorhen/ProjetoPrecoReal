import os
import json
import requests
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, auth, firestore
from confluent_kafka import Producer
import base64


app = Flask(__name__)
CORS(app, supports_credentials=True, origins=['https://frontend-tester-1foc8lpkl-jeanmnorhens-projects.vercel.app'])

# ---  Global Dependencies_ _(initiali zed to None)1 ---
db = None
producer = None
firebase_init_error = None
kafka_producer_init_error = None

# --- Funções Auxiliares  ---

def delivery_report(err, msg):
    if err is not None:
        print(f'Falha ao entregar mensagem Kafka: {err}')
    else:
        print(f'Mensagem Kafka entregue em {msg.topic()} [{msg.partition()}]')

def publish_event(topic, event_type, product_id, data, changes=None):
    if not producer:
        print("Produtor Kafka não está inicializado. Evento não publicado.")
        return
    event = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "product_id": product_id,
        "data": data,
        "source_service": "servico-produtos"
    }
    if changes:
        event["changes"] = changes
    try:
        event_value = json.dumps(event, default=str)
        producer.produce(topic, key=product_id, value=event_value, callback=delivery_report)
        producer.poll(0)
        print(f"Evento '{event_type}' para o produto {product_id} publicado no tópico {topic}.")
    except Exception as e:
        print(f"Erro ao publicar evento Kafka: {e}")


def check_permission(user_id, store_id):
    """Chama o servico-usuarios para verificar se um usuário tem permissão para gerenciar uma loja."""
    servico_usuarios_url = os.environ.get('SERVICO_USUARIOS_URL')
    if not servico_usuarios_url:
        print("ERRO: SERVICO_USUARIOS_URL não configurado.")
        return False, {"error": "URL do serviço de permissões não configurada."}

    try:
        # O token do usuário   original não é necessário aqui, pois usamos o segredo interno.
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


@app.route('/api/products', methods=['GET'])
def list_all_products():
    if not db:
        return jsonify({"error": "Dependência do Firestore não inicializada."}), 503

    try:
        products_ref = db.collection('products')
        docs = products_ref.stream()
        
        all_products = []
        for doc in docs:
            product_data = doc.to_dict()
            product_data['id'] = doc.id
            all_products.append(product_data)
            
        return jsonify({"products": all_products}), 200
    except Exception as e:
        return jsonify({"error": f"Erro ao listar produtos: {e}"}), 500

@app.route("/api/products", methods=["POST"])
def create_product():
    if not db:
        return jsonify({"error": "Dependência do Firestore não inicializada."}), 503

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization token is required"}), 401

    try:
        id_token = auth_header.split('Bearer ')[1]
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
    except Exception as e:
        return jsonify({"error": "Invalid or expired token", "details": str(e)}), 401

    product_data = request.get_json()
    if not product_data or not product_data.get('name') or not product_data.get('store_id'):
        return jsonify({"error": "Product name and store_id are required"}), 400
    
    store_id = product_data['store_id']

    # Nova verificação de permissão centralizada
    allowed, reason = check_permission(uid, store_id)
    if not allowed:
        return jsonify({"error": "User is not authorized to add products to this store", "details": reason}), 403

    try:
        product_to_create = product_data.copy()
        product_to_create['created_at'] = firestore.SERVER_TIMESTAMP
        product_to_create['updated_at'] = firestore.SERVER_TIMESTAMP
        _, doc_ref = db.collection('products').add(product_to_create)
        
        publish_event('eventos_produtos', 'ProductCreated', doc_ref.id, product_to_create)
        return jsonify({"message": "Product created successfully", "productId": doc_ref.id}), 201
    except Exception as e:
        return jsonify({"error": "Could not create product", "details": str(e)}), 500

@app.route('/api/products/<product_id>', methods=['GET'])
def get_product(product_id):
    if not db:
        return jsonify({"error": "Dependência do Firestore não inicializada."}), 503

    try:
        product_doc = db.collection('products').document(product_id).get()
        if not product_doc.exists:
            return jsonify({"error": "Produto não encontrado."}), 404
        product_data = product_doc.to_dict()
        product_data['id'] = product_doc.id
        return jsonify(product_data), 200
    except Exception as e:
        return jsonify({"error": f"Erro ao buscar produto: {e}"}), 500

@app.route('/api/products/<product_id>', methods=['PUT'])
def update_product(product_id):
    if not db:
        return jsonify({"error": "Dependência do Firestore não inicializada."}), 503

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

    product_ref = db.collection('products').document(product_id)
    
    try:
        product_doc = product_ref.get()
        if not product_doc.exists:
            return jsonify({"error": "Produto não encontrado."}), 404
        
        store_id = product_doc.to_dict().get('store_id')
        if not store_id:
            return jsonify({"error": "Produto não tem uma loja associada."}), 500

        # Nova verificação de permissão
        allowed, reason = check_permission(uid, store_id)
        if not allowed:
            return jsonify({"error": "User is not authorized to update this product", "details": reason}), 403

        update_data['updated_at'] = firestore.SERVER_TIMESTAMP
        product_ref.update(update_data)

        publish_event('eventos_produtos', 'ProductUpdated', product_id, update_data)
        return jsonify({"message": "Produto atualizado com sucesso.", "productId": product_id}), 200
    except Exception as e:
        return jsonify({"error": f"Erro ao atualizar produto: {e}"}), 500

@app.route('/api/products/<product_id>', methods=['DELETE', 'OPTIONS'])
def delete_product(product_id):
    if not db:
        return jsonify({"error": "Dependência do Firestore não inicializada."}), 503

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization token is required"}), 401

    try:
        id_token = auth_header.split('Bearer ')[1]
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
    except Exception as e:
        return jsonify({"error": "Invalid or expired token", "details": str(e)}), 401

    product_ref = db.collection('products').document(product_id)

    try:
        product_doc = product_ref.get()
        if not product_doc.exists:
            return jsonify({"error": "Produto não encontrado."}), 404

        store_id = product_doc.to_dict().get('store_id')
        if not store_id:
            return jsonify({"error": "Produto não tem uma loja associada."}), 500

        # Nova verificação de permissão
        allowed, reason = check_permission(uid, store_id)
        if not allowed:
            return jsonify({"error": "User is not authorized to delete this product", "details": reason}), 403

        product_ref.delete()

        publish_event('eventos_produtos', 'ProductDeleted', product_id, {"product_id": product_id})
        return '', 204
    except Exception as e:
        return jsonify({"error": f"Erro ao deletar produto: {e}"}), 500

def get_health_status():
    env_vars = {
        "FIREBASE_ADMIN_SDK_BASE64": "present" if os.environ.get('FIREBASE_ADMIN_SDK_BASE64') else "missing",
        "KAFKA_BOOTSTRAP_SERVER": "present" if os.environ.get('KAFKA_BOOTSTRAP_SERVER') else "missing",
        "KAFKA_API_KEY": "present" if os.environ.get('KAFKA_API_KEY') else "missing",
        "KAFKA_API_SECRET": "present" if os.environ.get('KAFKA_API_SECRET') else "missing"
    }

    status = {
        "environment_variables": env_vars,
        "dependencies": {
            "firestore": "ok" if db else "error",
            "kafka_producer": "ok" if producer else "error"
        },
        "initialization_errors": {
            "firestore": firebase_init_error,
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
        status["dependencies"]["kafka_producer"] == "ok"
    )
    http_status = 200 if all_ok else 503
    
    return jsonify(status), http_status

if __name__ == '__main__':
    app.run(debug=True)
