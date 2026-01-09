//
//  CodeSergeantApp.swift
//  CodeSergeantUI
//
//  SwiftUI Menu Bar App with Liquid Glass Design
//

import SwiftUI
import AppKit
import Foundation

@main
struct CodeSergeantApp: App {
    @StateObject private var appState = AppState()
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    
    var body: some Scene {
        // Menu Bar Extra (Menu Bar Icon + Dropdown)
        MenuBarExtra {
            MenuBarView()
                .environmentObject(appState)
        } label: {
            Image(systemName: "shield.lefthalf.filled")
                .symbolRenderingMode(.hierarchical)
        }
        .menuBarExtraStyle(.window)
        
        // Main Dashboard Window
        WindowGroup("Code Sergeant", id: "dashboard") {
            DashboardView()
                .environmentObject(appState)
        }
        .windowStyle(.hiddenTitleBar)
        .windowResizability(.contentSize)
        .defaultPosition(.center)
        .defaultSize(width: 520, height: 680)
        
        // Settings Window
        Settings {
            SettingsView()
                .environmentObject(appState)
        }
    }
}

// MARK: - App Delegate

class AppDelegate: NSObject, NSApplicationDelegate {
    private var bridgeProcess: Process?
    private var bridgeProcessPID: Int32?
    private let bridgePort = 5050
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Hide dock icon (menu bar only app)
        NSApp.setActivationPolicy(.accessory)
        
        // Set up signal handlers for cleanup
        setupSignalHandlers()
        
