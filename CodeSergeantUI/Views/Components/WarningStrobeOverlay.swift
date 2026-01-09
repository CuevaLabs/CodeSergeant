//
//  WarningStrobeOverlay.swift
//  CodeSergeantUI
//
//  Flashing border overlay for warning states (green/yellow/red)
//

import SwiftUI

/// Flashing border overlay for warning states
struct WarningStrobeOverlay: ViewModifier {
    let status: WarningStatus
    @State private var isFlashing = false
    
    func body(content: Content) -> some View {
        content
            .overlay(
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .stroke(strokeColor, lineWidth: strokeWidth)
                    .opacity(isFlashing ? 1.0 : 0.3)
                    .animation(
                        status == .red
                            ? .easeInOut(duration: 0.5).repeatForever(autoreverses: true)
                            : .easeInOut(duration: 1.0),
                        value: isFlashing
                    )
            )
            .onChange(of: status) { newStatus in
                withAnimation {
                    isFlashing = newStatus == .red
                }
            }
            .onAppear {
                isFlashing = status == .red
            }
    }
    
    private var strokeColor: Color {
        switch status {
        case .green:
            return .green
        case .yellow:
            return .yellow
        case .red:
            return .red
        }
    }
    
    private var strokeWidth: CGFloat {
        switch status {
        case .green:
            return 2
        case .yellow:
            return 3
        case .red:
            return 4
        }
    }
}

extension View {
    /// Apply warning strobe border based on status
    func warningStrobe(status: WarningStatus) -> some View {
        modifier(WarningStrobeOverlay(status: status))
    }
}

// MARK: - Preview

#Preview {
    VStack(spacing: 30) {
        // Green - on task
        Text("On Task")
            .font(.system(size: 24, weight: .bold))
            .frame(width: 200, height: 100)
            .background(.ultraThinMaterial)
            .cornerRadius(12)
            .warningStrobe(status: .green)
        
        // Yellow - thinking
        Text("Thinking")
            .font(.system(size: 24, weight: .bold))
            .frame(width: 200, height: 100)
            .background(.ultraThinMaterial)
            .cornerRadius(12)
            .warningStrobe(status: .yellow)
        
        // Red - off task (flashing)
        Text("Off Task")
            .font(.system(size: 24, weight: .bold))
            .frame(width: 200, height: 100)
            .background(.ultraThinMaterial)
            .cornerRadius(12)
            .warningStrobe(status: .red)
    }
    .padding(40)
    .background(GlassBackground())
}
