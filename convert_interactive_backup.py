#!/usr/bin/env python3
"""
Interactive Minecraft to Lego Converter
Console-driven GUI for easy file selection and conversion
"""

import os
import sys
import glob
import time
from datetime import datetime
from minecraft_to_lego_converter import MinecraftToLegoConverter

def clear_screen():
    """Clear the terminal screen"""
    print("\033[2J\033[H", end="")

def list_schematic_files():
    """List all .schematic and .schem files in current directory"""
    schematic_files = glob.glob("*.schematic")
    schematic_files.extend(glob.glob("*.SCHEMATIC"))  # Case insensitive
    schematic_files.extend(glob.glob("*.schem"))      # New Sponge/WorldEdit format
    schematic_files.extend(glob.glob("*.SCHEM"))
    return sorted(list(set(schematic_files)))  # Remove duplicates

def get_file_info(filepath):
    """Get file information for display"""
    try:
        stat = os.stat(filepath)
        size_kb = stat.st_size / 1024
        modified_time = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')

        return {
            'size_kb': size_kb,
            'modified': modified_time,
            'size_str': f"{size_kb:>8.1f} KB"
        }
    except:
        return {
            'size_kb': 0,
            'modified': 'Unknown',
            'size_str': '    ???? KB'
        }

def display_menu(schematic_files):
    """Display interactive menu for file selection"""
    print("🧱 Minecraft to Lego Converter")
    print("=" * 40)
    print()
    print("Select a Minecraft schematic file to convert:")
    print()

    if not schematic_files:
        print("❌ No schematic files found in current directory!")
        print()
        print("Supported formats: .schematic (old) and .schem (new)")
        print()
        print("Place your Minecraft schematic files here, or:")
        print("  • WorldEdit 1.13+: //schem save filename  (.schem)")
        print("  • WorldEdit older: //schematic save filename  (.schematic)")
        print("  • MCEdit/Amulet exports")
        print("  • Download from Minecraft community sites")
        print()
        print("Press Enter to refresh...")
        input()
        return None

    for i, filename in enumerate(schematic_files, 1):
        info = get_file_info(filename)

        # Special icons
        if 'house' in filename.lower():
            icon = "🏠"
        elif 'castle' in filename.lower():
            icon = "🏰"
        elif 'tower' in filename.lower():
            icon = "🗼"
        elif 'ship' in filename.lower():
            icon = "🚢"
        else:
            icon = "📦"

        print(f"  {i}. {icon} {filename} {info['size_str']}  ({info['modified']})")

    print()
    print("Controls:")
    print("  • Enter number to select file (e.g. '1')")
    print("  • Add '-o' to optimize/merge bricks (e.g. '1 -o')")
    print("  • 'r' or 'refresh' to reload file list")
    print("  • 'q' or 'quit' to exit")
    print()

    return schematic_files

def get_user_choice(max_choice):
    """Get user input for file selection, returns (choice, optimize_flag)"""
    while True:
        try:
            raw_input = input("Select file (1-{}): ".format(max_choice)).strip()
            choice = raw_input.lower()

            if choice in ['q', 'quit']:
                return 'quit', False
            elif choice in ['r', 'refresh']:
                return 'refresh', False

            # Check for -o optimize flag
            optimize = '-o' in choice
            # Remove the -o flag to get the number
            num_str = choice.replace('-o', '').replace('-0', '').strip()

            if num_str.isdigit():
                num = int(num_str)
                if 1 <= num <= max_choice:
                    return num, optimize
                else:
                    print(f"❌ Please enter a number between 1 and {max_choice}")
            else:
                print("❌ Please enter a number, 'q' to quit, or 'r' to refresh")
                print("   Add '-o' after number to optimize (e.g. '1 -o')")

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            sys.exit(0)
        except EOFError:
            print("\n👋 Goodbye!")
            sys.exit(0)