        // Start the Python bridge server in background
        startBridgeServer()
    }
    
    func applicationWillTerminate(_ notification: Notification) {
        // Clean up bridge server
        stopBridgeServer()
    }
    
    private func startBridgeServer() {
        // Bridge server is started as a separate process
        // This allows the SwiftUI app to communicate with Python backend
        DispatchQueue.global(qos: .background).async { [weak self] in
            guard let self = self else { return }
            let task = Process()
            let fileManager = FileManager.default
            
            // Find project root by searching for bridge/server.py
            // Start from current working directory or bundle path
            var searchPath = URL(fileURLWithPath: fileManager.currentDirectoryPath)
            
            // If running from Xcode, start from bundle path and search up
            let bundlePath = Bundle.main.bundlePath
            if bundlePath.contains("DerivedData") {
                // Running from Xcode - start from DerivedData and search up
                searchPath = URL(fileURLWithPath: bundlePath)
            }
            
            // Search up the directory tree for bridge/server.py
            var projectRoot: URL?
            var currentPath = searchPath
            
            while currentPath.path != "/" {
                let bridgePath = currentPath.appendingPathComponent("bridge/server.py")
                if fileManager.fileExists(atPath: bridgePath.path) {
                    projectRoot = currentPath
                    break
                }
                currentPath = currentPath.deletingLastPathComponent()
            }
            
            // Fallback: try hardcoded project path
            if projectRoot == nil {
                let hardcodedPath = URL(fileURLWithPath: "/Users/cuevalabs/Desktop/Projects/CodeSergeant")
                if fileManager.fileExists(atPath: hardcodedPath.appendingPathComponent("bridge/server.py").path) {
                    projectRoot = hardcodedPath
                }
            }
            
            guard let root = projectRoot else {
                print("❌ Could not find project root. Bridge server not started.")
                print("   Please start manually: cd /Users/cuevalabs/Desktop/Projects/CodeSergeant && python bridge/server.py")
                return
            }
            
            let scriptPath = root.appendingPathComponent("start_bridge.sh")
            let serverPath = root.appendingPathComponent("bridge/server.py")
            let venvPython = root.appendingPathComponent(".venv/bin/python")
            
            // Try venv python first, then script, then system python
            if fileManager.fileExists(atPath: venvPython.path) {
                // Use venv python directly
                task.executableURL = venvPython
                task.arguments = [serverPath.path]
                print("📦 Using venv Python: \(venvPython.path)")
            } else if fileManager.fileExists(atPath: scriptPath.path) {
                // Use startup script
                task.executableURL = URL(fileURLWithPath: "/bin/bash")
                task.arguments = [scriptPath.path]
                print("📜 Using startup script")
            } else {
                // Fallback: system python
                task.executableURL = URL(fileURLWithPath: "/usr/bin/env")
                task.arguments = ["python3", serverPath.path]
                print("⚠️ Using system Python (venv not found)")
            }
            
            task.currentDirectoryURL = root
            
            // Set environment variables
            var environment = ProcessInfo.processInfo.environment
            environment["PYTHONUNBUFFERED"] = "1"
            // Add venv to PATH if it exists
            if fileManager.fileExists(atPath: venvPython.path) {
                let venvBin = root.appendingPathComponent(".venv/bin").path
                if let currentPath = environment["PATH"] {
                    environment["PATH"] = "\(venvBin):\(currentPath)"
                } else {
                    environment["PATH"] = venvBin
                }
            }
            task.environment = environment
            
            do {
                try task.run()
                
                // Store process reference for cleanup
                self.bridgeProcess = task
                self.bridgeProcessPID = task.processIdentifier
                
                print("✅ Bridge server starting at \(root.path)")
                print("   Process ID: \(task.processIdentifier)")
            } catch {
                print("❌ Failed to start bridge server: \(error)")
                print("   Project root: \(root.path)")
                print("   Server path: \(serverPath.path)")
                print("   Please start manually:")
                print("   cd \(root.path)")
                print("   source .venv/bin/activate")
                print("   python bridge/server.py")
            }
        }
    }
    
    private func stopBridgeServer() {
        print("🛑 Stopping bridge server...")
        
        // Strategy 1: Try HTTP shutdown (with timeout)
        let shutdownSemaphore = DispatchSemaphore(value: 0)
        var httpShutdownSuccess = false
        
        if let url = URL(string: "http://127.0.0.1:\(bridgePort)/api/shutdown") {
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.timeoutInterval = 2.0 // 2 second timeout
            
            URLSession.shared.dataTask(with: request) { _, response, error in
                httpShutdownSuccess = (error == nil && (response as? HTTPURLResponse)?.statusCode == 200)
                shutdownSemaphore.signal()
            }.resume()
            
            // Wait up to 2 seconds for HTTP shutdown
            _ = shutdownSemaphore.wait(timeout: .now() + 2.0)
        }
        
        if httpShutdownSuccess {
            print("✅ Bridge server shutdown via HTTP")
            // Give it a moment to exit gracefully
            Thread.sleep(forTimeInterval: 0.5)
        }
        
        // Strategy 2: Terminate Process directly
        if let process = bridgeProcess, process.isRunning {
            print("🔄 Terminating bridge process (PID: \(process.processIdentifier))...")
            process.terminate()
            
            // Wait up to 2 seconds for graceful termination
            let terminationTimeout = Date().addingTimeInterval(2.0)
            while process.isRunning && Date() < terminationTimeout {
                Thread.sleep(forTimeInterval: 0.1)
            }
            
            if process.isRunning {
                print("⚠️ Process still running, force killing...")
                // Use kill command since Process doesn't have kill() method
                let killTask = Process()
                killTask.executableURL = URL(fileURLWithPath: "/bin/kill")
                killTask.arguments = ["-9", "\(process.processIdentifier)"]
                do {
                    try killTask.run()
                    killTask.waitUntilExit()
                    Thread.sleep(forTimeInterval: 0.2)
                } catch {
                    print("⚠️ Failed to force kill process: \(error)")
                }
            } else {
                print("✅ Bridge process terminated")
            }
        }
        
        // Strategy 3: Kill by PID if we have it but process reference is lost
        if let pid = bridgeProcessPID {
            let killTask = Process()
            killTask.executableURL = URL(fileURLWithPath: "/bin/kill")
            killTask.arguments = ["-9", "\(pid)"]
            do {
                try killTask.run()
                killTask.waitUntilExit()
                print("✅ Killed process by PID: \(pid)")
            } catch {
                // Process may already be dead, ignore error
            }
        }
        
        // Strategy 4: Fallback - kill any Python processes on the bridge port
        killPythonOnPort(bridgePort)
        
        // Clear references
        bridgeProcess = nil
        bridgeProcessPID = nil
        
        print("✅ Bridge server cleanup complete")
    }
    
    private func setupSignalHandlers() {
        // Handle SIGTERM (normal termination)
        signal(SIGTERM) { _ in
            DispatchQueue.main.async {
                if let delegate = NSApplication.shared.delegate as? AppDelegate {
                    delegate.stopBridgeServer()
                }
                exit(0)
            }
        }
        
        // Handle SIGINT (Ctrl+C)
        signal(SIGINT) { _ in
            DispatchQueue.main.async {
                if let delegate = NSApplication.shared.delegate as? AppDelegate {
                    delegate.stopBridgeServer()
                }
                exit(0)
            }
        }
    }
    
    private func killPythonOnPort(_ port: Int) {
        print("🔍 Checking for Python processes on port \(port)...")
        
        // Use lsof to find processes using the port
        let lsofTask = Process()
        lsofTask.executableURL = URL(fileURLWithPath: "/usr/sbin/lsof")
        lsofTask.arguments = ["-ti", ":\(port)"]
        
        let pipe = Pipe()
        lsofTask.standardOutput = pipe
        lsofTask.standardError = Pipe()
        
        do {
            try lsofTask.run()
            lsofTask.waitUntilExit()
            
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            guard let output = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines),
                  !output.isEmpty else {
                print("   No processes found on port \(port)")
                return
            }
            
            let pids = output.components(separatedBy: "\n").compactMap { Int32($0) }
            
            for pid in pids {
                // Verify it's a Python process
                let psTask = Process()
                psTask.executableURL = URL(fileURLWithPath: "/bin/ps")
                psTask.arguments = ["-p", "\(pid)", "-o", "comm="]
                
                let psPipe = Pipe()
                psTask.standardOutput = psPipe
                psTask.standardError = Pipe()
                
                do {
                    try psTask.run()
                    psTask.waitUntilExit()
                    
                    let psData = psPipe.fileHandleForReading.readDataToEndOfFile()
                    if let comm = String(data: psData, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines),
                       comm.lowercased().contains("python") {
                        print("   Killing Python process (PID: \(pid)) on port \(port)...")
                        
                        let killTask = Process()
                        killTask.executableURL = URL(fileURLWithPath: "/bin/kill")
                        killTask.arguments = ["-9", "\(pid)"]
                        try killTask.run()
                        killTask.waitUntilExit()
                        
                        print("   ✅ Killed PID \(pid)")
                    }
                } catch {
                    // Ignore errors checking process
                }
            }
        } catch {
            // lsof may not be available or port may be free
            print("   Could not check port \(port): \(error.localizedDescription)")
        }
    }
}

