import base64
import os

import folium
import folium.plugins
import numpy as np
import pandas as pd
import psycopg2
import streamlit as st
from OSMPythonTools.overpass import Overpass
from pandas.core.series import base
from scipy.spatial import ConvexHull, Delaunay
from streamlit_folium import folium_static
from streetlevel import streetview

from utils.boundaries import get_osm_data
from utils.sidebar import sidebar_components

# DB_URL = os.getenv("DB_URL")
DB_URL = "postgresql://utkarsh:uOphh5OzXd7N1aDrLWGtvD9gmN8DFWxN@dpg-csfl7aogph6c73f4h5m0-a.oregon-postgres.render.com/treeinv"
# Directory to store fetched images
IMAGE_DIR = "streetview_images"
os.makedirs(IMAGE_DIR, exist_ok=True)  # Ensure the directory exists

overpass = Overpass()

st.set_page_config(layout="wide", page_title="Tree Inventory of India")


@st.cache_data(ttl=60)
def load_data():
    # Load state and city data
    states = pd.read_csv("./locations/states.csv")
    cities = pd.read_csv("./locations/cities.csv")

    # Load coordinates from the database
    coordinates = []
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT tree_id, lat, lng, lat_offset, lng_offset FROM tree_details;"
        )
        coordinates = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"Error loading data from database: {e}")

    return states, cities, coordinates


def download_and_compress_images(coordinates, target_size=(300, 150)):
    for tree_id, lat, lon, lat_offset, lng_offset in coordinates:
        lat += lat_offset / 1113200
        lon += lng_offset / 1113200

        # File path for each image by tree_id
        image_path = f"{IMAGE_DIR}/tree_{tree_id}.jpg"

        # Only download if the image does not already exist
        if not os.path.exists(image_path):
            pano = streetview.find_panorama(lat, lon, radius=500)
            if pano:
                # Get and compress the panorama image
                panorama = streetview.get_panorama(pano, zoom=5)
                panorama = panorama.resize(
                    target_size,
                    # Image.ANTIALIAS
                )  # Resize to target size
                panorama.save(image_path, "JPEG", quality=85)


def add_boundary_to_map(boundary_coords, map_object, coordinates):
    points_array = np.array(boundary_coords)
    hull = ConvexHull(points_array)
    boundary_points = points_array[hull.vertices]
    folium.Polygon(
        locations=boundary_points, color="blue", weight=1, fill=True, fill_opacity=0.05
    ).add_to(map_object)

    delaunay = Delaunay(boundary_coords)
    filtered_coords = [
        (tree_id, lat, lon, lat_offset, lng_offset)
        for tree_id, lat, lon, lat_offset, lng_offset in coordinates
        if delaunay.find_simplex([lat, lon]) >= 0
    ]

    return filtered_coords


def add_tree_markers(map_object, coordinates):
    for tree_id, lat, lon, lat_offset, lng_offset in coordinates:
        lat += lat_offset / 1113200
        lon += lng_offset / 1113200

        # Check for existing compressed image
        image_path = f"{IMAGE_DIR}/tree_{tree_id}.jpg"
        if os.path.exists(image_path):
            # Encode the image in base64 for embedding in HTML
            with open(image_path, "rb") as img_file:
                img_data = img_file.read()
                img_base64 = base64.b64encode(img_data).decode("utf-8")
                image_html = (
                    f'<img src="data:image/jpg;base64,{img_base64}" width="100%">'
                )
        else:
            image_html = "<p>Street View not available</p>"

        popup_content = f"""
        <div style="width: 200px; line-height: 1.2; margin: 0;">
            <h4 style="margin: 0; padding-bottom: 4px;">Tree {tree_id}</h4>
            <p style="margin: 2px 0;"><strong>Latitude:</strong> {lat:.8f}</p>
            <p style="margin: 2px 0;"><strong>Longitude:</strong> {lon:.8f}</p>
            <p style="margin: 2px 0;"><strong>Species:</strong> A</p>
            <p style="margin: 2px 0;"><strong>Age:</strong> xxx</p>
            {image_html}
        </div>
        """

        # Initialize the marker with a default icon size
        marker = folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_content, max_width=200),
            icon=folium.Icon(icon="leaf", color="green", size=(5, 5)),
        )

        marker.add_to(map_object)

    return map_object


def main():
    st.title("🌳 Tree Inventory 🌳")
    st.markdown(
        "### Explore tree data and boundaries within India using interactive maps."
    )

    states_df, cities_df, coordinates = load_data()
    filtered_coordinates = coordinates

    # Pre-download and compress images
    download_and_compress_images(filtered_coordinates)

    center_lat, center_lon, zoom, location = sidebar_components(
        states_df, cities_df, st
    )
    st.sidebar.markdown(
        f"""
        <div style="background-color:#f0f0f5; padding: 10px; border-radius: 10px; margin-top: 20px;">
            <h2 style="color: #000000;">Total Trees 🌳 : {len(filtered_coordinates)}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        with open("map.html", "r", encoding="utf-8") as html_file:
            html_content = html_file.read()

        # Embed the HTML content in Streamlit
        st.components.v1.html(html_content, height=600, scrolling=True)
    except FileNotFoundError:
        st.error(
            "Map HTML file not found. Please ensure 'map.html' is in the correct directory."
        )

    # m = folium.Map(
    #     location=[center_lat, center_lon], zoom_start=zoom, max_zoom=23, tiles=None
    # )
    #
    # folium.TileLayer(
    #     tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    #     attr="Esri",
    # ).add_to(m)
    # folium.TileLayer(
    #     tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
    #     attr="Esri",
    # ).add_to(m)
    #
    # if location:
    #     boundary_data = get_osm_data(location)
    #     filtered_coordinates = add_boundary_to_map(boundary_data, m, coordinates)
    #
    # add_tree_markers(m, filtered_coordinates)
    #
    # folium.plugins.Fullscreen(
    #     position="topright",
    #     title="Expand me",
    #     title_cancel="Exit me",
    #     force_separate_button=True,
    # ).add_to(m)
    #
    # folium_static(m)


if __name__ == "__main__":
    main()
