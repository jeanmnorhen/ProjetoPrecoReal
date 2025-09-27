import pytest
import unittest.mock as mock
import os
import requests
import sys
import os
# Adiciona o diretório raiz do serviço ao sys.path
service_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if service_root not in sys.path:
    sys.path.insert(0, service_root)

from api.index import app, SERVICES_TO_MONITOR

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# Mock os.environ.get to provide dummy URLs for services
@pytest.fixture(autouse=True)
def mock_env_vars():
    with mock.patch.dict(os.environ, {
        "SERVICO_AGENTES_IA_URL": "http://mock-ai-service",
        "SERVICO_BUSCA_URL": "http://mock-search-service",
        "SERVICO_MONITORAMENTO_URL": "http://mock-monitoring-service",
        "SERVICO_PRODUTOS_URL": "http://mock-products-service",
        "SERVICO_USUARIOS_URL": "http://mock-users-service",
        "SERVICO_LOJAS_URL": "http://mock-stores-service",
        "SERVICO_OFERTAS_URL": "http://mock-offers-service",
    }):
        yield

def test_health_check_all_services_ok(client):
    with mock.patch('services.servico_healthcheck.api.index.requests.get') as mock_get:
        # Configure mock_get to return a successful response for all services
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_response.text = '{"status": "ok"}' # Set .text for raise_for_status
        mock_get.side_effect = [mock_response] * len(SERVICES_TO_MONITOR)

        response = client.get('/health')
        assert response.status_code == 200
        assert response.json['status'] == 'ok'
        
        # Verify that all services were called and returned 'ok'
        for service_name in SERVICES_TO_MONITOR.keys():
            assert response.json['services'][service_name]['status'] == 'ok'
            # Check that requests.get was called for each service
            health_path = "/health" if service_name == "servico_usuarios" else "/api/health"
            expected_url = os.environ.get(SERVICES_TO_MONITOR[service_name]) + health_path
            assert any(expected_url in call.args[0] for call in mock_get.call_args_list)
def test_health_check_some_services_degraded(client):
    with mock.patch('services.servico_healthcheck.api.index.requests.get') as mock_get:
        # Configure mock_get to simulate some services being down
        def mock_get_side_effect(url, *args, **kwargs):
            mock_response = mock.Mock()
            if "mock-ai-service" in url:
                mock_response.status_code = 500
                mock_response.json.return_value = {"status": "error", "details": "Internal Server Error"}
                mock_response.text = '{"status": "error", "details": "Internal Server Error"}' # Set .text
                mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
            elif "mock-search-service" in url:
                mock_response.status_code = 200
                mock_response.json.return_value = {"status": "ok"}
                mock_response.text = '{"status": "ok"}' # Set .text
                mock_response.raise_for_status.return_value = None
            else: # All other services are ok
                mock_response.status_code = 200
                mock_response.json.return_value = {"status": "ok"}
                mock_response.text = '{"status": "ok"}' # Set .text
                mock_response.raise_for_status.return_value = None
            return mock_response
        
        mock_get.side_effect = mock_get_side_effect

        response = client.get('/health')
        assert response.status_code == 503 # Overall status should be 503 if any service is not 'ok'
        assert response.json['status'] == 'degraded'
        
        # Verify specific service statuses
        assert response.json['services']['servico_agentes_ia']['status'] == 'error'
        assert "Internal Server Error" in response.json['services']['servico_agentes_ia']['details']
        assert response.json['services']['servico_busca']['status'] == 'ok'
        # Ensure other services are also checked
        assert response.json['services']['servico_produtos']['status'] == 'ok'

def test_health_check_service_url_not_configured(client):
    # Temporarily remove one service URL from environment for this test
    with mock.patch.dict(os.environ, {"SERVICO_USUARIOS_URL": ""}):
        with mock.patch('services.servico_healthcheck.api.index.requests.get') as mock_get:
            # All other services are mocked to be ok
            mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_response.text = '{"status": "ok"}' # Set .text
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            response = client.get('/health')
            assert response.status_code == 503 # Should be 503 if any service URL is missing
            assert response.json['status'] == 'degraded'
            assert response.json['services']['servico_usuarios']['status'] == 'unavailable'
            assert response.json['services']['servico_usuarios']['details'] == 'URL not configured'
            # Ensure other services are still reported as ok
            assert response.json['services']['servico_produtos']['status'] == 'ok'