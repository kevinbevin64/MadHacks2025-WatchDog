//
//  ContentView.swift
//  WatchDog
//
//  Created by Kevin Chen on 11/22/25.
//

import SwiftUI

struct ContentView: View {
    @State private var deviceToken: String? = nil
    @State private var notificationStatus: String = "Initializing..."
    @State private var lastNotification: [AnyHashable: Any]? = nil
    
    var body: some View {
        VStack(spacing: 20) {
            Text("WatchDog")
                .font(.largeTitle)
                .fontWeight(.bold)
                .padding(.top, 40)
            
            Text("Push Notifications")
                .font(.title2)
                .foregroundColor(.secondary)
            
            Divider()
                .padding(.vertical, 20)
            
            // Device Token Status
            VStack(alignment: .leading, spacing: 8) {
                Text("Status:")
                    .font(.headline)
                Text(notificationStatus)
                    .font(.body)
                    .foregroundColor(deviceToken != nil ? .green : .orange)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding()
            .background(Color(.systemGray6))
            .cornerRadius(10)
            
            // Device Token Display
            if let token = deviceToken {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Device Token:")
                        .font(.headline)
                    Text(token)
                        .font(.system(.caption, design: .monospaced))
                        .textSelection(.enabled)
                        .lineLimit(nil)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
                .background(Color(.systemGray6))
                .cornerRadius(10)
            }
            
            // Last Notification
            if let notification = lastNotification {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Last Notification:")
                        .font(.headline)
                    Text(formatNotification(notification))
                        .font(.system(.caption, design: .monospaced))
                        .textSelection(.enabled)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
                .background(Color(.systemBlue).opacity(0.1))
                .cornerRadius(10)
            }
            
            Spacer()
        }
        .padding()
        .onAppear {
            setupNotifications()
        }
    }
    
    func setupNotifications() {
        // Listen for device token
        NotificationCenter.default.addObserver(
            forName: NSNotification.Name("DeviceTokenReceived"),
            object: nil,
            queue: .main
        ) { notification in
            if let token = notification.userInfo?["token"] as? String {
                deviceToken = token
                notificationStatus = "Registered for push notifications"
            }
        }
        
        // Listen for token errors
        NotificationCenter.default.addObserver(
            forName: NSNotification.Name("DeviceTokenError"),
            object: nil,
            queue: .main
        ) { notification in
            if let error = notification.userInfo?["error"] as? String {
                notificationStatus = "Error: \(error)"
            }
        }
        
        // Listen for notifications
        NotificationCenter.default.addObserver(
            forName: NSNotification.Name("NotificationReceived"),
            object: nil,
            queue: .main
        ) { notification in
            lastNotification = notification.userInfo
        }
        
        // Listen for background notifications
        NotificationCenter.default.addObserver(
            forName: NSNotification.Name("BackgroundNotificationReceived"),
            object: nil,
            queue: .main
        ) { notification in
            lastNotification = notification.userInfo
        }
    }
    
    func formatNotification(_ notification: [AnyHashable: Any]) -> String {
        if let jsonData = try? JSONSerialization.data(withJSONObject: notification, options: .prettyPrinted),
           let jsonString = String(data: jsonData, encoding: .utf8) {
            return jsonString
        }
        return String(describing: notification)
    }
}

#Preview {
    ContentView()
}
