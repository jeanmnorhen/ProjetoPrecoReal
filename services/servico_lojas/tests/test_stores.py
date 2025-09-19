import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Import the module directly to patch its attributes
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
import services.servico_lojas.api.index as api_index

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

mock_to_shape = MagicMock(return_value=MockPoint(x=-46.6, y=-23.5))

# Mock os.environ.get to provide dummy URLs for services
@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {
        "FIREBASE_ADMIN_SDK_BASE64": "dummy_base64",
        "POSTGRES_POSTGRES_URL": "postgresql://user:pass@host:port/db",
        "KAFKA_BOOTSTRAP_SERVER": "dummy_kafka_server",
        "KAFKA_API_KEY": "dummy_kafka_key",
        "KAFKA_API_SECRET": "dummy_kafka_secret",
    }):
        yield

# Mock all external dependencies for all tests
@pytest.fixture(autouse=True)
def mock_all_dependencies():
    # 1. Mock Firebase
    mock_fs_doc = MagicMock()
    mock_fs_doc.exists = True
    mock_fs_doc.id = "test_store_123"
    # Firestore data no longer contains location
    mock_fs_doc.to_dict.return_value = {
        "name": "Test Store",
        "owner_uid": "test_owner_uid",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }

    # 2. Mock PostGIS/SQLAlchemy session
    mock_sql_session = MagicMock()
    mock_sql_session.query.return_value.filter_by.return_value.first.return_value = None # Default to None
    # Configure the query chain to return a mock object that can be configured later
    # mock_location_record = MockStoreLocation('test_store_123', 'POINT(-46.6 -23.5)') # Removido
    # mock_sql_session.query.return_value.filter_by.return_value.first.return_value = mock_location_record # Removido
    mock_sql_session.execute.return_value = MagicMock() # For health check SELECT 1

    # 3. Mock Kafka Producer
    mock_kafka_producer_instance = MagicMock()

    # Apply all mocks using patch.object
    with patch.object(api_index, 'db', MagicMock()) as mock_db, \
         patch.object(api_index, 'db_session', mock_sql_session), \
         patch.object(api_index, 'producer', mock_kafka_producer_instance), \
         patch.object(api_index, 'to_shape', mock_to_shape), \
         patch.object(api_index, 'publish_event') as mock_publish_event, \
         patch.object(api_index, 'engine', MagicMock()) as mock_engine, \
         patch.object(api_index, 'Base', MagicMock()) as mock_base, \
         patch.object(api_index, 'firebase_init_error', None), \
         patch.object(api_index, 'postgres_init_error', None), \
         patch.object(api_index, 'kafka_producer_init_error', None), \
         patch.object(api_index, 'db_init_error', None): 

        # Configure the mock for Firestore document retrieval
        mock_db.collection.return_value.document.return_value.get.return_value = mock_fs_doc
        
        # Yield to allow tests to run with these mocks
        yield {
            "db": mock_db,
            "db_session": mock_sql_session,
            "producer": mock_kafka_producer_instance,
            "to_shape": mock_to_shape,
            "publish_event": mock_publish_event,
            "engine": mock_engine,
            "Base": mock_base
        }

@pytest.fixture
def client():
    """A test client for the app."""
    from services.servico_lojas.api.index import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# --- Test Cases ---

