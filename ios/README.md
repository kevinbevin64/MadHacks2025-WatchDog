# WatchDog iOS App

SwiftUI app for receiving APNS push notifications.

## Setup

### 1. Enable Push Notifications Capability

1. Open the project in Xcode
2. Select your target → Signing & Capabilities
3. Click "+ Capability"
4. Add "Push Notifications"
5. Add "Background Modes" and enable "Remote notifications"

### 2. Configure APNS

1. In Apple Developer Portal, create an App ID with Push Notifications enabled
2. Create an APNs Key or Certificate
3. Configure your backend server to send push notifications using the APNs key/certificate

### 3. Update Backend Integration

In `WatchDogApp.swift`, update the `sendDeviceTokenToServer()` method to send the device token to your backend:

```swift
func sendDeviceTokenToServer(_ token: String) {
    let url = URL(string: "https://your-backend.com/api/register-device")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    
    let body: [String: Any] = [
        "device_token": token,
        "platform": "ios"
    ]
    
    request.httpBody = try? JSONSerialization.data(withJSONObject: body)
    
    URLSession.shared.dataTask(with: request) { data, response, error in
        if let error = error {
            print("Error sending device token: \(error)")
        } else {
            print("Device token sent successfully")
        }
    }.resume()
}
```

## Features

- ✅ Automatic push notification registration
- ✅ Device token display in UI
- ✅ Notification handling (foreground, background, and when app is closed)
- ✅ Status display for registration state
- ✅ Last notification display

## Testing

1. Run the app on a physical iOS device (push notifications don't work on simulator)
2. Grant notification permissions when prompted
3. The device token will be displayed in the app
4. Send a test push notification from your backend to verify it works

## Notes

- Push notifications require a physical device (not simulator)
- You need an Apple Developer account to test push notifications
- The device token is unique per app installation

