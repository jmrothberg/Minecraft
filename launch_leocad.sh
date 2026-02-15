#!/bin/bash
# Jonathan Rothberg's MineCraft to LEGO converter
# LeoCAD Launcher Script - opens .ldr files in LeoCAD for 3D viewing/editing

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LEOCAD_PATH="$SCRIPT_DIR/LeoCAD-Linux-25.09-x86_64.AppImage"

# Check if LeoCAD exists
if [ ! -f "$LEOCAD_PATH" ]; then
    echo "LeoCAD not found at: $LEOCAD_PATH"
    echo "Download from: https://www.leocad.org/download.html"
    exit 1
fi

# Check if executable
if [ ! -x "$LEOCAD_PATH" ]; then
    echo "Making LeoCAD executable..."
    chmod +x "$LEOCAD_PATH"
fi

# Try to launch LeoCAD with any arguments passed
echo "Launching LeoCAD..."

# Method 1: Try normal AppImage launch
if "$LEOCAD_PATH" "$@" 2>/dev/null; then
    exit 0
fi

# Method 2: If FUSE fails, try extraction method
echo "AppImage needs FUSE. Trying alternative method..."
echo "Extracting AppImage contents..."

TEMP_DIR="/tmp/leocad_extracted"
mkdir -p "$TEMP_DIR"

cd "$TEMP_DIR"
"$LEOCAD_PATH" --appimage-extract >/dev/null 2>&1

if [ -d "squashfs-root" ]; then
    echo "Extracted successfully!"
    EXECUTABLE="$TEMP_DIR/squashfs-root/usr/bin/leocad"
    if [ -f "$EXECUTABLE" ]; then
        export LD_LIBRARY_PATH="$TEMP_DIR/squashfs-root/usr/lib:$LD_LIBRARY_PATH"
        "$EXECUTABLE" "$@" &
    else
        echo "Could not find LeoCAD executable in extracted files"
        exit 1
    fi
else
    echo "Failed to extract AppImage"
    echo ""
    echo "Solutions:"
    echo "1. Install FUSE: sudo apt install libfuse2"
    echo "2. Use the Python viewer: python view_ldraw.py"
    exit 1
fi

if [ $# -eq 0 ]; then
    echo "Tip: Run './launch_leocad.sh models/your_file.ldr' to open a specific file"
fi