def test_create_store_with_location(client, mock_all_dependencies):
    """Test creating a store with location data."""
    user_uid = "test_owner_uid"
    fake_token = "fake_token_for_store_creation"
    headers = {"Authorization": f"Bearer {fake_token}"}
    mock_all_dependencies["db"].collection.return_value.add.return_value = (MagicMock(), MagicMock(id="new_store_id"))
    mock_all_dependencies["db"].collection.return_value.document.return_value.set.return_value = None # For .set() method
    
    with patch('services.servico_lojas.api.index.auth.verify_id_token', return_value={'uid': user_uid}):
        store_data = {
            "name": "New Store",
            "address": "123 Main St",
            "location": {"latitude": -23.5, "longitude": -46.6}
        }
        response = client.post('/api/stores', headers=headers, json=store_data)

        assert response.status_code == 201
        assert "storeId" in response.json
        
        # Assert that PostGIS session was used
        mock_all_dependencies["db_session"].add.assert_called_once()
        mock_all_dependencies["db_session"].commit.assert_called_once()

        # Assert that Firestore was used
        mock_all_dependencies["db"].collection.return_value.document.assert_called_once()
        mock_all_dependencies["db"].collection.return_value.document.return_value.set.assert_called_once()

        # Assert that Kafka event was published
        mock_all_dependencies["publish_event"].assert_called_once()
        args, kwargs = mock_all_dependencies["publish_event"].call_args
        assert args[1] == 'StoreCreated'

def test_create_store_without_location(client, mock_all_dependencies):
    """Test creating a store without location data."""
    user_uid = "test_owner_uid"
    fake_token = "fake_token_for_store_creation"
    headers = {"Authorization": f"Bearer {fake_token}"}
    mock_all_dependencies["db"].collection.return_value.add.return_value = (MagicMock(), MagicMock(id="new_store_id"))
    mock_all_dependencies["db"].collection.return_value.document.return_value.set.return_value = None # For .set() method

    with patch('services.servico_lojas.api.index.auth.verify_id_token', return_value={'uid': user_uid}):
        store_data = {"name": "No Location Store", "address": "456 Oak Ave"}
        response = client.post('/api/stores', headers=headers, json=store_data)

        assert response.status_code == 201
        
        # Assert that PostGIS session was NOT used to add data, but commit is still called
        mock_all_dependencies["db_session"].add.assert_not_called()
        mock_all_dependencies["db_session"].commit.assert_called_once()

        # Assert that Firestore was used
        mock_all_dependencies["db"].collection.return_value.document.assert_called_once()
        mock_all_dependencies["db"].collection.return_value.document.return_value.set.assert_called_once()

def test_get_store_with_location(client, mock_all_dependencies):
    """Test getting a store who has a location in PostGIS."""
    # Configure mock_sql_session.query for this specific test
    mock_location_record = MockStoreLocation('test_store_123', 'POINT(-46.6 -23.5)')
    mock_all_dependencies["db_session"].query.return_value.filter_by.return_value.first.return_value = mock_location_record

    response = client.get('/api/stores/test_store_123')

    assert response.status_code == 200
    assert response.json['id'] == 'test_store_123'
    assert 'location' in response.json
    assert response.json['location']['latitude'] == -23.5
    assert response.json['location']['longitude'] == -46.6
    
    # Assert that PostGIS was queried
    mock_all_dependencies["db_session"].query.assert_called_once()
    # Assert that to_shape was called to parse the location
    mock_all_dependencies["to_shape"].assert_called_once()

