//
//  SettingsView.swift
//  CodeSergeantUI
//
//  Settings panel with AI configuration, screen monitoring, and privacy options
//

import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var appState: AppState
    
    var body: some View {
        TabView {
            // AI Settings
            AISettingsTab()
                .environmentObject(appState)
                .tabItem {
                    Label("AI", systemImage: "cpu")
                }
            
            // Screen Monitoring
            ScreenMonitoringTab()
                .environmentObject(appState)
                .tabItem {
                    Label("Monitoring", systemImage: "eye")
                }
            
            // Personality
            PersonalityTab()
                .tabItem {
                    Label("Personality", systemImage: "person.fill")
                }
            
            // About
            AboutTab()
                .tabItem {
                    Label("About", systemImage: "info.circle")
                }
        }
        .frame(width: 500, height: 400)
    }
}

// MARK: - AI Settings Tab

struct AISettingsTab: View {
    @EnvironmentObject var appState: AppState
    @State private var openAIKey: String = ""
    @State private var showKey: Bool = false
    @State private var isSaving: Bool = false
    @State private var saveMessage: String?
    
    var body: some View {
        Form {
            Section {
                // OpenAI Status
                HStack {
                    Label("OpenAI", systemImage: "cpu")
                    Spacer()
                    StatusBadge(
                        status: appState.openAIAvailable ? "Active" : "Not Configured",
                        color: appState.openAIAvailable ? .green : .orange
                    )
                }
                
                // Ollama Status
                HStack {
                    Label("Ollama (Local)", systemImage: "server.rack")
                    Spacer()
                    StatusBadge(
                        status: appState.ollamaAvailable ? "Running" : "Not Running",
                        color: appState.ollamaAvailable ? .green : .gray
                    )
                }
                
                // Primary Backend
                HStack {
                    Label("Primary Backend", systemImage: "checkmark.circle.fill")
                    Spacer()
                    Text(appState.primaryBackend.capitalized)
                        .foregroundStyle(.secondary)
                }
            } header: {
                Text("Status")
            }
            
            Section {
                // API Key Input
                VStack(alignment: .leading, spacing: 8) {
                    Text("OpenAI API Key")
                        .font(.headline)
                    
                    HStack {
                        if showKey {
                            TextField("sk-...", text: $openAIKey)
                                .textFieldStyle(.roundedBorder)
                        } else {
                            SecureField("sk-...", text: $openAIKey)
                                .textFieldStyle(.roundedBorder)
                        }
                        
                        Button {
                            showKey.toggle()
                        } label: {
                            Image(systemName: showKey ? "eye.slash" : "eye")
                        }
                        .buttonStyle(.borderless)
                    }
                    
                    Text("Your API key is stored securely in .env and never logged")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                
                // Save Button
                HStack {
                    Button("Save API Key") {
                        saveAPIKey()
                    }
                    .disabled(openAIKey.isEmpty || isSaving)
                    
                    if let message = saveMessage {
                        Text(message)
                            .font(.caption)
                            .foregroundStyle(message.contains("Error") ? .red : .green)
                    }
                }
            } header: {
                Text("OpenAI Configuration")
            }
            
            Section {
                Link("Get an OpenAI API Key", destination: URL(string: "https://platform.openai.com/api-keys")!)
                
                Link("Install Ollama (Free Local AI)", destination: URL(string: "https://ollama.com/download")!)
            } header: {
                Text("Resources")
            }
        }
        .formStyle(.grouped)
        .padding()
    }
    
    private func saveAPIKey() {
        isSaving = true
        saveMessage = nil
        
        appState.setOpenAIKey(openAIKey)
        
        // Simulate save delay
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            isSaving = false
            saveMessage = "✓ Saved successfully"
            openAIKey = ""
            
            // Clear message after delay
            DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                saveMessage = nil
            }
        }
    }
}

// MARK: - Screen Monitoring Tab

struct ScreenMonitoringTab: View {
    @EnvironmentObject var appState: AppState
    @State private var blockedApps: String = ""
    