// MARK: - App State

// Warning status enum
enum WarningStatus: String {
    case green = "on_task"      // On task
    case yellow = "thinking"    // Thinking/idle
    case red = "off_task"       // Off task - trigger strobe
}

class AppState: ObservableObject {
    @Published var isSessionActive: Bool = false
    @Published var sessionGoal: String = ""
    @Published var focusTimeMinutes: Int = 0
    @Published var remainingSeconds: Int = 0
    @Published var isBreak: Bool = false
    @Published var isPaused: Bool = false  // NEW: Track pause state
    @Published var workMinutes: Double = 25
    @Published var breakMinutes: Double = 5
    
    // XP & Rank System (NEW)
    @Published var totalXP: Int = 0
    @Published var sessionXP: Int = 0
    @Published var currentRank: String = "Recruit"
    @Published var rankProgress: Double = 0.0  // 0.0 to 1.0
    @Published var nextRankName: String = "Private"
    @Published var xpToNextRank: Int = 100
    
    // Warning System (NEW)
    @Published var warningStatus: WarningStatus = .green
    @Published var lastJudgmentText: String = ""
    
    // AI Status
    @Published var openAIAvailable: Bool = false
    @Published var ollamaAvailable: Bool = false
    @Published var primaryBackend: String = "none"
    
    // Screen Monitoring
    @Published var screenMonitoringEnabled: Bool = false
    @Published var useLocalVision: Bool = true
    @Published var visionBackendStatus: String = "unknown"
    
    private var statusTimer: Timer?
    private let bridgeURL = "http://127.0.0.1:5050"
    
    init() {
        startStatusPolling()
    }
    
    deinit {
        statusTimer?.invalidate()
    }
    
    // MARK: - API Calls
    
