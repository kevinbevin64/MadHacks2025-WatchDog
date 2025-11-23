import cv2
import time
from wakepy import keep

from constants import NUM_FRAMES_ANALYZED, FPS
# from email_module import send_email
from analysis import should_notify
from push_notifications import send_motion_alert

COOLDOWN_SECONDS = 1

def backend_loop():
    print("dddddkdjfkdjfkdsjfkjsdf")
    with keep.presenting():
        time_step = 1.0 / FPS
        frames = []
        capture_device = cv2.VideoCapture(0)
        email_attempt_counter = 0
        last_alert_time = 0  # Initialize last alert time

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
                print("doing this")
                # Get the most recent frame and normalize to 0-1 range
                latest_frame = frames[-1]
                frame_normalized = latest_frame.astype("float32") / 255.0
                
                alarm, motion_fraction, fg_mask, suspicion = should_notify(frame_normalized)
                now = time.time()
                cooldown_passed = (now - last_alert_time) >= COOLDOWN_SECONDS

                # Debug output
                if alarm:
                    print(f"Alarm triggered! Suspicion: {suspicion:.2f}, Motion: {motion_fraction:.2%}, Cooldown passed: {cooldown_passed}")
                
                if alarm and cooldown_passed:
                    last_alert_time = now  # update timer
                    email_attempt_counter += 1
                    print("ALERT: sending push notification!")
                    
                    # Send push notification
                    send_motion_alert()
                elif alarm and not cooldown_passed:
                    time_remaining = COOLDOWN_SECONDS - (now - last_alert_time)
                    print(f"Alarm triggered but cooldown active. {time_remaining:.1f}s remaining.")
                    

if __name__ == "__main__":
    backend_loop()