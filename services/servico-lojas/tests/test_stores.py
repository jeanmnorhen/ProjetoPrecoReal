import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Import the module directly to patch its attributes
import sys
import os

# Add the service's root directory to the path to allow for relative imports
service_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if service_root not in sys.path:
    sys.path.insert(0, service_root)

from api import index as api_index

# Mock a StoreLocation record that the SQLAlchemy query would return
class MockStoreLocation:
    def __init__(self, store_id, location_str):
        self.store_id = store_id
        self.location = location_str # The WKT string

# Mock a Point object that to_shape would create
class MockPoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y

@pytest.fixture
def client():
    """A test client for the app."""
    app = api_index.app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture(autouse=True)
def mock_env_vars():
    """Mocks all necessary environment variables."""
    with patch.dict(os.environ, {
        "FIREBASE_ADMIN_SDK_BASE64": "dummy_base64",
        "POSTGRES_POSTGRES_URL": "postgresql://user:pass@host:port/db",
        "KAFKA_BOOTSTRAP_SERVER": "dummy_kafka_server",
        "KAFKA_API_KEY": "dummy_kafka_key",
        "KAFKA_API_SECRET": "dummy_kafka_secret",
        "SERVICO_USUARIOS_URL": "http://mock-user-service",
        "INTERNAL_SERVICE_SECRET": "dummy-internal-secret",
    }):
        yield

@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mocks all external dependencies for all tests."""
    with patch.object(api_index, 'db', MagicMock()) as mock_db, \
         patch.object(api_index, 'db_session', MagicMock()) as mock_db_session, \
         patch.object(api_index, 'producer', MagicMock()) as mock_producer, \
         patch.object(api_index, 'auth', MagicMock()) as mock_auth, \
         patch.object(api_index, 'check_permission', return_value=(True, "ok")) as mock_check_permission, \
         patch.object(api_index, 'publish_event', MagicMock()) as mock_publish_event, \
         patch.object(api_index, 'to_shape', return_value=MockPoint(x=-46.6, y=-23.5)) as mock_to_shape, \
         patch.object(api_index, 'firebase_init_error', None), \
         patch.object(api_index, 'postgres_init_error', None), \
         patch.object(api_index, 'kafka_producer_init_error', None), \
         patch.object(api_index, 'db_init_error', None):

        # --- Configure Default Mock Behaviors ---
        mock_auth.verify_id_token.return_value = {'uid': 'test_user_uid'}
        
        mock_fs_doc = MagicMock()
        mock_fs_doc.exists = True
        mock_fs_doc.id = "test_store_123"
        mock_fs_doc.to_dict.return_value = {
            "name": "Test Store",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_fs_doc
        mock_db_session.execute.return_value = MagicMock()

        yield {
            "db": mock_db,
            "db_session": mock_db_session,
            "producer": mock_producer,
            "auth": mock_auth,
            "check_permission": mock_check_permission,
            "publish_event": mock_publish_event,
            "to_shape": mock_to_shape
        }

# --- Test Cases ---

def test_update_store_success(client, mock_dependencies):
    """Test updating a store by an authorized user."""
    headers = {"Authorization": "Bearer fake_token"}
    update_data = {"name": "Updated Store Name"}

    response = client.put('/api/stores/test_store_123', headers=headers, json=update_data)

    assert response.status_code == 200
    assert response.json['storeId'] == 'test_store_123'
    mock_dependencies["check_permission"].assert_called_once_with('test_user_uid', 'test_store_123')
    mock_dependencies["db"].collection('stores').document('test_store_123').update.assert_called_once()
    mock_dependencies["publish_event"].assert_called_once()

def test_update_store_unauthorized(client, mock_dependencies):
    """Test updating a store by an unauthorized user."""
    headers = {"Authorization": "Bearer fake_token"}
    update_data = {"name": "Updated Store Name"}
    mock_dependencies["check_permission"].return_value = (False, "User is not the owner")

    response = client.put('/api/stores/test_store_123', headers=headers, json=update_data)

    assert response.status_code == 403
    assert "not authorized" in response.json['error']

def test_delete_store_success(client, mock_dependencies):
    """Test deleting a store by an authorized user."""
    headers = {"Authorization": "Bearer fake_token"}

    response = client.delete('/api/stores/test_store_123', headers=headers)

    assert response.status_code == 204
    mock_dependencies["check_permission"].assert_called_once_with('test_user_uid', 'test_store_123')
    mock_dependencies["db"].collection('stores').document('test_store_123').delete.assert_called_once()
    mock_dependencies["publish_event"].assert_called_once()

def test_delete_store_unauthorized(client, mock_dependencies):
    """Test deleting a store by an unauthorized user."""
    headers = {"Authorization": "Bearer fake_token"}
    mock_dependencies["check_permission"].return_value = (False, "User is not the owner")

    response = client.delete('/api/stores/test_store_123', headers=headers)

    assert response.status_code == 403
    assert "not authorized" in response.json['error']

# Keep other tests that were passing

def test_create_store_with_location(client, mock_dependencies):
    """Test creating a store with location data."""
    headers = {"Authorization": "Bearer fake_token"}
    with patch('api.index.requests.post') as mock_post:
        mock_post.return_value.raise_for_status.return_value = None
        store_data = {"name": "New Store", "location": {"latitude": -23.5, "longitude": -46.6}}
        response = client.post('/api/stores', headers=headers, json=store_data)
        assert response.status_code == 201
        assert "storeId" in response.json

def test_get_store_with_location(client, mock_dependencies):
    """Test getting a store who has a location in PostGIS."""
    mock_location_record = MockStoreLocation('test_store_123', 'POINT(-46.6 -23.5)')
    mock_dependencies["db_session"].query.return_value.filter_by.return_value.first.return_value = mock_location_record
    response = client.get('/api/stores/test_store_123')
    assert response.status_code == 200
    assert 'location' in response.json

def test_get_store_not_found(client, mock_dependencies):
    """Test getting a store that does not exist in Firestore."""
    mock_dependencies["db"].collection.return_value.document.return_value.get.return_value.exists = False
    response = client.get('/api/stores/non_existent_store')
    assert response.status_code == 404

def test_health_check_all_ok(client, mock_dependencies):
    """Test health check when all services are up."""
    response = client.get('/api/health')
    assert response.status_code == 200

def test_health_check_pg_error(client, mock_dependencies):
    """Test health check when PostgreSQL is down."""
    mock_dependencies["db_session"].execute.side_effect = Exception("Connection failed")
    response = client.get('/api/health')
    assert response.status_code == 503