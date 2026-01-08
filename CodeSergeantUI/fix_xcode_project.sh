#!/bin/bash
# Fix Xcode project file paths

echo "Cleaning Xcode cache..."
rm -rf ~/Library/Developer/Xcode/DerivedData/CodeSergeantUI-*
rm -rf ~/Library/Caches/com.apple.dt.Xcode/*

echo "✅ Xcode cache cleared"
echo ""
echo "Next steps:"
echo "1. Close Xcode completely"
echo "2. Reopen CodeSergeantUI.xcodeproj"
echo "3. If files still show errors, right-click the project → Add Files"
echo "   Select all Swift files and make sure 'Copy items if needed' is UNCHECKED"

