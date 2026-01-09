//
//  DashboardView.swift
//  CodeSergeantUI
//
//  Main dashboard with liquid glass design, XP system, and warning strobe
//

import SwiftUI
import AppKit

struct DashboardView: View {
    @EnvironmentObject var appState: AppState
    
    @State private var goalText: String = ""
    @State private var showingSettings = false
    @State private var animateIn = false
    
    var body: some View {
        ZStack {
            // Background
            GlassBackground(opacity: 0.6)
            
            // Content
            VStack(spacing: 0) {
                // Header
                headerView
                    .offset(y: animateIn ? 0 : -50)
                    .opacity(animateIn ? 1 : 0)
                
                Spacer()
                
                // Main content
                if appState.isSessionActive {
                    activeSessionView
                        .transition(.asymmetric(
                            insertion: .scale(scale: 0.8).combined(with: .opacity),
                            removal: .scale(scale: 1.1).combined(with: .opacity)
                        ))
                } else {
                    startSessionView
                        .transition(.asymmetric(
                            insertion: .scale(scale: 0.9).combined(with: .opacity),
                            removal: .scale(scale: 0.8).combined(with: .opacity)
                        ))
                }
                
                Spacer()
                
                // Footer status
                footerView
                    .offset(y: animateIn ? 0 : 50)
                    .opacity(animateIn ? 1 : 0)
            }
            .padding(30)
        }
        .frame(width: 520, height: 680)
        .warningStrobe(status: appState.warningStatus)  // Apply strobe border
        .onAppear {
            withAnimation(.spring(response: 0.6, dampingFraction: 0.8).delay(0.1)) {
                animateIn = true
            }
        }
    }
    
    // MARK: - Header
    
