import json
import logging
from confluent_kafka import Consumer, Producer, KafkaError
import time
import psycopg2
from psycopg2 import sql
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

producers = {
    'hospital_admission': Producer({'bootstrap.servers': 'kafka:9092'}),
    'emergency_incident': Producer({'bootstrap.servers': 'kafka:9092'}),
    'vaccination': Producer({'bootstrap.servers': 'kafka:9092'}),
    'low': Producer({'bootstrap.servers': 'kafka:9092'}),
    'medium': Producer({'bootstrap.servers': 'kafka:9092'}),
    'high': Producer({'bootstrap.servers': 'kafka:9092'})
}

def categorize_and_produce(event_data):
    """Categorize event by type and severity, and produce to respective topics."""
    if isinstance(event_data, list):
        for event in event_data:
            process_event(event)
    elif isinstance(event_data, dict):
        process_event(event_data)
    else:
        logger.error("Unsupported data structure: skipping event")

def process_event(event):
    """Processes and categorizes a single event"""
    event_type = event.get('EventType')
    severity = event.get('Severity')

    if event_type in producers:
        producers[event_type].produce(
            event_type, value=json.dumps(event), callback=delivery_report
        )
        producers[event_type].poll(0)

    if severity in producers:
        producers[severity].produce(
            severity, value=json.dumps(event), callback=delivery_report
        )
        producers[severity].poll(0)

    insert_event_into_db(event)

def delivery_report(err, msg):
    if err is not None:
        logger.error(f"Message delivery failed: {err}")
    else:
        logger.info(f"Message delivered to {msg.topic()} [{msg.partition()}]")

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'postgres'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD', 'postgres'),
            dbname=os.getenv('POSTGRES_DB', 'health_events_db')
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to PostgreSQL: {e}")
        return None

def insert_event_into_db(event):
    """Inserts a single event into the PostgreSQL database."""
    conn = get_db_connection()
    if conn is None:
        logger.error("No database connection available.")
        return

    try:
        with conn:
            with conn.cursor() as cur:
                insert_query = sql.SQL("""
                    INSERT INTO health_events (event_type, severity, details, timestamp, location)
                    VALUES (%s, %s, %s, NOW(), %s)
                """)
                cur.execute(insert_query, (
                    event.get('EventType'),
                    event.get('Severity'),
                    event.get('Details'),
                    event.get('Location')
                ))
                logger.info(f"Inserted event into DB: {event}")
    except Exception as e:
        logger.error(f"Error inserting event into DB: {e}")
    finally:
        conn.close()

def main():
    bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', '3.80.138.59:9092')
    topic = 'health_events'
    group_id = 'health_events_consumer_group'

    consumer = Consumer({
        'bootstrap.servers': bootstrap_servers,
        'group.id': group_id,
        'auto.offset.reset': 'earliest'
    })
    consumer.subscribe([topic])

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    logger.error(f"Consumer error: {msg.error()}")
                    continue

            try:
                event_data = json.loads(msg.value().decode('utf-8'))
                logger.info(f"Consumed event: {event_data}")
                categorize_and_produce(event_data)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON: {e}")
            except AttributeError as e:
                logger.error(f"Unexpected data format: {e}")

    except KeyboardInterrupt:
        logger.info("Shutdown signal received.")
    finally:
        consumer.close()
        for producer in producers.values():
            producer.flush()

if __name__ == "__main__":
        main()
