#!/bin/bash
# LeoCAD Launcher Script
# Makes it easy to run LeoCAD from anywhere

LEOCAD_PATH="/home/jonathan/Code_Runner/LeoCAD-Linux-25.09-x86_64.AppImage"

# Check if LeoCAD exists
if [ ! -f "$LEOCAD_PATH" ]; then
    echo "❌ LeoCAD not found at: $LEOCAD_PATH"
    echo "Run: python install_ldraw_tools.py → select leocad"
    exit 1
fi

# Check if executable
if [ ! -x "$LEOCAD_PATH" ]; then
    echo "🔧 Making LeoCAD executable..."
    chmod +x "$LEOCAD_PATH"
fi

# Try to launch LeoCAD with any arguments passed
echo "🚀 Launching LeoCAD..."

# Method 1: Try normal AppImage launch
if "$LEOCAD_PATH" "$@" 2>/dev/null; then
    # Success
    exit 0
fi

# Method 2: If FUSE fails, try extraction method
echo "⚠️  AppImage needs FUSE. Trying alternative method..."
echo "📦 Extracting AppImage contents..."

# Create temp directory for extraction
TEMP_DIR="/tmp/leocad_extracted"
mkdir -p "$TEMP_DIR"

# Extract AppImage (this works without FUSE)
cd "$TEMP_DIR"
"$LEOCAD_PATH" --appimage-extract >/dev/null 2>&1

if [ -d "squashfs-root" ]; then
    echo "✅ Extracted successfully!"
    echo "🚀 Launching LeoCAD from extracted files..."

    # Find the executable
    EXECUTABLE="$TEMP_DIR/squashfs-root/usr/bin/leocad"
    if [ -f "$EXECUTABLE" ]; then
        # Set library path and launch
        export LD_LIBRARY_PATH="$TEMP_DIR/squashfs-root/usr/lib:$LD_LIBRARY_PATH"
        "$EXECUTABLE" "$@" &
    else
        echo "❌ Could not find LeoCAD executable in extracted files"
        exit 1
    fi
else
    echo "❌ Failed to extract AppImage"
    echo ""
    echo "💡 Solutions:"
    echo "1. Ask system admin to install: sudo apt install libfuse2"
    echo "2. Try running as root (if you have permission)"
    echo "3. Use the web viewer: python -m http.server 8000 (then open ldraw_web_viewer.html)"
    echo "4. Use the Python viewer: python view_ldraw.py"
    exit 1
fi

# Optional: Show usage if no arguments
if [ $# -eq 0 ]; then
    echo "💡 Tip: Run 'launch_leocad.sh your_file.ldr' to open a specific file"
    echo "💡 Your converted files are in: /home/jonathan/Code_Runner/"
fi
