import cv2
import time
from wakepy import keep

from constants import NUM_FRAMES_ANALYZED, FPS
# from email_module import send_email
from analysis import should_notify

def backend_loop():
    with keep.presenting():
        time_step = 1.0 / FPS
        frames = []
        capture_device = cv2.VideoCapture(0)
        email_attempt_counter = 0

        while True:
            read_successfully, frame = capture_device.read()
            
            if read_successfully:
                greyscale_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                frames.append(greyscale_frame)

                # Remove extra frames
                if len(frames) > NUM_FRAMES_ANALYZED:
                    frames.pop(0)
            
            # Wait for the next time step 
            time.sleep(time_step)

            if len(frames) >= NUM_FRAMES_ANALYZED:
                # Get the most recent frame and normalize to 0-1 range
                latest_frame = frames[-1]
                frame_normalized = latest_frame.astype("float32") / 255.0
                
                alarm, motion_fraction, fg_mask, suspicion = should_notify(frame_normalized)
                if alarm:
                    email_attempt_counter += 1
                    print(f"Attempting to email! (Attempt #{email_attempt_counter})")

if __name__ == "__main__":
    backend_loop()