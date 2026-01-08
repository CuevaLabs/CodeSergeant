//
//  PythonBridge.swift
//  CodeSergeantUI
//
//  Service for communicating with the Python backend
//

import Foundation

/// Handles communication with the Python backend via HTTP
actor PythonBridge {
    static let shared = PythonBridge()
    
    private let baseURL: String
    private let session: URLSession
    
    private init() {
        self.baseURL = "http://127.0.0.1:5050"
        
        // Configure URLSession with timeout
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 10
        config.timeoutIntervalForResource = 30
        self.session = URLSession(configuration: config)
    }
    
    // MARK: - Health Check
    
    func isAvailable() async -> Bool {
        guard let url = URL(string: "\(baseURL)/api/health") else { return false }
        
        do {
            let (_, response) = try await session.data(from: url)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }
    
    // MARK: - Status
    
    func getStatus() async throws -> SessionStatus {
        let data = try await get("/api/status")
        return try JSONDecoder().decode(SessionStatus.self, from: data)
    }
    
    func getAIStatus() async throws -> AIStatus {
        let data = try await get("/api/ai/status")
        return try JSONDecoder().decode(AIStatus.self, from: data)
    }
    
    func getTimerStatus() async throws -> TimerStatus {
        let data = try await get("/api/timer")
        return try JSONDecoder().decode(TimerStatus.self, from: data)
    }
    
    func getScreenMonitoringStatus() async throws -> ScreenMonitoringStatus {
        let data = try await get("/api/screen-monitoring/status")
        return try JSONDecoder().decode(ScreenMonitoringStatus.self, from: data)
    }
    
    // MARK: - Session
    
    func startSession(goal: String, workMinutes: Int, breakMinutes: Int) async throws {
        let body: [String: Any] = [
            "goal": goal,
            "work_minutes": workMinutes,
            "break_minutes": breakMinutes
        ]
        _ = try await post("/api/session/start", body: body)
    }
    
    func endSession() async throws -> [String: Any] {
        let data = try await post("/api/session/end", body: nil)
        return (try? JSONSerialization.jsonObject(with: data) as? [String: Any]) ?? [:]
    }
    
    func pauseSession() async throws {
        _ = try await post("/api/session/pause", body: nil)
    }
    
    func resumeSession() async throws {
        _ = try await post("/api/session/resume", body: nil)
    }
    
    func skipBreak() async throws {
        _ = try await post("/api/session/skip-break", body: nil)
    }
    
    // MARK: - Settings
    
    func setOpenAIKey(_ key: String) async throws -> Bool {
        let body = ["api_key": key]
        let data = try await post("/api/openai-key", body: body)
        let response = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        return response?["success"] as? Bool ?? false
    }
    
    func toggleScreenMonitoring(_ enabled: Bool) async throws {
        let body = ["enabled": enabled]
        _ = try await post("/api/screen-monitoring/toggle", body: body)
    }
    
    func getConfig() async throws -> [String: Any] {
        let data = try await get("/api/config")
        return (try? JSONSerialization.jsonObject(with: data) as? [String: Any]) ?? [:]
    }
    
    func updateConfig(_ config: [String: Any]) async throws {
        _ = try await patch("/api/config", body: config)
    }
    
    // MARK: - TTS
    
    func speak(_ text: String) async throws {
        let body = ["text": text]
        _ = try await post("/api/tts/speak", body: body)
    }
    
    func stopSpeaking() async throws {
        _ = try await post("/api/tts/stop", body: nil)
    }
    
    // MARK: - Personality
    
    func setPersonality(_ profile: String) async throws {
        let body = ["profile": profile]
        _ = try await post("/api/personality", body: body)
    }
    
    // MARK: - HTTP Methods
    
    private func get(_ endpoint: String) async throws -> Data {
        guard let url = URL(string: "\(baseURL)\(endpoint)") else {
            throw BridgeError.invalidURL
        }
        
        let (data, response) = try await session.data(from: url)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw BridgeError.invalidResponse
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            throw BridgeError.httpError(httpResponse.statusCode)
        }
        
        return data
    }
    
    private func post(_ endpoint: String, body: [String: Any]?) async throws -> Data {
        guard let url = URL(string: "\(baseURL)\(endpoint)") else {
            throw BridgeError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        if let body = body {
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
        }
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw BridgeError.invalidResponse
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            throw BridgeError.httpError(httpResponse.statusCode)
        }
        
        return data
    }
    
    private func patch(_ endpoint: String, body: [String: Any]) async throws -> Data {
        guard let url = URL(string: "\(baseURL)\(endpoint)") else {
            throw BridgeError.invalidURL
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "PATCH"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        
        let (data, response) = try await session.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse else {
            throw BridgeError.invalidResponse
        }
        
        guard (200...299).contains(httpResponse.statusCode) else {
            throw BridgeError.httpError(httpResponse.statusCode)
        }
        
        return data
    }
}

// MARK: - Error Types

enum BridgeError: LocalizedError {
    case invalidURL
    case invalidResponse
    case httpError(Int)
    case decodingError
    
    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .invalidResponse:
            return "Invalid response from server"
        case .httpError(let code):
            return "HTTP error: \(code)"
        case .decodingError:
            return "Failed to decode response"
        }
    }
}

// MARK: - Response Types

struct SessionStatus: Codable {
    let sessionActive: Bool
    let focusTimeMinutes: Int
    let currentGoal: String?
    let personality: String
    let timestamp: String
    
    enum CodingKeys: String, CodingKey {
        case sessionActive = "session_active"
        case focusTimeMinutes = "focus_time_minutes"
        case currentGoal = "current_goal"
        case personality
        case timestamp
    }
}

struct AIStatus: Codable {
    let openaiAvailable: Bool
    let openaiModel: String
    let ollamaAvailable: Bool
    let ollamaModel: String
    let ollamaVisionModel: String
    let primaryBackend: String
    let ollamaServerMessage: String?
    
    enum CodingKeys: String, CodingKey {
        case openaiAvailable = "openai_available"
        case openaiModel = "openai_model"
        case ollamaAvailable = "ollama_available"
        case ollamaModel = "ollama_model"
        case ollamaVisionModel = "ollama_vision_model"
        case primaryBackend = "primary_backend"
        case ollamaServerMessage = "ollama_server_message"
    }
}

struct TimerStatus: Codable {
    let state: String
    let remainingSeconds: Int
    let totalSeconds: Int
    let isBreak: Bool
    let workMinutes: Int
    let breakMinutes: Int
    
    enum CodingKeys: String, CodingKey {
        case state
        case remainingSeconds = "remaining_seconds"
        case totalSeconds = "total_seconds"
        case isBreak = "is_break"
        case workMinutes = "work_minutes"
        case breakMinutes = "break_minutes"
    }
}

struct ScreenMonitoringStatus: Codable {
    let enabled: Bool
    let useLocalVision: Bool
    let backendStatus: String
    let checkIntervalSeconds: Int
    
    enum CodingKeys: String, CodingKey {
        case enabled
        case useLocalVision = "use_local_vision"
        case backendStatus = "backend_status"
        case checkIntervalSeconds = "check_interval_seconds"
    }
}

