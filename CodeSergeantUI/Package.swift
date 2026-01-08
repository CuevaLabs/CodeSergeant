// swift-tools-version: 5.9
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "CodeSergeantUI",
    platforms: [
        .macOS(.v14)  // macOS Sonoma for latest SwiftUI features
    ],
    products: [
        .executable(name: "CodeSergeantUI", targets: ["CodeSergeantUI"])
    ],
    dependencies: [],
    targets: [
        .executableTarget(
            name: "CodeSergeantUI",
            dependencies: [],
            path: ".",
            exclude: ["Package.swift"],
            sources: [
                "CodeSergeantApp.swift",
                "Views/DashboardView.swift",
                "Views/MenuBarView.swift",
                "Views/SettingsView.swift",
                "Views/Components/GlassCard.swift",
                "Views/Components/LiquidButton.swift",
                "Views/Components/TimerDisplay.swift",
                "Models/SessionModel.swift",
                "Models/ConfigModel.swift",
                "Services/PythonBridge.swift"
            ],
            resources: [
                .process("Resources")
            ]
        )
    ]
)

