

import pytest
from pytest_mock import mocker
from unittest.mock import MagicMock
from datetime import datetime, timezone
import os
import sys
from confluent_kafka import Producer

# Add the service's root directory to the path to allow for relative imports
service_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if service_root not in sys.path:
    sys.path.insert(0, service_root)

# Now we can import the app and its dependencies
from api import index as api_index


# Import a mock for the Point object that to_shape would create
class MockPoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y

# Mock a UserLocation record that the SQLAlchemy query would return
class MockUserLocation:
    def __init__(self, user_id, location_str):
        self.user_id = user_id
        self.location = location_str # The WKT string

@pytest.fixture(autouse=True)
def mock_env_vars(mocker):
    mocker.patch.dict(os.environ, {
        "FIREBASE_ADMIN_SDK_BASE64": "mock_firebase_sdk_base64",
        "POSTGRES_POSTGRES_URL": "postgresql://user:password@host:port/database",
        "KAFKA_BOOTSTRAP_SERVER": "dummy_kafka_server",
        "KAFKA_API_KEY": "dummy_kafka_key",
        "KAFKA_API_SECRET": "dummy_kafka_secret",
        "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION": "python",
    })

@pytest.fixture(autouse=True)
def mock_global_dependencies(mocker):
    # Mockar as variáveis globais que são inicializadas no api.index
    mocker.patch('api.index.db', mocker.MagicMock())
    mocker.patch('api.index.producer', mocker.MagicMock())
    mocker.patch('api.index.engine', mocker.MagicMock())
    mocker.patch('api.index.Base', mocker.MagicMock())
    mocker.patch('api.index.Critica', mocker.MagicMock()) # Mock Critica class

    # Mockar as variáveis globais de erro de inicialização para None
    mocker.patch('api.index.firebase_init_error', None)
    mocker.patch('api.index.postgres_init_error', None)
    mocker.patch('api.index.kafka_producer_init_error', None)
    mocker.patch('api.index.db_init_error', None)

    # Mockar funções de inicialização
    mocker.patch('firebase_admin.initialize_app')
    mocker.patch('api.index.create_engine', return_value=mocker.MagicMock())
    mocker.patch('api.index.sessionmaker', return_value=mocker.MagicMock())
    mocker.patch('api.index.Producer', return_value=mocker.MagicMock())
    mocker.patch('api.index.init_db')
    mocker.patch('api.index.text', return_value=mocker.MagicMock())
    
    # Mockar o db_session para ser um objeto válido
    mocker.patch('api.index.db_session', mocker.MagicMock(spec=api_index.sessionmaker()))

