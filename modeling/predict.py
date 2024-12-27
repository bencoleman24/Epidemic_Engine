import os
import psycopg2
from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.sql.functions import col
from pyspark.sql.functions import year, month, dayofmonth, hour

# Database connection parameters from environment variables
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "health_events_db")

pg_url = f"jdbc:postgresql://{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
pg_props = {
    "user": POSTGRES_USER,
    "password": POSTGRES_PASSWORD,
    "driver": "org.postgresql.Driver"
}

# Create SparkSession in local mode
spark = SparkSession.builder \
    .appName("LocalPrediction") \
    .master("local[*]") \
    .config("spark.driver.extraClassPath", "/app/postgresql.jar") \
    .getOrCreate()

# Load the model - previously trained by train_anomaly_detector_model.py in model_training folder
pipeline_model = PipelineModel.load("/app/modeling/anomaly_detector_model")

# Ensure the predictions table exists
def ensure_predictions_table():
    conn = None
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            dbname=POSTGRES_DB
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS predictions (
                        id INT PRIMARY KEY,
                        is_anomaly INT
                    );
                """)
    except Exception as e:
        print("Error ensuring predictions table:", e)
    finally:
        if conn:
            conn.close()

ensure_predictions_table()

# Select events from the last 10 minutes to predict on
recent_events = spark.read.jdbc(
    url=pg_url,
    table="""(
       SELECT 
          id, 
          event_type AS "EventType",
          severity AS "Severity",
          details AS "Details",
          location AS "Location",
          timestamp AS "Timestamp"
       FROM health_events 
       WHERE timestamp >= NOW() - INTERVAL '10 minutes'
    ) AS recent""",
    properties=pg_props
)

# If there are no new events, print a message and exit
if recent_events.count() == 0:
    print("No new events to predict on.")
else:
    recent_events = recent_events.withColumn("Year", year("Timestamp")) \
                                 .withColumn("Month", month("Timestamp")) \
                                 .withColumn("Day", dayofmonth("Timestamp")) \
                                 .withColumn("Hour", hour("Timestamp"))

    predictions = pipeline_model.transform(recent_events)
    final_preds = predictions.select("id", col("prediction").alias("is_anomaly"))

# Append the predictions to the predictions table
    final_preds.write.jdbc(
        url=pg_url,
        table="predictions",
        mode="append",
        properties=pg_props
    )
    print("Predictions appended to predictions table")

spark.stop()
# Stop spark session, we are done with prediction. Program will be re ran by system in 10 minutes.