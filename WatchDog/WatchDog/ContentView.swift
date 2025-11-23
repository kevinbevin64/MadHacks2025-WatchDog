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
    @State private var disturbanceCount: Int = 0
    
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
            
            // Disturbance Counter
            VStack(spacing: 8) {
                Text("Disturbances Detected")
                    .font(.headline)
                Text("\(disturbanceCount)")
                    .font(.system(size: 48, weight: .bold))
                    .foregroundColor(.red)
            }
            .frame(maxWidth: .infinity)
            .padding()
            .background(Color(.systemRed).opacity(0.1))
            .cornerRadius(10)
            
            // Last Notification
            if let notification = lastNotification {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Last Notification:")
                        .font(.headline)
                    
                    // Check for payload at root level or nested
                    if let payload = notification["payload"] as? String, payload == "disturbance" {
                        Text("🚨 DISTURBANCE DETECTED")
                            .font(.title3)
                            .fontWeight(.bold)
                            .foregroundColor(.red)
                    } else if let aps = notification["aps"] as? [AnyHashable: Any],
                              let payload = aps["payload"] as? String,
                              payload == "disturbance" {
                        Text("🚨 DISTURBANCE DETECTED")
                            .font(.title3)
                            .fontWeight(.bold)
                            .foregroundColor(.red)
                    }
                    
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
            guard let userInfo = notification.userInfo else { return }
            lastNotification = userInfo
            
            // Check for payload at root level or nested
            var payloadValue: String? = nil
            if let payload = userInfo["payload"] as? String {
                payloadValue = payload
            } else if let aps = userInfo["aps"] as? [AnyHashable: Any],
                      let payload = aps["payload"] as? String {
                payloadValue = payload
            }
            
            if let payload = payloadValue, payload == "disturbance" {
                disturbanceCount += 1
                print("Disturbance detected! Count: \(disturbanceCount)")
            }
        }
        
        // Listen for background notifications
        NotificationCenter.default.addObserver(
            forName: NSNotification.Name("BackgroundNotificationReceived"),
            object: nil,
            queue: .main
        ) { notification in
            guard let userInfo = notification.userInfo else { return }
            lastNotification = userInfo
            
            // Check for payload at root level or nested
            var payloadValue: String? = nil
            if let payload = userInfo["payload"] as? String {
                payloadValue = payload
            } else if let aps = userInfo["aps"] as? [AnyHashable: Any],
                      let payload = aps["payload"] as? String {
                payloadValue = payload
            }
            
            if let payload = payloadValue, payload == "disturbance" {
                disturbanceCount += 1
                print("Disturbance detected! Count: \(disturbanceCount)")
            }
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

