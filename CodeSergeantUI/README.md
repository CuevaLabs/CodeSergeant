# Code Sergeant UI

A modern SwiftUI menu bar app with **liquid glass design** for macOS Sonoma/Sequoia.

## Features

- **Liquid Glass Design** - Frosted glass backgrounds, smooth animations, depth effects
- **Menu Bar App** - Lives in the menu bar, no dock icon
- **Full Dashboard** - Goal input, timer settings, session tracking
- **Settings Panel** - AI configuration, screen monitoring, privacy controls
- **Python Backend Bridge** - Communicates with Python services via HTTP

## Requirements

- macOS 14.0+ (Sonoma or later)
- Xcode 15.0+
- Swift 5.9+

## Building

### Option 1: Xcode

1. Open `CodeSergeantUI` folder in Xcode
2. Select "My Mac" as the target
3. Build and Run (⌘R)

### Option 2: Swift Package Manager

```bash
cd CodeSergeantUI
swift build
swift run CodeSergeantUI
```

## Architecture

```
CodeSergeantUI/
├── CodeSergeantApp.swift      # Main app entry point
├── Views/
│   ├── DashboardView.swift    # Main dashboard window
│   ├── MenuBarView.swift      # Menu bar dropdown
│   ├── SettingsView.swift     # Settings tabs
│   └── Components/
│       ├── GlassCard.swift    # Glass card modifier
│       ├── LiquidButton.swift # Animated buttons
│       └── TimerDisplay.swift # Timer components
├── Models/
│   ├── SessionModel.swift     # Session data models
│   └── ConfigModel.swift      # Configuration models
├── Services/
│   ├── PythonBridge.swift     # HTTP client for Python backend
│   └── GlassEffect.swift      # Animation effects
└── Resources/
    └── Assets.xcassets        # App icons
```

## Design System

### Glass Card
```swift
Text("Content")
    .padding()
    .glassCard()
```

### Liquid Button
```swift
LiquidButton("Start Session", icon: "play.fill", style: .primary) {
    // Action
}
```

### Timer Display
```swift
TimerDisplay(
    remainingSeconds: 1234,
    totalSeconds: 1500,
    isBreak: false
)
```

### Animations
```swift
content
    .shimmer()          // Shimmer effect
    .glow(color: .blue) // Glow effect
    .breathing()        // Breathing animation
    .depthEffect()      // 3D depth on hover
    .parallaxEffect()   // Parallax on mouse move
```

## Python Bridge

The SwiftUI app communicates with the Python backend via HTTP on port 5050.

Start the bridge server:
```bash
cd /path/to/CodeSergeant
source .venv/bin/activate
python bridge/server.py
```

API endpoints:
- `GET /api/status` - Session status
- `GET /api/ai/status` - AI backend status
- `POST /api/session/start` - Start session
- `POST /api/session/end` - End session
- `POST /api/openai-key` - Set OpenAI API key
- `GET /api/timer` - Timer state

## License

MIT