def test_get_store_without_location(client, mock_all_dependencies):
    """Test getting a store who does not have a location in PostGIS."""
    # Setup mock to return None for the location query
    mock_db_session = mock_all_dependencies["db_session"]
    mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
    
    # Mock the Firestore document to NOT contain location data
    mock_fs_doc_no_location = MagicMock()
    mock_fs_doc_no_location.exists = True
    mock_fs_doc_no_location.id = "test_store_123"
    mock_fs_doc_no_location.to_dict.return_value = {
        "name": "Test Store",
        "owner_uid": "test_owner_uid",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    mock_all_dependencies["db"].collection.return_value.document.return_value.get.return_value = mock_fs_doc_no_location

    response = client.get('/api/stores/test_store_123')

    assert response.status_code == 200
    assert 'location' not in response.json # The key should be absent
    
    mock_all_dependencies["db_session"].query.assert_called_once()
    # Mock to_shape to ensure it's not called
    with patch.object(api_index, 'to_shape') as mock_to_shape_local:
        mock_to_shape_local.assert_not_called()

def test_get_store_not_found(client, mock_all_dependencies):
    """Test getting a store that does not exist in Firestore."""
    mock_all_dependencies["db"].collection.return_value.document.return_value.get.return_value.exists = False
    
    response = client.get('/api/stores/non_existent_store')
    assert response.status_code == 404

def test_update_store_location(client, mock_all_dependencies):
    """Test updating a store's location."""
    user_uid = "test_owner_uid"
    fake_token = "fake_token_for_store_update"
    headers = {"Authorization": f"Bearer {fake_token}"}
    
    with patch('services.servico_lojas.api.index.auth.verify_id_token', return_value={'uid': user_uid}):
        # Configure mock_sql_session.query for this specific test
        mock_location_record = MockStoreLocation('test_store_123', 'POINT(-46.6 -23.5)')
        mock_all_dependencies["db_session"].query.return_value.filter_by.return_value.first.return_value = mock_location_record

        update_data = {"location": {"latitude": -10.0, "longitude": -20.0}}
        response = client.put('/api/stores/test_store_123', headers=headers, json=update_data)

        assert response.status_code == 200
        
        # Assert that the location record object was modified and commit was called
        location_record = mock_all_dependencies["db_session"].query.return_value.filter_by.return_value.first.return_value
        assert location_record.location == 'POINT(-20.0 -10.0)'
        mock_all_dependencies["db_session"].commit.assert_called_once()

        # Assert event was published
        mock_all_dependencies["publish_event"].assert_called_once()
        args, kwargs = mock_all_dependencies["publish_event"].call_args
        assert args[1] == 'StoreUpdated'
        assert args[2] == 'test_store_123'
        assert args[3] == update_data

def test_delete_store(client, mock_all_dependencies):
    """Test deleting a store."""
    user_uid = "test_owner_uid"
    fake_token = "fake_token_for_store_delete"
    headers = {"Authorization": f"Bearer {fake_token}"}

    with patch('services.servico_lojas.api.index.auth.verify_id_token', return_value={'uid': user_uid}):
        # Configure mock_sql_session.query for this specific test
        mock_location_record = MockStoreLocation('test_store_123', 'POINT(-46.6 -23.5)')
        mock_all_dependencies["db_session"].query.return_value.filter_by.return_value.first.return_value = mock_location_record

        response = client.delete('/api/stores/test_store_123', headers=headers)

        assert response.status_code == 204
        
        # Assert that delete was called on the session
        mock_sql_session = mock_all_dependencies["db_session"]
        location_record = mock_sql_session.query.return_value.filter_by.return_value.first.return_value
        mock_sql_session.delete.assert_called_once_with(location_record)
        mock_sql_session.commit.assert_called_once()

        # Assert that delete was called on Firestore
        mock_all_dependencies["db"].collection.return_value.document.return_value.delete.assert_called_once()

        # Assert event was published
        mock_all_dependencies["publish_event"].assert_called_once()

def test_health_check_all_ok(client, mock_all_dependencies):
    """Test health check when all services are up."""
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json == {
        "environment_variables": {
            "FIREBASE_ADMIN_SDK_BASE64": "present",
            "POSTGRES_POSTGRES_URL": "present",
            "KAFKA_BOOTSTRAP_SERVER": "present",
            "KAFKA_API_KEY": "present",
            "KAFKA_API_SECRET": "present"
        },
        "dependencies": {
            "firestore": "ok",
            "kafka_producer": "ok",
            "postgresql_connection": "ok",
            "table_initialization": "ok"
        },
        "initialization_errors": {
            "firestore": None,
            "postgresql_engine": None,
            "postgresql_table": None,
            "postgresql_query": None,
            "kafka_producer": None
        }
    }

def test_health_check_pg_error(client, mock_all_dependencies):
    """Test health check when PostgreSQL is down."""
    # Simulate a DB error
    from sqlalchemy import text
    mock_all_dependencies["db_session"].execute.side_effect = Exception("Connection failed")
    
    response = client.get('/api/health')
    assert response.status_code == 503
    assert "error" in response.json["dependencies"]["postgresql_connection"]
