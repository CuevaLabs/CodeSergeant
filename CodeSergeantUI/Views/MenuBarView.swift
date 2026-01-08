//
//  MenuBarView.swift
//  CodeSergeantUI
//
//  Menu bar dropdown with liquid glass design
//

import SwiftUI

struct MenuBarView: View {
    @EnvironmentObject var appState: AppState
    @Environment(\.openWindow) private var openWindow
    
    var body: some View {
        VStack(spacing: 0) {
            // Header
            headerSection
            
            Divider()
                .background(.white.opacity(0.1))
            
            // Quick status
            statusSection
            
            Divider()
                .background(.white.opacity(0.1))
            
            // Actions
            actionsSection
            
            Divider()
                .background(.white.opacity(0.1))
            
            // Footer
            footerSection
        }
        .frame(width: 280)
        .background(.ultraThinMaterial)
    }
    
    // MARK: - Header
    
    private var headerSection: some View {
        HStack(spacing: 12) {
            Image(systemName: "shield.lefthalf.filled")
                .font(.system(size: 24))
                .foregroundStyle(
                    LinearGradient(
                        colors: [.blue, .purple],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
            
            VStack(alignment: .leading, spacing: 2) {
                Text("Code Sergeant")
                    .font(.system(size: 14, weight: .semibold))
                
                Text(appState.isSessionActive ? "Session Active" : "Ready")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }
            
            Spacer()
            
            // Status dot
            Circle()
                .fill(appState.isSessionActive ? Color.green : Color.gray)
                .frame(width: 10, height: 10)
        }
        .padding(16)
    }
    
    // MARK: - Status
    
    private var statusSection: some View {
        VStack(spacing: 12) {
            if appState.isSessionActive {
                // Timer display
                CompactTimerDisplay(
                    remainingSeconds: appState.remainingSeconds,
                    isBreak: appState.isBreak
                )
                
                // Current goal
                if !appState.sessionGoal.isEmpty {
                    HStack {
                        Image(systemName: "target")
                            .font(.system(size: 10))
                            .foregroundStyle(.secondary)
                        
                        Text(appState.sessionGoal)
                            .font(.system(size: 12))
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                            .truncationMode(.tail)
                    }
                }
                
                // Focus time
                HStack {
                    Image(systemName: "clock")
                        .font(.system(size: 10))
                        .foregroundStyle(.secondary)
                    
                    Text("\(appState.focusTimeMinutes) min focused today")
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                }
            } else {
                Text("No active session")
                    .font(.system(size: 12))
                    .foregroundStyle(.secondary)
            }
        }
        .padding(16)
    }
    
    // MARK: - Actions
    
    private var actionsSection: some View {
        VStack(spacing: 4) {
            if appState.isSessionActive {
                // Pause/Resume
                MenuBarButton(
                    title: "Pause Session",
                    icon: "pause.fill"
                ) {
                    appState.pauseSession()
                }
                
                // End session
                MenuBarButton(
                    title: "End Session",
                    icon: "stop.fill",
                    color: .red
                ) {
                    appState.endSession()
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
                // Open dashboard
                MenuBarButton(
                    title: "Start Focus Session",
                    icon: "play.fill",
                    color: .blue
                ) {
                    openWindow(id: "dashboard")
                }
            }
            
            // Always show dashboard option
            MenuBarButton(
                title: "Open Dashboard",
                icon: "rectangle.portrait.and.arrow.right.fill"
            ) {
                openWindow(id: "dashboard")
            }
        }
        .padding(8)
    }
    
    // MARK: - Footer
    
    private var footerSection: some View {
        VStack(spacing: 4) {
            // AI Status
            HStack {
                Image(systemName: "cpu")
                    .font(.system(size: 10))
                    .foregroundStyle(.secondary)
                
                Text(appState.primaryBackend == "openai" ? "OpenAI" : (appState.ollamaAvailable ? "Ollama" : "No AI"))
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
                
                Spacer()
                
                Circle()
                    .fill(appState.openAIAvailable || appState.ollamaAvailable ? Color.green : Color.red)
                    .frame(width: 6, height: 6)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            
            Divider()
                .background(.white.opacity(0.1))
            
            // Settings & Quit
            HStack(spacing: 8) {
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
                
                Button {
                    NSApplication.shared.terminate(nil)
                } label: {
                    Label("Quit", systemImage: "power")
                        .font(.system(size: 12))
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
        }
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
        .frame(width: 280)
}

