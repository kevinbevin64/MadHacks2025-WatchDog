from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import cv2
import time
import threading
import numpy as np
import os
import json
from wakepy import keep
from constants import NUM_FRAMES_ANALYZED, FPS
from analysis import should_notify
from send_to_rust_server import upload_video, upload_json
from push_notifications import send_motion_alert

app = Flask(__name__)
CORS(app)  # Enable CORS for Electron app

# Global state
video_capture = None
video_capture_lock = threading.Lock()
frames = []
is_detecting = False
email_attempt_counter = 0
current_alarm = False
current_suspicion = 0.0
keep_awake_context = None
detection_thread = None
last_alert_time = 0
COOLDOWN_SECONDS = 15  # Cooldown between alerts (in seconds)

# Recording constants
ROLLING_SECONDS = 5  # Keep 5 seconds of buffer before motion
POST_MOTION_SECONDS = 5  # Continue recording 5 seconds after motion stops
ROLLING_BUFFER_SIZE = int(ROLLING_SECONDS * FPS)
OUTPUT_DIR = "recordings"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# init_video_capture is now handled in detection_loop

# Shared frame buffer for streaming
latest_frame_buffer = None
frame_buffer_lock = threading.Lock()

def create_video_writer(filename, frame_width, frame_height):
    """Create a VideoWriter for saving recordings"""
    # Use MJPG codec for maximum compatibility and reliability
    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(
        filename, fourcc, FPS, (frame_width, frame_height)
    )
    if not writer.isOpened():
        print(f"Warning: Failed to open video writer for {filename}")
        return None
    return writer

def generate_frames():
    """Generate video frames for streaming"""
    global latest_frame_buffer
    
    while True:
        try:
            with frame_buffer_lock:
                frame_to_send = latest_frame_buffer
            
            if frame_to_send is None:
                # Send placeholder frame
                error_frame = cv2.putText(
                    np.zeros((480, 640, 3), dtype=np.uint8),
                    "Waiting for camera...",
                    (50, 240),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (255, 255, 255),
                    2
                )
                frame_to_send = error_frame
            
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame_to_send, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ret:
                time.sleep(0.1)
                continue
            
            frame_bytes = buffer.tobytes()
            
            # Yield frame in multipart format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            time.sleep(1.0 / FPS)  # Control frame rate
        except Exception as e:
            print(f"Error in frame generation: {e}")
            time.sleep(0.1)

