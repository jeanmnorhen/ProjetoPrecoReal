import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import os
import sys
import json

# Import the module directly to patch its attributes
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
import sys
import os
# Adiciona o diretório raiz do serviço ao sys.path
service_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if service_root not in sys.path:
    sys.path.insert(0, service_root)

from api import index as api_index

@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {
        "FIREBASE_ADMIN_SDK_BASE64": "dummy_firebase_sdk_base64",
        "ELASTIC_HOST": "http://mock-es:9200",
        "ELASTIC_API_KEY": "dummy_es_api_key",
        "KAFKA_BOOTSTRAP_SERVER": "dummy_kafka_server",
        "KAFKA_API_KEY": "dummy_kafka_key",
        "KAFKA_API_SECRET": "dummy_kafka_secret",
        "CRON_SECRET": "dummy_cron_secret",
    }):
        yield

@pytest.fixture(autouse=True)
def mock_all_dependencies():
    # 1. Mock Firebase
    mock_db = MagicMock()

    # 2. Mock Elasticsearch
    mock_es = MagicMock()
    mock_es.ping.return_value = True # Default to ping success

    # 3. Mock Kafka Consumer
    mock_kafka_consumer_instance = MagicMock()

    # Apply all mocks using patch.object for global dependencies
    with patch.object(api_index, 'db', mock_db), \
         patch.object(api_index, 'es', mock_es), \
         patch.object(api_index, 'kafka_consumer_instance', mock_kafka_consumer_instance), \
         patch.object(api_index, 'firebase_init_error', None), \
         patch.object(api_index, 'es_init_error', None), \
         patch.object(api_index, 'kafka_consumer_init_error', None):

        yield {
            "db": mock_db,
            "es": mock_es,
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
            "FIREBASE_ADMIN_SDK_BASE64": "present",
            "ELASTIC_HOST": "present",
            "ELASTIC_API_KEY": "present",
            "KAFKA_BOOTSTRAP_SERVER": "present",
            "KAFKA_API_KEY": "present",
            "KAFKA_API_SECRET": "present"
        },
        "dependencies": {
            "firestore": "ok",
            "elasticsearch": "ok",
            "kafka_consumer": "ok"
        },
        "initialization_errors": {
            "firestore": None,
            "elasticsearch": None,
            "kafka_consumer": None
        }
    }

def test_health_check_es_error(client, mock_all_dependencies):
    """Test health check when Elasticsearch is down."""
    mock_all_dependencies["es"].ping.return_value = False
    response = client.get('/api/health')
    assert response.status_code == 503
    assert response.json["dependencies"]["elasticsearch"] == "error (ping failed)"

def test_health_check_kafka_error(client, mock_all_dependencies):
    """Test health check when Kafka consumer is not initialized."""
    with patch.object(api_index, 'kafka_consumer_instance', new=None), \
         patch.object(api_index, 'kafka_consumer_init_error', "Variáveis de ambiente do Kafka não encontradas para o consumidor."):
        response = client.get('/api/health')
        assert response.status_code == 503
        assert response.json["dependencies"]["kafka_consumer"] == "error"
        assert response.json["initialization_errors"]["kafka_consumer"] == "Variáveis de ambiente do Kafka não encontradas para o consumidor."

def test_search_success(client, mock_all_dependencies):
    """Test a successful search query."""
    mock_all_dependencies["es"].search.return_value = {
        'hits': {
            'hits': [
                {'_id': 'user1', '_index': 'users', '_source': {'name': 'Test User'}},
                {'_id': 'prod1', '_index': 'products', '_source': {'name': 'Test Product'}}
            ]
        }
    }
    response = client.get('/api/search?q=test')
    assert response.status_code == 200
    assert len(response.json['results']) == 2
    assert response.json['results'][0]['id'] == 'user1'
    assert response.json['results'][0]['type'] == 'users'

def test_search_no_query(client):
    """Test search without a query parameter."""
    response = client.get('/api/search')
    assert response.status_code == 400
    assert "Parâmetro 'q' (query) é obrigatório." in response.json['error']

def test_reindex_success(client, mock_all_dependencies):
    """Test successful reindexing."""
    mock_db = mock_all_dependencies["db"]
    mock_es = mock_all_dependencies["es"]

    # Mock Firestore stream
    mock_doc1 = MagicMock()
    mock_doc1.id = "doc1"
    mock_doc1.to_dict.return_value = {"field1": "value1"}
    mock_doc2 = MagicMock()
    mock_doc2.id = "doc2"
    mock_doc2.to_dict.return_value = {"field2": "value2"}
    
    mock_db.collection.return_value.stream.return_value = [mock_doc1, mock_doc2]

    response = client.post('/api/search/reindex')
    assert response.status_code == 200
    assert response.json['status'] == 'Reindexação concluída'
    assert response.json['details']['users']['indexed_documents'] == 2
    mock_es.index.assert_called()

def test_consume_events_unauthorized(client):
    """Test consume events without authorization."""
    response = client.post('/api/search/consume')
    assert response.status_code == 401
    assert "Unauthorized" in response.json['error']

def test_consume_events_success(client, mock_all_dependencies):
    """Test successful consumption of Kafka events."""
    mock_kafka_consumer_instance = mock_all_dependencies["kafka_consumer_instance"]
    mock_es = mock_all_dependencies["es"]

    # Mock Kafka messages
    mock_msg1 = MagicMock()
    mock_msg1.error.return_value = None
    mock_msg1.value.return_value = json.dumps({"event_type": "UserCreated", "user_id": "user1", "data": {"name": "New User"}}).encode('utf-8')
    mock_msg1.topic.return_value = "eventos_usuarios"

    mock_msg2 = MagicMock()
    mock_msg2.error.return_value = None
    mock_msg2.value.return_value = json.dumps({"event_type": "ProductUpdated", "product_id": "prod1", "data": {"price": 10.0}}).encode('utf-8')
    mock_msg2.topic.return_value = "eventos_produtos"

    mock_kafka_consumer_instance.consume.return_value = [mock_msg1, mock_msg2] # Retorna todas as mensagens de uma vez

    headers = {"Authorization": "Bearer dummy_cron_secret"}
    response = client.post('/api/search/consume', headers=headers)
    assert response.status_code == 200
    assert response.json['status'] == 'ok'
    assert response.json['messages_processed'] == 2
    assert mock_es.index.call_count == 2 # Adicionar esta asserção
