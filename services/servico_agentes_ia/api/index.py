import requests
from dotenv import load_dotenv
load_dotenv(dotenv_path='.env.local')

import os
import json
import base64
from io import BytesIO
from PIL import Image
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from confluent_kafka import Consumer, Producer, KafkaError
import google.generativeai as genai

try:
    import firebase_admin
    from firebase_admin import credentials, firestore, auth
except ImportError:
    firebase_admin = None

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=['https://frontend-tester-1foc8lpkl-jeanmnorhens-projects.vercel.app'])

# --- Global Clients (Lazy Loaded) --- 
db = None
producer = None
kafka_consumer_instance = None
gemini_model = None

# ---Error Tracking ---
initialization_errors = {
    "firebase": None,
    "kafka_producer": None,
    "kafka_consumer": None,
    "gemini": None
}

# --- Lazy Loader Functions ---

def get_db():
    global db
    if db is None and firebase_admin:
        try:
            base64_sdk = os.environ.get('FIREBASE_ADMIN_SDK_BASE64')
            if base64_sdk:
                decoded_sdk = base64.b64decode(base64_sdk).decode('utf-8')
                cred_dict = json.loads(decoded_sdk)
                cred = credentials.Certificate(cred_dict)
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred, {'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET')})
                db = firestore.client()
                print("Firebase inicializado com sucesso (lazy). Firestore e Storage.")
            else:
                initialization_errors["firebase"] = "Variável FIREBASE_ADMIN_SDK_BASE64 não encontrada."
        except Exception as e:
            print(f"DEBUG: Firebase initialization failed: {e}")
            initialization_errors["firebase"] = str(e)
    elif not firebase_admin:
        initialization_errors["firebase"] = "Biblioteca firebase_admin não encontrada."
    return db

def upload_image_to_firebase(image_base64: str, filename: str) -> str:
    if not firebase_admin:
        raise Exception("Firebase Admin SDK não inicializado.")
    
    bucket = firebase_admin.storage.bucket()
    blob = bucket.blob(f"product_images/{filename}")
    image_bytes = base64.b64decode(image_base64)
    blob.upload_from_string(image_bytes, content_type='image/jpeg') # Assumindo JPEG, pode ser ajustado
    blob.make_public()
    return blob.public_url

def get_producer():
    global producer
    if producer is None and Producer:
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
                print("Produtor Kafka inicializado com sucesso (lazy).")
            else:
                initialization_errors["kafka_producer"] = "Variável de ambiente KAFKA_BOOTSTRAP_SERVER não encontrada."
        except Exception as e:
            print(f"DEBUG: Kafka Producer initialization failed: {e}")
            initialization_errors["kafka_producer"] = str(e)
    elif not Producer:
        initialization_errors["kafka_producer"] = "Biblioteca confluent_kafka não encontrada."
    return producer

def get_kafka_consumer():
    global kafka_consumer_instance
    if kafka_consumer_instance is None and Consumer:
        try:
            kafka_bootstrap_server = os.environ.get('KAFKA_BOOTSTRAP_SERVER')
            if kafka_bootstrap_server:
                kafka_api_key = os.environ.get('KAFKA_API_KEY')
                if kafka_api_key:
                    # Cloud Kafka configuration
                    print("Configurando consumidor Kafka para ambiente de nuvem (SASL)...")
                    kafka_conf = {
                        'bootstrap.servers': kafka_bootstrap_server,
                        'group.id': 'ai_agents_group_v1',
                        'auto.offset.reset': 'earliest',
                        'security.protocol': 'SASL_SSL',
                        'sasl.mechanisms': 'PLAIN',
                        'sasl.username': kafka_api_key,
                        'sasl.password': os.environ.get('KAFKA_API_SECRET')
                    }
                else:
                    # Local Docker Kafka configuration
                    print("Configurando consumidor Kafka para ambiente local (sem SASL)...")
                    kafka_conf = {
                        'bootstrap.servers': kafka_bootstrap_server,
                        'group.id': 'ai_agents_group_v1',
                        'auto.offset.reset': 'earliest'
                    }
                kafka_consumer_instance = Consumer(kafka_conf)
                kafka_consumer_instance.subscribe(['tarefas_ia'])
                print("Consumidor Kafka inicializado com sucesso (lazy).")
            else:
                initialization_errors["kafka_consumer"] = "Variáveis de ambiente do Kafka não encontradas."
        except Exception as e:
            print(f"DEBUG: Kafka Consumer initialization failed: {e}")
            initialization_errors["kafka_consumer"] = str(e)
    elif not Consumer:
        initialization_errors["kafka_consumer"] = "Biblioteca confluent_kafka não encontrada."
    return kafka_consumer_instance

