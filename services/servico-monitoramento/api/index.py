from dotenv import load_dotenv
load_dotenv(dotenv_path='.env.local')

import os
import json
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from confluent_kafka import Consumer, KafkaException

import requests

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=['https://frontend-tester-1foc8lpkl-jeanmnorhens-projects.vercel.app'])

# --- Variáveis globais para erros de inicialização ---1
influxdb_init_error = None
kafka_consumer_init_error = None

# --- InfluxDB Configuration ---
influxdb_client = None
influxdb_write_api = None
influxdb_bucket = None
try:
    influxdb_url = os.environ.get('INFLUXDB_URL')
    influxdb_token = os.environ.get('INFLUXDB_TOKEN')
    influxdb_org = os.environ.get('INFLUXDB_ORG')
    influxdb_bucket = os.environ.get('INFLUXDB_BUCKET')

    if influxdb_url and influxdb_token and influxdb_org and influxdb_bucket:
        influxdb_client = InfluxDBClient(url=influxdb_url, token=influxdb_token, org=influxdb_org)
        influxdb_write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)
        print("InfluxDB inicializado com sucesso.")
    else:
        influxdb_init_error = "Variáveis de ambiente do InfluxDB não encontradas."
        print(influxdb_init_error)
except Exception as e:
    influxdb_init_error = str(e)
    print(f"Erro ao inicializar InfluxDB: {e}")

# --- Kafka Consumer Configuration ---
kafka_consumer_instance = None
if Consumer:
    try:
        kafka_bootstrap_server = os.environ.get('KAFKA_BOOTSTRAP_SERVER')
        if kafka_bootstrap_server:
            kafka_api_key = os.environ.get('KAFKA_API_KEY')
            if kafka_api_key:
                # Cloud Kafka configuration
                print("Configurando consumidor Kafka para ambiente de nuvem (SASL)...")
                kafka_conf = {
                    'bootstrap.servers': kafka_bootstrap_server,
                    'group.id': 'monitoring_service_group_v2',
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
                    'group.id': 'monitoring_service_group_v2',
                    'auto.offset.reset': 'earliest'
                }
            kafka_consumer_instance = Consumer(kafka_conf)
            kafka_consumer_instance.subscribe(['eventos_ofertas'])
            print("Consumidor Kafka inicializado com sucesso.")
        else:
            kafka_consumer_init_error = "Variáveis de ambiente do Kafka não encontradas para o consumidor."
            print(kafka_consumer_init_error)
    except Exception as e:
        kafka_consumer_init_error = str(e)
        print(f"Erro ao inicializar Consumidor Kafka: {e}")
else:
    kafka_consumer_init_error = "Biblioteca confluent_kafka não encontrada."

# --- API Routes ---

@app.route('/api/monitoring/consume', methods=['POST', 'GET'])
def consume_and_write_prices():
    # Security check for cron job
    auth_header = request.headers.get('Authorization')
    cron_secret = os.environ.get('CRON_SECRET')
    if not cron_secret or auth_header != f'Bearer {cron_secret}':
        return jsonify({"error": "Unauthorized"}), 401

    if not influxdb_write_api:
        return jsonify({"error": "InfluxDB não está inicializado."}), 503
    
    if not kafka_consumer_instance:
        return jsonify({"error": "Consumidor Kafka não pôde ser criado.", "details": kafka_consumer_init_error}), 503

    messages_processed = 0
    try:
        msgs = kafka_consumer_instance.consume(num_messages=50, timeout=10.0)
        if not msgs:
            return jsonify({"status": "No new messages to process"}), 200

        points_to_write = []
        for msg in msgs:
            if msg.error():
                print(f"Kafka error: {msg.error()}")
                continue
            
            try:
                event_data = json.loads(msg.value().decode('utf-8'))
                data = event_data.get('data', {})
                
                product_id = data.get('product_id')
                offer_price = data.get('offer_price')
                timestamp = event_data.get('timestamp', datetime.now(timezone.utc).isoformat())

                if product_id and offer_price is not None:
                    point = Point("offer_price") \
                        .tag("product_id", product_id) \
                        .field("price", float(offer_price)) \
                        .time(timestamp)
                    points_to_write.append(point)
                    messages_processed += 1
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                print(f"Erro ao processar mensagem: {e} - Mensagem: {msg.value()}")

        if points_to_write:
            influxdb_write_api.write(bucket=influxdb_bucket, org=os.environ.get('INFLUXDB_ORG'), record=points_to_write)
            print(f"{len(points_to_write)} pontos de preço escritos no InfluxDB.")

    except Exception as e:
        return jsonify({"error": f"Erro durante o consumo de eventos: {e}"}), 500
    finally:
        # O consumidor não deve ser fechado aqui se for uma instância global
        # kafka_consumer_instance.close() # Removido
        pass

    return jsonify({"status": "ok", "messages_processed": messages_processed}), 200



