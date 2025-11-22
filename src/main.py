import cv2
import time

from constants import NUM_FRAMES_ANALYZED, FPS
from email_module import send_email

def main():
    keep_awake()

    time_step = 1.0 / FPS
    frames = []
    capture_device = cv2.VideoCapture(0)

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

        if len(frames) == NUM_FRAMES_ANALYZED and should_email(frames):
            send_email(receiver_email, image, text)

if __name__ == "__main__":
    main()