def detection_loop():
    """Main detection loop that runs in background"""
    global frames, is_detecting, email_attempt_counter, current_alarm, current_suspicion, video_capture, latest_frame_buffer, last_alert_time
    
    time_step = 1.0 / FPS
    
    # Recording state
    recording = False
    recording_writer = None
    recording_filename = None
    motion_last_seen = 0
    rolling_buffer = []
    frame_width = 640
    frame_height = 480
    was_detecting = False  # Track previous detection state
    
    # Initialize single video capture - try multiple camera indices
    if video_capture is None:
        for camera_index in range(3):  # Try cameras 0, 1, 2
            video_capture = cv2.VideoCapture(camera_index)
            if video_capture.isOpened():
                video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                frame_width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
                frame_height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
                print(f"Video capture initialized on camera index {camera_index}")
                break
            else:
                video_capture.release()
                video_capture = None
        
        if video_capture is None or not video_capture.isOpened():
            print("Error: Could not open video capture. Please check your camera connection.")
            return
    
    while True:
        try:
            # Always read frames for streaming, even when not detecting
            with video_capture_lock:
                read_successfully, frame = video_capture.read()
            
            if read_successfully:
                # Update frame buffer for streaming
                with frame_buffer_lock:
                    latest_frame_buffer = frame.copy()
                
                # Maintain rolling buffer for recording (5 seconds)
                if is_detecting:
                    rolling_buffer.append(frame.copy())
                    if len(rolling_buffer) > ROLLING_BUFFER_SIZE:
                        rolling_buffer.pop(0)
                
                # Write frame to recording if active
                if recording and recording_writer is not None:
                    try:
                        recording_writer.write(frame)
                    except Exception as e:
                        print(f"--- Error writing frame to video: {e}")
                        recording = False
                        if recording_writer is not None:
                            try:
                                recording_writer.release()
                            except:
                                pass
                        recording_writer = None
                
                # Check if detection was just stopped - stop recording immediately
                if was_detecting and not is_detecting and recording:
                    print("--- Detection stopped, stopping recording immediately.")
                    recording = False
                    
                    # Properly close the video writer
                    if recording_writer is not None:
                        try:
                            recording_writer.release()
                            recording_writer = None
                            time.sleep(0.5)
                        except Exception as e:
                            print(f"--- Error releasing video writer: {e}")
                    
                    # Store filename for upload (after writer is fully closed)
                    video_to_upload = recording_filename
                    recording_filename = None
                    
                    # Capture timestamp when video recording actually stops (video is captured)
                    video_capture_time = time.time()
                    video_capture_timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(video_capture_time))
                    
                    # Upload video and timestamp to Rust server (in background thread)
                    if video_to_upload and os.path.exists(video_to_upload):
                        def upload_after_delay():
                            time.sleep(1.0)
                            try:
                                print(f"--- Uploading video to Rust server: {video_to_upload}")
                                success = upload_video(video_to_upload)
                                if success:
                                    print("✓ Video uploaded successfully!")
                                else:
                                    print("✗ Video upload failed!")
                            except Exception as upload_error:
                                print(f"--- Error uploading video: {upload_error}")
                        
                        upload_thread = threading.Thread(target=upload_after_delay, daemon=True)
                        upload_thread.start()
                        
                        try:
                            # Create and upload timestamp JSON with video capture time
                            timestamp_data = {
                                "timestamp": video_capture_timestamp,
                                "unix_timestamp": video_capture_time,
                                "video_filename": os.path.basename(video_to_upload),
                                "alarm": current_alarm,
                                "suspicion": current_suspicion,
                                "email_attempts": email_attempt_counter
                            }
                            
                            # Save JSON to temp file and upload
                            json_filename = video_to_upload.replace('.avi', '.json')
                            with open(json_filename, 'w') as json_file:
                                json.dump(timestamp_data, json_file, indent=2)
                            
                            print(f"--- Uploading timestamp JSON: {json_filename}")
                            success = upload_json(json_filename)
                            if success:
                                print("✓ JSON uploaded successfully!")
                            else:
                                print("✗ JSON upload failed!")
                            
                            # Clean up temp JSON file
                            try:
                                os.remove(json_filename)
                            except:
                                pass
                                
                        except Exception as upload_error:
                            print(f"--- Error uploading to Rust server: {upload_error}")
                
                # Update was_detecting for next iteration
                was_detecting = is_detecting
                
                # Only do detection if enabled
                if is_detecting:
                    greyscale_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    frames.append(greyscale_frame)
                    
                    # Remove extra frames
                    if len(frames) > NUM_FRAMES_ANALYZED:
                        frames.pop(0)
                    
                    if len(frames) >= NUM_FRAMES_ANALYZED:
                        # Get the most recent frame and normalize to 0-1 range
                        latest_frame = frames[-1]
                        frame_normalized = latest_frame.astype("float32") / 255.0
                        
                        try:
                            alarm, motion_fraction, fg_mask, suspicion = should_notify(frame_normalized)
                            current_suspicion = suspicion
                            current_alarm = alarm
                            
                            now = time.time()
                            
                            if alarm:
                                # Update last motion time to keep recording alive
                                motion_last_seen = now
                                
                                # Start recording if not already running
                                if not recording:
                                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                                    recording_filename = os.path.join(OUTPUT_DIR, f"motion_{timestamp}.avi")
                                    print(f"--- Recording started: {recording_filename}")
                                    
                                    recording_writer = create_video_writer(
                                        recording_filename, frame_width, frame_height
                                    )
                                    
                                    if recording_writer is None:
                                        print(f"--- Failed to create video writer, skipping recording")
                                        continue
                                    
                                    recording = True
                                    
                                    # Write old 5-second buffer first
                                    for buffered_frame in rolling_buffer:
                                        if recording_writer is not None:
                                            recording_writer.write(buffered_frame)
                                
                                # Email cooldown check
                                cooldown_passed = (now - last_alert_time) >= COOLDOWN_SECONDS
                                
                                if cooldown_passed:
                                    last_alert_time = now
                                    email_attempt_counter += 1
                                    print(f"ALERT: Motion detected! Sending push notification (Attempt #{email_attempt_counter})")
                                    
                                    # Send push notification
                                    send_motion_alert()
                            
                            # Stop recording after no motion for POST_MOTION_SECONDS
                            if recording:
                                if (now - motion_last_seen) >= POST_MOTION_SECONDS:
                                    print("--- Recording stopped.")
                                    recording = False
                                    
                                    # Capture timestamp when video recording actually stops (video is captured)
                                    video_capture_time = time.time()
                                    video_capture_timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(video_capture_time))
                                    
                                    # Properly close the video writer
                                    if recording_writer is not None:
                                        try:
                                            recording_writer.release()
                                            recording_writer = None
                                            # Wait longer to ensure file is fully written and flushed to disk
                                            time.sleep(0.5)
                                        except Exception as e:
                                            print(f"--- Error releasing video writer: {e}")
                                    
                                    # Store filename for upload (after writer is fully closed)
                                    video_to_upload = recording_filename
                                    recording_filename = None
                                    
                                    # Upload video and timestamp to Rust server (in background thread to avoid blocking)
                                    if video_to_upload and os.path.exists(video_to_upload):
                                        def upload_after_delay():
                                            # Additional delay to ensure file system has released the file
                                            time.sleep(1.0)
                                            try:
                                                print(f"--- Uploading video to Rust server: {video_to_upload}")
                                                success = upload_video(video_to_upload)
                                                if success:
                                                    print("✓ Video uploaded successfully!")
                                                else:
                                                    print("✗ Video upload failed!")
                                            except Exception as upload_error:
                                                print(f"--- Error uploading video: {upload_error}")
                                        
                                        # Start upload in background thread
                                        upload_thread = threading.Thread(target=upload_after_delay, daemon=True)
                                        upload_thread.start()
                                        
                                        try:
                                            
                                            # Create and upload timestamp JSON with video capture time
                                            timestamp_data = {
                                                "timestamp": video_capture_timestamp,
                                                "unix_timestamp": video_capture_time,
                                                "video_filename": os.path.basename(video_to_upload),
                                                "alarm": current_alarm,
                                                "suspicion": current_suspicion,
                                                "email_attempts": email_attempt_counter
                                            }
                                            
                                            # Save JSON to temp file and upload
                                            json_filename = video_to_upload.replace('.avi', '.json')
                                            with open(json_filename, 'w') as json_file:
                                                json.dump(timestamp_data, json_file, indent=2)
                                            
                                            print(f"--- Uploading timestamp JSON: {json_filename}")
                                            success = upload_json(json_filename)
                                            if success:
                                                print("✓ JSON uploaded successfully!")
                                            else:
                                                print("✗ JSON upload failed!")
                                            
                                            # Clean up temp JSON file
                                            try:
                                                os.remove(json_filename)
                                            except:
                                                pass
                                                
                                        except Exception as upload_error:
                                            print(f"--- Error uploading to Rust server: {upload_error}")
                        except Exception as e:
                            print(f"Error in motion detection: {e}")
            
            time.sleep(time_step)
        except Exception as e:
            print(f"Error in detection loop: {e}")
            time.sleep(1)
            # Try to reinitialize - try multiple camera indices
            try:
                with video_capture_lock:
                    if video_capture is not None:
                        video_capture.release()
                    video_capture = None
                    for camera_index in range(3):  # Try cameras 0, 1, 2
                        video_capture = cv2.VideoCapture(camera_index)
                        if video_capture.isOpened():
                            video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                            video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                            print(f"Camera reinitialized on index {camera_index}")
                            break
                        else:
                            if video_capture is not None:
                                video_capture.release()
                            video_capture = None
            except Exception as e2:
                print(f"Error reinitializing capture: {e2}")
                time.sleep(2)

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    )

