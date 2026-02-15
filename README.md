# Jonathan Rothberg's MineCraft to LEGO Converter

Converts Minecraft schematic files (`.schematic` and `.schem`) to LEGO-compatible LDraw format (`.ldr`) for viewing, editing, and building with real LEGO bricks.

## Project Structure

```
Minecraft/
├── minecraft_to_lego_converter.py   # Core converter engine (CLI + Python API)
├── convert_interactive.py           # Interactive console GUI for easy conversion
├── launch_leocad.sh                 # LeoCAD launcher script
├── requirements.txt                 # Python dependencies
├── schematics/                      # Input: Minecraft schematic files
│   ├── 235.schematic                #   Old format (.schematic, pre-1.13)
│   └── kismet.schem                 #   New format (.schem, 1.13+)
└── models/                          # Output: Converted LEGO LDraw files
    ├── 235.ldr                      #   Basic conversion
    ├── 235Color.ldr                 #   Color-mapped conversion
    ├── 235expandedcolor.ldr         #   Expanded color palette
    ├── 235optimized.ldr             #   Brick-optimized (merged bricks)
    ├── 235proportion.ldr            #   Proportion-adjusted
    ├── kismet.ldr                   #   Kismet build conversions
    └── ...                          #   (various conversion iterations)
```

## How It Works

The conversion pipeline has three stages:

1. **Parse** — Reads Minecraft NBT data from `.schematic` (pre-1.13) or `.schem` (Sponge/WorldEdit 1.13+) files using `nbtlib`. Extracts the 3D block grid, block IDs, and block state properties.

2. **Convert** — Maps each Minecraft block to a LEGO brick:
   - Every block becomes a 1x1 LEGO brick (`3005.dat`) for accurate 1:1 conversion
   - 200+ block types mapped to correct LDraw colors (stone, wood, wool, concrete, terracotta, glass, ores, etc.)
   - Stairs become cheese slope bricks (`54200.dat`) with correct rotation, including inverted/ceiling stairs
   - Slabs and carpets become plates (`3024.dat`) positioned at top or bottom; double slabs become full bricks
   - **Optimization mode** (`-o`) merges adjacent same-color blocks into larger bricks (1x2 through 2x8) for fewer parts
   - **2x scale mode** (`-2x`) for more accurate Minecraft geometry — see below

3. **Output** — Writes standard LDraw `.ldr` files compatible with LeoCAD, LDView, LDCad, and other LEGO CAD software.

## Quick Start

### Interactive Mode (recommended)

```bash
python convert_interactive.py
```

This launches a console GUI that:
- Lists all `.schematic` and `.schem` files in `schematics/`
- Lets you pick a file by number
- Lets you name the output (saved to `models/`)
- Shows conversion progress with brick counts
- Optionally opens the result in LeoCAD