@pytest.fixture
def firebase_mock_db(mocker):
    mock_fs_doc = mocker.MagicMock()
    mock_fs_doc.exists = True
    mock_fs_doc.id = "test_user_123"
    mock_fs_doc.to_dict.return_value = {
        "email": "test@example.com",
        "name": "Test User",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    mock_db = mocker.patch('api.index.db', mocker.MagicMock())
    mock_db.collection.return_value.document.return_value.get.return_value = mock_fs_doc
    return mock_db

@pytest.fixture
def postgis_mock_session(mocker):
    mock_sql_session = mocker.MagicMock()
    mock_location_record = MockUserLocation('test_user_123', 'POINT(-46.6 -23.5)')
    mock_sql_session.query.return_value.filter_by.return_value.first.return_value = mock_location_record
    # Add mock for the health check query
    mock_sql_session.execute.return_value = MagicMock()
    mocker.patch('api.index.db_session', mock_sql_session)
    return mock_sql_session

@pytest.fixture
def kafka_mock_producer(mocker):
    mock_kafka_producer_instance = mocker.MagicMock()
    mocker.patch('api.index.producer', mock_kafka_producer_instance)
    return mock_kafka_producer_instance

@pytest.fixture
def to_shape_mock(mocker):
    mock_to_shape = mocker.MagicMock(return_value=MockPoint(x=-46.6, y=-23.5))
    mocker.patch('api.index.to_shape', mock_to_shape)
    return mock_to_shape

@pytest.fixture
def publish_event_mock(mocker):
    mock_publish_event = mocker.patch('api.index.publish_event')
    return mock_publish_event

@pytest.fixture
def client():
    """A test client for the app."""
    from api.index import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# --- Test Cases ---

def test_create_user_with_location(client, firebase_mock_db, postgis_mock_session, publish_event_mock):
    """Test creating a user with location data."""
    user_data = {
        "email": "new@example.com",
        "name": "New User",
        "location": {"latitude": -23.5, "longitude": -46.6}
    }
    response = client.post('/users', json=user_data)

    assert response.status_code == 201
    assert "id" in response.json
    
    # Assert that PostGIS session was used
    postgis_mock_session.add.assert_called_once()
    postgis_mock_session.commit.assert_called_once()

    # Assert that Firestore was used
    firebase_mock_db.collection.return_value.document.return_value.set.assert_called_once()

    # Assert that Kafka event was published
    publish_event_mock.assert_called_once()
    args, kwargs = publish_event_mock.call_args
    assert args[1] == 'UserCreated'

def test_create_user_without_location(client, firebase_mock_db, postgis_mock_session):
    """Test creating a user without location data."""
    user_data = {"email": "no-loc@example.com", "name": "No Location User"}
    response = client.post('/users', json=user_data)

    assert response.status_code == 201
    
    # Assert that PostGIS session was NOT used to add data, but commit is still called
    postgis_mock_session.add.assert_not_called()
    postgis_mock_session.commit.assert_called_once()

    # Assert that Firestore was used
    firebase_mock_db.collection.return_value.document.return_value.set.assert_called_once()

def test_get_user_with_location(client, firebase_mock_db, postgis_mock_session, to_shape_mock):
    """Test getting a user who has a location in PostGIS."""
    response = client.get('/users/test_user_123')

    assert response.status_code == 200
    assert response.json['id'] == 'test_user_123'
    assert 'location' in response.json
    assert response.json['location']['latitude'] == -23.5
    assert response.json['location']['longitude'] == -46.6
    
    # Assert that PostGIS was queried
    postgis_mock_session.query.assert_called_once()
    # Assert that to_shape was called to parse the location
    to_shape_mock.assert_called_once()

def test_get_user_without_location(client, firebase_mock_db, postgis_mock_session, to_shape_mock):
    """Test getting a user who does not have a location in PostGIS."""
    # Setup mock to return None for the location query
    postgis_mock_session.query.return_value.filter_by.return_value.first.return_value = None
    
    response = client.get('/users/test_user_123')

    assert response.status_code == 200
    assert 'location' not in response.json # The key should be absent
    
    postgis_mock_session.query.assert_called_once()
    to_shape_mock.assert_not_called() # Should not be called if no record is found

def test_get_user_not_found(client, firebase_mock_db):
    """Test getting a user that does not exist in Firestore."""
    firebase_mock_db.collection.return_value.document.return_value.get.return_value.exists = False
    
    response = client.get('/users/non_existent_user')
    assert response.status_code == 404

def test_update_user_location(client, firebase_mock_db, postgis_mock_session, publish_event_mock):
    """Test updating a user's location."""
    update_data = {"location": {"latitude": -10.0, "longitude": -20.0}}
    response = client.put('/users/test_user_123', json=update_data)

    assert response.status_code == 200
    
    # Assert that the location record object was modified and commit was called
    location_record = postgis_mock_session.query.return_value.filter_by.return_value.first.return_value
    assert location_record.location == 'POINT(-20.0 -10.0)'
    postgis_mock_session.commit.assert_called_once()

    # Assert event was published
    publish_event_mock.assert_called_once()
    args, kwargs = publish_event_mock.call_args
    assert args[1] == 'UserUpdated'
    assert args[2] == 'test_user_123'
    assert args[3] == update_data

def test_delete_user(client, firebase_mock_db, postgis_mock_session, publish_event_mock):
    """Test deleting a user."""
    response = client.delete('/users/test_user_123')

    assert response.status_code == 204
    
    # Assert that delete was called on the session
    location_record = postgis_mock_session.query.return_value.filter_by.return_value.first.return_value
    postgis_mock_session.delete.assert_called_once_with(location_record)
    postgis_mock_session.commit.assert_called_once()

    # Assert that delete was called on Firestore
    firebase_mock_db.collection.return_value.document.return_value.delete.assert_called_once()

    # Assert event was published
    publish_event_mock.assert_called_once()

def test_health_check_all_ok(client, firebase_mock_db, postgis_mock_session, kafka_mock_producer, mocker):
    """Test health check when all services are up."""
    # The get_health_status is already mocked by mock_global_dependencies to return an "ok" status
    # We just need to ensure the endpoint returns the correct structure and status code.
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json == {
        "environment_variables": {"FIREBASE_ADMIN_SDK_BASE64": "present", "POSTGRES_POSTGRES_URL": "present", "KAFKA_BOOTSTRAP_SERVER": "present", "KAFKA_API_KEY": "present", "KAFKA_API_SECRET": "present"},
        "dependencies": {"firestore": "ok", "kafka_producer": "ok", "postgresql_connection": "ok", "table_initialization": "ok"},
        "initialization_errors": {"firestore": None, "postgresql_engine": None, "postgresql_table": None, "postgresql_query": None, "kafka_producer": None}
    }

def test_health_check_pg_error(client, postgis_mock_session, mocker):
    """Test health check when PostgreSQL is down."""
    # Simulate a DB error
    from sqlalchemy import text
    postgis_mock_session.execute.side_effect = Exception("Connection failed")
    
    mocker.patch('api.index.get_health_status', return_value={
        "environment_variables": {"FIREBASE_ADMIN_SDK_BASE64": "present", "POSTGRES_POSTGRES_URL": "present", "KAFKA_BOOTSTRAP_SERVER": "present", "KAFKA_API_KEY": "present", "KAFKA_API_SECRET": "present"},
        "dependencies": {"firestore": "ok", "kafka_producer": "ok", "postgresql_connection": "error during query: Connection failed", "table_initialization": "ok"},
        "initialization_errors": {"firestore": None, "postgresql_engine": None, "postgresql_table": None, "postgresql_query": "Connection failed", "kafka_producer": None}
    })

    response = client.get('/health')
    assert response.status_code == 503
    assert response.json["dependencies"]["postgresql_connection"] == "error during query: Connection failed"
    assert response.json["initialization_errors"]["postgresql_query"] == "Connection failed"

# --- Testes para Críticas de Produtos ---

@pytest.fixture
def mock_critica_model(mocker):
    mock_critica_instance = mocker.MagicMock()
    mock_critica_instance.id = "mock-critica-id"
    mocker.patch('api.index.Critica', return_value=mock_critica_instance)
    return mock_critica_instance

@pytest.fixture
def mock_db_session_add_commit(mocker):
    mock_session = mocker.MagicMock()
    mock_session.add = mocker.MagicMock()
    mock_session.commit = mocker.MagicMock()
    mock_session.rollback = mocker.MagicMock()
    
    # Mockar o encadeamento de query
    mock_query_result = mocker.MagicMock()
    mock_query_result.filter_by.return_value.all.return_value = [] # Default para get_criticas
    mock_session.query.return_value = mock_query_result

    mocker.patch('api.index.db_session', mock_session)
    return mock_session

def test_add_critica_success(client, mock_critica_model, mock_db_session_add_commit):
    """Testa o envio bem-sucedido de uma crítica de produto."""
    critica_data = {
        "produto_id": "prod_123",
        "tipo_critica": "Foto incorreta",
        "comentario": "A foto não corresponde ao produto."
    }
    response = client.post('/api/criticas', json=critica_data)

    assert response.status_code == 201
    assert "id" in response.json
    assert response.json["message"] == "Crítica recebida e salva com sucesso!"
    mock_db_session_add_commit.add.assert_called_once_with(mock_critica_model)
    mock_db_session_add_commit.commit.assert_called_once()

def test_add_critica_no_json(client):
    """Testa o erro ao enviar uma crítica sem corpo JSON."""
    response = client.post('/api/criticas', data="não é json")

    assert response.status_code == 400
    assert response.json == {"error": "Missing JSON in request"}

def test_add_critica_missing_fields(client):
    """Testa o erro ao enviar uma crítica com campos faltando."""
    critica_data = {
        "produto_id": "prod_123"
        # "tipo_critica" está faltando
    }
    response = client.post('/api/criticas', json=critica_data)

    assert response.status_code == 400
    assert response.json == {"error": "Missing required fields: produto_id, tipo_critica"}

def test_get_criticas_success(client, mock_db_session_add_commit):
    """Testa a busca bem-sucedida de críticas pendentes."""
    mock_critica_1 = api_index.Critica(id="critica-1", produto_id="prod-1", tipo_critica="PRECO_INCORRETO", comentario="Comentário 1", status="PENDENTE", criado_em="2023-01-01T10:00:00Z")
    mock_critica_2 = api_index.Critica(id="critica-2", produto_id="prod-2", tipo_critica="IMAGEM_RUIM", comentario="Comentário 2", status="PENDENTE", criado_em="2023-01-01T11:00:00Z")
    mock_db_session_add_commit.query.return_value.filter_by.return_value.all.return_value = [mock_critica_1, mock_critica_2]

    response = client.get('/api/criticas')

    assert response.status_code == 200
    assert len(response.json) == 2
    assert response.json[0]["id"] == "critica-1"
    assert response.json[1]["id"] == "critica-2"

def test_get_criticas_no_criticas(client, mock_db_session_add_commit):
    """Testa a busca quando não há críticas pendentes."""
    mock_db_session_add_commit.query.return_value.filter_by.return_value.all.return_value = []

    response = client.get('/api/criticas')

    assert response.status_code == 200
    assert len(response.json) == 0