@app.route('/start_detection', methods=['POST'])
def start_detection():
    """Start motion detection"""
    global is_detecting, keep_awake_context
    
    if not is_detecting:
        is_detecting = True
        return jsonify({'status': 'started'})
    return jsonify({'status': 'already_running'})

@app.route('/stop_detection', methods=['POST'])
def stop_detection():
    """Stop motion detection"""
    global is_detecting
    
    if is_detecting:
        is_detecting = False
        return jsonify({'status': 'stopped'})
    return jsonify({'status': 'already_stopped'})

@app.route('/motion_status', methods=['GET'])
def motion_status():
    """Get current motion detection status"""
    return jsonify({
        'alarm': current_alarm,
        'suspicion': current_suspicion,
        'email_attempts': email_attempt_counter,
        'is_detecting': is_detecting
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    camera_status = 'available' if (video_capture is not None and video_capture.isOpened()) else 'unavailable'
    return jsonify({
        'status': 'ok',
        'camera': camera_status,
        'server': 'running'
    })

if __name__ == '__main__':
    # Start detection loop in background thread
    detection_thread = threading.Thread(target=detection_loop, daemon=True)
    detection_thread.start()
    
    # Try to use keep.presenting() but don't fail if it causes issues
    try:
        with keep.presenting():
            print("Starting server on http://localhost:8080")
            print("Video feed available at http://localhost:8080/video_feed")
            app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
    except Exception as e:
        print(f"Warning: keep.presenting() failed: {e}")
        print("Continuing without sleep prevention...")
        print("Starting server on http://localhost:8080")
        print("Video feed available at http://localhost:8080/video_feed")
        app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)

