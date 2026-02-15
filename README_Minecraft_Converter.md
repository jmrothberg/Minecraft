# Minecraft to Lego Converter

A complete Python toolchain that converts Minecraft schematic files (`.schematic` and `.schem`) to Lego-compatible LDraw format (`.ldr`) with professional viewing tools.

## Quick Start Workflow

1. **Convert:** `python convert_interactive.py` (interactive file browser & converter)
2. **View:** `python view_ldraw.py` (interactive 3D viewer)
3. **Edit:** `./launch_leocad.sh` (opens in professional LeoCAD editor)

*Alternative: Direct conversion with `python minecraft_to_lego_converter.py your_file.schematic`*

## Interactive Converter

The easiest way to convert your Minecraft files:

```bash
python convert_interactive.py
```

**What it does:**
- **Lists all .schematic files** in your directory with file sizes and dates
- **Special icons** for different structure types (🏠 houses, 🏰 castles, etc.)
- **Lets you pick by number** - no typing filenames!
- **Custom output names** or auto-generated ones
- **Shows conversion progress** with brick counts and timing
- **Automatically opens** the result in LeoCAD
- **Next steps guide** for what to do with your converted file

**Perfect for:** Converting multiple files, exploring your Minecraft builds, quick conversions.

## Features

- **Interactive Console GUI** - Browse and convert files without typing commands
- **Supports both .schematic and .schem formats** - old and new Minecraft versions
- Converts Minecraft blocks to appropriate Lego bricks
- **Smart block handling:** stairs → slopes, slabs → plates, carpets → thin plates
- Handles 200+ block types with accurate colors
- Generates LDraw files compatible with all Lego software
- Command-line interface for batch processing
- **Auto-opens** converted files in LeoCAD
- Progress display during conversion
- 3D coordinate conversion with proper scaling

## Installation

The required dependencies are already added to your `requirements.txt`:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Command Line

```bash
# Basic usage
python minecraft_to_lego_converter.py your_schematic.schematic

# Specify output file
python minecraft_to_lego_converter.py input.schematic -o output.ldr

# Verbose output
python minecraft_to_lego_converter.py input.schematic -v
```

### Python API

```python
from minecraft_to_lego_converter import MinecraftToLegoConverter

converter = MinecraftToLegoConverter()
success = converter.convert_file("my_house.schematic", "my_house.ldr")
```

## Supported Minecraft Blocks

The converter currently maps these Minecraft blocks to Lego bricks:

| Minecraft Block | ID | Lego Brick |
|-----------------|----|------------|
| Stone | 1 | 1x1 Brick (3024) |
| Grass | 2 | 2x2 Plate (3023) |
| Dirt | 3 | 2x2 Plate (3023) |
| Cobblestone | 4 | 2x6 Brick (2456) |
| Wood Planks | 5 | 2x2 Brick (3003) |
| Sand | 12 | 2x2 Plate (3023) |
| Gravel | 13 | 2x2 Plate (3023) |
| Wood | 17 | 1x2 Brick (3001) |
| Leaves | 18 | 1x2 Brick (3001) |
| Wool (all colors) | 35 | 2x2 Brick (3003) + color |
| Gold Block | 41 | 1x1 Brick (3024) |
| Iron Block | 42 | 2x2 Brick (3003) |
| Bricks | 45 | 1x6 Brick (3009) |
| TNT | 46 | 2x4 Plate (3020) |
| Bookshelf | 47 | 1x8 Brick (3008) |
| Obsidian | 49 | 1x1 Brick (3024) |
| Ice | 79 | 2x2 Plate (3023) |
| Snow | 80 | 2x2 Plate (3023) |

## Getting Minecraft Schematic Files

You can obtain `.schematic` files from:

1. **WorldEdit Plugin**: Use `//copy` and `//schematic save filename` in Minecraft
2. **MCEdit**: Export selections as schematic files
3. **Schematic Files Online**: Download from Minecraft community sites
4. **Your own creations**: Build in creative mode and export

## Viewing LDraw Files

The generated `.ldr` files can be viewed in several ways:

### Quick Python Viewer (Included)

View your models with an interactive file selector:

```bash
# Launch interactive viewer
python view_ldraw.py
```

The viewer will:
- List all available `.ldr` files
- Show file sizes and brick counts
- Let you select files by number
- Display 3D models with interactive controls

**Viewer Controls:**
- **Mouse:** Rotate, zoom, and pan the 3D model
- **Menu:** Select files by number, 'q' to quit, 'r' to refresh

Features:
- 3D visualization with matplotlib
- Interactive rotation, zoom, and pan
- Color-coded bricks
- Shows model statistics
- Easy file selection

### Web-Based Viewer (Included)

For a more interactive experience, open `ldraw_web_viewer.html` in your browser:

```bash
# Open in default browser (Linux)
xdg-open ldraw_web_viewer.html

# Or just double-click the file
```

Features:
- Browser-based 3D viewer using Three.js
- Smooth controls and animations
- Wireframe mode toggle
- No installation required
- Works on any device with a browser

### Native Linux LDraw Tools (Recommended)

Install professional LDraw software with the included installer:

```bash
python install_ldraw_tools.py
```

**Available Tools:**
- **LeoCAD** - Modern editor with real-time 3D rendering
- **LDView** - Fast viewer with advanced features and ray tracing

Both tools are native Linux applications that work perfectly with your generated `.ldr` files.

**Running LeoCAD:**
```bash
# Quick launch
./launch_leocad.sh

# Open specific file
./launch_leocad.sh test_house.ldr

# Direct AppImage (if FUSE works)
./LeoCAD-Linux-25.09-x86_64.AppImage
```

*Note: If you see FUSE errors, the launcher script will automatically try alternative methods.*

### Other LDraw Viewers

- **Lego Digital Designer** (official Lego software - Windows/Mac only)
- **LDraw Editors** like MLCad or LDCad
- **3D Printing Software** for physical Lego model creation
- **Online LDraw Viewers**

## Coordinate System

- **Minecraft**: X=east, Y=up, Z=south
- **LDraw**: X=right, Y=up, Z=out (towards viewer)
- Bricks are scaled by 20x for visibility and proper stud alignment

## Extending the Converter

### Adding New Block Mappings

Edit the `block_mappings` dictionary in `MinecraftToLegoConverter.__init__()`:

```python
self.block_mappings[block_id] = "lego_brick_number"
```

### Adding New Colors

Edit the `color_mappings` dictionary for wool and other colored blocks:

```python
self.color_mappings[data_value] = lego_color_id
```

### Custom Brick Types

For more accurate Lego representations, you can:
- Use different brick sizes based on block properties
- Add special bricks for functional blocks (doors, torches, etc.)
- Implement brick merging for larger structures

## Test the Converter

Run the included test:

```bash
python test_converter.py
```

This creates a simple house structure and converts it to `test_house.ldr`.

## Troubleshooting

### "nbtlib not found"
Make sure you're using the virtual environment:
```bash
source .venv/bin/activate
pip install nbtlib numpy
```

### "File not found"
- Check the file path is correct
- Ensure the schematic file has `.schematic` extension
- Verify the file isn't corrupted

### "Empty LDraw file"
- Check if your schematic contains blocks (not just air)
- Some block IDs might not be mapped yet

## Future Enhancements

- [ ] Support for more Minecraft blocks
- [ ] Better color mapping for all block types
- [ ] Brick optimization (merging adjacent bricks)
- [ ] Support for redstone components
- [ ] Door and window mechanisms
- [ ] Web interface for easy conversion
- [ ] Support for .nbt files (newer Minecraft format)

## License

Created for educational and personal use with Minecraft and Lego.
