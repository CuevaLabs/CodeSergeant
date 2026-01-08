//
//  GlassCard.swift
//  CodeSergeantUI
//
//  Liquid Glass card component with macOS Sonoma/Sequoia design
//

import SwiftUI

// MARK: - Glass Card Modifier

struct GlassCard: ViewModifier {
    var cornerRadius: CGFloat = 20
    var backgroundOpacity: Double = 0.3
    var borderOpacity: Double = 0.5
    var shadowRadius: CGFloat = 10
    var isHovering: Bool = false
    
    func body(content: Content) -> some View {
        content
            // Frosted glass background
            .background(
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .fill(.ultraThinMaterial)
                    .opacity(backgroundOpacity)
            )
            // Inner highlight (top-left light reflection)
            .overlay(
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .stroke(
                        LinearGradient(
                            colors: [
                                .white.opacity(borderOpacity),
                                .white.opacity(borderOpacity * 0.3),
                                .clear
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ),
                        lineWidth: 1
                    )
            )
            // Outer glow on hover
            .shadow(
                color: isHovering ? .blue.opacity(0.2) : .black.opacity(0.1),
                radius: isHovering ? shadowRadius * 1.5 : shadowRadius,
                x: 0,
                y: isHovering ? 8 : 5
            )
            // Scale on hover
            .scaleEffect(isHovering ? 1.02 : 1.0)
            .animation(.spring(response: 0.3, dampingFraction: 0.7), value: isHovering)
    }
}

// MARK: - View Extension

extension View {
    /// Apply liquid glass card styling
    func glassCard(
        cornerRadius: CGFloat = 20,
        backgroundOpacity: Double = 0.3,
        borderOpacity: Double = 0.5,
        shadowRadius: CGFloat = 10,
        isHovering: Bool = false
    ) -> some View {
        modifier(GlassCard(
            cornerRadius: cornerRadius,
            backgroundOpacity: backgroundOpacity,
            borderOpacity: borderOpacity,
            shadowRadius: shadowRadius,
            isHovering: isHovering
        ))
    }
}

// MARK: - Hover Glass Card

/// A glass card that automatically handles hover state
struct HoverGlassCard<Content: View>: View {
    let cornerRadius: CGFloat
    let content: Content
    
    @State private var isHovering = false
    
    init(cornerRadius: CGFloat = 20, @ViewBuilder content: () -> Content) {
        self.cornerRadius = cornerRadius
        self.content = content()
    }
    
    var body: some View {
        content
            .glassCard(cornerRadius: cornerRadius, isHovering: isHovering)
            .onHover { hovering in
                withAnimation(.spring(response: 0.2, dampingFraction: 0.7)) {
                    isHovering = hovering
                }
            }
    }
}

// MARK: - Glass Background

/// Full-screen glass background with depth effect
struct GlassBackground: View {
    var opacity: Double = 0.5
    
    var body: some View {
        ZStack {
            // Base dark color
            Color.black.opacity(0.3)
            
            // Gradient overlay for depth
            LinearGradient(
                colors: [
                    Color.blue.opacity(0.05),
                    Color.purple.opacity(0.05),
                    Color.clear
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            
            // Noise texture overlay (simulated)
            Rectangle()
                .fill(.ultraThinMaterial)
                .opacity(opacity)
        }
        .ignoresSafeArea()
    }
}

// MARK: - Animated Glass Border

/// Glass card with animated gradient border
struct AnimatedGlassBorder: ViewModifier {
    @State private var animationProgress: CGFloat = 0
    var cornerRadius: CGFloat = 20
    
    func body(content: Content) -> some View {
        content
            .overlay(
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .stroke(
                        AngularGradient(
                            gradient: Gradient(colors: [
                                .blue.opacity(0.6),
                                .purple.opacity(0.6),
                                .pink.opacity(0.6),
                                .blue.opacity(0.6)
                            ]),
                            center: .center,
                            startAngle: .degrees(animationProgress * 360),
                            endAngle: .degrees(animationProgress * 360 + 360.0)
                        ),
                        lineWidth: 2
                    )
                    .opacity(0.5)
            )
            .onAppear {
                withAnimation(.linear(duration: 3).repeatForever(autoreverses: false)) {
                    animationProgress = 1
                }
            }
    }
}

extension View {
    func animatedGlassBorder(cornerRadius: CGFloat = 20) -> some View {
        modifier(AnimatedGlassBorder(cornerRadius: cornerRadius))
    }
}

// MARK: - Preview

#Preview {
    VStack(spacing: 20) {
        // Basic glass card
        Text("Basic Glass Card")
            .font(.headline)
            .padding(20)
            .glassCard()
        
        // Hover glass card
        HoverGlassCard {
            VStack(alignment: .leading, spacing: 8) {
                Text("Hover Glass Card")
                    .font(.headline)
                Text("Hover over me!")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            .padding(20)
        }
        
        // Animated border card
        Text("Animated Border")
            .font(.headline)
            .padding(20)
            .glassCard()
            .animatedGlassBorder()
    }
    .padding(40)
    .frame(width: 400, height: 400)
    .background(GlassBackground())
}

