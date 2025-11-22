import ctypes
from ctypes import wintypes

class SleepController:
    """Controller to toggle sleep prevention on and off using Windows APIs."""
    
    # Windows constants for SetThreadExecutionState
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002
    ES_AWAYMODE_REQUIRED = 0x00000040  # Prevents away mode
    
    def __init__(self):
        self.is_awake = False
        self.kernel32 = ctypes.windll.kernel32
        self.current_flags = None
    
    def prevent_sleep(self, keep_screen_awake=True):
        """Prevent the system from going to sleep."""
        if not self.is_awake:
            # ES_CONTINUOUS | ES_SYSTEM_REQUIRED | (optionally ES_DISPLAY_REQUIRED)
            flags = self.ES_CONTINUOUS | self.ES_SYSTEM_REQUIRED
            if keep_screen_awake:
                flags |= self.ES_DISPLAY_REQUIRED
            
            self.current_flags = flags
            result = self.kernel32.SetThreadExecutionState(flags)
            if result:
                self.is_awake = True
                print(f"Sleep prevention enabled (flags: 0x{flags:X})")
                print("This will show up in 'powercfg /requests'")
            else:
                error = ctypes.get_last_error()
                print(f"Failed to enable sleep prevention. Error code: {error}")
        else:
            print("Sleep prevention already enabled")
    
    def allow_sleep(self):
        """Allow the system to go to sleep normally."""
        if self.is_awake:
            # Clear the execution state by setting only ES_CONTINUOUS
            result = self.kernel32.SetThreadExecutionState(self.ES_CONTINUOUS)
            if result:
                self.is_awake = False
                self.current_flags = None
                print("Sleep prevention disabled")
            else:
                error = ctypes.get_last_error()
                print(f"Failed to disable sleep prevention. Error code: {error}")
        else:
            print("Sleep prevention already disabled")
    
    def refresh(self):
        """Refresh the sleep prevention state (useful if it gets cleared)."""
        if self.is_awake and self.current_flags:
            result = self.kernel32.SetThreadExecutionState(self.current_flags)
            if result:
                print("Sleep prevention refreshed")
            else:
                print("Failed to refresh sleep prevention")
    
    def toggle(self, keep_screen_awake=True):
        """Toggle sleep prevention on/off."""
        if self.is_awake:
            self.allow_sleep()
        else:
            self.prevent_sleep(keep_screen_awake=keep_screen_awake)


# Example usage:
if __name__ == "__main__":
    controller = SleepController()
    
    # Prevent sleep (both system and display)
    controller.prevent_sleep(keep_screen_awake=True)
    
    # Keep the script running so the power request stays active
    # The power request is maintained as long as the process is alive
    try:
        print("\nSleep prevention is active. Press Ctrl+C to stop...")
        print("The screen should not go to sleep while this script is running.")
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.allow_sleep()
        print("\nSleep prevention disabled. Exiting...")