import folium
from folium.plugins import HeatMap
from flask import Flask, render_template_string
import pandas as pd
import psycopg2
import plotly.express as px
import plotly.io as pio
from datetime import datetime

# Flask App Initialization
app = Flask(__name__)

# PostgreSQL Database Configuration
db_config = {
    "host": "postgres",
    "port": 5432,
    "dbname": "health_events_db",
    "user": "postgres",
    "password": "postgres"
}


# Function to Fetch Data from PostgreSQL
def fetch_data():
    conn = psycopg2.connect(**db_config)
    query = "SELECT * FROM health_events;"
    data = pd.read_sql_query(query, conn)
    conn.close()
    return data

@app.route("/")
def dashboard():
    data = fetch_data()
    data['timestamp'] = pd.to_datetime(data['timestamp'])

    # Total counts per location
    location_counts = data['location'].value_counts().reset_index()
    location_counts.columns = ['location', 'count']

    # Most recent event
    most_recent_event = data.sort_values(by="timestamp", ascending=False).iloc[0]

    # Severity bar chart
    severity_counts = data.groupby(["location", "severity"]).size().reset_index(name="count")
    severity_fig = px.bar(
        severity_counts,
        x="location", y="count", color="severity",
        title="Event Severity Counts by Location", barmode="group"
    )
    severity_html = pio.to_html(severity_fig, full_html=False)

    # Event counts per event type (bar chart)
    event_type_counts = data['event_type'].value_counts().reset_index()
    event_type_counts.columns = ['event_type', 'count']
    event_type_fig = px.bar(
        event_type_counts,
        x="event_type", y="count",
        title="Event Counts by Event Type",
        labels={"event_type": "Event Type", "count": "Count"}
    )
    event_type_html = pio.to_html(event_type_fig, full_html=False)

    # Event type frequency (pie chart)
    event_type_fig_pie = px.pie(
        event_type_counts, names="event_type", values="count",
        title="Event Type Frequency"
    )
    event_type_pie_html = pio.to_html(event_type_fig_pie, full_html=False)

    # Heatmap for most recent events
    most_recent_events = data.sort_values(by="timestamp", ascending=False).groupby("location").first().reset_index()

    # Hardcoded lat/lon for locations
    location_data = {
        "Los Angeles": (34.0522, -118.2437),
        "Berlin": (52.5200, 13.4050),
        "London": (51.5074, -0.1278),
        "Paris": (48.8566, 2.3522),
        "New York": (40.7128, -74.0060),
        "Boston": (42.3601, -71.0589)
    }

    # Prepare heatmap data
    heatmap_data = []
    for _, row in most_recent_events.iterrows():
        if row['location'] in location_data:
            lat, lon = location_data[row['location']]
            heatmap_data.append([lat, lon, 1])

    # Initialize Folium map
    event_map = folium.Map(location=[48.8566, 2.3522], zoom_start=4)
    HeatMap(heatmap_data, radius=15, blur=10, min_opacity=0.4).add_to(event_map)

    # Add Markers for the most recent events
    for _, row in most_recent_events.iterrows():
        if row['location'] in location_data:
            lat, lon = location_data[row['location']]
            folium.Marker(
                location=[lat, lon],
                popup=f"Location: {row['location']}<br>Severity: {row['severity']}<br>Timestamp: {row['timestamp']}",
                icon=folium.Icon(color="red" if row['severity'] == "high" else
                                 "orange" if row['severity'] == "medium" else "green")
            ).add_to(event_map)

    map_html = event_map._repr_html_()

    # Render HTML
    return render_template_string("""
    <html>
        <head>
            <title>Health Event Dashboard</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #f5f5f5;
                    color: #333;
                }
                h1, h2 {
                    color: #fff;
                    background-color: #2c3e50;
                    padding: 10px;
                    text-align: center;
                }
                .container {
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: space-around;
                    margin: 20px;
                }
                .chart, .map {
                    background-color: #fff;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                    margin: 20px;
                    padding: 10px;
                    width: 45%;
                }
                .header {
                    text-align: center;
                    background-color: #3498db;
                    color: #fff;
                    padding: 15px;
                }
                .recent-event {
                    text-align: center;
                    background-color: #ecf0f1;
                    padding: 15px;
                    margin-bottom: 20px;
                    border-radius: 5px;
                }
            </style>
        </head>
        <body>
            <h1>Health Event Dashboard</h1>
            <div class="recent-event">
                <h2>Most Recent Event</h2>
                <p><b>Location:</b> {{ most_recent_event['location'] }}</p>
                <p><b>Severity:</b> {{ most_recent_event['severity'] }}</p>
                <p><b>Timestamp:</b> {{ most_recent_event['timestamp'] }}</p>
            </div>
            <div class="header">
                <h2>Total Event Counts by Location</h2>
                {% for _, row in location_counts.iterrows() %}
                    <p><b>{{ row['location'] }}:</b> {{ row['count'] }} events</p>
                {% endfor %}
            </div>
            <div class="container">
                <div class="chart">{{ severity_html|safe }}</div>
                <div class="chart">{{ event_type_html|safe }}</div>
                <div class="chart">{{ event_type_pie_html|safe }}</div>
                <div class="map">
                    <h3>Heatmap of Most Recent Events</h3>
                    {{ map_html|safe }}
                </div>
            </div>
            <script>
                setInterval(function() {
                    location.reload();
                }, 10000);  // Refresh every 30 seconds
            </script>
        </body>
    </html>
    """, location_counts=location_counts, most_recent_event=most_recent_event,
       severity_html=severity_html, event_type_html=event_type_html,
       event_type_pie_html=event_type_pie_html, map_html=map_html)



# Run Flask App
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
