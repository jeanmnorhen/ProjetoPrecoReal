import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from firebase_admin import firestore
import os
import sys

# Add the service's root directory to the path to allow for relative imports
service_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if service_root not in sys.path:
    sys.path.insert(0, service_root)

# Now we can import the app and its dependencies
from api import index as api_index

@pytest.fixture(autouse=True)
def mock_env_vars():
    """Mocks all necessary environment variables."""
    with patch.dict(os.environ, {
        "FIREBASE_ADMIN_SDK_BASE64": "mock_firebase_sdk_base64",
        "KAFKA_BOOTSTRAP_SERVER": "dummy_kafka_server",
        "KAFKA_API_KEY": "dummy_kafka_key",
        "KAFKA_API_SECRET": "dummy_kafka_secret",
        "SERVICO_USUARIOS_URL": "http://mock-user-service", # Needed for check_permission
    }):
        yield

@pytest.fixture
def client():
    """A test client for the app."""
    app = api_index.app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mocks all external dependencies for all tests."""
    with patch.object(api_index, 'db', MagicMock()) as mock_db, \
         patch.object(api_index, 'producer', MagicMock()) as mock_producer, \
         patch.object(api_index, 'auth', MagicMock()) as mock_auth, \
         patch.object(api_index, 'check_permission', return_value=(True, "ok")) as mock_check_permission, \
         patch.object(api_index, 'publish_event', MagicMock()) as mock_publish_event, \
         patch.object(api_index, 'firebase_init_error', None), \
         patch.object(api_index, 'kafka_producer_init_error', None):

        # --- Configure Default Mock Behaviors ---

        # Default for auth
        mock_auth.verify_id_token.return_value = {'uid': 'test_user_uid'}

        # Default for Firestore GET
        mock_product_doc = MagicMock()
        mock_product_doc.exists = True
        mock_product_doc.id = "test_product_id"
        mock_product_doc.to_dict.return_value = {
            'name': 'Produto Teste',
            'store_id': 'test_store_id',
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_product_doc

        # Default for Firestore ADD
        mock_product_doc_ref = MagicMock()
        mock_product_doc_ref.id = "new_product_id_456"
        mock_db.collection.return_value.add.return_value = (MagicMock(), mock_product_doc_ref)

        yield {
            "db": mock_db,
            "producer": mock_producer,
            "auth": mock_auth,
            "check_permission": mock_check_permission,
            "publish_event": mock_publish_event
        }

# --- Test Cases ---

def test_create_canonical_product_success(client, mock_dependencies):
    """Tests successful canonical product creation."""
    headers = {"Authorization": "Bearer fake_admin_token"}
    new_product_data = {
        "name": "Produto Canônico Teste",
        "category": "Teste",
        "description": "Descrição do produto canônico."
    }

    response = client.post("/api/products/canonical", headers=headers, json=new_product_data)

    assert response.status_code == 201
    assert response.json["productId"] == "new_product_id_456"
    mock_dependencies["db"].collection('products').add.assert_called_once()
    mock_dependencies["publish_event"].assert_called_once_with('eventos_produtos', 'CanonicalProductPending', 'new_product_id_456', {
        'name': 'Produto Canônico Teste',
        'category': 'Teste',
        'description': 'Descrição do produto canônico.',
        'status': 'pending_approval',
        'created_at': api_index.firestore.SERVER_TIMESTAMP,
        'updated_at': api_index.firestore.SERVER_TIMESTAMP
    })

def test_create_canonical_product_unauthorized(client, mock_dependencies):
    """Tests canonical product creation with invalid/missing token."""
    mock_dependencies["auth"].verify_id_token.side_effect = Exception("Invalid token")
    headers = {"Authorization": "Bearer invalid_token"}
    new_product_data = {"name": "Produto Canônico Teste"}

    response = client.post("/api/products/canonical", headers=headers, json=new_product_data)

    assert response.status_code == 401
    assert "Invalid or expired token" in response.json["error"]

def test_get_product_success(client, mock_dependencies):
    """Tests retrieving an existing product."""
    response = client.get('/api/products/test_product_id')
    assert response.status_code == 200
    assert response.json['id'] == 'test_product_id'
    assert response.json['name'] == 'Produto Teste'

def test_get_product_not_found(client, mock_dependencies):
    """Tests retrieving a non-existent product."""
    mock_dependencies["db"].collection.return_value.document.return_value.get.return_value.exists = False
    response = client.get('/api/products/non_existent_product')
    assert response.status_code == 404

def test_update_product_success(client, mock_dependencies):
    """Tests updating a product by an authorized user."""
    headers = {"Authorization": "Bearer fake_token"}
    update_data = {"price": 89.99}
    
    response = client.put('/api/products/test_product_id', headers=headers, json=update_data)

    assert response.status_code == 200
    assert response.json['productId'] == 'test_product_id'
    mock_dependencies["check_permission"].assert_called_once_with('test_user_uid', 'test_store_id')
    mock_dependencies["db"].collection.return_value.document.return_value.update.assert_called_once()
    mock_dependencies["publish_event"].assert_called_once()

def test_update_product_unauthorized(client, mock_dependencies):
    """Tests updating a product by an unauthorized user."""
    mock_dependencies["check_permission"].return_value = (False, "not owner")
    headers = {"Authorization": "Bearer fake_token"}
    update_data = {"price": 89.99}

    response = client.put('/api/products/test_product_id', headers=headers, json=update_data)

    assert response.status_code == 403
    assert "not authorized" in response.json["error"]

def test_delete_product_success(client, mock_dependencies):
    """Tests deleting a product by an authorized user."""
    headers = {"Authorization": "Bearer fake_token"}
    
    response = client.delete('/api/products/test_product_id', headers=headers)

    assert response.status_code == 204
    mock_dependencies["check_permission"].assert_called_once_with('test_user_uid', 'test_store_id')
    mock_dependencies["db"].collection.return_value.document.return_value.delete.assert_called_once()
    mock_dependencies["publish_event"].assert_called_once()

def test_delete_product_unauthorized(client, mock_dependencies):
    """Tests deleting a product by an unauthorized user."""
    mock_dependencies["check_permission"].return_value = (False, "not owner")
    headers = {"Authorization": "Bearer fake_token"}

    response = client.delete('/api/products/test_product_id', headers=headers)

    assert response.status_code == 403
    assert "not authorized" in response.json["error"]

def test_health_check_all_ok(client):
    """Test health check when all services are up."""
    with patch.object(api_index, 'get_health_status', return_value={
        "dependencies": {"firestore": "ok", "kafka_producer": "ok"},
        "initialization_errors": {"firestore": None, "kafka_producer": None},
        "environment_variables": {"FIREBASE_ADMIN_SDK_BASE64": "present", "KAFKA_BOOTSTRAP_SERVER": "present", "KAFKA_API_KEY": "present", "KAFKA_API_SECRET": "present"}
    }):
        response = client.get('/api/health')
        assert response.status_code == 200
        assert response.json["dependencies"]["firestore"] == "ok"