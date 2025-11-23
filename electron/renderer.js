const videoFeed = document.getElementById('videoFeed');
const startButton = document.getElementById('startButton');
const status = document.getElementById('status');

let isDetecting = false;
let videoStream = null;

// Connect to video feed from Python server
function startVideoFeed() {
    // Check if server is running first
    checkServerConnection().then(() => {
        status.textContent = 'Connecting to video feed...';
        status.style.color = '#fbbf24';
        
        // For MJPEG streams, use img tag with timestamp to prevent caching
        const videoUrl = 'http://localhost:8080/video_feed?t=' + Date.now();
        videoFeed.src = videoUrl;
        
        videoFeed.onerror = () => {
            status.textContent = 'Error: Could not load video feed';
            status.style.color = '#ef4444';
            // Retry after 2 seconds
            setTimeout(startVideoFeed, 2000);
        };
        
        videoFeed.onload = () => {
            status.textContent = 'Video feed connected';
            status.style.color = '#4ade80';
        };
    }).catch(() => {
        status.textContent = 'Error: Server not running. Start server.py first.';
        status.style.color = '#ef4444';
        // Retry after 3 seconds
        setTimeout(startVideoFeed, 3000);
    });
}

// Check if server is running
async function checkServerConnection() {
    return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
            reject(new Error('Server not available'));
        }, 2000);
        
        fetch('http://localhost:8080/health', {
            method: 'GET'
        })
        .then(response => {
            clearTimeout(timeout);
            if (response.ok) {
                return response.json();
            } else {
                throw new Error('Server returned error');
            }
        })
        .then(data => {
            if (data.camera === 'unavailable') {
                console.warn('Camera is not available');
            }
            resolve(true);
        })
        .catch(error => {
            clearTimeout(timeout);
            reject(error);
        });
    });
}

// Start motion detection
async function startMotionDetection() {
    try {
        const response = await fetch('http://localhost:8080/start_detection', {
            method: 'POST'
        });
        
        if (response.ok) {
            isDetecting = true;
            startButton.textContent = 'Stop Motion Detection';
            startButton.classList.add('detecting');
            status.textContent = 'Motion Detection Active';
            status.classList.add('detecting');
            
            // Start polling for motion alerts
            pollMotionStatus();
        } else {
            throw new Error('Failed to start detection');
        }
    } catch (error) {
        console.error('Error starting motion detection:', error);
        status.textContent = 'Error: Could not start detection';
        status.style.color = '#ef4444';
    }
}

// Stop motion detection
async function stopMotionDetection() {
    try {
        const response = await fetch('http://localhost:8080/stop_detection', {
            method: 'POST'
        });
        
        if (response.ok) {
            isDetecting = false;
            startButton.textContent = 'Start Motion Detection';
            startButton.classList.remove('detecting');
            status.textContent = 'Motion Detection Stopped';
            status.classList.remove('detecting');
            status.classList.remove('alarm');
        }
    } catch (error) {
        console.error('Error stopping motion detection:', error);
    }
}

// Poll for motion status
async function pollMotionStatus() {
    if (!isDetecting) return;
    
    try {
        const response = await fetch('http://localhost:8080/motion_status');
        const data = await response.json();
        
        if (data.alarm) {
            status.textContent = `ALARM: Motion Detected! (${data.email_attempts} attempts)`;
            status.classList.add('alarm');
            status.classList.remove('detecting', 'warning');
            status.style.color = ''; // Clear inline style to use CSS class
        } else {
            const suspicionPercent = data.suspicion * 100;
            status.textContent = `Detecting... Suspicion: ${suspicionPercent.toFixed(1)}%`;
            status.classList.remove('alarm');
            status.style.color = ''; // Clear inline style to use CSS class
            
            // Color based on suspicion level: yellow at 50%, red at 75%
            if (data.suspicion >= 0.75) {
                status.classList.add('alarm');
                status.classList.remove('detecting', 'warning');
            } else if (data.suspicion >= 0.50) {
                status.classList.add('warning');
                status.classList.remove('detecting', 'alarm');
            } else {
                status.classList.add('detecting');
                status.classList.remove('warning', 'alarm');
            }
        }
    } catch (error) {
        console.error('Error polling motion status:', error);
    }
    
    // Poll every 500ms
    setTimeout(pollMotionStatus, 500);
}

// Button click handler
startButton.addEventListener('click', () => {
    if (isDetecting) {
        stopMotionDetection();
    } else {
        startMotionDetection();
    }
});

// Initialize video feed when page loads
window.addEventListener('load', () => {
    startVideoFeed();
});

