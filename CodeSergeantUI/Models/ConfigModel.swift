//
//  ConfigModel.swift
//  CodeSergeantUI
//
//  Configuration models for the app
//

import Foundation

/// App configuration
struct AppConfig: Codable {
    var pomodoro: PomodoroConfig
    var openai: OpenAIConfig
    var ollama: OllamaConfig
    var tts: TTSConfig
    var screenMonitoring: ScreenMonitoringConfig
    var motivation: MotivationConfig
    var personality: PersonalityConfig
    
    enum CodingKeys: String, CodingKey {
        case pomodoro
        case openai
        case ollama
        case tts
        case screenMonitoring = "screen_monitoring"
        case motivation
        case personality
    }
}

struct PomodoroConfig: Codable {
    var workMinutes: Int
    var breakMinutes: Int
    var longBreakMinutes: Int
    var sessionsBeforeLongBreak: Int
    
    enum CodingKeys: String, CodingKey {
        case workMinutes = "work_minutes"
        case breakMinutes = "break_minutes"
        case longBreakMinutes = "long_break_minutes"
        case sessionsBeforeLongBreak = "sessions_before_long_break"
    }
}

struct OpenAIConfig: Codable {
    var apiKey: String?
    var model: String
    
    enum CodingKeys: String, CodingKey {
        case apiKey = "api_key"
        case model
    }
}

struct OllamaConfig: Codable {
    var model: String
    var baseUrl: String
    
    enum CodingKeys: String, CodingKey {
        case model
        case baseUrl = "base_url"
    }
}

struct TTSConfig: Codable {
    var engine: String
    var rate: Int
    var volume: Double
    var elevenlabsApiKey: String?
    var elevenlabsVoiceId: String?
    
    enum CodingKeys: String, CodingKey {
        case engine
        case rate
        case volume
        case elevenlabsApiKey = "elevenlabs_api_key"
        case elevenlabsVoiceId = "elevenlabs_voice_id"
    }
}

struct ScreenMonitoringConfig: Codable {
    var enabled: Bool
    var appBlocklist: [String]
    var blurRegions: [BlurRegion]
    var useLocalVision: Bool
    var checkIntervalSeconds: Int
    
    enum CodingKeys: String, CodingKey {
        case enabled
        case appBlocklist = "app_blocklist"
        case blurRegions = "blur_regions"
        case useLocalVision = "use_local_vision"
        case checkIntervalSeconds = "check_interval_seconds"
    }
}

struct BlurRegion: Codable {
    var x: Int
    var y: Int
    var width: Int
    var height: Int
    var label: String?
}

struct MotivationConfig: Codable {
    var enabled: Bool
    var checkIntervalMinutes: Int
    
    enum CodingKeys: String, CodingKey {
        case enabled
        case checkIntervalMinutes = "check_interval_minutes"
    }
}

struct PersonalityConfig: Codable {
    var profile: String
    var intensity: Double
}

// MARK: - Default Config

extension AppConfig {
    static var `default`: AppConfig {
        AppConfig(
            pomodoro: PomodoroConfig(
                workMinutes: 25,
                breakMinutes: 5,
                longBreakMinutes: 15,
                sessionsBeforeLongBreak: 4
            ),
            openai: OpenAIConfig(
                apiKey: nil,
                model: "gpt-4o-mini"
            ),
            ollama: OllamaConfig(
                model: "llama3.2",
                baseUrl: "http://localhost:11434"
            ),
            tts: TTSConfig(
                engine: "pyttsx3",
                rate: 180,
                volume: 1.0,
                elevenlabsApiKey: nil,
                elevenlabsVoiceId: nil
            ),
            screenMonitoring: ScreenMonitoringConfig(
                enabled: false,
                appBlocklist: [
                    "1Password", "LastPass", "Keychain Access",
                    "PayPal", "Chase", "Bank of America"
                ],
                blurRegions: [],
                useLocalVision: true,
                checkIntervalSeconds: 120
            ),
            motivation: MotivationConfig(
                enabled: true,
                checkIntervalMinutes: 3
            ),
            personality: PersonalityConfig(
                profile: "drill_sergeant",
                intensity: 0.7
            )
        )
    }
}

