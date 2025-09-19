import pytest
from pytest_mock import mocker
from unittest.mock import MagicMock
from datetime import datetime, timezone
from firebase_admin import firestore
import os
import sys


# Mock a StoreLocation record that the SQLAlchemy query would create
class MockStoreLocation:
    def __init__(self, store_id, location_str):
        self.store_id = store_id
        self.location = location_str # The WKT string

# Mock a Point object that to_shape would create
class MockPoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y

@pytest.fixture(autouse=True)
def mock_env_vars(mocker):
    mocker.patch.dict(os.environ, {
        "FIREBASE_ADMIN_SDK_BASE64": "mock_firebase_sdk_base64",
        "KAFKA_BOOTSTRAP_SERVER": "",
        "KAFKA_API_KEY": "",
        "KAFKA_API_SECRET": "",
        "PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION": "python",
    })

@pytest.fixture(autouse=True)
def mock_global_dependencies(mocker):
    # Mockar as variáveis globais que são inicializadas no api.index
    mock_api_index = mocker.MagicMock()
    mocker.patch.dict('sys.modules', {'api.index': mock_api_index})

    # Configurar os atributos do mock_api_index
    mock_api_index.db = mocker.MagicMock()
    mock_api_index.producer = mocker.MagicMock()
    mock_api_index.firebase_init_error = None
    mock_api_index.kafka_producer_init_error = None
    mock_api_index.initialize_app = mocker.MagicMock()
    mock_api_index.Producer = mocker.MagicMock()
    mock_api_index.get_health_status = mocker.MagicMock(return_value={
        "environment_variables": {"FIREBASE_ADMIN_SDK_BASE64": "present", "KAFKA_BOOTSTRAP_SERVER": "present", "KAFKA_API_KEY": "present", "KAFKA_API_SECRET": "present"},
        "dependencies": {"firestore": "ok", "kafka_producer": "ok"},
        "initialization_errors": {"firestore": None, "kafka_producer": None}
    })

@pytest.fixture
def firebase_mock_db(mocker):
    mock_fs_doc = mocker.MagicMock()
    mock_fs_doc.exists = True
    mock_fs_doc.id = "test_product_id"
    mock_fs_doc.to_dict.return_value = {
        'name': 'Produto Teste',
        'store_id': 'test_store_id',
        'owner_uid': 'test_owner_uid',
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    }
    mock_db = mocker.patch('api.index.db', mocker.MagicMock())
    mock_db.collection.return_value.document.return_value.get.return_value = mock_fs_doc
    return mock_db

@pytest.fixture
def kafka_mock_producer(mocker):
    mock_kafka_producer_instance = mocker.MagicMock()
    mocker.patch('api.index.producer', mock_kafka_producer_instance)
    return mock_kafka_producer_instance

@pytest.fixture
def mock_auth(mocker):
    mock_auth_instance = mocker.MagicMock()
    mocker.patch('firebase_admin.auth', mock_auth_instance)
    return mock_auth_instance

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

def test_create_product_success(client, firebase_mock_db, mock_auth, publish_event_mock):
    """Testa a criação de um produto por um usuário que é dono da loja."""
    # 1. Setup do Mock
    fake_token = "fake_token_for_product_creation"
    headers = {"Authorization": f"Bearer {fake_token}"}
    user_uid = "test_owner_uid"
    store_id = "my_awesome_store_id"

    # Mock da autenticação
    mock_auth.verify_id_token.return_value = {'uid': user_uid}

    # Mock da verificação de dono da loja (leitura no Firestore)
    mock_store_doc = MagicMock()
    mock_store_doc.exists = True
    mock_store_doc.to_dict.return_value = {'owner_uid': user_uid, 'name': 'Loja do Jean'}
    
    # Mock da criação do produto (escrita no Firestore)
    mock_product_doc_ref = MagicMock()
    mock_product_doc_ref.id = "new_product_id_456"
    
    # Configura o mock do cliente Firestore para retornar os mocks acima
    firebase_mock_db.collection.return_value.document.return_value.get.return_value = mock_store_doc
    firebase_mock_db.collection.return_value.add.return_value = (MagicMock(), mock_product_doc_ref)

    # 2. Dados da Requisição
    new_product_data = {
        "name": "Produto Teste",
        "price": 99.99,
        "store_id": store_id,
        "category": "Teste"
    }

    # 3. Execução
    response = client.post("/api/products", headers=headers, json=new_product_data)

    # 4. Asserções
    assert response.status_code == 201
    assert response.json == {"message": "Product created successfully", "productId": "new_product_id_456"}

    # Verifica a chamada de verificação de dono
    firebase_mock_db.collection.assert_any_call('stores')
    firebase_mock_db.collection('stores').document.assert_called_once_with(store_id)

    # Verifica a chamada de criação de produto
    firebase_mock_db.collection.assert_any_call('products')
    # Get the arguments passed to the add method
    args, kwargs = firebase_mock_db.collection('products').add.call_args
    actual_product_data = args[0]

    # Assert on the content of the dictionary, ignoring the timestamp objects
    assert actual_product_data['name'] == new_product_data['name']
    assert actual_product_data['price'] == new_product_data['price']
    assert actual_product_data['store_id'] == new_product_data['store_id']
    assert actual_product_data['category'] == new_product_data['category']
    assert actual_product_data['owner_uid'] == user_uid
    assert isinstance(actual_product_data['created_at'], type(firestore.SERVER_TIMESTAMP))
    assert isinstance(actual_product_data['updated_at'], type(firestore.SERVER_TIMESTAMP))

    # Verifica que o evento Kafka foi publicado
    publish_event_mock.assert_called_once()
    args, kwargs = publish_event_mock.call_args
    assert args[1] == 'ProductCreated'
    assert args[2] == "new_product_id_456"

