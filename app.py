import os
from math import asin, atan2, cos, degrees, pi, radians, sin, sqrt

import psycopg2
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

app = Flask(__name__)

DB_URL = os.getenv("DB_URL")
API_KEY = os.getenv("API_KEY")


@app.route("/")
def home():
    return render_template("map3d.html")


@app.route("/map-config")
def get_map_config():
    lat, lng = 41.89193, 12.51133
    return jsonify({"api_key": API_KEY, "center": {"lat": lat, "lng": lng}})


@app.route("/tree-filter", methods=["POST"])
def filter_trees():
    try:
        # Get data from POST request
        data = request.get_json()
        center_lat = data.get("lat")
        center_lng = data.get("lng")
        radius = data.get("radius")  # Radius in meters

        # Ensure data is valid
        if not all([center_lat, center_lng, radius]):
            raise ValueError("Missing required fields in request body.")

        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()

        # SQL query to fetch tree data
        cursor.execute(
            """
            SELECT 
                t.tree_id, 
                t.lat, 
                t.lng 
            FROM tree_details t
            JOIN streetview_images i ON t.image_id = i.image_id;
            """
        )

        data = cursor.fetchall()
        cursor.close()
        conn.close()

        # Calculate distance and filter trees
        filtered_trees = []
        R = 6371000  # Radius of Earth in meters
        lat1 = radians(center_lat)
        lon1 = radians(center_lng)

        for row in data:
            tree_lat = row[1]
            tree_lng = row[2]

            # Haversine formula
            lat2 = radians(tree_lat)
            lon2 = radians(tree_lng)

            dlon = lon2 - lon1
            dlat = lat2 - lat1

            a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))

            distance = R * c  # Distance in meters

            # If within radius, add to the filtered list
            if distance <= radius:
                filtered_trees.append(
                    {
                        "id": row[0],
                        "lat": row[1],
                        "lng": row[2],
                        "distance": distance,
                    }
                )

        # Generate points on circumference
        circumference_points = []
        num_points = 36
        for angle in range(0, 360, 360 // num_points):
            bearing = radians(angle)
            circ_lat = degrees(
                asin(
                    sin(lat1) * cos(radius / R)
                    + cos(lat1) * sin(radius / R) * cos(bearing)
                )
            )
            circ_lng = degrees(
                lon1
                + atan2(
                    sin(bearing) * sin(radius / R) * cos(lat1),
                    cos(radius / R) - sin(lat1) * sin(radians(circ_lat)),
                )
            )

            # Ensure longitude stays within bounds (-180 to 180)
            circ_lng = (circ_lng + 540) % 360 - 180

            circumference_points.append({"lat": circ_lat, "lng": circ_lng})
        circumference_points.append(circumference_points[0])

        # Return the tree count, filtered tree data, and circumference points
        return jsonify(
            {
                "treeCount": len(filtered_trees),
                "trees": filtered_trees,
                "circumferencePoints": circumference_points,
            }
        )

    except Exception as e:
        print("Error occurred:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/trees", methods=["GET"])
def get_tree_data():
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()

        # SQL query to fetch tree details along with image path
        cursor.execute(
            """
            SELECT 
                t.tree_id, 
                t.lat, 
                t.lng, 
                i.pano_id,
                t.species,
                t.common_name,
                t.description
            FROM tree_details t
            JOIN streetview_images i ON t.image_id = i.image_id;
        """
        )

        data = cursor.fetchall()
        cursor.close()
        conn.close()

        # Convert to JSON response with the image_path
        response = [
            {
                "id": row[0],
                "lat": row[1],
                "lng": row[2],
                "imagePath": f"/static/images/{row[3].split('/')[-1]}_90/tree/im.jpg",
                "species": row[4],
                "commonName": row[5],
                "description": row[6] if row[6] else "No description available.",
            }
            for row in data
        ]

        return jsonify(response)
    except Exception as e:
        print("Error occurred:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
