//
//  MenuBarView.swift
//  CodeSergeantUI
//
//  Menu bar dropdown with liquid glass design, XP system, and warning strobe
//

import SwiftUI
import AppKit

struct MenuBarView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.openWindow) private var openWindow
    @State private var showingEndSessionAlert = false
    
    var body: some View {
        VStack(spacing: 0) {
            // Header with rank/status
            headerSection
            
            Divider().background(.white.opacity(0.1))
            
            // XP Display (compact)
            xpSection
            
            Divider().background(.white.opacity(0.1))
            
            // Quick status
            statusSection
            
            Divider().background(.white.opacity(0.1))
            
            // Actions
            actionsSection
            
            Divider().background(.white.opacity(0.1))
            
            // Footer
            footerSection
        }
        .frame(width: 300)
        .background(.ultraThinMaterial)
        .warningStrobe(status: appState.warningStatus)  // Apply strobe border
    }
    
    // MARK: - Header
    
    private var headerSection: some View {
        HStack(spacing: 12) {
            // App icon (using SF Symbol until custom icon.png provided)
            Image(systemName: "shield.lefthalf.filled")
                .font(.system(size: 24))
                .foregroundStyle(
                    LinearGradient(
                        colors: militaryGradient,
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
            
            VStack(alignment: .leading, spacing: 2) {
                Text("CODE SERGEANT")
                    .font(.system(size: 14, weight: .black, design: .monospaced))
                    .tracking(1)
                
                // Status with color dot
                HStack(spacing: 6) {
                    Circle()
                        .fill(statusDotColor)
                        .frame(width: 8, height: 8)
                    
                    Text(appState.isSessionActive ? "ACTIVE" : "READY")
                        .font(.system(size: 11, weight: .semibold, design: .monospaced))
                        .foregroundStyle(.secondary)
                }
            }
            
            Spacer()
        }
        .padding(16)
    }
    
    // MARK: - XP Section
    
    private var xpSection: some View {
        VStack(spacing: 8) {
            XPDisplay(
                totalXP: appState.totalXP,
                sessionXP: appState.sessionXP,
                currentRank: appState.currentRank,
                rankProgress: appState.rankProgress,
                nextRankName: appState.nextRankName,
                xpToNextRank: appState.xpToNextRank,
                isCompact: true
            )
            
            // Session stats (if active)
            if appState.isSessionActive {
                HStack(spacing: 12) {
                    StatPill(icon: "clock.fill", value: "\(appState.focusTimeMinutes)m")
                    if !appState.sessionGoal.isEmpty {
                        StatPill(icon: "target", value: appState.sessionGoal, isText: true)
                    }
                }
            }
        }
        .padding(12)
    }
    
    // MARK: - Status
    
    private var statusSection: some View {
        VStack(spacing: 8) {
            if appState.isSessionActive {
                CompactTimerDisplay(
                    remainingSeconds: appState.remainingSeconds,
                    isBreak: appState.isBreak
                )
            } else {
                Text("No active session")
                    .font(.system(size: 12))
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
    }
    
    // MARK: - Actions
    
    private var actionsSection: some View {
        VStack(spacing: 4) {
            if appState.isSessionActive {
                // Pause/Resume toggle with proper state - FIXED
                MenuBarButton(
                    title: appState.isPaused ? "Resume" : "Pause",
                    icon: appState.isPaused ? "play.fill" : "pause.fill"
                ) {
                    if appState.isPaused {
                        appState.resumeSession()
                    } else {
                        appState.pauseSession()
                    }
                }
                
                // End session with confirmation - FIXED
                MenuBarButton(
                    title: "End Session",
                    icon: "stop.fill",
                    color: .red
                ) {
                    showEndSessionConfirmation()
                }
                
                // Skip break (if on break)
                if appState.isBreak {
                    MenuBarButton(
                        title: "Skip Break",
                        icon: "forward.fill",
                        color: .orange
                    ) {
                        appState.skipBreak()
                    }
                }
            } else {
                // Start focus session
                MenuBarButton(
                    title: "Start Focus Session",
                    icon: "play.fill",
                    color: .blue
                ) {
                    openWindow(id: "dashboard")
                }
            }
            
            // Dashboard access
            MenuBarButton(
                title: "Open Dashboard",
                icon: "chart.bar.fill"
            ) {
                openWindow(id: "dashboard")
            }
        }
        .padding(8)
    }
    
    // MARK: - Footer
    
    private var footerSection: some View {
        HStack(spacing: 8) {
            // Settings button - FIXED
            Button {
                if #available(macOS 14.0, *) {
                    NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
                } else {
                    NSApp.sendAction(Selector(("showPreferencesWindow:")), to: nil, from: nil)
                }
            } label: {
                Label("Settings", systemImage: "gear")
                    .font(.system(size: 12))
            }
            .buttonStyle(.plain)
            .foregroundStyle(.secondary)
            
            Spacer()
            
            // AI status indicator
            HStack(spacing: 4) {
                Circle()
                    .fill(appState.openAIAvailable || appState.ollamaAvailable ? Color.green : Color.red)
                    .frame(width: 6, height: 6)
                
                Text(appState.primaryBackend.uppercased())
                    .font(.system(size: 10, weight: .medium, design: .monospaced))
                    .foregroundStyle(.secondary)
            }
            
            // Quit button
            Button {
                NSApplication.shared.terminate(nil)
            } label: {
                Image(systemName: "power")
                    .font(.system(size: 12))
            }
            .buttonStyle(.plain)
            .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
    }
    
    // MARK: - Helpers
    
    private var militaryGradient: [Color] {
        [Color(red: 0.3, green: 0.5, blue: 0.2), Color(red: 0.2, green: 0.3, blue: 0.5)]  // Olive green + navy blue
    }
    
    private var statusDotColor: Color {
        switch appState.warningStatus {
        case .green:
            return .green
        case .yellow:
            return .yellow
        case .red:
            return .red
        }
    }
    
    private func showEndSessionConfirmation() {
        let penalty = Int(Double(appState.sessionXP) * 0.5)  // 50% penalty
        
        let alert = NSAlert()
        alert.messageText = "End Session Early?"
        alert.informativeText = "Ending now will lose \(penalty) XP (50% penalty).\n\nAre you sure you want to end?"
        alert.alertStyle = .warning
        alert.addButton(withTitle: "End Session")
        alert.addButton(withTitle: "Keep Going")
        
        let response = alert.runModal()
        
        if response == .alertFirstButtonReturn {
            // End with early penalty
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
                    appState?.isSessionActive = false
                    appState?.sessionGoal = ""
                    appState?.focusTimeMinutes = 0
                }
            }
        }.resume()
    }
}

// MARK: - Helper Components

struct StatPill: View {
    let icon: String
    let value: String
    var isText: Bool = false
    
    var body: some View {
        HStack(spacing: 4) {
            Image(systemName: icon)
                .font(.system(size: 10))
                .foregroundStyle(.secondary)
            
            Text(value)
                .font(.system(size: 11, weight: .medium))
                .foregroundStyle(.secondary)
                .lineLimit(1)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(
            Capsule()
                .fill(.white.opacity(0.08))
        )
    }
}

// MARK: - Menu Bar Button

struct MenuBarButton: View {
    let title: String
    let icon: String
    var color: Color = .primary
    let action: () -> Void
    
    @State private var isHovering = false
    
    var body: some View {
        Button(action: action) {
            HStack(spacing: 10) {
                Image(systemName: icon)
                    .font(.system(size: 12))
                    .foregroundStyle(color)
                    .frame(width: 20)
                
                Text(title)
                    .font(.system(size: 13))
                
                Spacer()
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .fill(isHovering ? .white.opacity(0.1) : .clear)
            )
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovering = hovering
            }
        }
    }
}

// MARK: - Preview

#Preview {
    MenuBarView()
        .environmentObject(AppState())
        .frame(width: 300)
}
