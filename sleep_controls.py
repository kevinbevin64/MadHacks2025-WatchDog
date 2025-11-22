import platform
import ctypes
import subprocess
import sys

class SleepController:
    """Cross-platform controller to toggle sleep prevention on and off."""
    
    def __init__(self):
        self.is_awake = False
        self.platform = platform.system()
        self._platform_specific_init()
        self.current_state = None
    
    def _platform_specific_init(self):
        """Initialize platform-specific resources."""
        if self.platform == "Windows":
            # Windows constants for SetThreadExecutionState
            self.ES_CONTINUOUS = 0x80000000
            self.ES_SYSTEM_REQUIRED = 0x00000001
            self.ES_DISPLAY_REQUIRED = 0x00000002
            self.kernel32 = ctypes.windll.kernel32
        elif self.platform == "Darwin":  # macOS
            try:
                import objc
                from AppKit import NSApplication, NSApp
                self.NSApplication = NSApplication
                self.NSApp = NSApp
            except ImportError:
                self.NSApplication = None
                print("Warning: PyObjC not available. Install with: pip install pyobjc")
        elif self.platform == "Linux":
            # Linux uses systemd-inhibit or xset
            self._check_linux_dependencies()
    
    def _check_linux_dependencies(self):
        """Check if required Linux tools are available."""
        try:
            subprocess.run(['which', 'systemd-inhibit'], 
                         capture_output=True, check=True)
            self.use_systemd = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.use_systemd = False
            # Fallback to xset if available
            try:
                subprocess.run(['which', 'xset'], 
                             capture_output=True, check=True)
                self.use_xset = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                self.use_xset = False
                print("Warning: Neither systemd-inhibit nor xset found. Sleep prevention may not work.")
    
    def prevent_sleep(self, keep_screen_awake=True):
        """Prevent the system from going to sleep (cross-platform)."""
        if self.is_awake:
            print("Sleep prevention already enabled")
            return
        
        if self.platform == "Windows":
            self._prevent_sleep_windows(keep_screen_awake)
        elif self.platform == "Darwin":  # macOS
            self._prevent_sleep_macos(keep_screen_awake)
        elif self.platform == "Linux":
            self._prevent_sleep_linux(keep_screen_awake)
        else:
            print(f"Unsupported platform: {self.platform}")
            return
        
        if self.is_awake:
            print(f"Sleep prevention enabled on {self.platform}")
    
    def _prevent_sleep_windows(self, keep_screen_awake):
        """Windows implementation using SetThreadExecutionState."""
        flags = self.ES_CONTINUOUS | self.ES_SYSTEM_REQUIRED
        if keep_screen_awake:
            flags |= self.ES_DISPLAY_REQUIRED
        
        self.current_state = flags
        result = self.kernel32.SetThreadExecutionState(flags)
        if result:
            self.is_awake = True
        else:
            error = ctypes.get_last_error()
            print(f"Failed to enable sleep prevention. Error code: {error}")
    
    def _prevent_sleep_macos(self, keep_screen_awake):
        """macOS implementation using IOKit."""
        try:
            import ctypes.util
            # Load IOKit framework
            iokit = ctypes.CDLL('/System/Library/Frameworks/IOKit.framework/IOKit')
            
            # IOPMAssertionCreateWithName constants
            kIOPMAssertionTypeNoIdleSleep = ctypes.c_char_p(b"PreventUserIdleSystemSleep")
            kIOPMAssertionTypeNoDisplaySleep = ctypes.c_char_p(b"PreventUserIdleDisplaySleep")
            
            # Create assertion
            assertion_id = ctypes.c_uint32()
            
            # Prevent system sleep
            result = iokit.IOPMAssertionCreateWithName(
                kIOPMAssertionTypeNoIdleSleep,
                1,  # kIOPMAssertionLevelOn
                kIOPMAssertionTypeNoIdleSleep,
                ctypes.byref(assertion_id)
            )
            
            if result == 0:
                self.current_state = {'system': assertion_id.value}
                self.is_awake = True
                
                # Prevent display sleep if requested
                if keep_screen_awake:
                    display_id = ctypes.c_uint32()
                    result = iokit.IOPMAssertionCreateWithName(
                        kIOPMAssertionTypeNoDisplaySleep,
                        1,
                        kIOPMAssertionTypeNoDisplaySleep,
                        ctypes.byref(display_id)
                    )
                    if result == 0:
                        self.current_state['display'] = display_id.value
            else:
                print(f"Failed to enable sleep prevention. Error code: {result}")
        except Exception as e:
            print(f"Error setting up macOS sleep prevention: {e}")
            print("Trying alternative method...")
            # Fallback: use caffeinate command
            try:
                self.caffeinate_process = subprocess.Popen(
                    ['caffeinate', '-d', '-i'] if keep_screen_awake else ['caffeinate', '-i'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                self.current_state = {'process': self.caffeinate_process}
                self.is_awake = True
            except Exception as e2:
                print(f"Fallback method also failed: {e2}")
    
    def _prevent_sleep_linux(self, keep_screen_awake):
        """Linux implementation using systemd-inhibit or xset."""
        if self.use_systemd:
            try:
                # Use systemd-inhibit to prevent sleep
                cmd = ['systemd-inhibit', '--what=idle:sleep', '--who=SleepController', 
                       '--why=Preventing system sleep', '--mode=block', 'sleep', 'infinity']
                if keep_screen_awake:
                    cmd[1] = 'idle:sleep:handle-lid-switch'
                
                self.inhibit_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                self.current_state = {'process': self.inhibit_process}
                self.is_awake = True
            except Exception as e:
                print(f"Failed to use systemd-inhibit: {e}")
                self._prevent_sleep_linux_xset(keep_screen_awake)
        elif self.use_xset:
            self._prevent_sleep_linux_xset(keep_screen_awake)
        else:
            print("No suitable method available for Linux sleep prevention")
    
    def _prevent_sleep_linux_xset(self, keep_screen_awake):
        """Linux fallback using xset."""
        try:
            # Disable screen saver and DPMS
            subprocess.run(['xset', 's', 'off'], check=True)
            subprocess.run(['xset', '-dpms'], check=True)
            if keep_screen_awake:
                subprocess.run(['xset', 's', 'noblank'], check=True)
            self.current_state = {'method': 'xset'}
            self.is_awake = True
        except Exception as e:
            print(f"Failed to use xset: {e}")
    
    def allow_sleep(self):
        """Allow the system to go to sleep normally (cross-platform)."""
        if not self.is_awake:
            print("Sleep prevention already disabled")
            return
        
        if self.platform == "Windows":
            self._allow_sleep_windows()
        elif self.platform == "Darwin":  # macOS
            self._allow_sleep_macos()
        elif self.platform == "Linux":
            self._allow_sleep_linux()
        
        if not self.is_awake:
            print(f"Sleep prevention disabled on {self.platform}")
    
    def _allow_sleep_windows(self):
        """Windows implementation to allow sleep."""
        result = self.kernel32.SetThreadExecutionState(self.ES_CONTINUOUS)
        if result:
            self.is_awake = False
            self.current_state = None
        else:
            error = ctypes.get_last_error()
            print(f"Failed to disable sleep prevention. Error code: {error}")
    
    def _allow_sleep_macos(self):
        """macOS implementation to allow sleep."""
        if self.current_state and 'process' in self.current_state:
            # Using caffeinate process
            try:
                self.current_state['process'].terminate()
                self.current_state['process'].wait()
            except Exception as e:
                print(f"Error terminating caffeinate: {e}")
        elif self.current_state:
            # Using IOKit assertions
            try:
                import ctypes.util
                iokit = ctypes.CDLL('/System/Library/Frameworks/IOKit.framework/IOKit')
                
                if 'system' in self.current_state:
                    iokit.IOPMAssertionRelease(self.current_state['system'])
                if 'display' in self.current_state:
                    iokit.IOPMAssertionRelease(self.current_state['display'])
            except Exception as e:
                print(f"Error releasing IOKit assertions: {e}")
        
        self.is_awake = False
        self.current_state = None
    
    def _allow_sleep_linux(self):
        """Linux implementation to allow sleep."""
        if self.current_state and 'process' in self.current_state:
            # Using systemd-inhibit process
            try:
                self.current_state['process'].terminate()
                self.current_state['process'].wait()
            except Exception as e:
                print(f"Error terminating inhibit process: {e}")
        elif self.current_state and self.current_state.get('method') == 'xset':
            # Restore xset settings
            try:
                subprocess.run(['xset', 's', 'default'], check=False)
                subprocess.run(['xset', '+dpms'], check=False)
            except Exception as e:
                print(f"Error restoring xset settings: {e}")
        
        self.is_awake = False
        self.current_state = None
    
    def refresh(self):
        """Refresh the sleep prevention state (useful if it gets cleared)."""
        if self.is_awake:
            # Re-apply the current state
            keep_screen = True  # Default to keeping screen on
            if self.platform == "Windows" and self.current_state:
                keep_screen = bool(self.current_state & self.ES_DISPLAY_REQUIRED)
            
            self.allow_sleep()
            self.prevent_sleep(keep_screen_awake=keep_screen)
            print("Sleep prevention refreshed")
        else:
            print("Sleep prevention not active")
    
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