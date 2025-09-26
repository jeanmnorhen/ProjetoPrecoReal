from dotenv import load_dotenv
load_dotenv(dotenv_path='.env.local')

import os
import requests
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# define a list of services to monitor and their environment variable names
# The health endpoint for all services is assumed to be /api/health 3
SERVICES_TO_MONITOR = {
    "servico_agentes_ia": "SERVICO_AGENTES_IA_URL",
    "servico_busca": "SERVICO_BUSCA_URL",
    "servico_monitoramento": "SERVICO_MONITORAMENTO_URL",
    "servico_produtos": "SERVICO_PRODUTOS_URL",
    "servico_usuarios": "SERVICO_USUARIOS_URL",
    "servico_lojas": "SERVICO_LOJAS_URL",
    "servico_ofertas": "SERVICO_OFERTAS_URL"
}

def get_overall_health_status():
    overall_status = {"status": "ok", "services": {}}
    all_services_ok = True

    for service_name, env_var_name in SERVICES_TO_MONITOR.items():
        service_url = os.environ.get(env_var_name)
        service_health_status = {"status": "unavailable", "details": "URL not configured"}

        if service_url:
            try:
                # Assuming health endpoint is /api/health for all services
                health_endpoint = f"{service_url}/api/health"
                response = requests.get(health_endpoint, timeout=5)
                response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
                
                service_health_status = response.json()
                if service_health_status.get("status") != "ok" and not (service_health_status.get("dependencies") and all(s == "ok" for s in service_health_status["dependencies"].values())):
                    all_services_ok = False

            except requests.exceptions.Timeout:
                service_health_status = {"status": "timeout", "details": "Request timed out"}
                all_services_ok = False
            except requests.exceptions.ConnectionError:
                service_health_status = {"status": "unreachable", "details": "Service is unreachable"}
                all_services_ok = False
            except requests.exceptions.HTTPError as e:
                service_health_status = {"status": "error", "details": f"HTTP Error: {e.response.status_code} - {e.response.text}"}
                all_services_ok = False
            except Exception as e:
                service_health_status = {"status": "error", "details": str(e)}
                all_services_ok = False
        else:
            all_services_ok = False # Mark overall as not ok if any service URL is missing

        overall_status["services"][service_name] = service_health_status
    
    if not all_services_ok:
        overall_status["status"] = "degraded" # Or "error" depending on desired strictness

    return overall_status

@app.route('/health', methods=['GET'])
def health_check():
    status = get_overall_health_status()
    http_status_code = 200 if status["status"] == "ok" else 503
    return jsonify(status), http_status_code

if __name__ == '__main__':
    app.run(debug=True)
