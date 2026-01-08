//
//  GlassEffect.swift
//  CodeSergeantUI
//
//  Advanced liquid glass effects and animations
//

import SwiftUI
import AppKit

// MARK: - Parallax Effect

struct ParallaxEffect: ViewModifier {
    @State private var offset: CGSize = .zero
    var intensity: CGFloat = 20
    
    func body(content: Content) -> some View {
        content
            .offset(x: offset.width, y: offset.height)
            .onContinuousHover { phase in
                switch phase {
                case .active(let location):
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                        // Calculate offset based on mouse position
                        let centerX = 260.0 // Approximate center
                        let centerY = 340.0
                        offset = CGSize(
                            width: (location.x - centerX) / centerX * intensity,
                            height: (location.y - centerY) / centerY * intensity
                        )
                    }
                case .ended:
                    withAnimation(.spring(response: 0.5, dampingFraction: 0.7)) {
                        offset = .zero
                    }
                }
            }
    }
}

extension View {
    func parallaxEffect(intensity: CGFloat = 20) -> some View {
        modifier(ParallaxEffect(intensity: intensity))
    }
}

// MARK: - Shimmer Effect

struct ShimmerEffect: ViewModifier {
    @State private var phase: CGFloat = 0
    var duration: Double = 2.5
    
    func body(content: Content) -> some View {
        content
            .overlay(
                LinearGradient(
                    colors: [
                        .clear,
                        .white.opacity(0.1),
                        .white.opacity(0.2),
                        .white.opacity(0.1),
                        .clear
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .rotationEffect(.degrees(30))
                .offset(x: phase * 500 - 250)
                .mask(content)
            )
            .onAppear {
                withAnimation(.linear(duration: duration).repeatForever(autoreverses: false)) {
                    phase = 1
                }
            }
    }
}

extension View {
    func shimmer(duration: Double = 2.5) -> some View {
        modifier(ShimmerEffect(duration: duration))
    }
}

// MARK: - Glow Effect

struct GlowEffect: ViewModifier {
    var color: Color
    var radius: CGFloat
    var isAnimated: Bool
    
    @State private var animationPhase: CGFloat = 0
    
    func body(content: Content) -> some View {
        content
            .shadow(
                color: color.opacity(isAnimated ? 0.3 + 0.2 * CGFloat(sin(animationPhase * .pi * 2)) : 0.5),
                radius: isAnimated ? radius + 5 * CGFloat(sin(animationPhase * .pi * 2)) : radius
            )
            .onAppear {
                if isAnimated {
                    withAnimation(.easeInOut(duration: 2).repeatForever(autoreverses: false)) {
                        animationPhase = 1
                    }
                }
            }
    }
}

extension View {
    func glow(color: Color = .blue, radius: CGFloat = 10, animated: Bool = false) -> some View {
        modifier(GlowEffect(color: color, radius: radius, isAnimated: animated))
    }
}

// MARK: - Depth Effect

struct DepthEffect: ViewModifier {
    var depth: CGFloat
    @State private var isHovering = false
    
    func body(content: Content) -> some View {
        content
            .rotation3DEffect(
                .degrees(isHovering ? 2 : 0),
                axis: (x: 1, y: 0, z: 0),
                perspective: 0.5
            )
            .shadow(
                color: .black.opacity(isHovering ? 0.3 : 0.1),
                radius: isHovering ? depth * 2 : depth,
                x: 0,
                y: isHovering ? depth : depth / 2
            )
            .scaleEffect(isHovering ? 1.02 : 1.0)
            .animation(.spring(response: 0.4, dampingFraction: 0.7), value: isHovering)
            .onHover { hovering in
                isHovering = hovering
            }
    }
}

extension View {
    func depthEffect(_ depth: CGFloat = 10) -> some View {
        modifier(DepthEffect(depth: depth))
    }
}

// MARK: - Breathing Animation

struct BreathingEffect: ViewModifier {
    @State private var isBreathing = false
    var intensity: CGFloat
    var duration: Double
    
    func body(content: Content) -> some View {
        content
            .scaleEffect(isBreathing ? 1 + intensity : 1)
            .opacity(isBreathing ? 1 : 0.9)
            .animation(
                .easeInOut(duration: duration)
                .repeatForever(autoreverses: true),
                value: isBreathing
            )
            .onAppear {
                isBreathing = true
            }
    }
}

extension View {
    func breathing(intensity: CGFloat = 0.02, duration: Double = 2) -> some View {
        modifier(BreathingEffect(intensity: intensity, duration: duration))
    }
}

// MARK: - Staggered Animation

struct StaggeredAnimation: ViewModifier {
    let index: Int
    let total: Int
    @State private var isVisible = false
    
    var delay: Double {
        Double(index) * 0.1
    }
    
    func body(content: Content) -> some View {
        content
            .opacity(isVisible ? 1 : 0)
            .offset(y: isVisible ? 0 : 20)
            .animation(
                .spring(response: 0.5, dampingFraction: 0.7)
                .delay(delay),
                value: isVisible
            )
            .onAppear {
                isVisible = true
            }
    }
}

extension View {
    func staggeredAnimation(index: Int, total: Int) -> some View {
        modifier(StaggeredAnimation(index: index, total: total))
    }
}

// MARK: - Morphing Shape

struct MorphingBackground: View {
    @State private var morphProgress: CGFloat = 0
    let colors: [Color]
    
    var body: some View {
        Canvas { context, size in
            let rect = CGRect(origin: .zero, size: size)
            
            // Create morphing blob shapes
            for (index, color) in colors.enumerated() {
                let offset = CGFloat(index) * 0.33
                let phase = (morphProgress + offset).truncatingRemainder(dividingBy: 1)
                
                let path = createBlobPath(in: rect, phase: phase, index: index)
                context.fill(path, with: .color(color.opacity(0.3)))
            }
        }
        .blur(radius: 60)
        .onAppear {
            withAnimation(.linear(duration: 10).repeatForever(autoreverses: false)) {
                morphProgress = 1
            }
        }
    }
    
    private func createBlobPath(in rect: CGRect, phase: CGFloat, index: Int) -> Path {
        var path = Path()
        
        let centerX = rect.midX + cos(phase * .pi * 2 + CGFloat(index)) * 50
        let centerY = rect.midY + sin(phase * .pi * 2 + CGFloat(index)) * 50
        let radius = min(rect.width, rect.height) * 0.3 + sin(phase * .pi * 4) * 20
        
        path.addEllipse(in: CGRect(
            x: centerX - radius,
            y: centerY - radius,
            width: radius * 2,
            height: radius * 2
        ))
        
        return path
    }
}

// MARK: - Liquid Animation

struct LiquidWave: Shape {
    var progress: CGFloat
    var waveHeight: CGFloat = 10
    var frequency: CGFloat = 2
    
    var animatableData: CGFloat {
        get { progress }
        set { progress = newValue }
    }
    
    func path(in rect: CGRect) -> Path {
        var path = Path()
        
        let midHeight = rect.height / 2
        
        path.move(to: CGPoint(x: 0, y: midHeight))
        
        for x in stride(from: 0, through: rect.width, by: 1) {
            let relativeX = x / rect.width
            let sine = sin((relativeX + progress) * frequency * .pi * 2)
            let y = midHeight + sine * waveHeight
            path.addLine(to: CGPoint(x: x, y: y))
        }
        
        path.addLine(to: CGPoint(x: rect.width, y: rect.height))
        path.addLine(to: CGPoint(x: 0, y: rect.height))
        path.closeSubpath()
        
        return path
    }
}

// MARK: - Window Animation Helpers

extension NSWindow {
    /// Animate window to a position with spring physics
    func animateFrame(to frame: NSRect, duration: Double = 0.3) {
        NSAnimationContext.runAnimationGroup { context in
            context.duration = duration
            context.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
            self.animator().setFrame(frame, display: true)
        }
    }
    
    /// Animate window appearing from menu bar (unsuck effect)
    func animateUnsuck(from menuBarPoint: NSPoint, to targetFrame: NSRect) {
        // Start small near menu bar
        let startFrame = NSRect(
            x: menuBarPoint.x - 10,
            y: menuBarPoint.y - 10,
            width: 20,
            height: 20
        )
        
        setFrame(startFrame, display: false)
        alphaValue = 0
        makeKeyAndOrderFront(nil)
        
        NSAnimationContext.runAnimationGroup { context in
            context.duration = 0.35
            context.timingFunction = CAMediaTimingFunction(controlPoints: 0.34, 1.56, 0.64, 1)
            self.animator().setFrame(targetFrame, display: true)
            self.animator().alphaValue = 1
        }
    }
    
    /// Animate window disappearing to menu bar (suck effect)
    func animateSuck(to menuBarPoint: NSPoint, completion: @escaping () -> Void) {
        let endFrame = NSRect(
            x: menuBarPoint.x - 1,
            y: menuBarPoint.y - 1,
            width: 2,
            height: 2
        )
        
        NSAnimationContext.runAnimationGroup({ context in
            context.duration = 0.3
            context.timingFunction = CAMediaTimingFunction(controlPoints: 0.34, 0, 0.64, 1)
            self.animator().setFrame(endFrame, display: true)
            self.animator().alphaValue = 0
        }, completionHandler: {
            self.orderOut(nil)
            completion()
        })
    }
}

// MARK: - Preview

#Preview {
    VStack(spacing: 20) {
        // Shimmer
        Text("Shimmer Effect")
            .font(.headline)
            .padding()
            .glassCard()
            .shimmer()
        
        // Glow
        Text("Glow Effect")
            .font(.headline)
            .padding()
            .glassCard()
            .glow(color: .blue, radius: 15, animated: true)
        
        // Breathing
        Text("Breathing")
            .font(.headline)
            .padding()
            .glassCard()
            .breathing()
        
        // Depth
        Text("Depth Effect")
            .font(.headline)
            .padding()
            .glassCard()
            .depthEffect()
    }
    .padding(40)
    .frame(width: 400, height: 500)
    .background(
        ZStack {
            GlassBackground()
            MorphingBackground(colors: [.blue, .purple, .pink])
        }
    )
}