def test_get_product_success(client, firebase_mock_db):
    """Testa a recuperação de um produto existente."""
    response = client.get('/api/products/test_product_id')

    assert response.status_code == 200
    assert response.json['id'] == 'test_product_id'
    assert response.json['name'] == 'Produto Teste'

def test_get_product_not_found(client, firebase_mock_db):
    """Testa a recuperação de um produto inexistente."""
    firebase_mock_db.collection.return_value.document.return_value.get.return_value.exists = False
    response = client.get('/api/products/non_existent_product')
    assert response.status_code == 404

def test_update_product_success(client, firebase_mock_db, mock_auth, publish_event_mock):
    """Testa a atualização de um produto por um usuário autorizado."""
    user_uid = "test_owner_uid"
    fake_token = "fake_token_for_product_update"
    headers = {"Authorization": f"Bearer {fake_token}"}
    
    mock_auth.verify_id_token.return_value = {'uid': user_uid}

    update_data = {"price": 89.99}
    response = client.put('/api/products/test_product_id', headers=headers, json=update_data)

    assert response.status_code == 200
    assert response.json['message'] == 'Produto atualizado com sucesso.'
    assert response.json['productId'] == 'test_product_id'

    firebase_mock_db.collection.return_value.document.return_value.update.assert_called_once()
    publish_event_mock.assert_called_once()
    args, kwargs = publish_event_mock.call_args
    assert args[1] == 'ProductUpdated'
    assert args[2] == 'test_product_id'
    assert args[3]['price'] == 89.99

def test_update_product_unauthorized(client, firebase_mock_db, mock_auth):
    """Testa a atualização de um produto por um usuário não autorizado."""
    unauthorized_uid = "unauthorized_user_uid"
    fake_token = "fake_token_for_unauthorized_update"
    headers = {"Authorization": f"Bearer {fake_token}"}
    
    mock_auth.verify_id_token.return_value = {'uid': unauthorized_uid}

    update_data = {"price": 89.99} # Definir update_data aqui
    response = client.put('/api/products/test_product_id', headers=headers, json=update_data)

    assert response.status_code == 403
    assert response.json['error'] == 'User is not authorized to update this product'

def test_delete_product_success(client, firebase_mock_db, mock_auth, publish_event_mock):
    """Testa a exclusão de um produto por um usuário autorizado."""
    user_uid = "test_owner_uid"
    fake_token = "fake_token_for_product_delete"
    headers = {"Authorization": f"Bearer {fake_token}"}
    
    mock_auth.verify_id_token.return_value = {'uid': user_uid}

    response = client.delete('/api/products/test_product_id', headers=headers)

    assert response.status_code == 204
    firebase_mock_db.collection.return_value.document.return_value.delete.assert_called_once()
    publish_event_mock.assert_called_once()
    args, kwargs = publish_event_mock.call_args
    assert args[1] == 'ProductDeleted'
    assert args[2] == 'test_product_id'

def test_delete_product_unauthorized(client, firebase_mock_db, mock_auth):
    """Testa a exclusão de um produto por um usuário não autorizado."""
    unauthorized_uid = "unauthorized_user_uid"
    fake_token = "fake_token_for_unauthorized_delete"
    headers = {"Authorization": f"Bearer {fake_token}"}
    
    mock_auth.verify_id_token.return_value = {'uid': unauthorized_uid}

    response = client.delete('/api/products/test_product_id', headers=headers)

    assert response.status_code == 403
    assert response.json['error'] == 'User is not authorized to delete this product'

def test_health_check_all_ok(client, firebase_mock_db, kafka_mock_producer, mocker):
    """Test health check when all services are up."""
    # The get_health_status is already mocked by mock_global_dependencies to return an "ok" status
    # We just need to ensure the endpoint returns the correct structure and status code.
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json == {
        "environment_variables": {"FIREBASE_ADMIN_SDK_BASE64": "present", "KAFKA_BOOTSTRAP_SERVER": "present", "KAFKA_API_KEY": "present", "KAFKA_API_SECRET": "present"},
        "dependencies": {"firestore": "ok", "kafka_producer": "ok"},
        "initialization_errors": {"firestore": None, "kafka_producer": None}
    }

def test_health_check_kafka_error(client, mocker):
    """Test health check when Kafka producer is not initialized."""
    # Use patch to mock the module-level producer variable
    mocker.patch('api.index.producer', new=None)
    # We need to mock get_health_status to reflect the error state
    mocker.patch('api.index.get_health_status', return_value={
        "environment_variables": {"FIREBASE_ADMIN_SDK_BASE64": "present", "KAFKA_BOOTSTRAP_SERVER": "missing", "KAFKA_API_KEY": "missing", "KAFKA_API_SECRET": "missing"},
        "dependencies": {"firestore": "ok", "kafka_producer": "error"},
        "initialization_errors": {"firestore": None, "kafka_producer": "Variáveis de ambiente do Kafka não encontradas para o producer."
    }})
    response = client.get('/api/health')
    assert response.status_code == 503
    assert response.json["dependencies"]["kafka_producer"] == "error"
    assert response.json["initialization_errors"]["kafka_producer"] == "Variáveis de ambiente do Kafka não encontradas para o producer."
