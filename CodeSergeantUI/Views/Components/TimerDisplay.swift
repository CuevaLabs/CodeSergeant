//
//  TimerDisplay.swift
//  CodeSergeantUI
//
//  Liquid glass timer display with animations
//

import SwiftUI

// MARK: - Timer Display

struct TimerDisplay: View {
    let remainingSeconds: Int
    let totalSeconds: Int
    let isBreak: Bool
    
    @State private var pulseAnimation = false
    
    private var progress: Double {
        guard totalSeconds > 0 else { return 0 }
        return Double(totalSeconds - remainingSeconds) / Double(totalSeconds)
    }
    
    private var timeString: String {
        let minutes = remainingSeconds / 60
        let seconds = remainingSeconds % 60
        return String(format: "%02d:%02d", minutes, seconds)
    }
    
    var body: some View {
        ZStack {
            // Background ring
            Circle()
                .stroke(
                    LinearGradient(
                        colors: [.white.opacity(0.1), .white.opacity(0.05)],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    ),
                    lineWidth: 12
                )
            
            // Progress ring
            Circle()
                .trim(from: 0, to: progress)
                .stroke(
                    AngularGradient(
                        colors: isBreak
                            ? [.green.opacity(0.8), .teal.opacity(0.8)]
                            : [.blue.opacity(0.8), .purple.opacity(0.8)],
                        center: .center
                    ),
                    style: StrokeStyle(lineWidth: 12, lineCap: .round)
                )
                .rotationEffect(.degrees(-90))
                .animation(.easeInOut(duration: 0.5), value: progress)
            
            // Glow effect
            Circle()
                .trim(from: max(0, progress - 0.05), to: progress)
                .stroke(
                    isBreak ? Color.green : Color.blue,
                    style: StrokeStyle(lineWidth: 12, lineCap: .round)
                )
                .rotationEffect(.degrees(-90))
                .blur(radius: 8)
                .opacity(0.6)
            
            // Inner content
            VStack(spacing: 4) {
                // Status label
                Text(isBreak ? "BREAK" : "FOCUS")
                    .font(.system(size: 14, weight: .bold, design: .rounded))
                    .foregroundStyle(.secondary)
                    .tracking(2)
                
                // Time display
                Text(timeString)
                    .font(.system(size: 48, weight: .bold, design: .rounded))
                    .foregroundStyle(
                        LinearGradient(
                            colors: [.white, .white.opacity(0.8)],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
                    .monospacedDigit()
                    .contentTransition(.numericText())
                    .animation(.spring(response: 0.3, dampingFraction: 0.7), value: remainingSeconds)
                
                // Progress percentage
                Text("\(Int(progress * 100))%")
                    .font(.system(size: 14, weight: .medium, design: .rounded))
                    .foregroundStyle(.secondary)
            }
            .scaleEffect(pulseAnimation ? 1.02 : 1.0)
            .animation(
                .easeInOut(duration: 1)
                .repeatForever(autoreverses: true),
                value: pulseAnimation
            )
        }
        .frame(width: 200, height: 200)
        .padding(20)
        .glassCard(cornerRadius: 100, backgroundOpacity: 0.2)
        .onAppear {
            pulseAnimation = true
        }
    }
}

// MARK: - Compact Timer

struct CompactTimerDisplay: View {
    let remainingSeconds: Int
    let isBreak: Bool
    
    private var timeString: String {
        let minutes = remainingSeconds / 60
        let seconds = remainingSeconds % 60
        return String(format: "%02d:%02d", minutes, seconds)
    }
    
    var body: some View {
        HStack(spacing: 8) {
            // Status indicator
            Circle()
                .fill(isBreak ? Color.green : Color.blue)
                .frame(width: 8, height: 8)
            
            // Time
            Text(timeString)
                .font(.system(size: 18, weight: .semibold, design: .rounded))
                .monospacedDigit()
                .foregroundStyle(.primary)
            
            // Label
            Text(isBreak ? "break" : "focus")
                .font(.system(size: 12, weight: .medium))
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .glassCard(cornerRadius: 20, backgroundOpacity: 0.2)
    }
}

// MARK: - Timer Slider

struct TimerSlider: View {
    let label: String
    @Binding var value: Double
    let range: ClosedRange<Double>
    let step: Double
    let unit: String
    
    @State private var isEditing = false
    
    init(
        label: String,
        value: Binding<Double>,
        range: ClosedRange<Double>,
        step: Double = 5,
        unit: String = "min"
    ) {
        self.label = label
        self._value = value
        self.range = range
        self.step = step
        self.unit = unit
    }
    
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(label)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(.secondary)
                
                Spacer()
                
                Text("\(Int(value)) \(unit)")
                    .font(.system(size: 16, weight: .bold, design: .rounded))
                    .foregroundStyle(.primary)
                    .monospacedDigit()
                    .animation(.spring(response: 0.2), value: value)
            }
            
            // Custom slider
            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    // Track background
                    RoundedRectangle(cornerRadius: 6)
                        .fill(.white.opacity(0.1))
                        .frame(height: 12)
                    
                    // Filled track
                    RoundedRectangle(cornerRadius: 6)
                        .fill(
                            LinearGradient(
                                colors: [.blue.opacity(0.8), .purple.opacity(0.8)],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(
                            width: trackWidth(in: geometry.size.width),
                            height: 12
                        )
                    
                    // Thumb
                    Circle()
                        .fill(.white)
                        .frame(width: isEditing ? 24 : 20, height: isEditing ? 24 : 20)
                        .shadow(color: .blue.opacity(0.3), radius: isEditing ? 8 : 4)
                        .offset(x: thumbOffset(in: geometry.size.width))
                        .gesture(
                            DragGesture()
                                .onChanged { gesture in
                                    isEditing = true
                                    updateValue(from: gesture.location.x, in: geometry.size.width)
                                }
                                .onEnded { _ in
                                    isEditing = false
                                }
                        )
                        .animation(.spring(response: 0.2, dampingFraction: 0.7), value: isEditing)
                }
            }
            .frame(height: 24)
        }
    }
    
    private func trackWidth(in totalWidth: CGFloat) -> CGFloat {
        let percent = (value - range.lowerBound) / (range.upperBound - range.lowerBound)
        return totalWidth * CGFloat(percent)
    }
    
    private func thumbOffset(in totalWidth: CGFloat) -> CGFloat {
        let percent = (value - range.lowerBound) / (range.upperBound - range.lowerBound)
        return (totalWidth - 20) * CGFloat(percent)
    }
    
    private func updateValue(from x: CGFloat, in totalWidth: CGFloat) {
        let percent = max(0, min(1, x / totalWidth))
        let rawValue = range.lowerBound + (range.upperBound - range.lowerBound) * Double(percent)
        let steppedValue = (rawValue / step).rounded() * step
        value = max(range.lowerBound, min(range.upperBound, steppedValue))
    }
}

// MARK: - Preview

#Preview {
    VStack(spacing: 30) {
        TimerDisplay(
            remainingSeconds: 1234,
            totalSeconds: 1500,
            isBreak: false
        )
        
        CompactTimerDisplay(
            remainingSeconds: 234,
            isBreak: true
        )
        
        TimerSlider(
            label: "Work Duration",
            value: .constant(25),
            range: 15...60
        )
        .padding(.horizontal, 20)
        
        TimerSlider(
            label: "Break Duration",
            value: .constant(5),
            range: 5...15
        )
        .padding(.horizontal, 20)
    }
    .padding(40)
    .frame(width: 400, height: 600)
    .background(GlassBackground())
}

