//
//  SessionModel.swift
//  CodeSergeantUI
//
//  Models for focus session state
//

import Foundation

/// Represents a focus session
struct FocusSession: Codable, Identifiable {
    let id: UUID
    var goal: String
    var workMinutes: Int
    var breakMinutes: Int
    var startTime: Date
    var endTime: Date?
    var totalFocusTime: TimeInterval
    var isCompleted: Bool
    
    init(
        id: UUID = UUID(),
        goal: String,
        workMinutes: Int = 25,
        breakMinutes: Int = 5,
        startTime: Date = Date(),
        endTime: Date? = nil,
        totalFocusTime: TimeInterval = 0,
        isCompleted: Bool = false
    ) {
        self.id = id
        self.goal = goal
        self.workMinutes = workMinutes
        self.breakMinutes = breakMinutes
        self.startTime = startTime
        self.endTime = endTime
        self.totalFocusTime = totalFocusTime
        self.isCompleted = isCompleted
    }
    
    var duration: TimeInterval {
        guard let endTime = endTime else {
            return Date().timeIntervalSince(startTime)
        }
        return endTime.timeIntervalSince(startTime)
    }
    
    var durationMinutes: Int {
        Int(duration / 60)
    }
}

/// Timer state
enum TimerState: String, Codable {
    case idle
    case working
    case onBreak = "break"
    case paused
    case completed
}

/// Session statistics
struct SessionStats {
    var totalSessions: Int
    var totalFocusMinutes: Int
    var averageSessionLength: Int
    var longestStreak: Int
    var currentStreak: Int
    
    static var empty: SessionStats {
        SessionStats(
            totalSessions: 0,
            totalFocusMinutes: 0,
            averageSessionLength: 0,
            longestStreak: 0,
            currentStreak: 0
        )
    }
}

/// Activity judgment from AI
struct ActivityJudgment: Codable {
    let classification: ActivityClassification
    let confidence: Double
    let reason: String
    let say: String
    let action: JudgmentAction
}

enum ActivityClassification: String, Codable {
    case onTask = "on_task"
    case offTask = "off_task"
    case thinking
    case idle
    case unknown
}

enum JudgmentAction: String, Codable {
    case none
    case warn
    case yell
}

/// Motivation state from AI
struct MotivationState: Codable {
    let state: MotivationType
    let confidence: Double
    let suggestion: String
}

enum MotivationType: String, Codable {
    case flow
    case productive
    case struggling
    case distracted
    case fatigued
}

/// Screen analysis result
struct ScreenAnalysis: Codable, Identifiable {
    let id: UUID
    let timestamp: Date
    let appName: String
    let description: String
    let progressAssessment: String
    let isOnTask: Bool
    let confidence: Double
    
    init(
        id: UUID = UUID(),
        timestamp: Date = Date(),
        appName: String,
        description: String,
        progressAssessment: String,
        isOnTask: Bool,
        confidence: Double
    ) {
        self.id = id
        self.timestamp = timestamp
        self.appName = appName
        self.description = description
        self.progressAssessment = progressAssessment
        self.isOnTask = isOnTask
        self.confidence = confidence
    }
}