def get_gemini_model():
    global gemini_model
    if gemini_model is None:
        try:
            gemini_api_key = os.environ.get('GEMINI_API_KEY')
            if gemini_api_key:
                genai.configure(api_key=gemini_api_key)
                gemini_model = genai.GenerativeModel('gemini-pro-vision')
                print("Modelo Gemini inicializado com sucesso (lazy).")
            else:
                initialization_errors["gemini"] = "Variável GEMINI_API_KEY não encontrada."
        except Exception as e:
            print(f"DEBUG: Gemini initialization failed: {e}")
            initialization_errors["gemini"] = str(e)
    return gemini_model

# --- Kafka Publishing Logic ---

def delivery_report(err, msg):
    if err is not None:
        print(f'Falha ao entregar mensagem Kafka: {err}')
    else:
        print(f'Mensagem Kafka entregue em {msg.topic()} [{msg.partition()}]')

def publish_event(topic, event_type, task_id, data, changes=None):
    kafka_producer = get_producer()
    if not kafka_producer:
        print("Produtor Kafka não está inicializado. Evento não publicado.")
        return

    event = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task_id": task_id,
        "data": data,
        "source_service": "servico_agentes_ia"
    }
    if changes:
        event["changes"] = changes
    try:
        event_value = json.dumps(event, default=str)
        kafka_producer.produce(topic, key=task_id, value=event_value, callback=delivery_report)
        kafka_producer.poll(0)
        print(f"Evento '{event_type}' para a tarefa {task_id} publicado no tópico {topic}.")
    except Exception as e:
        print(f"Erro ao publicar evento Kafka: {e}")

# --- Search Helper ---

