# MadHacks2025-WatchDog

Motion detection system with Electron GUI.

## Dependencies

### Python Dependencies
- OpenCV
- NumPy
- wakepy
- Flask
- flask-cors

### Node.js Dependencies
- Electron

## Setup

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Install Node.js Dependencies
```bash
npm install
```

## Running the Application

### Step 1: Start the Python Server
```bash
python src/server.py
```

The server will start on `http://localhost:8080` and stream the video feed.

### Step 2: Start the Electron App
In a new terminal:
```bash
npm start
```

## Usage

1. The Electron app will open and display the video feed automatically
2. Click the green "Start Motion Detection" button to begin motion detection
3. The button will turn red and say "Stop Motion Detection" when active
4. Status updates will appear in the top-left corner of the video feed
5. When motion is detected, an alarm will be triggered and email attempts will be logged

## Development

To run Electron with DevTools:
```bash
npm run dev
```
