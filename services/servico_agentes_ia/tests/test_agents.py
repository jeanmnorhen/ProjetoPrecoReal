import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import os
import sys
import json
import base64

# Import the module directly to patch its attributes
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
import services.servico_agentes_ia.api.index as api_index

@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {
        "FIREBASE_ADMIN_SDK_BASE64": "dummy_firebase_sdk_base64",
        "KAFKA_BOOTSTRAP_SERVER": "dummy_kafka_server",
        "KAFKA_API_KEY": "dummy_kafka_key",
        "KAFKA_API_SECRET": "dummy_kafka_secret",
        "GEMINI_API_KEY": "dummy_gemini_api_key",
        "CRON_SECRET": "dummy_cron_secret",
    }):
        yield

@pytest.fixture(autouse=True)
def mock_all_dependencies():
    # 1. Mock Firebase
    mock_db = MagicMock()

    # 2. Mock Kafka Producer
    mock_producer = MagicMock()

    # 3. Mock Kafka Consumer
    mock_kafka_consumer_instance = MagicMock()

    # 4. Mock Gemini Model
    mock_gemini_model = MagicMock()
    mock_gemini_model.generate_content.return_value.text = "Produto Teste" # Default response

    # 5. Mock PIL.Image.open
    mock_image_open = MagicMock()
    mock_image_open.return_value = MagicMock() # Return a mock image object

    # Apply all mocks using patch.object for global dependencies
    with patch.object(api_index, 'db', mock_db), \
         patch.object(api_index, 'producer', mock_producer), \
         patch.object(api_index, 'kafka_consumer_instance', mock_kafka_consumer_instance), \
         patch.object(api_index, 'gemini_model', mock_gemini_model), \
         patch('PIL.Image.open', mock_image_open), \
         patch.object(api_index, 'initialization_errors', {
             "firebase": None,
             "kafka_producer": None,
             "kafka_consumer": None,
             "gemini": None
         }):

        yield {
            "db": mock_db,
            "producer": mock_producer,
            "kafka_consumer_instance": mock_kafka_consumer_instance,
            "gemini_model": mock_gemini_model,
            "image_open": mock_image_open
        }

@pytest.fixture
def client():
    """A test client for the app."""
    from services.servico_agentes_ia.api.index import app
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
            "GEMINI_API_KEY": "present",
            "KAFKA_BOOTSTRAP_SERVER": "present",
            "KAFKA_API_KEY": "present",
            "KAFKA_API_SECRET": "present",
            "FIREBASE_ADMIN_SDK_BASE64": "present"
        },
        "dependencies": {
            "gemini_api": "ok",
            "kafka_consumer": "ok",
            "kafka_producer": "ok",
            "firestore": "ok"
        },
        "initialization_errors": {
            "firebase": None,
            "kafka_producer": None,
            "kafka_consumer": None,
            "gemini": None
        }
    }

def test_health_check_firebase_error(client, mock_all_dependencies):
    """Test health check when Firebase is not initialized."""
    with patch.object(api_index, 'initialization_errors', {"firebase": "Firebase error", "kafka_producer": None, "kafka_consumer": None, "gemini": None}):
        response = client.get('/api/health')
        assert response.status_code == 503
        assert response.json["dependencies"]["firestore"] == "error"
        assert response.json["initialization_errors"]["firebase"] == "Firebase error"

def test_health_check_kafka_producer_error(client, mock_all_dependencies):
    """Test health check when Kafka producer is not initialized."""
    with patch.object(api_index, 'initialization_errors', {"firebase": None, "kafka_producer": "Kafka producer error", "kafka_consumer": None, "gemini": None}):
        response = client.get('/api/health')
        assert response.status_code == 503
        assert response.json["dependencies"]["kafka_producer"] == "error"
        assert response.json["initialization_errors"]["kafka_producer"] == "Kafka producer error"

def test_health_check_kafka_consumer_error(client, mock_all_dependencies):
    """Test health check when Kafka consumer is not initialized."""
    with patch.object(api_index, 'initialization_errors', {"firebase": None, "kafka_producer": None, "kafka_consumer": "Kafka consumer error", "gemini": None}):
        response = client.get('/api/health')
        assert response.status_code == 503
        assert response.json["dependencies"]["kafka_consumer"] == "error"
        assert response.json["initialization_errors"]["kafka_consumer"] == "Kafka consumer error"

def test_health_check_gemini_error(client, mock_all_dependencies):
    """Test health check when Gemini model is not initialized."""
    with patch.object(api_index, 'initialization_errors', {"firebase": None, "kafka_producer": None, "kafka_consumer": None, "gemini": "Gemini error"}):
        response = client.get('/api/health')
        assert response.status_code == 503
        assert response.json["dependencies"]["gemini_api"] == "error"
        assert response.json["initialization_errors"]["gemini"] == "Gemini error"

def test_consume_tasks_unauthorized(client):
    """Test consume tasks without authorization."""
    response = client.post('/api/agents/consume')
    assert response.status_code == 401
    assert "Unauthorized" in response.json['error']

def test_consume_tasks_success_image_analysis(client, mock_all_dependencies):
    """Test successful consumption of an image analysis task."""
    mock_kafka_consumer_instance = mock_all_dependencies["kafka_consumer_instance"]
    mock_db = mock_all_dependencies["db"]
    mock_producer = mock_all_dependencies["producer"]
    mock_gemini_model = mock_all_dependencies["gemini_model"]

    # Create a dummy base64 image
    dummy_image_bytes = b"dummy_image_data"
    dummy_image_b64 = base64.b64encode(dummy_image_bytes).decode('utf-8')

    # Mock Kafka message for image analysis task
    mock_msg = MagicMock()
    mock_msg.error.return_value = None
    mock_msg.value.return_value = json.dumps({
        "task_type": "image_analysis",
        "task_id": "task123",
        "image_b64": dummy_image_b64,
        "source_image_url": "http://example.com/image.jpg"
    }).encode('utf-8')
    mock_msg.topic.return_value = "tarefas_ia"

    mock_kafka_consumer_instance.consume.return_value = [mock_msg]

    headers = {"Authorization": "Bearer dummy_cron_secret"}
    response = client.post('/api/agents/consume', headers=headers)
    assert response.status_code == 200
    assert response.json['status'] == 'ok'
    assert response.json['messages_processed'] == 1
    assert response.json['results'][0]['suggestion_created'] == 'Produto Teste'
    
    mock_gemini_model.generate_content.assert_called_once()
    mock_db.collection.return_value.add.assert_called_once()
    mock_producer.produce.assert_called_once()
