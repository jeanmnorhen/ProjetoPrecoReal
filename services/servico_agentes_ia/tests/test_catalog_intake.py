import importlib
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import os
import sys
import json
import base64
import requests

# Add the project root directory to the path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now we can import the app and its dependencies
from services.servico_agentes_ia.api import index as api_index

@pytest.fixture(autouse=True)
def mock_env_vars():
    """Mocks all necessary environment variables."""
    with patch.dict(os.environ, {
        "FIREBASE_ADMIN_SDK_BASE64": "mock_firebase_sdk_base64",
        "KAFKA_BOOTSTRAP_SERVER": "dummy_kafka_server",
        "KAFKA_API_KEY": "dummy_kafka_key",
        "KAFKA_API_SECRET": "dummy_kafka_secret",
        "GEMINI_API_KEY": "dummy_gemini_api_key",
        "CRON_SECRET": "dummy_cron_secret",
        "SERVICO_BUSCA_URL": "http://mock-search-service",
        "SERVICO_PRODUTOS_URL": "http://mock-products-service",
        "FIREBASE_STORAGE_BUCKET": "mock-storage-bucket"
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
         patch.object(api_index, 'genai', MagicMock()) as mock_genai, \
         patch('requests.get', MagicMock()) as mock_requests_get, \
         patch('requests.post', MagicMock()) as mock_requests_post, \
         patch('PIL.Image.open', MagicMock()) as mock_image_open, \
         patch.object(api_index, 'upload_image_to_firebase', return_value="http://mock-image-url.com/image.jpg") as mock_upload_image_to_firebase, \
         patch.object(api_index, 'firebase_admin', MagicMock()) as mock_firebase_admin, \
         patch.object(api_index, 'initialization_errors', {
             "firebase": None,
             "kafka_producer": None,
             "kafka_consumer": None,
             "gemini": None
         }):

        # --- Configure Default Mock Behaviors ---

        # Default for auth
        mock_auth.verify_id_token.return_value = {'uid': 'test_user_uid'}

        # Default for Gemini
        mock_genai.GenerativeModel.return_value.generate_content.return_value.text = json.dumps({
            "name": "Produto Gerado",
            "categories": ["Categoria1", "Categoria2"],
            "description": "Descrição gerada pela IA."
        })

        # Default for requests.get (servico-busca)
        mock_requests_get.return_value = MagicMock(status_code=200, ok=True)
        mock_requests_get.return_value.json.return_value = {"hits": 0, "products": []} # Default: product not found

        # Default for requests.post (servico-produtos)
        mock_requests_post.return_value = MagicMock(status_code=201, ok=True)
        mock_requests_post.return_value.json.return_value = {"message": "Success", "productId": "new_prod_id"}

        # Default for Firebase Storage
        mock_firebase_admin.storage.bucket.return_value.blob.return_value.upload_from_string.return_value = None
        mock_firebase_admin.storage.bucket.return_value.blob.return_value.make_public.return_value = None
        mock_firebase_admin.storage.bucket.return_value.blob.return_value.public_url = "http://mock-image-url.com/image.jpg"

        yield {
            "db": mock_db,
            "producer": mock_producer,
            "auth": mock_auth,
            "genai": mock_genai,
            "requests_get": mock_requests_get,
            "requests_post": mock_requests_post,
            "image_open": mock_image_open,
            "firebase_admin": mock_firebase_admin,
            "upload_image_to_firebase": mock_upload_image_to_firebase
        }

# --- Test Cases for catalog-intake endpoint ---

def test_catalog_intake_unauthorized(client):
    """Tests catalog intake without authorization."""
    response = client.post('/api/agents/catalog-intake', json={'text_query': 'test'})
    assert response.status_code == 401

def test_catalog_intake_missing_input(client, mock_dependencies):
    """Tests catalog intake with missing input."""
    headers = {"Authorization": "Bearer fake_token"}
    response = client.post('/api/agents/catalog-intake', headers=headers, json={})
    assert response.status_code == 400
    assert "Request body is missing" in response.json['error']

def test_catalog_intake_text_query_product_found(client, mock_dependencies):
    """Tests catalog intake with text query where product is found."""
    mock_dependencies["requests_get"].return_value.json.return_value = {
        "results": [{'id': 'prod123', 'name': 'Existing Product'}]
    }
    headers = {"Authorization": "Bearer fake_token"}
    response = client.post('/api/agents/catalog-intake', headers=headers, json={'text_query': 'Existing Product'})
    assert response.status_code == 200
    assert "Produto encontrado no catálogo." in response.json['message']
    assert response.json['product']['id'] == 'prod123'
    mock_dependencies["genai"].GenerativeModel.return_value.generate_content.assert_not_called() # IA não deve ser chamada

def test_catalog_intake_text_query_product_not_found(client, mock_dependencies):
    """Tests catalog intake with text query where product is not found, leading to AI generation."""
    mock_dependencies["requests_get"].return_value.json.return_value = {"results": []} # Nenhum produto encontrado
    headers = {"Authorization": "Bearer fake_token"}
    response = client.post('/api/agents/catalog-intake', headers=headers, json={'text_query': 'New Product'})
    assert response.status_code == 202
    assert "Novo produto gerado pela IA e enviado para aprovação." in response.json['message']
    mock_dependencies["genai"].GenerativeModel.return_value.generate_content.assert_called_once()
    mock_dependencies["requests_post"].assert_called_once_with(
        "http://mock-products-service/api/products/canonical",
        headers={'Authorization': 'Bearer fake_token', 'Content-Type': 'application/json'},
        json={'name': 'Produto Gerado', 'description': 'Descrição gerada pela IA.', 'category': 'Categoria1,Categoria2', 'image_url': None}
    )

def test_catalog_intake_image_product_found(client, mock_dependencies):
    """Tests catalog intake with image where product is found, leading to image update."""
    mock_dependencies["requests_get"].return_value.json.return_value = {
        "results": [{'id': 'prod123', 'name': 'Existing Product'}]
    }
    headers = {"Authorization": "Bearer fake_token"}
    dummy_image_b64 = base64.b64encode(b"dummy_image_data").decode('utf-8')
    response = client.post('/api/agents/catalog-intake', headers=headers, json={'image_base64': dummy_image_b64})
    assert response.status_code == 200
    assert "Nova imagem adicionada para revisão." in response.json['message']
    mock_dependencies["upload_image_to_firebase"].assert_called_once()
    mock_dependencies["requests_post"].assert_called_once_with(
        "http://mock-products-service/api/products/prod123/images",
        headers={'Authorization': 'Bearer fake_token', 'Content-Type': 'application/json'},
        json={'image_url': 'http://mock-image-url.com/image.jpg', 'source': 'image_analysis'}
    )
    mock_dependencies["genai"].GenerativeModel.return_value.generate_content.assert_called_once() # Chamado para identificar o produto da imagem

def test_catalog_intake_image_product_not_found(client, mock_dependencies):
    """Tests catalog intake with image where product is not found, leading to AI generation and image upload."""
    mock_dependencies["requests_get"].return_value.json.return_value = {"results": []} # Nenhum produto encontrado
    headers = {"Authorization": "Bearer fake_token"}
    dummy_image_b64 = base64.b64encode(b"dummy_image_data").decode('utf-8')
    response = client.post('/api/agents/catalog-intake', headers=headers, json={'image_base64': dummy_image_b64})
    assert response.status_code == 202
    assert "Novo produto gerado pela IA e enviado para aprovação." in response.json['message']
    mock_dependencies["upload_image_to_firebase"].assert_called_once()
    mock_dependencies["genai"].GenerativeModel.return_value.generate_content.assert_called_once()
    mock_dependencies["requests_post"].assert_called_once_with(
        "http://mock-products-service/api/products/canonical",
        headers={'Authorization': 'Bearer fake_token', 'Content-Type': 'application/json'},
        json={'name': 'Produto Gerado', 'description': 'Descrição gerada pela IA.', 'category': 'Categoria1,Categoria2', 'image_url': 'http://mock-image-url.com/image.jpg'}
    )

def test_catalog_intake_category_query(client, mock_dependencies):
    """Tests catalog intake with category query, leading to AI generation of multiple products."""
    mock_dependencies["genai"].GenerativeModel.return_value.generate_content.return_value.text = json.dumps([
        {"name": "Produto Cat 1", "description": "Desc Cat 1"},
        {"name": "Produto Cat 2", "description": "Desc Cat 2"}
    ])
    headers = {"Authorization": "Bearer fake_token"}
    response = client.post('/api/agents/catalog-intake', headers=headers, json={'category_query': 'Bebidas'})
    assert response.status_code == 202
    assert "Sugestões de produtos para a categoria 'Bebidas' geradas e enviadas para aprovação." in response.json['message']
    assert len(response.json['productIds']) == 2
    assert mock_dependencies["requests_post"].call_count == 2 # Two products created
