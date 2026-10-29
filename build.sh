#!/bin/bash
# ==============================================================================
# Apple Stock Monitor — Native macOS Build Script
# Compiles the Swift AppKit native GUI and bundles check_stock.py into a
# 100% self-contained macOS application bundle.
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

APP_NAME="Apple Stock Monitor.app"
BUILD_DIR="$DIR/build"
APP_PATH="$BUILD_DIR/$APP_NAME"
ICON_SOURCE="/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/com.apple.iphone.icns"

echo "🔨 Compiling native Swift AppKit binary..."
mkdir -p "$BUILD_DIR"
swiftc -O -o "$BUILD_DIR/AppleStockMonitorBin" "$DIR/native_app.swift"

echo "📦 Assembling macOS App Bundle ($APP_NAME)..."
rm -rf "$APP_PATH"
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

# Move compiled binary
mv "$BUILD_DIR/AppleStockMonitorBin" "$APP_PATH/Contents/MacOS/Apple Stock Monitor"
chmod +x "$APP_PATH/Contents/MacOS/Apple Stock Monitor"

# Bundle python checker script directly inside Resources so the app is 100% portable
cp "$DIR/check_stock.py" "$APP_PATH/Contents/Resources/check_stock.py"
chmod +x "$APP_PATH/Contents/Resources/check_stock.py"

# Create Info.plist
cat << 'EOF' > "$APP_PATH/Contents/Info.plist"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>Apple Stock Monitor</string>
    <key>CFBundleIconFile</key>
    <string>applet.icns</string>
    <key>CFBundleIdentifier</key>
    <string>com.apple.stock.monitor</string>
    <key>CFBundleName</key>
    <string>Apple Stock Monitor</string>
    <key>CFBundleDisplayName</key>
    <string>Apple Stock Monitor</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>2.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# Copy native macOS iPhone icon if present
if [ -f "$ICON_SOURCE" ]; then
    echo "🎨 Applying icon..."
    cp "$ICON_SOURCE" "$APP_PATH/Contents/Resources/applet.icns"
fi

# Local ad-hoc code-sign
echo "🔏 Code-signing bundle..."
codesign --force --deep --sign - "$APP_PATH" 2>/dev/null || true

# Copy to Desktop if user directory is present
if [ -d "$HOME/Desktop" ]; then
    echo "📱 Copying to ~/Desktop..."
    rm -rf "$HOME/Desktop/$APP_NAME"
    cp -R "$APP_PATH" "$HOME/Desktop/$APP_NAME"
fi

echo "✅ Success! Application built at: $APP_PATH"