@app.route('/api/monitoring/prices', methods=['GET'])
def get_price_history():
    if not influxdb_client:
        return jsonify({"error": "InfluxDB não está inicializado."}), 503

    product_id = request.args.get('product_id')
    if not product_id:
        return jsonify({"error": "Parâmetro 'product_id' é obrigatório."}), 400

    query_api = influxdb_client.query_api()
    
    # Query for historical data
    history_query = f'''
        from(bucket: "{influxdb_bucket}")
          |> range(start: -30d)
          |> filter(fn: (r) => r._measurement == "offer_price")
          |> filter(fn: (r) => r.product_id == "{product_id}")
          |> sort(columns: ["_time"])
    '''
    
    # Query for aggregations (mean, min, max)
    aggregation_query = f'''
        from(bucket: "{influxdb_bucket}")
          |> range(start: -30d)
          |> filter(fn: (r) => r._measurement == "offer_price")
          |> filter(fn: (r) => r.product_id == "{product_id}")
          |> group()
          |> aggregateWindow(every: 30d, fn: mean, createEmpty: false)
          |> yield(name: "mean")
        
        from(bucket: "{influxdb_bucket}")
          |> range(start: -30d)
          |> filter(fn: (r) => r._measurement == "offer_price")
          |> filter(fn: (r) => r.product_id == "{product_id}")
          |> group()
          |> aggregateWindow(every: 30d, fn: min, createEmpty: false)
          |> yield(name: "min")

        from(bucket: "{influxdb_bucket}")
          |> range(start: -30d)
          |> filter(fn: (r) => r._measurement == "offer_price")
          |> filter(fn: (r) => r.product_id == "{product_id}")
          |> group()
          |> aggregateWindow(every: 30d, fn: max, createEmpty: false)
          |> yield(name: "max")
    '''

    try:
        # Execute history query
        history_tables = query_api.query(history_query, org=os.environ.get('INFLUXDB_ORG'))
        historical_data = []
        for table in history_tables:
            for record in table.records:
                historical_data.append({
                    "time": record.get_time().isoformat(),
                    "price": record.get_value()
                })
        
        # Execute aggregation query
        aggregation_tables = query_api.query(aggregation_query, org=os.environ.get('INFLUXDB_ORG'))
        aggregations = {}
        for table in aggregation_tables:
            for record in table.records:
                if record.get_measurement() == "offer_price": # Ensure it's from our measurement
                    if record.get_field() == "mean":
                        aggregations["mean_price"] = record.get_value()
                    elif record.get_field() == "min":
                        aggregations["min_price"] = record.get_value()
                    elif record.get_field() == "max":
                        aggregations["max_price"] = record.get_value()

        return jsonify({"product_id": product_id, "historical_data": historical_data, "aggregations": aggregations}), 200
    except Exception as e:
        print(f"Error querying InfluxDB: {e}")
        return jsonify({"error": f"Erro ao buscar histórico de preços e agregações: {e}"}), 500

# --- Novas Rotas para o Dashboard Administrativo ---

@app.route('/api/metricas/uso', methods=['GET'])
def get_usage_metrics():
    """Retorna métricas de uso do aplicativo (mock)."""
    # Em um cenário real, estes dados viriam do InfluxDB ou de outro sistema de analytics
    mock_data = {
        "active_users_today": 1502,
        "active_users_week": 8432,
        "searches_per_day": [
            {"date": "2025-09-20", "count": 12034},
            {"date": "2025-09-21", "count": 15234},
            {"date": "2025-09-22", "count": 14890},
            {"date": "2025-09-23", "count": 16012},
            {"date": "2025-09-24", "count": 15589},
        ],
        "top_searched_products": [
            {"product_name": "Leite Integral", "count": 5432},
            {"product_name": "Pão Francês", "count": 4987},
            {"product_name": "Arroz Agulhinha 5kg", "count": 3123},
        ]
    }
    return jsonify(mock_data), 200

