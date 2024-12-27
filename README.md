## Epidemic Engine - Final Integration

### <ins>   Overview: </ins>
This project integrates multiple components developed over previous projects into a cohesive end to end pipeline. The system ingests real-time health event data from Kafka, stores it in a PostgreSQL database, and uses a trained ML model to detect anomalies. The architecture uses Docker Compose to orchestrate all services.

#

### <ins>  Key Components</ins>

##### Deployment:
- The system is ran by running `podman-compose build` and then `podman-compose up`. This will launch all the containers in docker-compose.yml. This eliminates the complexity of starting each component individually.
- There are `depends_on` clauses in the `docker-compose.yml` which make sure that the Consumer and Predictor services only start once the Kafka and PostgreSQL services are confirmed healthy. Health checks are also defined for Kafka, PostgreSQL, Consumer, and Predictor which check periodically to verify service availability. 
- Each service is configured with a `restart: on-failure policy`. This improves the reliability of the pipeline
- The pre-trained `anomaly_detector_model` is included in the predictor image, so no extra steps are needed in deployment to load the model and the predictor immediately has access to the trained pipeline for generating anomaly predictions.
- The streamed data is also used to create a dshboard of all visualization, being updated every 10 second with newly streamed data

##### Kafka:
- Provides a health_events topic
- Events are continuously streamed and consumed by the consumer service.

##### Consumer Service (consumer.py):
- Consumes events from the health_events topic on Kafka.
- Inserts the events into the health_events table in the PostgreSQL databaset.

##### Postgres Database:
- Stores health events in the health events table
- Stores ML anomaly predictions in the predictions table.
- `init_db.sql` sets up the initial health_events table.
- The `predict.py` script sets up the predictions table and inserts predictions.

##### Model Training (Offline):
- `train_model.py` uses PySpark locally to train an anomaly detection model on the historical CSV data from project 2.
- This model is shown to have a high accuracy (>95%) from its performance on the testing data in project 2.
- The trained model is saved to the `anomaly_detector_model` folder.
- This model training done outside of the podman enviornment. The resulting model artifacts are then included in the podman image. 

##### Predictor Service (predict.py)
- Uses PySpark and the saved `anomaly_detector_model` pipeline to classify recent events as anomalies.
- Runs every 10 minutes and queries the last 10 minutes of events from Postgres to predict on.
- Writes predictions (`id`, and `is_anomaly`) to the `predictions` table.
- Note: When the project is booted up, it waits 2 minutes before being ran for the first time, then it runs every 10 minutes.

##### Health Event Dashboard and Visualizations
- For the dashboards, the headers show the most recent health event alongside the health event counts for each location.
- The first bar chart displays the historical event counts by severity for each location for all the data.
- The second chart displays the counts for each event type within the data. The pie chart below displays the event type split within the data for a clearer visualization.
- The map is our real time visualization, displaying the most recent event for every location on a map. The marker is colored to match the severity
- The dashboard is updated evey 10 seconds with the new data streamed in.


#
### <ins>  Directory Structure</ins>

The following is the structure of the project repository:
```plaintext
project3/
├── kafka_server/
│   ├── consumer.py
│   ├── Dockerfile
│   ├── init_db.sql
│   └── requirements.txt
├── modeling/
│   ├── anomaly_detector/
│   │   ├── metadata/
│   │   └── stages/
│   ├── model_training/
│   │   └── venv/
│   ├── 1m_health_events.csv
│   ├── train_anomaly_detector.py
│   ├── Dockerfile.predictor
│   ├── postgresql-42.2.20.jar
│   ├── predict.py
│   └── requirements_predictor.txt
├── postgres_bind/
├── visualization/
│   ├── app.py
│   ├── Dockerfile.visualization
├── .gitignore
├── docker-compose.yml
├── INSTRUCTIONS.md
└── README.md
```

#
### <ins> Running the Project and Accessing the Features</ins>

##### Running the Pipeline
- Navigate to the `project3` folder.
- If `modeling/anomaly_detector_model` is not present, you need to first run `train_anomaly_detector_model.py` located in `modeling/model_training`. 
- In the terminal run `podman-compose build` and then `podman-compose up`
- Data should start streaming almost immediately into `health_events`, `predictions` will not be created until 2 minutes later.
- Run `podman ps` to ensure the 5 components are running and healthy (postgres, kafka, consumer, predictor, visualization)
- If needed, you can view the logs of any of these components by running `podman logs CONTAINER_ID`

##### Viewing the PostgreSQL Data
- In the terminal run: `podman exec -it project3_postgres_1 bash`     
(you may have to replace project3_postgres_1 to reflect your enviornment, run `podman ps` to see the name needed)
- Then run `psql -U postgres -d health_events_db`
- Then run a query of your choice, one example is `SELECT * FROM health_events ORDER BY id DESC;` to view all of the data in `health_events` starting with the most recent loaded in. 
- You can also query the `predictions` table similarly.

##### Accessing our Dashboard
- In a web browser navigate to `http://localhost:5001`
- You should then see our live updating dashboard. It will refresh every 30 seconds.
#
### <ins> Some Troubleshooting Tips </ins>
- If the predictor doesn’t produce predictions, check if the predict.py logs show errors.
- If the visualization page doesn’t load, confirm that the visualization container is healthy and that postgresql-client is installed.
- If Kafka is unhealthy, check kafka logs and ensure the ports aren’t blocked.

#
