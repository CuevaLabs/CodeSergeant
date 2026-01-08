//
//  LiquidButton.swift
//  CodeSergeantUI
//
//  Liquid glass button with gradient, spring animations, and press effects
//

import SwiftUI

// MARK: - Liquid Button

struct LiquidButton: View {
    let title: String
    let icon: String?
    let style: ButtonStyle
    let action: () -> Void
    
    @State private var isPressed = false
    @State private var isHovering = false
    
    enum ButtonStyle {
        case primary    // Blue/purple gradient
        case secondary  // Subtle glass
        case success    // Green gradient
        case danger     // Red gradient
        case ghost      // Transparent with border
        
        var gradient: LinearGradient {
            switch self {
            case .primary:
                return LinearGradient(
                    colors: [Color.blue.opacity(0.9), Color.purple.opacity(0.9)],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            case .success:
                return LinearGradient(
                    colors: [Color.green.opacity(0.9), Color.teal.opacity(0.9)],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            case .danger:
                return LinearGradient(
                    colors: [Color.red.opacity(0.9), Color.orange.opacity(0.9)],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            case .secondary, .ghost:
                return LinearGradient(
                    colors: [Color.white.opacity(0.1), Color.white.opacity(0.05)],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            }
        }
        
        var textColor: Color {
            switch self {
            case .ghost:
                return .primary
            default:
                return .white
            }
        }
    }
    
    init(
        _ title: String,
        icon: String? = nil,
        style: ButtonStyle = .primary,
        action: @escaping () -> Void
    ) {
        self.title = title
        self.icon = icon
        self.style = style
        self.action = action
    }
    
    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if let icon = icon {
                    Image(systemName: icon)
                        .font(.system(size: 14, weight: .semibold))
                }
                
                Text(title)
                    .font(.system(size: 15, weight: .semibold))
            }
            .foregroundColor(style.textColor)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .padding(.horizontal, 20)
            .background(
                ZStack {
                    // Base gradient
                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                        .fill(style.gradient)
                    
                    // Glass overlay
                    if style == .secondary || style == .ghost {
                        RoundedRectangle(cornerRadius: 14, style: .continuous)
                            .fill(.ultraThinMaterial)
                    }
                    
                    // Highlight on hover
                    if isHovering && !isPressed {
                        RoundedRectangle(cornerRadius: 14, style: .continuous)
                            .fill(.white.opacity(0.1))
                    }
                    
                    // Press darken
                    if isPressed {
                        RoundedRectangle(cornerRadius: 14, style: .continuous)
                            .fill(.black.opacity(0.2))
                    }
                }
            )
            // Inner border highlight
            .overlay(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .stroke(
                        LinearGradient(
                            colors: [
                                .white.opacity(style == .ghost ? 0.3 : 0.4),
                                .white.opacity(0.1),
                                .clear
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ),
                        lineWidth: 1
                    )
            )
            // Shadow
            .shadow(
                color: shadowColor,
                radius: isPressed ? 4 : (isHovering ? 12 : 8),
                x: 0,
                y: isPressed ? 2 : (isHovering ? 6 : 4)
            )
            // Press scale
            .scaleEffect(isPressed ? 0.96 : (isHovering ? 1.02 : 1.0))
            // Smooth spring animation
            .animation(.spring(response: 0.25, dampingFraction: 0.6), value: isPressed)
            .animation(.spring(response: 0.3, dampingFraction: 0.7), value: isHovering)
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            isHovering = hovering
        }
        .pressActions(
            onPress: { isPressed = true },
            onRelease: { isPressed = false }
        )
    }
    
    private var shadowColor: Color {
        switch style {
        case .primary:
            return .blue.opacity(isHovering ? 0.4 : 0.3)
        case .success:
            return .green.opacity(isHovering ? 0.4 : 0.3)
        case .danger:
            return .red.opacity(isHovering ? 0.4 : 0.3)
        case .secondary, .ghost:
            return .black.opacity(0.2)
        }
    }
}

// MARK: - Icon Button

struct LiquidIconButton: View {
    let icon: String
    let size: CGFloat
    let action: () -> Void
    
    @State private var isPressed = false
    @State private var isHovering = false
    
    init(_ icon: String, size: CGFloat = 36, action: @escaping () -> Void) {
        self.icon = icon
        self.size = size
        self.action = action
    }
    
    var body: some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: size * 0.4, weight: .medium))
                .foregroundColor(.primary)
                .frame(width: size, height: size)
                .background(
                    Circle()
                        .fill(.ultraThinMaterial)
                        .overlay(
                            Circle()
                                .stroke(.white.opacity(0.2), lineWidth: 1)
                        )
                        .shadow(color: .black.opacity(0.1), radius: isHovering ? 8 : 4, y: isHovering ? 4 : 2)
                )
                .scaleEffect(isPressed ? 0.9 : (isHovering ? 1.1 : 1.0))
                .animation(.spring(response: 0.25, dampingFraction: 0.6), value: isPressed)
                .animation(.spring(response: 0.3, dampingFraction: 0.7), value: isHovering)
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            isHovering = hovering
        }
        .pressActions(
            onPress: { isPressed = true },
            onRelease: { isPressed = false }
        )
    }
}

// MARK: - Press Actions Modifier

struct PressActions: ViewModifier {
    var onPress: () -> Void
    var onRelease: () -> Void
    
    func body(content: Content) -> some View {
        content
            .simultaneousGesture(
                DragGesture(minimumDistance: 0)
                    .onChanged { _ in onPress() }
                    .onEnded { _ in onRelease() }
            )
    }
}

extension View {
    func pressActions(onPress: @escaping () -> Void, onRelease: @escaping () -> Void) -> some View {
        modifier(PressActions(onPress: onPress, onRelease: onRelease))
    }
}

// MARK: - Preview

#Preview {
    VStack(spacing: 16) {
        LiquidButton("Start Focus Session", icon: "play.fill", style: .primary) {}
        
        LiquidButton("End Session", icon: "stop.fill", style: .danger) {}
        
        LiquidButton("Skip Break", icon: "forward.fill", style: .success) {}
        
        LiquidButton("Settings", icon: "gear", style: .secondary) {}
        
        LiquidButton("Cancel", style: .ghost) {}
        
        HStack(spacing: 12) {
            LiquidIconButton("pause.fill") {}
            LiquidIconButton("play.fill") {}
            LiquidIconButton("forward.fill") {}
            LiquidIconButton("gear") {}
        }
    }
    .padding(40)
    .frame(width: 400, height: 500)
    .background(GlassBackground())
}

