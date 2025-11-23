//
//  WatchDogApp.swift
//  WatchDog
//
//  Created by Kevin Chen on 11/22/25.
//

import SwiftUI
import UserNotifications

@main
struct WatchDogApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

// AppDelegate for handling push notifications
class AppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {
    
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        
        // Set up notification center delegate
        UNUserNotificationCenter.current().delegate = self
        
        // Check if app was launched from a notification tap
        if let notificationPayload = launchOptions?[.remoteNotification] as? [AnyHashable: Any] {
            print("App launched from notification: \(notificationPayload)")
            // Post notification so UI can update when it loads
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                NotificationCenter.default.post(name: NSNotification.Name("NotificationReceived"), object: nil, userInfo: notificationPayload)
            }
        }
        
        // Request notification permissions
        requestNotificationPermissions()
        
        // Register for remote notifications
        application.registerForRemoteNotifications()
        
        return true
    }
    
    // MARK: - Notification Permissions
    
    func requestNotificationPermissions() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { granted, error in
            if granted {
                print("Notification permission granted")
                DispatchQueue.main.async {
                    UIApplication.shared.registerForRemoteNotifications()
                }
            } else {
                print("Notification permission denied: \(error?.localizedDescription ?? "Unknown error")")
            }
        }
    }
    
    // MARK: - Remote Notification Registration
    
    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        let tokenParts = deviceToken.map { data in String(format: "%02.2hhx", data) }
        let token = tokenParts.joined()
        print("Device Token: \(token)")
        
        // TODO: Send device token to your backend server
        sendDeviceTokenToServer(token)
        
        // Post notification to update UI
        NotificationCenter.default.post(name: NSNotification.Name("DeviceTokenReceived"), object: nil, userInfo: ["token": token])
    }
    
    func application(_ application: UIApplication, didFailToRegisterForRemoteNotificationsWithError error: Error) {
        print("Failed to register for remote notifications: \(error.localizedDescription)")
        NotificationCenter.default.post(name: NSNotification.Name("DeviceTokenError"), object: nil, userInfo: ["error": error.localizedDescription])
    }
    
    // MARK: - Handle Notifications
    
    func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification, withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        // Show notification even when app is in foreground
        completionHandler([.alert, .sound, .badge])
    }
    
    func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse, withCompletionHandler completionHandler: @escaping () -> Void) {
        // Handle notification tap - this is called when user taps a notification
        // Works even if app was completely terminated
        let userInfo = response.notification.request.content.userInfo
        print("Notification tapped - app may have been terminated: \(userInfo)")
        
        // Post notification to update UI (app will be launched if it was terminated)
        NotificationCenter.default.post(name: NSNotification.Name("NotificationReceived"), object: nil, userInfo: userInfo)
        
        completionHandler()
    }
    
    // MARK: - Background Notifications
    
    func application(_ application: UIApplication, didReceiveRemoteNotification userInfo: [AnyHashable: Any], fetchCompletionHandler completionHandler: @escaping (UIBackgroundFetchResult) -> Void) {
        // This is called when app is in BACKGROUND (not terminated)
        // For terminated apps, iOS just shows the notification - no code runs until user taps
        print("Background notification received (app is in background): \(userInfo)")
        
        // Post notification to update UI when app comes to foreground
        NotificationCenter.default.post(name: NSNotification.Name("BackgroundNotificationReceived"), object: nil, userInfo: userInfo)
        
        completionHandler(.newData)
    }
    
    // MARK: - Helper Methods
    
    func sendDeviceTokenToServer(_ token: String) {
        // TODO: Implement API call to send device token to your backend
        // Example:
        // let url = URL(string: "https://your-backend.com/api/register-device")!
        // var request = URLRequest(url: url)
        // request.httpMethod = "POST"
        // request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        // let body = ["device_token": token, "platform": "ios"]
        // request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        // URLSession.shared.dataTask(with: request).resume()
        
        print("TODO: Send device token to server: \(token)")
    }
}