async def search_existing_product(search_term: str):
    search_service_url = os.environ.get('SERVICO_BUSCA_URL')
    if not search_service_url:
        print("URL do serviço de busca não configurada.")
        return None

    try:
        # Usando requests de forma síncrona por simplicidade, idealmente usaríamos httpx para async
        response = requests.get(
            f"{search_service_url}/api/search",
            params={"q": search_term, "type": "canonical"},
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao contatar o serviço de busca: {e}")
        return None

# --- AI Agent Logic ---

def process_image_analysis(task):
    model = get_gemini_model()
    firestore_db = get_db()

    if not model or not firestore_db:
        return {"error": "Dependências críticas (Gemini ou Firestore) não inicializadas."}

    try:
        image_b64 = task.get('image_b64')
        if not image_b64:
            return {"error": "No image data in task"}

        image_bytes = base64.b64decode(image_b64)
        img = Image.open(BytesIO(image_bytes))
        
        prompt = "Identifique o nome completo do produto principal nesta imagem, incluindo marca e volume/peso, se visível. Responda apenas com o nome do produto."
        response = model.generate_content([prompt, img])
        product_name = response.text.strip()
        print(f"Produto identificado pela IA: {product_name}")

        # Verificar se o produto já existe no catálogo canônico
        product_ref = firestore_db.collection('products').where('name', '==', product_name).limit(1)
        product_docs = list(product_ref.stream())
        product_exists = len(product_docs) > 0

        task_id = task.get('task_id')

        if product_exists:
            # Produto existe, fluxo normal
            print(f"Produto '{product_name}' já existe no catálogo.")
            result_data = {
                "task_id": task_id,
                "product_name": product_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "completed"
            }
            publish_event('resultados_ia', 'ImageAnalysisResult', task_id, result_data)
            return {"identified_product": product_name, "details": result_data}
        else:
            # Produto não existe, criar sugestão
            print(f"Produto '{product_name}' não encontrado. Criando sugestão.")
            suggestion_data = {
                "term": product_name,
                "source": "image_analysis",
                "status": "pending",
                "created_at": firestore.SERVER_TIMESTAMP,
                "task_id": task_id
            }
            firestore_db.collection('product_suggestions').add(suggestion_data)

            result_data = {
                "task_id": task_id,
                "suggestion_term": product_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "suggestion_created"
            }
            publish_event('resultados_ia', 'ImageAnalysisSuggestion', task_id, result_data)
            return {"suggestion_created": product_name, "details": result_data}

    except Exception as e:
        print(f"Erro na análise de imagem: {e}")
        return {"error": str(e)}

# --- API Endpoints ---

@app.route('/api/agents/consume', methods=['POST', 'GET'])
def consume_tasks():
    # Security check for cron job, similar to other consumer services
    auth_header = request.headers.get('Authorization')
    cron_secret = os.environ.get('CRON_SECRET')
    if not cron_secret or auth_header != f'Bearer {cron_secret}':
        return jsonify({"error": "Unauthorized"}), 401

    consumer = get_kafka_consumer()
    if not consumer:
        return jsonify({"error": "Kafka consumer not initialized.", "details": initialization_errors["kafka_consumer"]}), 503

    messages_processed = 0
    results = []
    try:
        msgs = consumer.consume(num_messages=5, timeout=10.0)
        if not msgs:
            return jsonify({"status": "No new messages to process"}), 200

        for msg in msgs:
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    print(f"Kafka error: {msg.error()}")
                continue

            try:
                task = json.loads(msg.value().decode('utf-8'))
                print(f"Task recebida: {task}")
                task_type = task.get('task_type')
                
                result = None
                if task_type == 'image_analysis' or task_type == 'analisar_imagem':
                    print(f"Processando tarefa de análise de imagem: {task.get('task_id')}")
                    result = process_image_analysis(task)
                else:
                    print(f"Tipo de tarefa desconhecido: {task_type}")
                    result = {"error": "Unknown task type"}
                
                results.append(result)
                messages_processed += 1

            except json.JSONDecodeError as e:
                print(f"Failed to decode message: {e}")

    except Exception as e:
        print(f"An error occurred during message consumption: {e}")
        return jsonify({"error": str(e)}), 500

    return jsonify({"status": "ok", "messages_processed": messages_processed, "results": results}), 200

@app.route('/api/agents/suggestions', methods=['GET'])
def get_pending_suggestions():
    # Protegendo o endpoint, apenas usuários autenticados podem acessar
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({"error": "Authorization header missing"}), 401
    try:
        id_token = auth_header.split('Bearer ')[1]
        auth.verify_id_token(id_token)
    except Exception as e:
        return jsonify({"error": f"Invalid or expired token: {str(e)}"}), 401

    firestore_db = get_db()
    if not firestore_db:
        return jsonify({"error": "Firestore not initialized"}), 503

    try:
        suggestions_ref = firestore_db.collection('product_suggestions')
        pending_query = suggestions_ref.where('status', '==', 'pending').order_by('created_at')
        docs = pending_query.stream()
        
        suggestions = []
        for doc in docs:
            suggestion_data = doc.to_dict()
            suggestion_data['id'] = doc.id
            # Garantir que o timestamp seja serializável
            if 'created_at' in suggestion_data and hasattr(suggestion_data['created_at'], 'isoformat'):
                 suggestion_data['created_at'] = suggestion_data['created_at'].isoformat()
            suggestions.append(suggestion_data)
            
        return jsonify(suggestions), 200
    except Exception as e:
        print(f"Erro ao buscar sugestões: {e}")
        return jsonify({"error": f"Erro ao buscar sugestões: {e}"}), 500

@app.route('/api/agents/suggestions/<suggestion_id>/reject', methods=['PUT'])
def reject_suggestion(suggestion_id):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({"error": "Authorization header missing"}), 401
    try:
        id_token = auth_header.split('Bearer ')[1]
        auth.verify_id_token(id_token)
    except Exception as e:
        return jsonify({"error": f"Invalid or expired token: {str(e)}"}), 401

    firestore_db = get_db()
    if not firestore_db:
        return jsonify({"error": "Firestore not initialized"}), 503

    try:
        suggestion_ref = firestore_db.collection('product_suggestions').document(suggestion_id)
        suggestion_doc = suggestion_ref.get()

        if not suggestion_doc.exists:
            return jsonify({"error": "Sugestão não encontrada."}), 404

        # Atualiza o status para 'rejected'
        suggestion_ref.update({'status': 'rejected', 'updated_at': firestore.SERVER_TIMESTAMP})

        # Publica evento Kafka
        publish_event('resultados_ia', 'SuggestionRejected', suggestion_id, {'status': 'rejected'})

        return jsonify({"message": "Sugestão rejeitada com sucesso."}), 200
    except Exception as e:
        print(f"Erro ao rejeitar sugestão: {e}")
        return jsonify({"error": f"Erro ao rejeitar sugestão: {e}"}), 500

@app.route('/api/agents/catalog-intake', methods=['POST'])
def catalog_intake():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({"error": "Authorization header missing"}), 401
    try:
        id_token = auth_header.split('Bearer ')[1]
        auth.verify_id_token(id_token)
    except Exception as e:
        return jsonify({"error": f"Invalid or expired token: {str(e)}"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is missing"}), 400

    text_query = data.get('text_query')
    image_base64 = data.get('image_base64')
    category_query = data.get('category_query')

    if not text_query and not image_base64 and not category_query:
        return jsonify({"error": "A requisição deve conter 'text_query', 'image_base64' ou 'category_query'"}), 400

    # Lógica principal da rotina
    try:
        # Cenário 1: Category Query
        if category_query:
            model = get_gemini_model()
            if not model:
                return jsonify({"error": "Modelo de IA não inicializado"}), 503
            
            prompt_category = f"Liste 10 produtos populares na categoria '{category_query}', com nome e uma breve descrição. Formate a resposta como um JSON, uma lista de objetos com as chaves 'name' e 'description'."
            response_category = model.generate_content(prompt_category)
            cleaned_response_text = response_category.text.strip().replace('```json', '').replace('```', '')
            suggested_products = json.loads(cleaned_response_text)

            products_service_url = os.environ.get('SERVICO_PRODUTOS_URL')
            if not products_service_url:
                return jsonify({"error": "URL do serviço de produtos não configurada"}), 500

            created_products_ids = []
            for product_suggestion in suggested_products:
                new_product_payload = {
                    "name": product_suggestion.get('name'),
                    "description": product_suggestion.get('description'),
                    "category": category_query,
                    "image_url": None # Gemini não gera imagem aqui
                }
                creation_response = requests.post(
                    f"{products_service_url}/api/products/canonical",
                    headers={"Authorization": auth_header, "Content-Type": "application/json"},
                    json=new_product_payload
                )
                if creation_response.status_code == 201:
                    created_products_ids.append(creation_response.json().get('productId'))
                else:
                    print(f"Erro ao criar produto da categoria {category_query}: {creation_response.text}")
            
            return jsonify({"message": f"Sugestões de produtos para a categoria '{category_query}' geradas e enviadas para aprovação.", "productIds": created_products_ids}), 202

        # Passo 1: Busca (implementação inicial para text_query)
        search_results = None
        if text_query:
            search_results = requests.get(f"{os.environ.get('SERVICO_BUSCA_URL')}/api/search", params={"q": text_query, "type": "canonical"}).json()
        elif image_base64: # Se for imagem, tenta identificar o produto primeiro para buscar
            model = get_gemini_model()
            if not model:
                return jsonify({"error": "Modelo de IA não inicializado"}), 503
            image_bytes = base64.b64decode(image_base64)
            img = Image.open(BytesIO(image_bytes))
            prompt_identify = "Identifique o nome completo do produto principal nesta imagem, incluindo marca e volume/peso, se visível. Responda apenas com o nome do produto." 
            response_identify = model.generate_content([prompt_identify, img])
            identified_product_name = response_identify.text.strip()
            if identified_product_name:
                search_results = requests.get(f"{os.environ.get('SERVICO_BUSCA_URL')}/api/search", params={"q": identified_product_name, "type": "canonical"}).json()
            else:
                return jsonify({"error": "Não foi possível identificar o produto na imagem para busca."}), 400

        if search_results and search_results.get('results') and len(search_results.get('results')) > 0:
            # Lógica para produto encontrado
            product_id = search_results['results'][0]['id'] # Assume o primeiro resultado como o mais relevante
            product_name = search_results['results'][0]['name']

            if image_base64:
                # Upload da nova imagem e adição como candidata
                filename = f"{product_id}_{datetime.now(timezone.utc).timestamp()}.jpg"
                uploaded_image_url = upload_image_to_firebase(image_base64, filename)

                products_service_url = os.environ.get('SERVICO_PRODUTOS_URL')
                if not products_service_url:
                    return jsonify({"error": "URL do serviço de produtos não configurada"}), 500

                add_image_response = requests.post(
                    f"{products_service_url}/api/products/{product_id}/images",
                    headers={"Authorization": auth_header, "Content-Type": "application/json"},
                    json={'image_url': uploaded_image_url, 'source': 'image_analysis'}
                )

                if add_image_response.status_code != 201:
                    return jsonify({"error": "Falha ao adicionar imagem candidata", "details": add_image_response.text}), 500

                return jsonify({"message": "Produto existente encontrado. Nova imagem adicionada para revisão.", "productId": product_id, "imageUrl": uploaded_image_url}), 200
            else:
                return jsonify({"message": "Produto encontrado no catálogo.", "product": search_results['results'][0]}), 200

        # Passo 2: Se não encontrado, gerar com IA
        model = get_gemini_model()
        if not model:
            return jsonify({"error": "Modelo de IA não inicializado"}), 503

        generated_image_url = None
        if image_base64:
            # Upload da imagem original para o Firebase Storage
            filename = f"new_product_{datetime.now(timezone.utc).timestamp()}.jpg"
            generated_image_url = upload_image_to_firebase(image_base64, filename)
            # O prompt para Gemini já está na lógica abaixo
            prompt_gemini = ["Gere nome, uma lista de 3 categorias relevantes (da mais genérica para a mais específica), e uma descrição técnica para o produto principal nesta imagem. Formate a resposta como um JSON com as chaves 'name', 'categories', e 'description'.", img]
        else: # text_query
            prompt_gemini = f"Gere nome, uma lista de 3 categorias relevantes (da mais genérica para a mais específica), e uma descrição técnica para o produto: '{text_query}'. Formate a resposta como um JSON com as chaves 'name', 'categories', e 'description'."

        response = model.generate_content(prompt_gemini)
        cleaned_response_text = response.text.strip().replace('```json', '').replace('```', '')
        product_details = json.loads(cleaned_response_text)

        products_service_url = os.environ.get('SERVICO_PRODUTOS_URL')
        if not products_service_url:
            return jsonify({"error": "URL do serviço de produtos não configurada"}), 500

        new_product_payload = {
            "name": product_details.get('name'),
            "description": product_details.get('description'),
            "category": ",".join(product_details.get('categories', [])),
            "image_url": generated_image_url # Adiciona a URL da imagem gerada
        }

        creation_response = requests.post(
            f"{products_service_url}/api/products/canonical",
            headers={"Authorization": auth_header, "Content-Type": "application/json"},
            json=new_product_payload
        )

        if creation_response.status_code != 201:
            return jsonify({"error": "Falha ao criar produto canônico pendente", "details": creation_response.text}), 500

        return jsonify({"message": "Novo produto gerado pela IA e enviado para aprovação.", "details": creation_response.json()}), 202

    except Exception as e:
        print(f"DEBUG: Exceção no catalog_intake: {e}")
        return jsonify({"error": f"Erro no processo de catalogação: {str(e)}"}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    # Attempt to initialize all clients
    get_db()
    get_producer()
    get_kafka_consumer()
    get_gemini_model()

    env_vars = {
        "GEMINI_API_KEY": "present" if os.environ.get('GEMINI_API_KEY') else "missing",
        "KAFKA_BOOTSTRAP_SERVER": "present" if os.environ.get('KAFKA_BOOTSTRAP_SERVER') else "missing",
        "KAFKA_API_KEY": "present" if os.environ.get('KAFKA_API_KEY') else "missing",
        "KAFKA_API_SECRET": "present" if os.environ.get('KAFKA_API_SECRET') else "missing",
        "FIREBASE_ADMIN_SDK_BASE64": "present" if os.environ.get('FIREBASE_ADMIN_SDK_BASE64') else "missing"
    }

    status = {
        "environment_variables": env_vars,
        "dependencies": {
            "gemini_api": "ok" if not initialization_errors["gemini"] else "error",
            "kafka_consumer": "ok" if not initialization_errors["kafka_consumer"] else "error",
            "kafka_producer": "ok" if not initialization_errors["kafka_producer"] else "error",
            "firestore": "ok" if not initialization_errors["firebase"] else "error"
        },
        "initialization_errors": initialization_errors
    }
    
    all_ok = all(dep_status == "ok" for dep_status in status["dependencies"].values())
    http_status = 200 if all_ok else 503
    
    return jsonify(status), http_status

if __name__ == '__main__':
    app.run(debug=True)