def get_output_filename(input_filename):
    """Get output filename from user"""
    base_name = os.path.splitext(input_filename)[0]

    print(f"\n📝 Output filename for '{input_filename}':")
    print(f"   Default: {base_name}.ldr")

    while True:
        choice = input("Enter filename (or press Enter for default): ").strip()

        if not choice:
            return f"{base_name}.ldr"
        elif choice.lower().endswith('.ldr'):
            return choice
        else:
            return f"{choice}.ldr"

def show_conversion_progress(converter, schematic_file, output_file, optimize=False):
    """Show conversion progress with animation"""
    print(f"\n🔄 Converting '{schematic_file}' to Lego...")
    if optimize:
        print("🔧 OPTIMIZATION ENABLED - will merge into larger bricks")
    print("=" * 50)

    # Load schematic
    print("📂 Loading schematic file...")
    schematic = converter.load_schematic(schematic_file)

    if not schematic:
        print("❌ Failed to load schematic file!")
        return False

    width, height, length = schematic['width'], schematic['height'], schematic['length']
    total_blocks = width * height * length

    print(f"✅ Loaded {width}x{height}x{length} schematic ({total_blocks} blocks)")

    # Convert to LDraw
    print("🔧 Converting blocks to Lego bricks...")
    start_time = time.time()

    ldraw_content = converter.convert_to_ldraw(schematic, optimize=optimize)

    # Count bricks
    brick_lines = [line for line in ldraw_content.split('\n') if line.strip() and not line.startswith('0')]
    brick_count = len(brick_lines)

    conversion_time = time.time() - start_time

    # Save file
    print(f"💾 Saving to '{output_file}'...")
    converter.save_ldraw_file(ldraw_content, output_file)

    print("✅ Conversion complete!")
    print(f"   📦 {brick_count} Lego bricks created")
    print(f"   ⏱️  Conversion time: {conversion_time:.2f}s")
    print(f"   📄 Output: {output_file}")

    return True

def open_in_leocad(output_file):
    """Try to open the converted file in LeoCAD"""
    print(f"\n🎮 Opening '{output_file}' in LeoCAD...")

    if not os.path.exists('./launch_leocad.sh'):
        print("⚠️  LeoCAD launcher not found. Install with: python install_ldraw_tools.py")
        print(f"   File saved as: {output_file}")
        return

    # Try to launch LeoCAD
    os.system(f"./launch_leocad.sh '{output_file}' &>/dev/null &")
    print("✅ LeoCAD launched! (may take a moment to appear)")

def show_next_steps(output_file):
    """Show what user can do next"""
    print(f"\n🎯 Next steps with '{output_file}':")
    print()
    print("1. 🖱️  Edit in LeoCAD (professional 3D editor)")
    print("2. 👁️  View with: python view_ldraw.py")
    print("3. 🌐 Web view: Open ldraw_web_viewer.html in browser")
    print("4. 📄 Convert another: Run this script again")
    print()
    print("💡 Pro tip: LeoCAD lets you modify, paint, and export your Lego models!")
def main():
    """Main interactive conversion loop"""

    while True:
        clear_screen()

        # List and display files
        schematic_files = list_schematic_files()
        result = display_menu(schematic_files)

        if result is None:
            continue  # No files found, user pressed enter to refresh

        # Get user choice (returns tuple: choice, optimize_flag)
        choice, optimize = get_user_choice(len(schematic_files))

        if choice == 'quit':
            print("👋 Goodbye!")
            return
        elif choice == 'refresh':
            continue  # Reload file list

        # Get selected file
        selected_file = schematic_files[choice - 1]

        # Get output filename
        output_file = get_output_filename(selected_file)

        # Check if output exists
        if os.path.exists(output_file):
            overwrite = input(f"⚠️  '{output_file}' already exists. Overwrite? (y/N): ").strip().lower()
            if overwrite not in ['y', 'yes']:
                continue

        # Convert file
        converter = MinecraftToLegoConverter()
        success = show_conversion_progress(converter, selected_file, output_file, optimize)

        if success:
            # Open in LeoCAD
            open_in_leocad(output_file)

            # Show next steps
            show_next_steps(output_file)

        # Wait for user
        print()
        input("Press Enter to continue...")
        clear_screen()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
