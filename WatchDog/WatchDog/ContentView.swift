//
//  ContentView.swift
//  WatchDog
//
//  Created by Kevin Chen on 11/22/25.
//

import SwiftUI
import AVKit
import AVFoundation
import CoreMedia

struct ContentView: View {
    @State private var lastNotification: [AnyHashable: Any]? = nil
    @State private var disturbanceCount: Int = 0
    @State private var isDownloading = false
    @State private var downloadError: String? = nil
    @State private var showPlayer = false
    @State private var tempVideoURL: URL? = nil
    
    // UserDefaults key for persistence
    private let disturbanceCountKey = "disturbanceCount"
    
    // Configure your server URL here
    // private let serverURL = "http://localhost:8081"  // Change this to your server URL
    private let serverURL = "https://unspread-unchivalrous-jacquelynn.ngrok-free.dev"
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 24) {
                    // Header
                    VStack(spacing: 8) {
                        Image(systemName: "eye.fill")
                            .font(.system(size: 60))
                            .foregroundColor(.blue)
                            .padding(.top, 20)
                        
                        Text("Sentry")
                            .font(.system(size: 32, weight: .bold))
                        
                        Text("Motion Detection System")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                    .padding(.bottom, 8)
                    
                    // Disturbance Counter - Prominent Display
                    VStack(spacing: 16) {
                        HStack {
                            Image(systemName: "bell.badge.fill")
                                .font(.title2)
                                .foregroundColor(.red)
                            Text("Disturbances Detected")
                                .font(.headline)
                        }
                        
                        Text("\(disturbanceCount)")
                            .font(.system(size: 64, weight: .bold, design: .rounded))
                            .foregroundColor(.red)
                            .padding(.vertical, 8)
                        
                        if disturbanceCount == 0 {
                            Text("All clear")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                        } else {
                            Text("Motion detected \(disturbanceCount) time\(disturbanceCount == 1 ? "" : "s")")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                        }
                        
                        // Reset Button
                        if disturbanceCount > 0 {
                            Button(action: {
                                resetCounter()
                            }) {
                                HStack {
                                    Image(systemName: "arrow.counterclockwise")
                                    Text("Reset Counter")
                                }
                                .font(.subheadline)
                                .foregroundColor(.white)
                                .padding(.horizontal, 20)
                                .padding(.vertical, 10)
                                .background(Color.red)
                                .cornerRadius(10)
                            }
                            .padding(.top, 8)
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 24)
                    .padding(.horizontal, 20)
                    .background(
                        RoundedRectangle(cornerRadius: 16)
                            .fill(Color.red.opacity(0.1))
                            .overlay(
                                RoundedRectangle(cornerRadius: 16)
                                    .stroke(Color.red.opacity(0.3), lineWidth: 2)
                            )
                    )
                    
                    // Video Play Section
                    VStack(spacing: 16) {
                        HStack {
                            Image(systemName: "video.fill")
                                .foregroundColor(.blue)
                            Text("Video Recording")
                                .font(.headline)
                        }
                        
                        Button(action: {
                            downloadAndPlayVideo()
                        }) {
                            HStack {
                                if isDownloading {
                                    ProgressView()
                                        .progressViewStyle(CircularProgressViewStyle(tint: .white))
                                        .scaleEffect(0.8)
                                } else {
                                    Image(systemName: "play.circle.fill")
                                }
                                Text(isDownloading ? "Downloading..." : "Play Latest Video")
                            }
                            .font(.subheadline)
                            .foregroundColor(.white)
                            .padding(.horizontal, 20)
                            .padding(.vertical, 12)
                            .background(isDownloading ? Color.gray : Color.blue)
                            .cornerRadius(10)
                        }
                        .disabled(isDownloading)
                        
                        if let error = downloadError {
                            Text(error)
                                .font(.caption)
                                .foregroundColor(.red)
                                .multilineTextAlignment(.center)
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color(.systemGray6))
                    .cornerRadius(12)
                    
                    // Last Notification
                    if let notification = lastNotification {
                        VStack(alignment: .leading, spacing: 12) {
                            HStack {
                                Image(systemName: "bell.fill")
                                    .foregroundColor(.blue)
                                Text("Last Notification")
                                    .font(.headline)
                            }
                            
                            // Check for payload at root level or nested
                            if let payload = notification["payload"] as? String, payload == "disturbance" {
                                HStack {
                                    Image(systemName: "exclamationmark.triangle.fill")
                                        .foregroundColor(.red)
                                    Text("DISTURBANCE DETECTED")
                                        .font(.subheadline)
                                        .fontWeight(.bold)
                                        .foregroundColor(.red)
                                }
                                .padding(.vertical, 4)
                            } else if let aps = notification["aps"] as? [AnyHashable: Any],
                                      let payload = aps["payload"] as? String,
                                      payload == "disturbance" {
                                HStack {
                                    Image(systemName: "exclamationmark.triangle.fill")
                                        .foregroundColor(.red)
                                    Text("DISTURBANCE DETECTED")
                                        .font(.subheadline)
                                        .fontWeight(.bold)
                                        .foregroundColor(.red)
                                }
                                .padding(.vertical, 4)
                            }
                            
                            if let aps = notification["aps"] as? [AnyHashable: Any],
                               let alert = aps["alert"] as? [AnyHashable: Any] {
                                if let title = alert["title"] as? String {
                                    Text(title)
                                        .font(.subheadline)
                                        .fontWeight(.semibold)
                                }
                                if let body = alert["body"] as? String {
                                    Text(body)
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            }
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding()
                        .background(Color(.systemGray6))
                        .cornerRadius(12)
                    }
                    
                    Spacer(minLength: 20)
                }
                .padding(.horizontal, 20)
                .padding(.vertical, 16)
            }
            .navigationBarHidden(true)
        }
        .onAppear {
            loadDisturbanceCount()
            setupNotifications()
        }
        .sheet(isPresented: $showPlayer) {
            if let videoURL = tempVideoURL {
                VideoPlayerView(videoURL: videoURL, onError: { errorMessage in
                    downloadError = errorMessage
                    showPlayer = false
                    // Clean up temp file
                    try? FileManager.default.removeItem(at: videoURL)
                    tempVideoURL = nil
                })
                .onDisappear {
                    // Clean up temp file when player is dismissed
                    if let url = tempVideoURL {
                        try? FileManager.default.removeItem(at: url)
                        tempVideoURL = nil
                    }
                }
            }
        }
    }
    
    // Load disturbance count from UserDefaults
    func loadDisturbanceCount() {
        disturbanceCount = UserDefaults.standard.integer(forKey: disturbanceCountKey)
    }
    
    // Save disturbance count to UserDefaults
    func saveDisturbanceCount() {
        UserDefaults.standard.set(disturbanceCount, forKey: disturbanceCountKey)
    }
    
    // Reset counter
    func resetCounter() {
        disturbanceCount = 0
        saveDisturbanceCount()
    }
    
    // Download video from server and play it
    func downloadAndPlayVideo() {
        // First, fetch the JSON
        fetchJSON()
        
        guard let url = URL(string: "\(serverURL)/video") else {
            downloadError = "Invalid server URL"
            return
        }
        
        isDownloading = true
        downloadError = nil
        
        // Create request with headers (for ngrok if needed)
        var request = URLRequest(url: url)
        request.setValue("application/octet-stream", forHTTPHeaderField: "Accept")
        // Add ngrok-skip-browser-warning header if using ngrok
        if serverURL.contains("ngrok") {
            request.setValue("true", forHTTPHeaderField: "ngrok-skip-browser-warning")
        }
        
        // Download directly to memory instead of using downloadTask
        let task = URLSession.shared.dataTask(with: request) { [self] data, response, error in
            DispatchQueue.main.async {
                isDownloading = false
            }
            
            if let error = error {
                print("Download error: \(error.localizedDescription)")
                DispatchQueue.main.async {
                    downloadError = "Download failed: \(error.localizedDescription)"
                }
                return
            }
            
            // Check HTTP response
            if let httpResponse = response as? HTTPURLResponse {
                print("HTTP Status: \(httpResponse.statusCode)")
                if httpResponse.statusCode != 200 {
                    DispatchQueue.main.async {
                        downloadError = "Server error: HTTP \(httpResponse.statusCode)"
                    }
                    return
                }
                
                // Log content type
                if let contentType = httpResponse.value(forHTTPHeaderField: "Content-Type") {
                    print("Content-Type: \(contentType)")
                }
                
                // Log content length
                if let contentLength = httpResponse.value(forHTTPHeaderField: "Content-Length"),
                   let length = Int64(contentLength) {
                    print("Content-Length: \(length) bytes")
                }
            }
            
            guard let data = data else {
                DispatchQueue.main.async {
                    downloadError = "No data received"
                }
                return
            }
            
            print("Downloaded \(data.count) bytes to memory")
            
            if data.isEmpty {
                DispatchQueue.main.async {
                    downloadError = "Downloaded file is empty"
                }
                return
            }
            
            // Write data directly to a temp file we control
            let tempDir = FileManager.default.temporaryDirectory
            let tempURL = tempDir.appendingPathComponent("temp_video_\(UUID().uuidString).avi")
            
            // Remove old temp file if it exists
            if FileManager.default.fileExists(atPath: tempURL.path) {
                try? FileManager.default.removeItem(at: tempURL)
            }
            
            // Write data to file
            do {
                try data.write(to: tempURL)
                print("Video written to temp location: \(tempURL.path)")
                print("File size on disk: \(data.count) bytes")
                
                // Verify file was written
                if FileManager.default.fileExists(atPath: tempURL.path) {
                    let fileAttributes = try FileManager.default.attributesOfItem(atPath: tempURL.path)
                    if let fileSize = fileAttributes[.size] as? Int64 {
                        print("Verified file size: \(fileSize) bytes")
                    }
                }
                
                // Process video on main thread
                DispatchQueue.main.async {
                    self.processVideo(url: tempURL)
                }
            } catch {
                print("Failed to write video to temp: \(error)")
                DispatchQueue.main.async {
                    downloadError = "Failed to save video: \(error.localizedDescription)"
                }
            }
        }
        
        task.resume()
    }
    
    // Process video: print codec info and convert if needed
    func processVideo(url: URL) {
        let asset = AVAsset(url: url)
        
        // Load essential properties first
        asset.loadValuesAsynchronously(forKeys: ["playable", "tracks"]) {
            var playableError: NSError?
            var tracksError: NSError?
            let playableStatus = asset.statusOfValue(forKey: "playable", error: &playableError)
            let tracksStatus = asset.statusOfValue(forKey: "tracks", error: &tracksError)
            
            DispatchQueue.main.async {
                let playable = playableStatus == .loaded && asset.isPlayable
                print("Video is playable: \(playable) (status: \(playableStatus.rawValue))")
                
                if let error = playableError {
                    print("Error loading playable status: \(error.localizedDescription)")
                }
                if let error = tracksError {
                    print("Error loading tracks: \(error.localizedDescription)")
                }
                
                // Print codec information using async loading
                let videoTracks = asset.tracks(withMediaType: .video)
                print("Video tracks: \(videoTracks.count) (tracks status: \(tracksStatus.rawValue))")
                
                // If no tracks, try to get more info about the asset
                if videoTracks.isEmpty {
                    print("⚠️ No video tracks found!")
                    print("Asset duration: \(asset.duration.seconds) seconds")
                    print("Asset metadata: \(asset.metadata.count) items")
                    
                    // Check all track types
                    let allTracks = asset.tracks
                    print("Total tracks (all types): \(allTracks.count)")
                    for track in allTracks {
                        print("  Track type: \(track.mediaType.rawValue)")
                    }
                    
                    // Try to play anyway - sometimes tracks load later
                    print("Attempting to play anyway...")
                    self.tempVideoURL = url
                    self.downloadError = nil
                    self.isDownloading = false
                    self.showPlayer = true
                    return
                }
                
                // Load format descriptions asynchronously using the traditional method
                var loadedTracks: [(track: AVAssetTrack, formatDescriptions: [CMFormatDescription])] = []
                let dispatchGroup = DispatchGroup()
                
                for (index, track) in videoTracks.enumerated() {
            dispatchGroup.enter()
            track.loadValuesAsynchronously(forKeys: ["formatDescriptions"]) {
                var error: NSError?
                let status = track.statusOfValue(forKey: "formatDescriptions", error: &error)
                
                defer { dispatchGroup.leave() }
                
                if let error = error {
                    print("Error loading format descriptions for track \(index): \(error.localizedDescription)")
                    return
                }
                
                if status != .loaded {
                    print("Format descriptions not loaded for track \(index), status: \(status.rawValue)")
                    return
                }
                
                // Access formatDescriptions property (deprecated but works)
                // formatDescriptions returns [CMFormatDescription]
                let formatDescriptions = track.formatDescriptions as? [CMFormatDescription] ?? []
                
                guard !formatDescriptions.isEmpty else {
                    print("No format descriptions for track \(index)")
                    print("Raw formatDescriptions count: \(track.formatDescriptions.count)")
                    return
                }
                
                loadedTracks.append((track: track, formatDescriptions: formatDescriptions))
                
                print("\n--- Video Track \(index) ---")
                print("Format descriptions count: \(formatDescriptions.count)")
                
                // Get codec information
                for (descIndex, formatDescription) in formatDescriptions.enumerated() {
                    let codecType = CMFormatDescriptionGetMediaSubType(formatDescription)
                    let codecString = fourCharCodeToString(codecType)
                    let codecHex = String(format: "0x%08X", codecType)
                    print("Format \(descIndex) - Codec: \(codecString) (\(codecHex))")
                    
                    // Check dimensions
                    let dimensions = CMVideoFormatDescriptionGetDimensions(formatDescription)
                    print("  Dimensions: \(Int(dimensions.width))x\(Int(dimensions.height))")
                    
                    // Check if it's a supported codec
                    let isH264 = codecType == kCMVideoCodecType_H264
                    let isH265 = codecType == kCMVideoCodecType_HEVC
                    let isSupported = isH264 || isH265
                    print("  Is H.264/H.265: \(isSupported)")
                    
                    // Also check the raw values for debugging
                    print("  H.264 constant: \(String(format: "0x%08X", kCMVideoCodecType_H264))")
                    print("  HEVC constant: \(String(format: "0x%08X", kCMVideoCodecType_HEVC))")
                }
                }
                }
                
                // Wait for all tracks to load, then proceed
                dispatchGroup.notify(queue: .main) {
                    // Check if codec is supported
                    let isSupported = self.isCodecSupported(tracks: loadedTracks)
                    
                    print("\n=== Codec Detection Summary ===")
                    print("Video is playable: \(playable)")
                    print("Loaded tracks count: \(loadedTracks.count)")
                    print("Is codec supported: \(isSupported)")
                    
                    // If video is playable, just show it regardless of codec detection
                    // (Sometimes isPlayable is more reliable than our codec detection)
                    if playable {
                        print("✅ Video is playable, showing directly")
                        self.tempVideoURL = url
                        self.downloadError = nil
                        self.isDownloading = false
                        self.showPlayer = true
                    } else if !loadedTracks.isEmpty && !isSupported {
                        print("\n⚠️ Video codec not supported, attempting conversion...")
                        self.convertVideoToH264(sourceURL: url) { convertedURL in
                            DispatchQueue.main.async {
                                if let convertedURL = convertedURL {
                                    // Clean up original
                                    try? FileManager.default.removeItem(at: url)
                                    self.tempVideoURL = convertedURL
                                    self.downloadError = nil
                                    self.isDownloading = false
                                    self.showPlayer = true
                                } else {
                                    // If conversion fails, try original anyway
                                    print("Conversion failed, trying original file anyway...")
                                    self.tempVideoURL = url
                                    self.downloadError = nil
                                    self.isDownloading = false
                                    self.showPlayer = true
                                }
                            }
                        }
                    } else {
                        // Video might be playable even if detection failed, try it
                        print("⚠️ Codec detection uncertain, trying to play anyway...")
                        self.tempVideoURL = url
                        self.downloadError = nil
                        self.isDownloading = false
                        self.showPlayer = true
                    }
                }
            }
        }
    }
    
    // Check if codec is supported (H.264 or H.265)
    func isCodecSupported(tracks: [(track: AVAssetTrack, formatDescriptions: [CMFormatDescription])]) -> Bool {
        for (trackIndex, (_, formatDescriptions)) in tracks.enumerated() {
            for (descIndex, formatDescription) in formatDescriptions.enumerated() {
                let codecType = CMFormatDescriptionGetMediaSubType(formatDescription)
                let h264Value = kCMVideoCodecType_H264
                let hevcValue = kCMVideoCodecType_HEVC
                
                print("Track \(trackIndex), Format \(descIndex): Comparing codec \(String(format: "0x%08X", codecType))")
                print("  H.264 constant: \(String(format: "0x%08X", h264Value))")
                print("  HEVC constant: \(String(format: "0x%08X", hevcValue))")
                print("  Is H.264: \(codecType == h264Value)")
                print("  Is HEVC: \(codecType == hevcValue)")
                
                if codecType == h264Value || codecType == hevcValue {
                    print("  ✅ Codec is supported!")
                    return true
                }
            }
        }
        print("  ❌ No supported codec found")
        return false
    }
    
    // Convert four character code to string
    func fourCharCodeToString(_ code: FourCharCode) -> String {
        let bytes = [
            UInt8((code >> 24) & 0xFF),
            UInt8((code >> 16) & 0xFF),
            UInt8((code >> 8) & 0xFF),
            UInt8(code & 0xFF)
        ]
        return String(bytes: bytes, encoding: .ascii) ?? "Unknown"
    }
    
    // Convert video to H.264 format
    func convertVideoToH264(sourceURL: URL, completion: @escaping (URL?) -> Void) {
        let asset = AVAsset(url: sourceURL)
        
        // Create output URL
        let tempDir = FileManager.default.temporaryDirectory
        let outputURL = tempDir.appendingPathComponent("converted_\(UUID().uuidString).mp4")
        
        // Remove old file if exists
        if FileManager.default.fileExists(atPath: outputURL.path) {
            try? FileManager.default.removeItem(at: outputURL)
        }
        
        // Get video track
        guard let videoTrack = asset.tracks(withMediaType: .video).first else {
            print("No video track found for conversion")
            completion(nil)
            return
        }
        
        // Create export session
        guard let exportSession = AVAssetExportSession(asset: asset, presetName: AVAssetExportPresetHighestQuality) else {
            print("Failed to create export session")
            completion(nil)
            return
        }
        
        exportSession.outputURL = outputURL
        exportSession.outputFileType = .mp4
        exportSession.videoComposition = createVideoComposition(for: videoTrack, in: asset)
        
        print("Starting video conversion...")
        exportSession.exportAsynchronously {
            switch exportSession.status {
            case .completed:
                print("✅ Video conversion completed: \(outputURL.path)")
                completion(outputURL)
            case .failed:
                print("❌ Video conversion failed: \(exportSession.error?.localizedDescription ?? "Unknown error")")
                completion(nil)
            case .cancelled:
                print("⚠️ Video conversion cancelled")
                completion(nil)
            default:
                print("⚠️ Video conversion status: \(exportSession.status.rawValue)")
                completion(nil)
            }
        }
    }
    
    // Create video composition for export
    func createVideoComposition(for track: AVAssetTrack, in asset: AVAsset) -> AVMutableVideoComposition? {
        let videoComposition = AVMutableVideoComposition()
        videoComposition.renderSize = track.naturalSize
        videoComposition.frameDuration = CMTime(value: 1, timescale: 30) // 30 fps
        
        let instruction = AVMutableVideoCompositionInstruction()
        instruction.timeRange = CMTimeRange(start: .zero, duration: asset.duration)
        
        let layerInstruction = AVMutableVideoCompositionLayerInstruction(assetTrack: track)
        instruction.layerInstructions = [layerInstruction]
        
        videoComposition.instructions = [instruction]
        return videoComposition
    }
    
    // Fetch JSON from server and print the filename
    func fetchJSON() {
        guard let url = URL(string: "\(serverURL)/json") else {
            print("❌ Invalid JSON URL")
            return
        }
        
        // Create request with headers (for ngrok if needed)
        var request = URLRequest(url: url)
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if serverURL.contains("ngrok") {
            request.setValue("true", forHTTPHeaderField: "ngrok-skip-browser-warning")
        }
        
        let task = URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                print("❌ JSON fetch error: \(error.localizedDescription)")
                return
            }
            
            // Check HTTP response
            if let httpResponse = response as? HTTPURLResponse {
                if httpResponse.statusCode != 200 {
                    print("❌ JSON fetch failed with status: \(httpResponse.statusCode)")
                    return
                }
            }
            
            guard let data = data else {
                print("❌ No JSON data received")
                return
            }
            
            // Parse JSON and extract filename
            do {
                if let jsonObject = try JSONSerialization.jsonObject(with: data, options: []) as? [String: Any],
                   let filename = jsonObject["video_filename"] as? String {
                    print("📁 Filename: \(filename)")
                } else {
                    print("❌ Could not find 'video_filename' in JSON response")
                    if let jsonString = String(data: data, encoding: .utf8) {
                        print("Raw response: \(jsonString)")
                    }
                }
            } catch {
                print("❌ Failed to parse JSON: \(error.localizedDescription)")
                if let jsonString = String(data: data, encoding: .utf8) {
                    print("Raw response: \(jsonString)")
                }
            }
        }
        
        task.resume()
    }
    
    
    func setupNotifications() {
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
                saveDisturbanceCount()
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
                saveDisturbanceCount()
                print("Disturbance detected! Count: \(disturbanceCount)")
            }
        }
    }
}

