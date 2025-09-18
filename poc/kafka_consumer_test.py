import os
import json
from confluent_kafka import Consumer, KafkaException

# Carrega as configurações do Kafka a partir de variáveis de ambiente
conf = {
    'bootstrap.servers': os.environ.get('KAFKA_BOOTSTRAP_SERVER'),
    'security.protocol': 'SASL_SSL',
    'sasl.mechanisms': 'PLAIN',
    'sasl.username': os.environ.get('KAFKA_API_KEY'),
    'sasl.password': os.environ.get('KAFKA_API_SECRET'),
    'group.id': 'my_consumer_group',
    'auto.offset.reset': 'earliest'
}

topic = 'tarefas_ia'
consumer = Consumer(conf)

try:
    consumer.subscribe([topic])

    print(f"Consumidor iniciado. Escutando o tópico '{topic}'. Pressione Ctrl+C para sair.")

    while True:
        msg = consumer.poll(timeout=1.0)
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaException._PARTITION_EOF:
                # End of partition event
                print(f'%% {msg.topic()} [{msg.partition()}] reached end offset {msg.offset()}')
            elif msg.error():
                raise KafkaException(msg.error())
        else:
            # Message successfully received
            print(f"Mensagem recebida: Tópico={msg.topic()}, Partição={msg.partition()}, Offset={msg.offset()}")
            print(f"Chave: {msg.key().decode('utf-8') if msg.key() else 'N/A'}")
            print(f"Valor: {msg.value().decode('utf-8')}")

except KeyboardInterrupt:
    pass
finally:
    # Close down consumer to commit final offsets. 
    consumer.close()
    print("Consumidor encerrado.")