    private var headerView: some View {
        HStack {
            // App icon and title
            HStack(spacing: 12) {
                Image(systemName: "shield.lefthalf.filled")
                    .font(.system(size: 28))
                    .foregroundStyle(
                        LinearGradient(
                            colors: militaryGradient,
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                
                VStack(alignment: .leading, spacing: 2) {
                    Text("CODE SERGEANT")
                        .font(.system(size: 22, weight: .black, design: .monospaced))
                        .tracking(1)
                        .foregroundStyle(.primary)
                    
                    Text(appState.isSessionActive ? "Session Active" : "Ready to Focus")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(.secondary)
                }
            }
            
            Spacer()
            
            // Settings button - FIXED
            LiquidIconButton("gear", size: 40) {
                if #available(macOS 14.0, *) {
                    NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
                } else {
                    NSApp.sendAction(Selector(("showPreferencesWindow:")), to: nil, from: nil)
                }
            }
        }
        .padding(.bottom, 10)
    }
    
    // MARK: - Start Session View
    
    private var startSessionView: some View {
        VStack(spacing: 24) {
            // Goal input card
            HoverGlassCard(cornerRadius: 24) {
                VStack(alignment: .leading, spacing: 14) {
                    Label("MISSION", systemImage: "target")
                        .font(.system(size: 14, weight: .bold, design: .monospaced))
                        .foregroundStyle(.secondary)
                        .tracking(1)
                    
                    TextField("What do you want to accomplish?", text: $goalText)
                        .textFieldStyle(.plain)
                        .font(.system(size: 16))
                        .padding(14)
                        .background(
                            RoundedRectangle(cornerRadius: 12, style: .continuous)
                                .fill(.white.opacity(0.08))
                        )
                        .overlay(
                            RoundedRectangle(cornerRadius: 12, style: .continuous)
                                .stroke(.white.opacity(0.1), lineWidth: 1)
                        )
                }
                .padding(20)
            }
            .animation(.spring(response: 0.4, dampingFraction: 0.7), value: goalText)
            
            // Timer settings card
            HoverGlassCard(cornerRadius: 24) {
                VStack(spacing: 20) {
                    Label("SESSION SETTINGS", systemImage: "timer")
                        .font(.system(size: 14, weight: .bold, design: .monospaced))
                        .foregroundStyle(.secondary)
                        .tracking(1)
                        .frame(maxWidth: .infinity, alignment: .leading)
                    
                    TimerSlider(
                        label: "Work Duration",
                        value: $appState.workMinutes,
                        range: 15...60,
                        step: 5,
                        unit: "min"
                    )
                    
                    Divider()
                        .background(.white.opacity(0.1))
                    
                    TimerSlider(
                        label: "Break Duration",
                        value: $appState.breakMinutes,
                        range: 5...15,
                        step: 5,
                        unit: "min"
                    )
                }
                .padding(20)
            }
            
            // Start button
            LiquidButton("Start Focus Session", icon: "play.fill", style: .primary) {
                appState.sessionGoal = goalText
                withAnimation(.spring(response: 0.5, dampingFraction: 0.8)) {
                    appState.startSession()
                }
            }
            .disabled(goalText.trimmingCharacters(in: .whitespaces).isEmpty)
            .opacity(goalText.trimmingCharacters(in: .whitespaces).isEmpty ? 0.6 : 1)
            .animation(.easeInOut(duration: 0.2), value: goalText.isEmpty)
        }
        .padding(.horizontal, 10)
    }
    
    // MARK: - Active Session View
    
    private var activeSessionView: some View {
        VStack(spacing: 24) {
            // Timer with XP display below
            VStack(spacing: 16) {
                TimerDisplay(
                    remainingSeconds: appState.remainingSeconds,
                    totalSeconds: Int(appState.workMinutes) * 60,
                    isBreak: appState.isBreak
                )
                
                // XP earned this session with animation - DOPAMINE REWARD!
                HStack(spacing: 12) {
                    Image(systemName: "star.fill")
                        .font(.system(size: 16))
                        .foregroundStyle(.yellow)
                    
                    Text("+\(appState.sessionXP) XP")
                        .font(.system(size: 20, weight: .bold, design: .rounded))
                        .foregroundStyle(.yellow)
                        .contentTransition(.numericText())
                        .animation(.spring(response: 0.3), value: appState.sessionXP)
                    
                    Text("this session")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(.secondary)
                }
            }
            
            // Current goal
            HoverGlassCard(cornerRadius: 20) {
                VStack(alignment: .leading, spacing: 8) {
                    Label("MISSION", systemImage: "target")
                        .font(.system(size: 12, weight: .black, design: .monospaced))
                        .foregroundStyle(.secondary)
                        .tracking(1)
                    
                    Text(appState.sessionGoal.isEmpty ? "No goal set" : appState.sessionGoal)
                        .font(.system(size: 16, weight: .medium))
                        .foregroundStyle(.primary)
                        .lineLimit(2)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(16)
            }
            
            // Stats row - REPLACED "Focus Status" with Rank Display
            HStack(spacing: 16) {
                StatCard(
                    label: "Focus Time",
                    value: "\(appState.focusTimeMinutes)",
                    unit: "min",
                    icon: "clock.fill",
                    color: .blue
                )
                
                // Rank display instead of redundant focus status
                StatCard(
                    label: "Rank",
                    value: String(appState.currentRank.prefix(3)).uppercased(),
                    unit: "",
                    icon: "star.fill",
                    color: rankColor
                )
            }
            
            // Control buttons - FIXED pause/resume toggle
            HStack(spacing: 12) {
                // Pause/Resume button with proper state tracking - FIXED
                LiquidIconButton(
                    appState.isPaused ? "play.fill" : "pause.fill",
                    size: 44
                ) {
                    if appState.isPaused {
                        appState.resumeSession()
                    } else {
                        appState.pauseSession()
                    }
                }
                
                LiquidButton("End Session", icon: "stop.fill", style: .danger) {
                    showEndSessionConfirmation()
                }
                
                if appState.isBreak {
                    LiquidIconButton("forward.fill", size: 44) {
                        appState.skipBreak()
                    }
                }
            }
        }
        .padding(.horizontal, 10)
    }
    
    // MARK: - Footer
    
    private var footerView: some View {
        HStack(spacing: 12) {
            // AI status indicator
            HStack(spacing: 6) {
                Circle()
                    .fill(appState.openAIAvailable || appState.ollamaAvailable ? Color.green : Color.orange)
                    .frame(width: 8, height: 8)
                
                Text(appState.primaryBackend == "openai" ? "OpenAI" : (appState.ollamaAvailable ? "Ollama" : "No AI"))
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(.secondary)
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .glassCard(cornerRadius: 12, backgroundOpacity: 0.2)
            
            Spacer()
            
            // Screen monitoring status
            if appState.screenMonitoringEnabled {
                HStack(spacing: 6) {
                    Image(systemName: "eye.fill")
                        .font(.system(size: 10))
                        .foregroundStyle(.secondary)
                    
                    Text("Screen Monitoring")
                        .font(.system(size: 11, weight: .medium))
                        .foregroundStyle(.secondary)
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .glassCard(cornerRadius: 12, backgroundOpacity: 0.2)
            }
        }
        .padding(.top, 10)
    }
    
    // MARK: - Helpers
    
    private var militaryGradient: [Color] {
        [Color(red: 0.3, green: 0.5, blue: 0.2), Color(red: 0.2, green: 0.3, blue: 0.5)]  // Olive green + navy blue
    }
    
    private var rankColor: Color {
        switch appState.currentRank.lowercased() {
        case "recruit":
            return .gray
        case "private":
            return Color(red: 0.3, green: 0.5, blue: 0.8)  // Navy blue
        case "corporal":
            return Color(red: 0.3, green: 0.6, blue: 0.3)  // Olive green
        case "sergeant":
            return Color(red: 0.6, green: 0.3, blue: 0.8)  // Purple
        case "staff sergeant":
            return Color(red: 0.8, green: 0.6, blue: 0.2)  // Gold
        case "captain":
            return Color(red: 0.9, green: 0.4, blue: 0.2)  // Orange
        default:
            return .white
        }
    }
    
    private func showEndSessionConfirmation() {
        let penalty = Int(Double(appState.sessionXP) * 0.5)  // 50% penalty
        
        let alert = NSAlert()
        alert.messageText = "End Session Early?"
        alert.informativeText = "You'll lose \(penalty) XP (50% penalty).\n\nContinue?"
        alert.alertStyle = .warning
        alert.addButton(withTitle: "End Session")
        alert.addButton(withTitle: "Keep Going")
        
        let response = alert.runModal()
        
        if response == .alertFirstButtonReturn {
            endSessionEarly()
        }
    }
    
    private func endSessionEarly() {
        guard let url = URL(string: "http://127.0.0.1:5050/api/session/end") else { return }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        // Pass early=true to apply XP penalty
        let body: [String: Any] = ["early": true]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        URLSession.shared.dataTask(with: request) { [weak appState] data, response, error in
            if error == nil {
                DispatchQueue.main.async {
                    withAnimation(.spring(response: 0.5, dampingFraction: 0.8)) {
                        appState?.isSessionActive = false
                        appState?.sessionGoal = ""
                        appState?.focusTimeMinutes = 0
                    }
                }
            }
        }.resume()
    }
}

// MARK: - Stat Card

struct StatCard: View {
    let label: String
    let value: String
    let unit: String
    let icon: String
    let color: Color
    
    var body: some View {
        HoverGlassCard(cornerRadius: 16) {
            VStack(alignment: .leading, spacing: 8) {
                Image(systemName: icon)
                    .font(.system(size: 16))
                    .foregroundStyle(color)
                
                HStack(alignment: .lastTextBaseline, spacing: 4) {
                    Text(value)
                        .font(.system(size: 24, weight: .bold, design: .rounded))
                        .foregroundStyle(.primary)
                    
                    if !unit.isEmpty {
                        Text(unit)
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(.secondary)
                    }
                }
                
                Text(label)
                    .font(.system(size: 11, weight: .medium, design: .monospaced))
                    .foregroundStyle(.secondary)
                    .tracking(0.5)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(14)
        }
    }
}

// MARK: - Preview

#Preview {
    DashboardView()
        .environmentObject(AppState())
}
