from pyspark.sql import SparkSession
from pyspark.sql.functions import to_timestamp, year, month, dayofmonth, hour
from pyspark.ml.feature import StringIndexer, VectorAssembler
from pyspark.ml.classification import DecisionTreeClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml import Pipeline

# Initialize SparkSession in local mode
spark = SparkSession.builder \
    .appName("LocalModelTraining") \
    .master("local[*]") \
    .getOrCreate()

train_file = "1m_health_events_dataset.csv"
df = spark.read.csv(train_file, header=True, inferSchema=True)

df = df.withColumn("Timestamp", to_timestamp("Timestamp", "yyyy-MM-dd HH:mm:ss"))

df = df.withColumn("Year", year("Timestamp")) \
       .withColumn("Month", month("Timestamp")) \
       .withColumn("Day", dayofmonth("Timestamp")) \
       .withColumn("Hour", hour("Timestamp"))

categorical_columns = ["EventType", "Location", "Severity", "Details"]
numeric_columns = ["Year", "Month", "Day", "Hour"]

indexers = [
    StringIndexer(inputCol=col_name, outputCol=col_name + "_index", handleInvalid="keep").fit(df)
    for col_name in categorical_columns
]

vector_assembler = VectorAssembler(
    inputCols=[col + "_index" for col in categorical_columns] + numeric_columns,
    outputCol="features"
)

dt = DecisionTreeClassifier(featuresCol="features", labelCol="Is_Anomaly", maxDepth=10, maxBins=128)
pipeline = Pipeline(stages=indexers + [vector_assembler, dt])

train_df, val_df = df.randomSplit([0.8, 0.2], seed=42)
pipeline_model = pipeline.fit(train_df)

evaluator = MulticlassClassificationEvaluator(labelCol="Is_Anomaly", predictionCol="prediction", metricName="accuracy")
val_predictions = pipeline_model.transform(val_df)

pipeline_model.write().overwrite().save("../anomaly_detector_model")

spark.stop()
