# Jonathan Rothberg's MineCraft to LEGO Converter

Converts Minecraft schematic files (`.schematic` and `.schem`) into LEGO bricks you can assemble (`.ldr`) and an STL you can print.

## Project Structure

```
Minecraft/
├── minecraft_to_lego_converter.py   # Core converter engine (CLI + Python API)
├── convert_interactive.py           # Window for picking a file and converting it
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

2. **Convert** — Maps each Minecraft block to a real LEGO part on the stud grid:
   - 200+ block types mapped to LDraw colors (stone, wood, wool, concrete, terracotta, glass, ores, etc.)
   - **2× scale** (the default in the window) makes each block 2 studs wide and 2 bricks tall, which is enough room for steps and slopes
   - Straight stairs with nothing stacked on them become a slope brick (`3040`) on the high half, sitting on a full brick. The low half stays a flat step
   - A stair with a block on top stays a flat step (`3004`) so that block has studs to sit on
   - Inner corners fill three of the four studs; outer corners keep one stud
   - Upside-down stairs flip that: the step is on the bottom and a full brick is on top
   - An overhang is joined into one longer brick with the neighbor that holds it up. Bricks do not clutch sideways, so a lip has to be part of the same piece as the wall
   - Slabs are half a block. At 2× that is one brick in the lower or upper half. Carpet is a plate
   - **Merge** combines neighboring blocks of the same color into longer bricks (fewer pieces)

3. **Output** — An LDraw `.ldr` file for LeoCAD, and a binary STL in millimeters (8 mm per stud, 9.6 mm per brick) with a base plate and studs on the exposed tops. Open the STL in MeshLab, then send it to your slicer.

## Quick Start

### Window (this is the one to use)

```bash
.venv/bin/python convert_interactive.py
```

The window lists the schematics in `schematics/`, and you can also choose a file from anywhere. 2× scale, merged bricks, a LEGO file, and an STL are on by default. Convert writes into `models/`, then **Open LEGO file**, **Open STL**, and **Show in Finder** are enabled.

Pieces that stick out farther than a real brick can reach are listed in the progress box. They are still in the model, as separate pieces.

### Command line

```bash
# 2× scale is the default: steps, slopes, and overhangs, plus an STL
.venv/bin/python minecraft_to_lego_converter.py schematics/kismet.schem -o models/kismet.ldr --stl models/kismet.stl

# Also merge same-color neighbors into longer bricks
.venv/bin/python minecraft_to_lego_converter.py schematics/kismet.schem --optimize --stl models/kismet.stl

# One stud per block (stairs are full bricks, so they still connect)
.venv/bin/python minecraft_to_lego_converter.py schematics/235.schematic --scale 1 -o models/235.ldr
```

### Python API

```python
from minecraft_to_lego_converter import MinecraftToLegoConverter

converter = MinecraftToLegoConverter()

# Standard conversion (1:1 blocks)
converter.convert_file("schematics/my_build.schematic", "models/my_build.ldr")

# Optimized conversion (merged bricks, fewer parts)
converter.convert_file("schematics/my_build.schem", "models/my_build.ldr", optimize=True)

# 2x scale, merged bricks, and a printable STL
converter.convert_file(
    "schematics/my_build.schem", "models/my_build.ldr",
    scale=2, optimize=True, stl_path="models/my_build.stl")
```

## Stairs, slopes, and overhangs

2× scale is what you want for a build you will assemble or print. Each Minecraft block is 2 studs by 2 studs, and two bricks tall.

A right-side-up straight stair is a full 2×2 brick on the bottom. The high half is a slope (`3040`) when nothing sits on it, so the face actually slopes down to the step. If a block sits on the stair, that half is a flat 1×2 brick instead, because a slope has no studs. Inner corners keep three studs. Outer corners keep one. Upside-down stairs put the step on the bottom and the full brick on top.

An overhang only works in LEGO when it is the same piece as a brick that has studs under it. The converter does that join, up to a 2×8 brick. Anything past that is called out in the window. It is still in the file.

The STL uses real millimeters: 8 mm per stud, 9.6 mm per brick, a 3.2 mm base under the lowest blocks, and studs only on exposed tops. Slopes overlap the brick under them by 0.2 mm so a slicer treats them as one solid. A 45° LEGO slope is a bit steeper than 45° in real millimeters, so the slicer may add a little support under those faces.

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

**macOS:** install [LeoCAD 26.09](https://github.com/leozide/leocad/releases/download/v26.09/LeoCAD-macOS-26.09.dmg) (Universal, includes Apple Silicon and the LDraw parts library). Open the DMG and drag `LeoCAD.app` into `/Applications`. The launcher looks there:

```bash
./launch_leocad.sh models/your_file.ldr
```

The first launch may need approval in System Settings → Privacy & Security if macOS blocks an app from the internet.

**Linux:** download the LeoCAD AppImage from [leocad.org](https://www.leocad.org/download.html) and place it in the project root:

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

## Viewing the files

| File | Viewer | Notes |
|------|--------|-------|
| `.ldr` | LeoCAD | Edit the bricks. Launcher: `./launch_leocad.sh` |
| `.ldr` | LDView, BrickLink Studio | Other LEGO viewers |
| `.stl` | MeshLab | Open the mesh before you slice it. `brew install --cask meshlab` |
| `.stl` | Your slicer | PrusaSlicer, Bambu Studio, or Cura. The model is already in millimeters |

## Supported Blocks

The converter handles 200+ Minecraft block types including:
- All wood types (oak, spruce, birch, jungle, acacia, dark oak, mangrove, cherry, bamboo, crimson, warped)
- All wool, carpet, concrete, and terracotta colors (16 each)
- All stained glass and glass pane colors (transparent)
- Stairs (facing, upside-down, inner and outer corners) and slabs (top/bottom/double)
- Ores, minerals, and metal blocks
- Nether blocks, End blocks, deepslate variants
- Stone types (granite, diorite, andesite + polished variants)

## License

Created by Jonathan Rothberg for educational and personal use with Minecraft and LEGO.
