import cv2
import time
from wakepy import keep
import os
print("Current working directory:", os.getcwd())

from constants import NUM_FRAMES_ANALYZED, FPS
from analysis import should_notify
from push_notifications import send_motion_alert

COOLDOWN_SECONDS = 15
ROLLING_SECONDS = 5
POST_MOTION_SECONDS = 15
ROLLING_BUFFER_SIZE = int(ROLLING_SECONDS * FPS)

OUTPUT_DIR = "recordings"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_video_writer(filename, frame_width, frame_height):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    return cv2.VideoWriter(
        filename, fourcc, FPS, (frame_width, frame_height)
    )

def backend_loop():
    with keep.presenting():
        time_step = 1.0 / FPS
        frames = []
        rolling_buffer = []

        capture_device = cv2.VideoCapture(0)

        if not capture_device.isOpened():
            raise RuntimeError("Camera failed to open")

        frame_width  = int(capture_device.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(capture_device.get(cv2.CAP_PROP_FRAME_HEIGHT))

        last_alert_time = 0

        # --- Recording state ---
        recording = False
        recording_writer = None
        motion_last_seen = 0  

        while True:
            read_successfully, frame = capture_device.read()

            if read_successfully:
                # greyscale for analysis
                greyscale_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                frames.append(greyscale_frame)
                if len(frames) > NUM_FRAMES_ANALYZED:
                    frames.pop(0)

                # rolling 5-second color buffer
                rolling_buffer.append(frame.copy())
                if len(rolling_buffer) > ROLLING_BUFFER_SIZE:
                    rolling_buffer.pop(0)

                # If currently recording, write every new frame
                if recording:
                    recording_writer.write(frame)

            time.sleep(time_step)

            # --- Motion Analysis ---
            if len(frames) >= NUM_FRAMES_ANALYZED:

                normalized = frames[-1].astype("float32") / 255.0
                alarm, motion_fraction, fg_mask, suspicion = should_notify(normalized)

                now = time.time()
                cooldown_passed = (now - last_alert_time) >= COOLDOWN_SECONDS

                # --------------------------------------------
                # START RECORDING IF MOTION DETECTED
                # --------------------------------------------
                if alarm:

                    # For alert cooldown
                    if cooldown_passed:
                        last_alert_time = now
                        print("ALERT: sending push!")
                        send_motion_alert()

                    # Update last motion time to keep recording alive
                    motion_last_seen = now

                    # Start recording if it isn't already running
                    if not recording:
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        filename = os.path.join(OUTPUT_DIR, f"motion_{timestamp}.mp4")
                        print(f"--- Recording started: {filename}")

                        recording_writer = create_video_writer(
                            filename, frame_width, frame_height
                        )
                        recording = True

                        # Write old 5-second buffer first
                        for buffered_frame in rolling_buffer:
                            recording_writer.write(buffered_frame)

                # --------------------------------------------
                # STOP RECORDING AFTER NO MOTION FOR 15s
                # --------------------------------------------
                if recording:
                    if (now - motion_last_seen) >= POST_MOTION_SECONDS:
                        print("--- Recording stopped.")

                        recording = False
                        recording_writer.release()
                        recording_writer = None

if __name__ == "__main__":
    backend_loop()