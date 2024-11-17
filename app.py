import os

import psycopg2
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template

load_dotenv()

app = Flask(__name__)

DB_URL = os.getenv("DB_URL")
API_KEY = os.getenv("API_KEY")


@app.route("/")
def home():
    return render_template("map3d.html")


@app.route("/map-config")
def get_map_config():
    return jsonify({"api_key": API_KEY, "center": {"lat": 43.6425, "lng": -79.3871}})


@app.route("/trees", methods=["GET"])
def get_tree_data():
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT tree_id, lat, lng, lat_offset, lng_offset FROM tree_details;"
        )
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        # Convert to JSON response
        response = [
            {
                "tree_id": row[0],
                "lat": row[1],
                "lng": row[2],
                "lat_offset": 0.0001,
                "lng_offset": 0.0001,
            }
            for row in data
        ]
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