// Video Player View
struct VideoPlayerView: UIViewControllerRepresentable {
    let videoURL: URL
    let onError: (String) -> Void
    
    func makeCoordinator() -> Coordinator {
        Coordinator(onError: onError)
    }
    
    func makeUIViewController(context: Context) -> AVPlayerViewController {
        print("Creating video player for URL: \(videoURL.path)")
        
        let player = AVPlayer(url: videoURL)
        let playerViewController = AVPlayerViewController()
        playerViewController.player = player
        
        // Check player item status after a delay
        if let playerItem = player.currentItem {
            // Monitor for errors using notifications
            NotificationCenter.default.addObserver(
                context.coordinator,
                selector: #selector(Coordinator.playerItemFailed(_:)),
                name: .AVPlayerItemFailedToPlayToEndTime,
                object: playerItem
            )
            
            // Check initial status after a delay
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                switch playerItem.status {
                case .readyToPlay:
                    print("Player item is ready to play")
                case .failed:
                    let errorMsg = playerItem.error?.localizedDescription ?? "Video codec not supported"
                    print("Player item failed: \(errorMsg)")
                    if let error = playerItem.error as NSError? {
                        print("Error domain: \(error.domain), code: \(error.code)")
                        // Check for specific codec errors
                        if error.domain == "AVFoundationErrorDomain" {
                            context.coordinator.onError("Video format not supported. iOS requires H.264/H.265 codec in MP4 container.")
                        } else {
                            context.coordinator.onError("Video cannot be played: \(errorMsg)")
                        }
                    } else {
                        context.coordinator.onError("Video cannot be played. The file format may not be supported by iOS.")
                    }
                case .unknown:
                    print("Player item status unknown - still loading")
                @unknown default:
                    print("Player item status unknown")
                }
            }
        }
        
        return playerViewController
    }
    
    func updateUIViewController(_ uiViewController: AVPlayerViewController, context: Context) {
        // No updates needed
    }
    
    // Coordinator to handle notifications
    class Coordinator: NSObject {
        let onError: (String) -> Void
        
        init(onError: @escaping (String) -> Void) {
            self.onError = onError
        }
        
        @objc func playerItemFailed(_ notification: Notification) {
            if let error = notification.userInfo?[AVPlayerItemFailedToPlayToEndTimeErrorKey] as? NSError {
                print("Player failed: \(error.localizedDescription)")
                DispatchQueue.main.async {
                    self.onError("Video playback failed: \(error.localizedDescription)")
                }
            }
        }
        
        deinit {
            NotificationCenter.default.removeObserver(self)
        }
    }
}

#Preview {
    ContentView()
}
