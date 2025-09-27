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
        mock_auth.verify_id_token.return_value = {'uid': 'test_user_uid', 'admin': False}

        # Mock Firestore transaction
        mock_transaction = MagicMock()
        mock_db.transaction.return_value = mock_transaction
        mock_transaction.update = MagicMock() # Mock the update method on the transaction object

        # Default for Firestore GET (product)
        mock_product_doc = MagicMock()
        mock_product_doc.exists = True
        mock_product_doc.id = "test_product_id"
        mock_product_doc.to_dict.return_value = {
            'name': 'Produto Teste',
            'store_id': 'test_store_id',
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
            'status': 'approved',
            'image_url': 'http://old-image.jpg'
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_product_doc

        # Default for Firestore GET (image subcollection)
        mock_image_doc = MagicMock()
        mock_image_doc.exists = True
        mock_image_doc.id = "test_image_id"
        mock_image_doc.to_dict.return_value = {
            'image_url': 'http://new-primary-image.jpg',
            'source': 'manual_upload',
            'status': 'approved',
            'is_primary': False,
            'created_at': datetime.now(timezone.utc)
        }
        mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value = mock_image_doc

        # Mock for stream() on images subcollection
        mock_db.collection.return_value.document.return_value.collection.return_value.where.return_value.stream.return_value = []

        yield {
            "db": mock_db,
            "producer": mock_producer,
            "auth": mock_auth,
            "check_permission": mock_check_permission,
            "publish_event": mock_publish_event,
            "transaction": mock_transaction # Expose the mock transaction
        }

# --- Test Cases for set_primary_product_image ---

def test_set_primary_image_success_store_product(client, mock_dependencies):
    """Tests successful setting of a primary image for a store product."""
    headers = {"Authorization": "Bearer fake_token"}
    product_id = "test_product_id"
    image_id = "test_image_id"

    # Mock product to have a store_id
    mock_dependencies["db"].collection.return_value.document.return_value.get.return_value.to_dict.return_value = {
        'name': 'Produto Teste',
        'store_id': 'test_store_id',
        'status': 'approved',
        'image_url': 'http://old-image.jpg'
    }
    # Mock image to be set as primary
    mock_dependencies["db"].collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value.to_dict.return_value = {
        'image_url': 'http://new-primary-image.jpg',
        'is_primary': False
    }

    response = client.post(f'/api/products/{product_id}/images/{image_id}/set-primary', headers=headers)

    assert response.status_code == 200
    assert response.json['message'] == "Imagem definida como principal com sucesso."
    mock_dependencies["check_permission"].assert_called_once_with('test_user_uid', 'test_store_id')
    
    # Verify Firestore updates (transactional operations)
    mock_dependencies["db"].transaction.assert_called_once()
    # Check that update was called on the transaction object
    assert mock_dependencies["transaction"].update.call_count == 2 # One for image, one for product
    # Check that publish_event was called
    mock_dependencies["publish_event"].assert_called_once_with(
        'eventos_produtos', 'ProductImageSetPrimary', product_id, {"image_id": image_id, "image_url": "http://new-primary-image.jpg"}
    )

def test_set_primary_image_success_canonical_product_admin(client, mock_dependencies):
    """Tests successful setting of a primary image for a canonical product by an admin."""
    headers = {"Authorization": "Bearer fake_admin_token"}
    product_id = "test_canonical_product_id"
    image_id = "test_image_id"

    # Mock product to be canonical (no store_id)
    mock_dependencies["db"].collection.return_value.document.return_value.get.return_value.to_dict.return_value = {
        'name': 'Produto Canônico Teste',
        'status': 'approved',
        'image_url': 'http://old-canonical-image.jpg'
    }
    # Mock admin user
    mock_dependencies["auth"].verify_id_token.return_value = {'uid': 'admin_uid', 'admin': True}
    # Mock image to be set as primary
    mock_dependencies["db"].collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value.to_dict.return_value = {
        'image_url': 'http://new-primary-canonical-image.jpg',
        'is_primary': False
    }

    response = client.post(f'/api/products/{product_id}/images/{image_id}/set-primary', headers=headers)

    assert response.status_code == 200
    assert response.json['message'] == "Imagem definida como principal com sucesso."
    mock_dependencies["check_permission"].assert_not_called() # No store_id, so no permission check
    mock_dependencies["db"].transaction.assert_called_once()
    assert mock_dependencies["transaction"].update.call_count == 2 # One for image, one for product
    mock_dependencies["publish_event"].assert_called_once_with(
        'eventos_produtos', 'ProductImageSetPrimary', product_id, {"image_id": image_id, "image_url": "http://new-primary-canonical-image.jpg"}
    )

def test_set_primary_image_unauthorized(client, mock_dependencies):
    """Tests setting primary image without authorization."""
    headers = {"Authorization": "Bearer fake_token"}
    product_id = "test_product_id"
    image_id = "test_image_id"

    mock_dependencies["check_permission"].return_value = (False, "not authorized")

    response = client.post(f'/api/products/{product_id}/images/{image_id}/set-primary', headers=headers)

    assert response.status_code == 403
    assert "User is not authorized" in response.json['error']

def test_set_primary_image_product_not_found(client, mock_dependencies):
    """Tests setting primary image for a non-existent product."""
    headers = {"Authorization": "Bearer fake_token"}
    product_id = "non_existent_product_id"
    image_id = "test_image_id"

    mock_dependencies["db"].collection.return_value.document.return_value.get.return_value.exists = False

    response = client.post(f'/api/products/{product_id}/images/{image_id}/set-primary', headers=headers)

    assert response.status_code == 404
    assert "Produto não encontrado." in response.json['error']

def test_set_primary_image_image_not_found(client, mock_dependencies):
    """Tests setting primary image with a non-existent image ID."""
    headers = {"Authorization": "Bearer fake_token"}
    product_id = "test_product_id"
    image_id = "non_existent_image_id"

    mock_dependencies["db"].collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value.exists = False

    response = client.post(f'/api/products/{product_id}/images/{image_id}/set-primary', headers=headers)

    assert response.status_code == 404
    assert "Imagem não encontrada." in response.json['error']

def test_set_primary_image_missing_image_url(client, mock_dependencies):
    """Tests setting primary image when the image document lacks an image_url."""
    headers = {"Authorization": "Bearer fake_token"}
    product_id = "test_product_id"
    image_id = "test_image_id"

    mock_dependencies["db"].collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value.to_dict.return_value = {
        'source': 'manual_upload',
        'status': 'approved',
        'is_primary': False,
        'created_at': datetime.now(timezone.utc)
    }

    response = client.post(f'/api/products/{product_id}/images/{image_id}/set-primary', headers=headers)

    assert response.status_code == 500
    assert "URL da imagem principal não encontrada." in response.json['error']

def test_set_primary_image_canonical_product_non_admin(client, mock_dependencies):
    """Tests setting primary image for a canonical product by a non-admin user."""
    headers = {"Authorization": "Bearer fake_token"}
    product_id = "test_canonical_product_id"
    image_id = "test_image_id"

    # Mock product to be canonical (no store_id)
    mock_dependencies["db"].collection.return_value.document.return_value.get.return_value.to_dict.return_value = {
        'name': 'Produto Canônico Teste',
        'status': 'approved',
        'image_url': 'http://old-canonical-image.jpg'
    }
    # Mock non-admin user
    mock_dependencies["auth"].verify_id_token.return_value = {'uid': 'non_admin_uid', 'admin': False}

    response = client.post(f'/api/products/{product_id}/images/{image_id}/set-primary', headers=headers)

    assert response.status_code == 403
    assert "Only administrators can set primary images for canonical products." in response.json['error']