**Flags** (add after the file number):
- `-o` — Optimize: merge adjacent same-color 1x1 bricks into larger ones (fewer parts)
- `-2x` — 2x scale: more accurate Minecraft geometry (see [2x Scale Mode](#2x-scale-mode--more-accurate-minecraft-geometry))
- Combine: `2 -o -2x`

### Command Line

```bash
# Basic conversion
python minecraft_to_lego_converter.py schematics/your_file.schematic

# Specify output file
python minecraft_to_lego_converter.py schematics/input.schematic -o models/output.ldr

# 2x scale for accurate stairs and slabs
python minecraft_to_lego_converter.py schematics/input.schem --scale 2

# 2x scale + verbose
python minecraft_to_lego_converter.py schematics/input.schem --scale 2 -v
```

### Python API

```python
from minecraft_to_lego_converter import MinecraftToLegoConverter

converter = MinecraftToLegoConverter()

# Standard conversion (1:1 blocks)
converter.convert_file("schematics/my_build.schematic", "models/my_build.ldr")

# Optimized conversion (merged bricks, fewer parts)
converter.convert_file("schematics/my_build.schem", "models/my_build.ldr", optimize=True)

# 2x scale (accurate stairs/slabs, can combine with optimize=True)
converter.convert_file("schematics/my_build.schem", "models/my_build.ldr", scale=2, optimize=True)
```

## 2x Scale Mode — More Accurate Minecraft Geometry

The default 1:1 conversion maps each Minecraft block to a single 1x1 LEGO brick. This works well for full cubes (stone, wood, wool), but Minecraft has sub-block shapes — stairs, slabs, carpet — that don't have a perfect LEGO equivalent at 1-stud scale.

**2x scale** solves this by making each Minecraft block **2 studs wide × 2 bricks tall** (40×48×40 LDU). This gives enough room to accurately represent non-cube geometry:

| Block Type | 1x scale (default) | 2x scale (`-2x`) |
|------------|--------------------|--------------------|
| **Stairs** | Cheese slope — angled approximation, no step shape | **L-shaped step**: full 2×2 brick on bottom + 1×2 brick on the tall side. Actual step geometry matching Minecraft |
| **Inverted stairs** | Not supported (rendered same as normal stairs) | **Correctly flipped**: full brick on top layer, step on bottom, matching Minecraft ceiling stairs |
| **Slabs** | Plate (8 LDU = 1/3 brick height) — wrong ratio, slabs should be 1/2 | **Single 2×2 brick = exactly half** the 2-brick block height. Perfect 1/2 ratio |
| **Carpet** | Plate (oversized relative to block) | **2×2 plate** at correct floor level within the block space |
| **Full blocks** | 1×1 brick | Two stacked 2×2 bricks (fills the full 2-brick height) |

**When to use 2x:** Any build with stairs, slabs, or carpet — especially detailed architecture like Kismet where stairs define the shape. The resulting model is larger (2× in each dimension) but geometrically faithful to the Minecraft original.

**When 1x is fine:** Pixel-art walls, flat structures, or builds made entirely of full cubes.

### How it works at 2x scale

A Minecraft stair block (e.g. `oak_stairs[facing=north,half=bottom]`) becomes two LEGO bricks arranged in an L-shape:

```
     ┌─────┐
     │3004 │  ← 1×2 brick (rotated), only on the tall side
     │     │
┌────┴─────┤
│  3003    │  ← 2×2 brick, full footprint
│          │
└──────────┘
```

The `facing` direction determines which side gets the upper brick, and `half=top` (inverted/ceiling stairs) flips the layers. This matches how Minecraft stairs actually look — an L-shaped step, not a slope.

## Setting Up on a New System

### 1. Clone the repository

```bash
git clone https://github.com/jmrothberg/Minecraft.git
cd Minecraft
```

### 2. Create a Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- **nbtlib** — Parses Minecraft NBT files (the binary format used by `.schematic` and `.schem`)
- **numpy** — Array operations for the 3D block grid
- **matplotlib** — (optional) Python-based 3D model viewer

### 4. (Optional) Install LeoCAD for 3D viewing

Download the LeoCAD AppImage from [leocad.org](https://www.leocad.org/download.html) and place it in the project root:

```bash
# Download LeoCAD (Linux AppImage)
wget https://github.com/leocad/leocad/releases/download/v25.09/LeoCAD-Linux-25.09-x86_64.AppImage
chmod +x LeoCAD-Linux-25.09-x86_64.AppImage

# If AppImage fails, install FUSE:
sudo apt install libfuse2
```

Then use the launcher:
```bash
./launch_leocad.sh models/your_file.ldr
```

### 5. Add your Minecraft schematics

Place `.schematic` or `.schem` files in the `schematics/` directory. You can get these from:
- **WorldEdit**: `//copy` then `//schem save filename`
- **MCEdit / Amulet**: Export selections
- **Minecraft community sites**: Download shared builds

## Viewing LDraw Files

| Viewer | Platform | Notes |
|--------|----------|-------|
| **LeoCAD** | Linux/Mac/Windows | Full 3D editor, included launcher script |
| **LDView** | Linux/Mac/Windows | Fast viewer with ray tracing |
| **LDCad** | Linux/Windows | Advanced LEGO CAD editor |
| **Bricklink Studio** | Mac/Windows | Official LEGO building instructions |

## Supported Blocks

The converter handles 200+ Minecraft block types including:
- All wood types (oak, spruce, birch, jungle, acacia, dark oak, mangrove, cherry, bamboo, crimson, warped)
- All wool, carpet, concrete, and terracotta colors (16 each)
- All stained glass and glass pane colors (transparent)
- Stairs (directional rotation + inverted/ceiling stairs) and slabs (top/bottom/double)
- Ores, minerals, and metal blocks
- Nether blocks, End blocks, deepslate variants
- Stone types (granite, diorite, andesite + polished variants)

## License

Created by Jonathan Rothberg for educational and personal use with Minecraft and LEGO.
