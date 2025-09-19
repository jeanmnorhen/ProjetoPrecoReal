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
CORS(app)

# --- Global Clients (Lazy Loaded) ---
db = None
producer = None
kafka_consumer_instance = None
gemini_model = None

# --- Error Tracking ---
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
                    firebase_admin.initialize_app(cred)
                db = firestore.client()
                print("Firebase inicializado com sucesso (lazy).")
            else:
                initialization_errors["firebase"] = "Variável FIREBASE_ADMIN_SDK_BASE64 não encontrada."
        except Exception as e:
            print(f"DEBUG: Firebase initialization failed: {e}")
            initialization_errors["firebase"] = str(e)
    elif not firebase_admin:
        initialization_errors["firebase"] = "Biblioteca firebase_admin não encontrada."
    return db

def get_producer():
    global producer
    if producer is None and Producer:
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
                print("Produtor Kafka inicializado com sucesso (lazy).")
            else:
                initialization_errors["kafka_producer"] = "Variáveis de ambiente do Kafka não encontradas."
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
            kafka_conf = {
                'bootstrap.servers': os.environ.get('KAFKA_BOOTSTRAP_SERVER'),
                'group.id': 'ai_agents_group_v1',
                'auto.offset.reset': 'earliest',
                'security.protocol': 'SASL_SSL',
                'sasl.mechanisms': 'PLAIN',
                'sasl.username': os.environ.get('KAFKA_API_KEY'),
                'sasl.password': os.environ.get('KAFKA_API_SECRET')
            }
            if kafka_conf['bootstrap.servers']:
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

# --- AI Agent Logic ---

def process_image_analysis(task):
    model = get_gemini_model()
    if not model:
        return {"error": "Modelo Gemini não inicializado."}

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
        
        result_data = {
            "task_id": task.get('task_id'),
            "product_name": product_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_image_url": task.get('source_image_url'),
            "status": "completed"
        }

        firestore_db = get_db()
        if firestore_db:
            try:
                doc_ref = firestore_db.collection('ai_results').document(task.get('task_id'))
                doc_ref.set(result_data)
                print(f"Resultado da IA salvo no Firestore para task_id: {task.get('task_id')}")
            except Exception as e:
                print(f"Erro ao salvar resultado no Firestore: {e}")
                result_data["firestore_error"] = str(e)
        else:
            result_data["firestore_error"] = "Firestore not initialized"

        publish_event('resultados_ia', 'ImageAnalysisResult', task.get('task_id'), result_data)

        return {"identified_product": product_name, "details": result_data}

    except Exception as e:
        print(f"Erro na análise de imagem: {e}")
        return {"error": str(e)}

# --- API Endpoints ---

@app.route('/api/agents/consume', methods=['POST', 'GET'])
def consume_tasks():
    get_db() # Ensure Firebase is initialized
    if not firebase_admin or not firebase_admin._apps:
        return jsonify({"error": "Firebase Admin SDK not initialized."}), 500

    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({"error": "Authorization header missing"}), 401

    try:
        id_token = auth_header.split('Bearer ')[1]
        decoded_token = auth.verify_id_token(id_token)
        # You can access user_id with decoded_token['uid'] if needed
        print(f"Firebase ID Token verified for user: {decoded_token['uid']}")
    except Exception as e:
        return jsonify({"error": f"Invalid or expired token: {str(e)}"}), 401

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
