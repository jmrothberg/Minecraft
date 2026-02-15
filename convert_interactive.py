#!/usr/bin/env python3
"""
Jonathan Rothberg's MineCraft to LEGO converter

Interactive console GUI for easy file selection and conversion.
Browse .schematic and .schem files, pick by number, and convert to LDraw (.ldr).
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
    """List all .schematic and .schem files in schematics/ directory"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    schem_dir = os.path.join(script_dir, "schematics")
    os.makedirs(schem_dir, exist_ok=True)
    schematic_files = glob.glob(os.path.join(schem_dir, "*.schematic"))
    schematic_files.extend(glob.glob(os.path.join(schem_dir, "*.SCHEMATIC")))
    schematic_files.extend(glob.glob(os.path.join(schem_dir, "*.schem")))
    schematic_files.extend(glob.glob(os.path.join(schem_dir, "*.SCHEM")))
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
    print("Options:")
    print("  Enter a number to convert (e.g. '2')")
    print()
    print("  Flags (add after number):")
    print("    -o   Optimize: merge adjacent same-color blocks into")
    print("         larger bricks (2x2, 2x4, etc). Fewer parts, faster render.")
    print("         Without -o: every block becomes a single 1x1 brick.")
    print("    -2x  2x scale: each Minecraft block = 2 LEGO studs.")
    print("         Stairs become real L-shaped steps, slabs are exact half-height.")
    print("         Without -2x: 1 stud per block (smaller but less detail).")
    print()
    print("  Examples: '2'  '2 -o'  '2 -2x'  '2 -o -2x'")
    print("  Type 'q' to quit, 'r' to refresh file list")
    print()

    return schematic_files

def get_user_choice(max_choice):
    """Get user input for file selection, returns (choice, optimize_flag, scale)"""
    while True:
        try:
            raw_input = input("Select file (1-{}): ".format(max_choice)).strip()
            choice = raw_input.lower()

            if choice in ['q', 'quit']:
                return 'quit', False, 1
            elif choice in ['r', 'refresh']:
                return 'refresh', False, 1

            # Check for flags
            optimize = '-o' in choice
            scale = 2 if '-2x' in choice else 1
            # Remove flags to get the number
            num_str = choice.replace('-2x', '').replace('-o', '').replace('-0', '').strip()

            if num_str.isdigit():
                num = int(num_str)
                if 1 <= num <= max_choice:
                    return num, optimize, scale
                else:
                    print(f"Please enter a number between 1 and {max_choice}")
            else:
                print("Please enter a number, 'q' to quit, or 'r' to refresh")
                print("   Add '-o' to optimize, '-2x' for 2x scale (e.g. '1 -o -2x')")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            sys.exit(0)
        except EOFError:
            print("\nGoodbye!")
            sys.exit(0)

def get_output_filename(input_filename):
    """Get output filename from user, saving to models/ directory"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(script_dir, "models")
    os.makedirs(models_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(input_filename))[0]
    default_output = os.path.join(models_dir, f"{base_name}.ldr")

    print(f"\n📝 Output filename for '{os.path.basename(input_filename)}':")
    print(f"   Default: models/{base_name}.ldr")

    while True:
        choice = input("Enter filename (or press Enter for default): ").strip()

        if not choice:
            return default_output
        elif choice.lower().endswith('.ldr'):
            return os.path.join(models_dir, choice)
        else:
            return os.path.join(models_dir, f"{choice}.ldr")

def show_conversion_progress(converter, schematic_file, output_file, optimize=False, scale=1):
    """Show conversion progress with animation"""
    print(f"\nConverting '{schematic_file}' to Lego...")
    if optimize:
        print("OPTIMIZATION ENABLED - will merge into larger bricks")
    if scale > 1:
        print(f"SCALE: {scale}x (each MC block = {scale} studs, better stairs/slabs)")
    print("=" * 50)

    # Load schematic
    print("Loading schematic file...")
    schematic = converter.load_schematic(schematic_file)

    if not schematic:
        print("Failed to load schematic file!")
        return False

    width, height, length = schematic['width'], schematic['height'], schematic['length']
    total_blocks = width * height * length

    print(f"Loaded {width}x{height}x{length} schematic ({total_blocks} blocks)")

    # Convert to LDraw
    print("Converting blocks to Lego bricks...")
    start_time = time.time()

    ldraw_content = converter.convert_to_ldraw(schematic, optimize=optimize, scale=scale)

    # Count bricks
    brick_lines = [line for line in ldraw_content.split('\n') if line.strip() and not line.startswith('0')]
    brick_count = len(brick_lines)

    conversion_time = time.time() - start_time

    # Save file
    print(f"Saving to '{output_file}'...")
    converter.save_ldraw_file(ldraw_content, output_file)

    print("Conversion complete!")
    print(f"   {brick_count} Lego bricks created")
    print(f"   Conversion time: {conversion_time:.2f}s")
    print(f"   Output: {output_file}")

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

        # Get user choice (returns tuple: choice, optimize_flag, scale)
        choice, optimize, scale = get_user_choice(len(schematic_files))

        if choice == 'quit':
            print("Goodbye!")
            return
        elif choice == 'refresh':
            continue  # Reload file list

        # Get selected file
        selected_file = schematic_files[choice - 1]

        # Get output filename
        output_file = get_output_filename(selected_file)

        # Check if output exists
        if os.path.exists(output_file):
            overwrite = input(f"'{output_file}' already exists. Overwrite? (y/N): ").strip().lower()
            if overwrite not in ['y', 'yes']:
                continue

        # Convert file
        converter = MinecraftToLegoConverter()
        success = show_conversion_progress(converter, selected_file, output_file, optimize, scale)

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
