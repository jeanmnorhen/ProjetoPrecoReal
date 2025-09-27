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
            'updated_at': datetime.now(timezone.utc),
            'status': 'pending_approval' # Default status for new tests
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_product_doc

        # Default for Firestore ADD
        mock_product_doc_ref = MagicMock()
        mock_product_doc_ref.id = "new_product_id_456"
        mock_db.collection.return_value.add.return_value = (MagicMock(), mock_product_doc_ref)

        # Default for Firestore ADD to subcollection (for images)
        mock_image_doc_ref = MagicMock()
        mock_image_doc_ref.id = "new_image_id_789"
        mock_db.collection.return_value.document.return_value.collection.return_value.add.return_value = (MagicMock(), mock_image_doc_ref)

        yield {
            "db": mock_db,
            "producer": mock_producer,
            "auth": mock_auth,
            "check_permission": mock_check_permission,
            "publish_event": mock_publish_event
        }

# --- Test Cases for New Features ---

def test_list_pending_products_success(client, mock_dependencies):
    """Tests successful listing of pending products."""
    mock_dependencies["db"].collection.return_value.where.return_value.stream.return_value = [
        MagicMock(id="prod1", to_dict=lambda: {"name": "Prod1", "status": "pending_approval"}),
        MagicMock(id="prod2", to_dict=lambda: {"name": "Prod2", "status": "pending_approval"}),
    ]
    headers = {"Authorization": "Bearer fake_admin_token"}
    response = client.get('/api/products/pending', headers=headers)
    assert response.status_code == 200
    assert len(response.json['products']) == 2
    assert response.json['products'][0]['id'] == "prod1"

def test_list_pending_products_unauthorized(client, mock_dependencies):
    """Tests listing pending products without authorization."""
    response = client.get('/api/products/pending')
    assert response.status_code == 401

def test_approve_product_success(client, mock_dependencies):
    """Tests successful product approval."""
    headers = {"Authorization": "Bearer fake_admin_token"}
    response = client.post('/api/products/test_product_id/approve', headers=headers)
    assert response.status_code == 200
    assert response.json['message'] == "Produto aprovado com sucesso."
    mock_dependencies["db"].collection.return_value.document.return_value.update.assert_called_once_with({'status': 'approved', 'updated_at': api_index.firestore.SERVER_TIMESTAMP})
    mock_dependencies["publish_event"].assert_called_once_with('eventos_produtos', 'CanonicalProductApproved', 'test_product_id', {'status': 'approved', 'updated_at': api_index.firestore.SERVER_TIMESTAMP})

def test_approve_product_unauthorized(client, mock_dependencies):
    """Tests product approval without authorization."""
    response = client.post('/api/products/test_product_id/approve')
    assert response.status_code == 401

def test_reject_product_success(client, mock_dependencies):
    """Tests successful product rejection."""
    headers = {"Authorization": "Bearer fake_admin_token"}
    response = client.post('/api/products/test_product_id/reject', headers=headers)
    assert response.status_code == 200
    assert response.json['message'] == "Produto rejeitado com sucesso."
    mock_dependencies["db"].collection.return_value.document.return_value.update.assert_called_once_with({'status': 'rejected', 'updated_at': api_index.firestore.SERVER_TIMESTAMP})
    mock_dependencies["publish_event"].assert_called_once_with('eventos_produtos', 'CanonicalProductRejected', 'test_product_id', {'status': 'rejected', 'updated_at': api_index.firestore.SERVER_TIMESTAMP})

def test_reject_product_unauthorized(client, mock_dependencies):
    """Tests product rejection without authorization."""
    response = client.post('/api/products/test_product_id/reject')
    assert response.status_code == 401

def test_add_product_image_success(client, mock_dependencies):
    """Tests successful addition of a product image."""
    headers = {"Authorization": "Bearer fake_admin_token"}
    image_data = {"image_url": "http://example.com/new_image.jpg", "source": "manual_upload"}
    response = client.post('/api/products/test_product_id/images', headers=headers, json=image_data)
    assert response.status_code == 201
    assert response.json['message'] == "Imagem candidata adicionada com sucesso."
    mock_dependencies["db"].collection.return_value.document.return_value.collection.return_value.add.assert_called_once()

def test_add_product_image_unauthorized(client, mock_dependencies):
    """Tests adding a product image without authorization."""
    image_data = {"image_url": "http://example.com/new_image.jpg"}
    response = client.post('/api/products/test_product_id/images', json=image_data)
    assert response.status_code == 401

def test_add_product_image_missing_url(client, mock_dependencies):
    """Tests adding a product image with missing URL."""
    headers = {"Authorization": "Bearer fake_admin_token"}
    image_data = {"source": "manual_upload"}
    response = client.post('/api/products/test_product_id/images', headers=headers, json=image_data)
    assert response.status_code == 400
    assert "image_url é obrigatório." in response.json["error"]
