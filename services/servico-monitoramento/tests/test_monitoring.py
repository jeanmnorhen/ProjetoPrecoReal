import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import os
import sys
import json

# Add the service's root directory to the path to allow for relative imports
service_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if service_root not in sys.path:
    sys.path.insert(0, service_root)

from api import index as api_index

@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {
        "INFLUXDB_URL": "http://mock-influxdb:8086",
        "INFLUXDB_TOKEN": "dummy_influxdb_token",
        "INFLUXDB_ORG": "dummy_influxdb_org",
        "INFLUXDB_BUCKET": "dummy_influxdb_bucket",
        "KAFKA_BOOTSTRAP_SERVER": "dummy_kafka_server",
        "KAFKA_API_KEY": "dummy_kafka_key",
        "KAFKA_API_SECRET": "dummy_kafka_secret",
        "CRON_SECRET": "dummy_cron_secret",
    }):
        yield

@pytest.fixture(autouse=True)
def mock_all_dependencies():
    # 1. Mock InfluxDB
    mock_influxdb_client = MagicMock()
    mock_influxdb_client.ping.return_value = None # Default to ping success
    mock_influxdb_write_api = MagicMock()

    # 2. Mock Kafka Consumer
    mock_kafka_consumer_instance = MagicMock()

    # Apply all mocks using patch.object for global dependencies
    with patch.object(api_index, 'influxdb_client', mock_influxdb_client), \
         patch.object(api_index, 'influxdb_write_api', mock_influxdb_write_api), \
         patch.object(api_index, 'kafka_consumer_instance', mock_kafka_consumer_instance), \
         patch.object(api_index, 'influxdb_init_error', None), \
         patch.object(api_index, 'kafka_consumer_init_error', None):

        yield {
            "influxdb_client": mock_influxdb_client,
            "influxdb_write_api": mock_influxdb_write_api,
            "kafka_consumer_instance": mock_kafka_consumer_instance
        }

@pytest.fixture
def client():
    """A test client for the app."""
    from api.index import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# --- Test Cases ---

def test_health_check_all_ok(client, mock_all_dependencies):
    """Test health check when all services are up."""
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json == {
        "environment_variables": {
            "INFLUXDB_URL": "present",
            "INFLUXDB_TOKEN": "present",
            "INFLUXDB_ORG": "present",
            "INFLUXDB_BUCKET": "present",
            "KAFKA_BOOTSTRAP_SERVER": "present",
            "KAFKA_API_KEY": "present",
            "KAFKA_API_SECRET": "present"
        },
        "dependencies": {
            "influxdb": "ok",
            "kafka_consumer": "ok"
        },
        "initialization_errors": {
            "influxdb": None,
            "kafka_consumer": None
        }
    }

def test_health_check_influxdb_error(client, mock_all_dependencies):
    """Test health check when InfluxDB is down."""
    mock_all_dependencies["influxdb_client"].ping.side_effect = Exception("InfluxDB connection error")
    response = client.get('/api/health')
    assert response.status_code == 503
    assert "error (ping failed" in response.json["dependencies"]["influxdb"]

def test_health_check_kafka_error(client, mock_all_dependencies):
    """Test health check when Kafka consumer is not initialized."""
    with patch.object(api_index, 'kafka_consumer_instance', new=None), \
         patch.object(api_index, 'kafka_consumer_init_error', "Kafka failed to initialize"):
        response = client.get('/api/health')
        assert response.status_code == 503
        assert response.json["dependencies"]["kafka_consumer"] == "error"
        assert response.json["initialization_errors"]["kafka_consumer"] is not None

def test_consume_and_write_prices_unauthorized(client):
    """Test consume events without authorization."""
    response = client.post('/api/monitoring/consume')
    assert response.status_code == 401
    assert "Unauthorized" in response.json['error']

