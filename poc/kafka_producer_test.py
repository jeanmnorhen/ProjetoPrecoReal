import os
import json
from confluent_kafka import Producer

# Carrega as configurações do Kafka a partir de variáveis de ambiente
conf = {
    'bootstrap.servers': os.environ.get('KAFKA_BOOTSTRAP_SERVER'),
    'security.protocol': 'SASL_SSL',
    'sasl.mechanisms': 'PLAIN',
    'sasl.username': os.environ.get('KAFKA_API_KEY'),
    'sasl.password': os.environ.get('KAFKA_API_SECRET')
}

topic = 'tarefas_ia'
producer = Producer(conf)

def delivery_report(err, msg):
    """ Callback para reportar o resultado da entrega da mensagem."""
    if err is not None:
        print(f'Falha ao entregar mensagem: {err}')
    else:
        print(f'Mensagem entregue em {msg.topic()} [{msg.partition()}]')

# Mensagem de teste para enviar
test_message = {
    'task_id': '12345',
    'task_type': 'analisar_imagem',
    'image_url': 'https://exemplo.com/imagem.jpg'
}

# Envia a mensagem
producer.produce(
    topic,
    key=test_message['task_id'],
    value=json.dumps(test_message),
    callback=delivery_report
)

# Espera todas as mensagens serem entregues
producer.flush()

print(f"Mensagem de teste enviada ao tópico '{topic}'.")
