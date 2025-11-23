from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import cv2
import time
import threading
import numpy as np
from wakepy import keep
from constants import NUM_FRAMES_ANALYZED, FPS
from analysis import should_notify

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
COOLDOWN_SECONDS = 15  # 2 minutes cooldown between email alerts

# init_video_capture is now handled in detection_loop

# Shared frame buffer for streaming
latest_frame_buffer = None
frame_buffer_lock = threading.Lock()

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
    
    # Initialize single video capture - try multiple camera indices
    if video_capture is None:
        for camera_index in range(3):  # Try cameras 0, 1, 2
            video_capture = cv2.VideoCapture(camera_index)
            if video_capture.isOpened():
                video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
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
                            
                            if alarm:
                                now = time.time()
                                cooldown_passed = (now - last_alert_time) >= COOLDOWN_SECONDS
                                
                                if cooldown_passed:
                                    last_alert_time = now
                                    email_attempt_counter += 1
                                    print(f"Attempting to email! (Attempt #{email_attempt_counter})")
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