def test_consume_and_write_prices_success(client, mock_all_dependencies):
    """Test successful consumption and writing of Kafka events to InfluxDB."""
    mock_kafka_consumer_instance = mock_all_dependencies["kafka_consumer_instance"]
    mock_influxdb_write_api = mock_all_dependencies["influxdb_write_api"]

    # Mock Kafka messages
    mock_msg1 = MagicMock()
    mock_msg1.error.return_value = None
    mock_msg1.value.return_value = json.dumps({"data": {"product_id": "prod1", "offer_price": 10.50}, "timestamp": datetime.now(timezone.utc).isoformat()}).encode('utf-8')
    mock_msg1.topic.return_value = "eventos_ofertas"

    mock_msg2 = MagicMock()
    mock_msg2.error.return_value = None
    mock_msg2.value.return_value = json.dumps({"data": {"product_id": "prod2", "offer_price": 20.75}, "timestamp": datetime.now(timezone.utc).isoformat()}).encode('utf-8')
    mock_msg2.topic.return_value = "eventos_ofertas"

    mock_kafka_consumer_instance.consume.return_value = [mock_msg1, mock_msg2]

    headers = {"Authorization": "Bearer dummy_cron_secret"}
    response = client.post('/api/monitoring/consume', headers=headers)
    assert response.status_code == 200
    assert response.json['status'] == 'ok'
    assert response.json['messages_processed'] == 2
    mock_influxdb_write_api.write.assert_called_once()

def test_get_price_history_success(client, mock_all_dependencies):
    """Test successful retrieval of price history."""
    mock_influxdb_client = mock_all_dependencies["influxdb_client"]
    mock_query_api = MagicMock()
    mock_influxdb_client.query_api.return_value = mock_query_api

    # Mock InfluxDB query results
    mock_record1 = MagicMock()
    mock_record1.get_time.return_value = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    mock_record1.get_value.return_value = 10.0
    mock_record2 = MagicMock()
    mock_record2.get_time.return_value = datetime(2023, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
    mock_record2.get_value.return_value = 12.0

    mock_table_history = MagicMock()
    mock_table_history.records = [mock_record1, mock_record2]

    mock_record_mean = MagicMock()
    mock_record_mean.get_measurement.return_value = "offer_price"
    mock_record_mean.get_field.return_value = "mean"
    mock_record_mean.get_value.return_value = 11.0

    mock_record_min = MagicMock()
    mock_record_min.get_measurement.return_value = "offer_price"
    mock_record_min.get_field.return_value = "min"
    mock_record_min.get_value.return_value = 10.0

    mock_record_max = MagicMock()
    mock_record_max.get_measurement.return_value = "offer_price"
    mock_record_max.get_field.return_value = "max"
    mock_record_max.get_value.return_value = 12.0

    mock_table_aggregations = MagicMock()
    mock_table_aggregations.records = [mock_record_mean, mock_record_min, mock_record_max]

    mock_query_api.query.side_effect = [[mock_table_history], [mock_table_aggregations]]

    response = client.get('/api/monitoring/prices?product_id=prod1')
    assert response.status_code == 200
    assert response.json['product_id'] == 'prod1'
    assert len(response.json['historical_data']) == 2
    assert response.json['aggregations']['mean_price'] == 11.0

def test_get_price_history_no_product_id(client):
    """Test retrieval of price history without product_id."""
    response = client.get('/api/monitoring/prices')
    assert response.status_code == 400
    assert "Parâmetro 'product_id' é obrigatório." in response.json['error']

# --- Testes para as Novas Rotas do Dashboard ---

def test_get_usage_metrics(client):
    """Testa o endpoint de métricas de uso."""
    response = client.get('/api/metricas/uso')
    assert response.status_code == 200
    data = response.json
    assert "active_users_today" in data
    assert "searches_per_day" in data
    assert "top_searched_products" in data
    assert isinstance(data['searches_per_day'], list)

def test_get_price_averages(client):
    """Testa o endpoint de médias de preços."""
    # Teste sem parâmetros
    response = client.get('/api/metricas/precos')
    assert response.status_code == 200
    data = response.json
    assert data['product_id'] == 'default_product'
    assert "average_price_trend" in data

    # Teste com parâmetros
    response = client.get('/api/metricas/precos?product_id=prod123&region=sul')
    assert response.status_code == 200
    data = response.json
    assert data['product_id'] == 'prod123'
    assert data['region'] == 'sul'
