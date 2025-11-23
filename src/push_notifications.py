"""
Apple Push Notification Service (APNs) module for sending push notifications to iOS devices.
Uses PyJWT and curl (via subprocess) for Python 3.13 compatibility.
"""
import os
import jwt
import time
import requests
import subprocess
import json

# Configuration - UPDATE THESE VALUES

# APNs environment: 'sandbox' for development, 'production' for production
APNS_ENVIRONMENT = "sandbox"  # Change to "production" for App Store builds

def generate_jwt_token():
    """Generate JWT token for APNs authentication"""
    try:
        with open(P8_KEY_PATH, 'r') as f:
            private_key = f.read()
        
        # Ensure the key doesn't have extra whitespace
        private_key = private_key.strip()
        
        # Verify key format
        if not private_key.startswith("-----BEGIN"):
            print(f"WARNING: Key file format may be incorrect. First 50 chars: {private_key[:50]}")
        if "PRIVATE KEY" not in private_key:
            print("WARNING: Key file may not be a valid private key")
        
        # JWT headers for APNs
        headers = {
            "alg": "ES256",
            "kid": KEY_ID
        }
        
        # JWT payload for APNs
        payload = {
            "iss": TEAM_ID,
            "iat": int(time.time())
        }
        
        print(f"Generating JWT with Team ID: {TEAM_ID}, Key ID: {KEY_ID}, Bundle ID: {BUNDLE_ID}")
        
        # Encode JWT token
        # Note: jwt.encode returns a string in PyJWT 2.0+
        token = jwt.encode(payload, private_key, algorithm="ES256", headers=headers)
        
        # Handle both string and bytes return types
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        
        return token
    except Exception as e:
        print(f"Error generating JWT token: {e}")
        import traceback
        traceback.print_exc()
        return None

def send_push_notification(title="Motion Detected", body="WatchDog detected motion!", device_token=None, custom_data=None):
    """
    Send a push notification to an iOS device via APNs using HTTP/2.
    Uses requests library with ALPN support for HTTP/2.
    
    Args:
        title: Notification title
        body: Notification body text
        device_token: Device token to send to (defaults to DEVICE_TOKEN constant)
        custom_data: Dictionary of custom data to include in notification
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Use provided device token or default
        token = device_token or DEVICE_TOKEN
        
        # Validate configuration
        if TEAM_ID == "YOUR_TEAM_ID" or KEY_ID == "YOUR_KEY_ID" or BUNDLE_ID == "YOUR_BUNDLE_ID":
            print("ERROR: Please update APNs configuration in push_notifications.py")
            return False
        
        if not os.path.exists(P8_KEY_PATH):
            print(f"ERROR: P8 key file not found at {P8_KEY_PATH}")
            return False
        
        if token == "YOUR_DEVICE_TOKEN":
            print("ERROR: Please provide a device token")
            return False
        
        # Generate JWT token
        jwt_token = generate_jwt_token()
        if not jwt_token:
            print("ERROR: Failed to generate JWT token")
            return False
        
        # Debug: Print first/last chars of token (don't print full token for security)
        print(f"Generated JWT token (length: {len(jwt_token)}, starts with: {jwt_token[:20]}...)")
        
        # Determine APNs URL based on environment
        apns_url = "https://api.sandbox.push.apple.com" if APNS_ENVIRONMENT == "sandbox" else "https://api.push.apple.com"
        url = f"{apns_url}/3/device/{token}"
        
        # Build notification payload
        payload = {
            "aps": {
                "alert": {
                    "title": title,
                    "body": body
                },
                "sound": "default",
                "badge": 1
            }
        }
        
        # Add custom data if provided
        if custom_data:
            for key, value in custom_data.items():
                payload[key] = value
        
        # Send HTTP/2 request to APNs using curl (via subprocess) since Python HTTP/2 libraries have Python 3.13 issues
        import json
        import subprocess
        
        headers = {
            "authorization": f"bearer {jwt_token}",
            "apns-topic": BUNDLE_ID,
            "apns-priority": "10",
            "apns-push-type": "alert",
            "content-type": "application/json"
        }
        
        # Use curl with HTTP/2 support (curl supports HTTP/2 natively)
        curl_cmd = [
            "curl",
            "-X", "POST",
            url,
            "--http2",
            "-H", f"authorization: bearer {jwt_token}",
            "-H", f"apns-topic: {BUNDLE_ID}",
            "-H", "apns-priority: 10",
            "-H", "apns-push-type: alert",
            "-H", "content-type: application/json",
            "-d", json.dumps(payload),
            "-w", "\n%{http_code}",
            "-s", "-S"  # Silent but show errors
        ]
        
        try:
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=10)
            
            # Parse response (curl outputs status code on last line)
            output_lines = result.stdout.strip().split('\n')
            if output_lines:
                # Last line is HTTP status code
                status_code = int(output_lines[-1]) if output_lines[-1].isdigit() else None
                
                if status_code == 200:
                    print(f"Push notification sent successfully to device: {token[:20]}...")
                    return True
                else:
                    error_msg = '\n'.join(output_lines[:-1]) if len(output_lines) > 1 else result.stderr
                    print(f"Failed to send push notification. Status: {status_code}, Response: {error_msg}")
                    return False
            else:
                print(f"Failed to send push notification. Error: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("Timeout sending push notification")
            return False
        except FileNotFoundError:
            # Fallback to requests if curl is not available
            print("curl not found, trying with requests (may not work - APNs requires HTTP/2)")
            response = requests.post(url, json=payload, headers=headers, timeout=10.0)
            
            if response.status_code == 200:
                print(f"Push notification sent successfully to device: {token[:20]}...")
                return True
            else:
                print(f"Failed to send push notification. Status: {response.status_code}, Response: {response.text}")
                return False
        
    except Exception as e:
        print(f"Error sending push notification: {e}")
        import traceback
        traceback.print_exc()
        return False


def send_motion_alert():
    """
    Send a motion detection alert push notification.
    """
    title = "🚨 Motion Detected!"
    body = "WatchDog detected motion."
    
    custom_data = {
        "payload": "disturbance"
    }
    
    return send_push_notification(
        title=title,
        body=body,
        custom_data=custom_data
    )
