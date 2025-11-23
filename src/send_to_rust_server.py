#!/usr/bin/env python3
"""
Python script to send data to the Rust server.
Supports sending video files and JSON data.
"""

import requests
import json
import os
import sys
from pathlib import Path

RUST_SERVER_URL = "http://localhost:8081"

# Upload a video
def upload_video(file_path):
    try:
        with open(file_path, "rb") as f:
            response = requests.post(f"{RUST_SERVER_URL}/video", data=f, timeout=10)
        print(f"Video upload status: {response.status_code} - {response.text}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print(f"⚠ Warning: Could not connect to Rust server at {RUST_SERVER_URL}")
        print("  Make sure the Rust server is running on port 8081")
        return False
    except requests.exceptions.Timeout:
        print(f"⚠ Warning: Upload to Rust server timed out")
        return False
    except Exception as e:
        print(f"⚠ Error uploading video: {e}")
        return False

# Upload a JSON
def upload_json(file_path):
    try:
        with open(file_path, "r") as f:
            json_data = f.read()
        headers = {'Content-Type': 'application/json'}
        response = requests.post(f"{RUST_SERVER_URL}/json", data=json_data, headers=headers, timeout=10)
        print(f"JSON upload status: {response.status_code} - {response.text}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print(f"⚠ Warning: Could not connect to Rust server at {RUST_SERVER_URL}")
        print("  Make sure the Rust server is running on port 8081")
        return False
    except requests.exceptions.Timeout:
        print(f"⚠ Warning: Upload to Rust server timed out")
        return False
    except Exception as e:
        print(f"⚠ Error uploading JSON: {e}")
        return False