    func startSession() {
        guard let url = URL(string: "\(bridgeURL)/api/session/start") else { return }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "goal": sessionGoal,
            "work_minutes": Int(workMinutes),
            "break_minutes": Int(breakMinutes)
        ]
        
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            if error == nil {
                DispatchQueue.main.async {
                    self?.isSessionActive = true
                }
            }
        }.resume()
    }
    
    func endSession() {
        guard let url = URL(string: "\(bridgeURL)/api/session/end") else { return }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            if error == nil {
                DispatchQueue.main.async {
                    self?.isSessionActive = false
                    self?.sessionGoal = ""
                    self?.focusTimeMinutes = 0
                }
            }
        }.resume()
    }
    
    func pauseSession() {
        sendPOST(endpoint: "/api/session/pause")
    }
    
    func resumeSession() {
        sendPOST(endpoint: "/api/session/resume")
    }
    
    func skipBreak() {
        sendPOST(endpoint: "/api/session/skip-break")
    }
    
    func setOpenAIKey(_ key: String) {
        guard let url = URL(string: "\(bridgeURL)/api/openai-key") else { return }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: ["api_key": key])
        
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            if error == nil {
                self?.fetchAIStatus()
            }
        }.resume()
    }
    
    func toggleScreenMonitoring(_ enabled: Bool) {
        guard let url = URL(string: "\(bridgeURL)/api/screen-monitoring/toggle") else { return }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: ["enabled": enabled])
        
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            if error == nil {
                DispatchQueue.main.async {
                    self?.screenMonitoringEnabled = enabled
                }
            }
        }.resume()
    }
    
    // MARK: - Polling
    
    private func startStatusPolling() {
        statusTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            self?.fetchStatus()
            self?.fetchTimerStatus()
            self?.fetchXPStatus()          // NEW: Poll XP status
            self?.fetchJudgmentStatus()    // NEW: Poll judgment for warning system
        }
        
        // Initial fetch
        fetchStatus()
        fetchAIStatus()
        fetchScreenMonitoringStatus()
        fetchXPStatus()          // NEW
        fetchJudgmentStatus()    // NEW
    }
    
    private func fetchStatus() {
        guard let url = URL(string: "\(bridgeURL)/api/status") else { return }
        
        URLSession.shared.dataTask(with: url) { [weak self] data, response, error in
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }
            
            DispatchQueue.main.async {
                self?.isSessionActive = json["session_active"] as? Bool ?? false
                self?.focusTimeMinutes = json["focus_time_minutes"] as? Int ?? 0
                if let goal = json["current_goal"] as? String, !goal.isEmpty {
                    self?.sessionGoal = goal
                }
            }
        }.resume()
    }
    
    private func fetchTimerStatus() {
        guard let url = URL(string: "\(bridgeURL)/api/timer") else { return }
        
        URLSession.shared.dataTask(with: url) { [weak self] data, response, error in
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }
            
            DispatchQueue.main.async {
                self?.remainingSeconds = json["remaining_seconds"] as? Int ?? 0
                self?.isBreak = json["is_break"] as? Bool ?? false
                self?.isPaused = json["is_paused"] as? Bool ?? false  // NEW: Track pause state
            }
        }.resume()
    }
    
    private func fetchXPStatus() {
        guard let url = URL(string: "\(bridgeURL)/api/xp/status") else { return }
        
        URLSession.shared.dataTask(with: url) { [weak self] data, response, error in
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }
            
            DispatchQueue.main.async {
                self?.totalXP = json["total_xp"] as? Int ?? 0
                self?.sessionXP = json["session_xp"] as? Int ?? 0
                self?.currentRank = json["current_rank"] as? String ?? "Recruit"
                self?.rankProgress = json["rank_progress"] as? Double ?? 0.0
                self?.nextRankName = json["next_rank_name"] as? String ?? ""
                self?.xpToNextRank = json["xp_to_next_rank"] as? Int ?? 0
            }
        }.resume()
    }
    
    private func fetchJudgmentStatus() {
        guard let url = URL(string: "\(bridgeURL)/api/judgment/current") else { return }
        
        URLSession.shared.dataTask(with: url) { [weak self] data, response, error in
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }
            
            DispatchQueue.main.async {
                let classification = json["classification"] as? String ?? "idle"
                self?.warningStatus = WarningStatus(rawValue: classification) ?? .green
                self?.lastJudgmentText = json["reason"] as? String ?? ""
            }
        }.resume()
    }
    
    private func fetchAIStatus() {
        guard let url = URL(string: "\(bridgeURL)/api/ai/status") else { return }
        
        URLSession.shared.dataTask(with: url) { [weak self] data, response, error in
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }
            
            DispatchQueue.main.async {
                self?.openAIAvailable = json["openai_available"] as? Bool ?? false
                self?.ollamaAvailable = json["ollama_available"] as? Bool ?? false
                self?.primaryBackend = json["primary_backend"] as? String ?? "none"
            }
        }.resume()
    }
    
    private func fetchScreenMonitoringStatus() {
        guard let url = URL(string: "\(bridgeURL)/api/screen-monitoring/status") else { return }
        
        URLSession.shared.dataTask(with: url) { [weak self] data, response, error in
            guard let data = data,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return }
            
            DispatchQueue.main.async {
                self?.screenMonitoringEnabled = json["enabled"] as? Bool ?? false
                self?.useLocalVision = json["use_local_vision"] as? Bool ?? true
                self?.visionBackendStatus = json["backend_status"] as? String ?? "unknown"
            }
        }.resume()
    }
    
    private func sendPOST(endpoint: String) {
        guard let url = URL(string: "\(bridgeURL)\(endpoint)") else { return }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        
        URLSession.shared.dataTask(with: request).resume()
    }
}

