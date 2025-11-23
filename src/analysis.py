import cv2
import numpy as np

# ------------------------------
# Global state for the detector
# ------------------------------
backSub = cv2.createBackgroundSubtractorMOG2(
    history=300,        # how many frames to build background
    varThreshold=16,    # sensitivity to changes (lower = more sensitive)
    detectShadows=False # keep it simple
)

suspicion = 0.0  # runs between 0 and 1


def should_notify(frame_float_0_to_1, roi_mask=None):
    global backSub, suspicion

    # 1. Convert normalized float frame [0,1] -> uint8 [0,255]
    frame_u8 = (frame_float_0_to_1 * 255).astype("uint8")

    # 2. Apply background subtractor to get foreground (moving) mask
    fg_mask = backSub.apply(frame_u8)  # 0 = background, 255 = moving

    # 3. Restrict to ROI if provided
    if roi_mask is not None:
        fg_mask = cv2.bitwise_and(fg_mask, fg_mask, mask=roi_mask)

    # 4. Compute motion fraction: how many pixels are "moving"
    motion_fraction = np.mean(fg_mask > 0)

    # 5. Update suspicion score with simple temporal smoothing
    MOTION_THRESHOLD = 0.015   # 1.5% of pixels moving = "something's happening" (lower = more sensitive)
    INCREASE_RATE    = 0.12   # how fast suspicion rises when there's motion (higher = faster)
    DECREASE_RATE    = 0.04   # how fast suspicion falls when it's calm (lower = slower to calm)

    if motion_fraction > MOTION_THRESHOLD:
        suspicion = min(1.0, suspicion + INCREASE_RATE)
    else:
        suspicion = max(0.0, suspicion - DECREASE_RATE)

    # 6. Final decision: is someone messing with my stuff?
    TRIGGER_THRESHOLD = 0.4  # Lower threshold = easier to trigger alarm
    alarm = suspicion > TRIGGER_THRESHOLD

    return alarm, motion_fraction, fg_mask, suspicion