@app.route('/api/metricas/precos', methods=['GET'])
def get_price_averages():
    """Retorna médias de preços de produtos para o dashboard (mock)."""
    product_id = request.args.get('product_id', 'default_product')
    region = request.args.get('region', 'default_region')

    # Mock data - em um cenário real, faria uma query complexa no InfluxDB
    mock_data = {
        "product_id": product_id,
        "region": region,
        "average_price_trend": [
            {"date": "2025-07-01", "avg_price": 5.50},
            {"date": "2025-08-01", "avg_price": 5.65},
            {"date": "2025-09-01", "avg_price": 5.60},
        ],
        "competitor_average": 5.75,
        "market_average": 5.68
    }
    return jsonify(mock_data), 200

def get_health_status():
    env_vars = {
        "INFLUXDB_URL": "present" if os.environ.get('INFLUXDB_URL') else "missing",
        "INFLUXDB_TOKEN": "present" if os.environ.get('INFLUXDB_TOKEN') else "missing",
        "INFLUXDB_ORG": "present" if os.environ.get('INFLUXDB_ORG') else "missing",
        "INFLUXDB_BUCKET": "present" if os.environ.get('INFLUXDB_BUCKET') else "missing",
        "KAFKA_BOOTSTRAP_SERVER": "present" if os.environ.get('KAFKA_BOOTSTRAP_SERVER') else "missing",
        "KAFKA_API_KEY": "present" if os.environ.get('KAFKA_API_KEY') else "missing",
        "KAFKA_API_SECRET": "present" if os.environ.get('KAFKA_API_SECRET') else "missing"
    }

    influx_status = "error"
    if influxdb_client:
        try:
            influxdb_client.ping()
            influx_status = "ok"
        except Exception as e:
            influx_status = f"error (ping failed: {e})"
    else:
        influx_status = "error (not initialized)"

    status = {
        "environment_variables": env_vars,
        "dependencies": {
            "influxdb": influx_status,
            "kafka_consumer": "ok" if kafka_consumer_instance else "error"
        },
        "initialization_errors": {
            "influxdb": influxdb_init_error,
            "kafka_consumer": kafka_consumer_init_error
        }
    }
    return status

@app.route('/api/health', methods=['GET'])
def health_check():
    status = get_health_status()
    
    all_ok = (
        all(value == "present" for value in status["environment_variables"].values()) and
        status["dependencies"]["influxdb"] == "ok" and
        status["dependencies"]["kafka_consumer"] == "ok"
    )
    http_status = 200 if all_ok else 503
    
    return jsonify(status), http_status

@app.route('/api/metricas/gerais', methods=['GET'])
def get_general_metrics():
    # URLs from environment variables (set in .env.local)
    servico_usuarios_url = os.environ.get('SERVICO_USUARIOS_URL')
    servico_produtos_url = os.environ.get('SERVICO_PRODUTOS_URL')
    
    criticas_pendentes = 0
    produtos_catalogo = 0
    errors = {}

    # Get pending critiques count
    if servico_usuarios_url:
        try:
            # Assuming the /api/criticas endpoint returns a list
            response = requests.get(f"{servico_usuarios_url}/api/criticas", timeout=5)
            if response.ok:
                criticas_pendentes = len(response.json())
            else:
                errors['criticas_service'] = f"Error {response.status_code}"
        except requests.RequestException as e:
            errors['criticas_service'] = str(e)
    else:
        errors['criticas_service'] = "SERVICO_USUARIOS_URL not set"

    # Get canonical products count
    if servico_produtos_url:
        try:
            # Assuming the /api/products endpoint returns a list under a 'products' key
            response = requests.get(f"{servico_produtos_url}/api/products", timeout=5)
            if response.ok:
                produtos_catalogo = len(response.json().get('products', []))
            else:
                errors['produtos_service'] = f"Error {response.status_code}"
        except requests.RequestException as e:
            errors['produtos_service'] = str(e)
    else:
        errors['produtos_service'] = "SERVICO_PRODUTOS_URL not set"

    return jsonify({
        "pending_critiques_count": criticas_pendentes,
        "canonical_products_count": produtos_catalogo,
        "errors": errors if errors else "none"
    })

if __name__ == '__main__':
    app.run(debug=True)