    var body: some View {
        Form {
            Section {
                Toggle("Enable Screen Monitoring", isOn: Binding(
                    get: { appState.screenMonitoringEnabled },
                    set: { appState.toggleScreenMonitoring($0) }
                ))
                
                // Vision Backend Status
                HStack {
                    Label("Vision Backend", systemImage: "eye.fill")
                    Spacer()
                    StatusBadge(
                        status: appState.visionBackendStatus.replacingOccurrences(of: "_", with: " ").capitalized,
                        color: statusColor
                    )
                }
                
                // Local/Cloud toggle
                Toggle("Use Local Vision (LLaVA)", isOn: $appState.useLocalVision)
                    .disabled(!appState.ollamaAvailable)
                
                if appState.useLocalVision && !appState.ollamaAvailable {
                    HStack {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundStyle(.orange)
                        Text("Ollama not running. Will fall back to OpenAI.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            } header: {
                Text("Screen Analysis")
            } footer: {
                Text("Screen monitoring captures your screen periodically to analyze your progress. Data is never stored to disk.")
            }
            
            Section {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Blocked Apps")
                        .font(.headline)
                    
                    Text("Apps that will never be captured (banking, passwords, etc.)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    
                    TextEditor(text: $blockedApps)
                        .frame(height: 100)
                        .font(.system(.body, design: .monospaced))
                        .overlay(
                            RoundedRectangle(cornerRadius: 4)
                                .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                        )
                }
            } header: {
                Text("Privacy Blocklist")
            }
        }
        .formStyle(.grouped)
        .padding()
        .onAppear {
            // Load default blocked apps
            blockedApps = """
            1Password
            LastPass
            Keychain Access
            PayPal
            Chase
            Bank of America
            """
        }
    }
    
    private var statusColor: Color {
        switch appState.visionBackendStatus {
        case "ollama":
            return .green
        case "openai", "openai_fallback":
            return .blue
        case "ollama_fallback":
            return .orange
        case "disabled":
            return .red
        default:
            return .gray
        }
    }
}

// MARK: - Personality Tab

struct PersonalityTab: View {
    @State private var selectedPersonality = "drill_sergeant"
    @State private var intensityLevel: Double = 0.7
    
    let personalities = [
        ("drill_sergeant", "Drill Sergeant", "Tough love motivation with military precision"),
        ("coach", "Supportive Coach", "Encouraging and patient guidance"),
        ("mentor", "Wise Mentor", "Thoughtful insights and gentle nudges"),
        ("minimal", "Minimal", "Just the essentials, no fluff")
    ]
    
    var body: some View {
        Form {
            Section {
                Picker("Personality", selection: $selectedPersonality) {
                    ForEach(personalities, id: \.0) { personality in
                        VStack(alignment: .leading) {
                            Text(personality.1)
                            Text(personality.2)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .tag(personality.0)
                    }
                }
                .pickerStyle(.radioGroup)
            } header: {
                Text("Choose Your Guide")
            }
            
            Section {
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("Intensity")
                        Spacer()
                        Text("\(Int(intensityLevel * 100))%")
                            .foregroundStyle(.secondary)
                    }
                    
                    Slider(value: $intensityLevel, in: 0...1)
                    
                    HStack {
                        Text("Gentle")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Spacer()
                        Text("Intense")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            } header: {
                Text("Motivation Intensity")
            } footer: {
                Text("Higher intensity means more frequent and direct feedback.")
            }
        }
        .formStyle(.grouped)
        .padding()
    }
}

// MARK: - About Tab

struct AboutTab: View {
    var body: some View {
        VStack(spacing: 20) {
            Spacer()
            
            // App icon
            Image(systemName: "shield.lefthalf.filled")
                .font(.system(size: 64))
                .foregroundStyle(
                    LinearGradient(
                        colors: [.blue, .purple],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                )
            
            // App name
            Text("Code Sergeant")
                .font(.system(size: 24, weight: .bold))
            
            // Version
            Text("Version 2.0.0")
                .font(.system(size: 14))
                .foregroundStyle(.secondary)
            
            // Description
            Text("Your AI-powered productivity drill sergeant.\nStay focused. Get things done.")
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)
            
            Spacer()
            
            // Links
            HStack(spacing: 20) {
                Link("GitHub", destination: URL(string: "https://github.com/CuevaLabs/CodeSergeant")!)
                Link("Documentation", destination: URL(string: "https://github.com/CuevaLabs/CodeSergeant#readme")!)
                Link("Report Issue", destination: URL(string: "https://github.com/CuevaLabs/CodeSergeant/issues")!)
            }
            .font(.system(size: 12))
            
            // Copyright
            Text("© 2026 Code Sergeant")
                .font(.system(size: 11))
                .foregroundStyle(.tertiary)
            
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: - Status Badge

struct StatusBadge: View {
    let status: String
    let color: Color
    
    var body: some View {
        HStack(spacing: 4) {
            Circle()
                .fill(color)
                .frame(width: 6, height: 6)
            
            Text(status)
                .font(.system(size: 11, weight: .medium))
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(color.opacity(0.1))
        )
    }
}

// MARK: - Preview

#Preview {
    SettingsView()
        .environmentObject(AppState())
}

