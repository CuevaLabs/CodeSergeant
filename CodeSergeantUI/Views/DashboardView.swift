//
//  DashboardView.swift
//  CodeSergeantUI
//
//  Main dashboard with liquid glass design for focus sessions
//

import SwiftUI

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
                            colors: [.blue, .purple],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                
                VStack(alignment: .leading, spacing: 2) {
                    Text("Code Sergeant")
                        .font(.system(size: 22, weight: .bold, design: .rounded))
                        .foregroundStyle(.primary)
                    
                    Text(appState.isSessionActive ? "Session Active" : "Ready to Focus")
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(.secondary)
                }
            }
            
            Spacer()
            
            // Settings button
            LiquidIconButton("gear", size: 40) {
                showingSettings = true
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
                    Label("Focus Goal", systemImage: "target")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(.secondary)
                    
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
                    Label("Session Settings", systemImage: "timer")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(.secondary)
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
            // Timer display
            TimerDisplay(
                remainingSeconds: appState.remainingSeconds,
                totalSeconds: Int(appState.workMinutes) * 60,
                isBreak: appState.isBreak
            )
            
            // Current goal
            HoverGlassCard(cornerRadius: 20) {
                VStack(alignment: .leading, spacing: 8) {
                    Label("Current Goal", systemImage: "target")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundStyle(.secondary)
                    
                    Text(appState.sessionGoal.isEmpty ? "No goal set" : appState.sessionGoal)
                        .font(.system(size: 16, weight: .medium))
                        .foregroundStyle(.primary)
                        .lineLimit(2)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(16)
            }
            
            // Session stats
            HStack(spacing: 16) {
                StatCard(
                    label: "Focus Time",
                    value: "\(appState.focusTimeMinutes)",
                    unit: "min",
                    icon: "clock.fill",
                    color: .blue
                )
                
                StatCard(
                    label: "Status",
                    value: appState.isBreak ? "Break" : "Focus",
                    unit: "",
                    icon: appState.isBreak ? "cup.and.saucer.fill" : "brain.head.profile",
                    color: appState.isBreak ? .green : .purple
                )
            }
            
            // Control buttons
            HStack(spacing: 12) {
                LiquidIconButton("pause.fill", size: 44) {
                    appState.pauseSession()
                }
                
                LiquidButton("End Session", icon: "stop.fill", style: .danger) {
                    withAnimation(.spring(response: 0.5, dampingFraction: 0.8)) {
                        appState.endSession()
                    }
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
                    .fill(appState.openAIAvailable ? Color.green : Color.orange)
                    .frame(width: 8, height: 8)
                
                Text(appState.primaryBackend == "openai" ? "OpenAI" : "Ollama")
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
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(.secondary)
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

