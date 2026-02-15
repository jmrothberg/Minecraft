#!/usr/bin/env python3
"""
Minecraft to Lego Converter
Converts Minecraft schematic files to LDraw format for Lego Digital Designer

Author: CodeRunner IDE
Created: 2026-01-04
"""

import os
import sys
import argparse
import numpy as np
from typing import Dict, List, Tuple, Optional
import nbtlib  # For parsing Minecraft NBT files

class MinecraftToLegoConverter:
    """
    Converts Minecraft schematic files to Lego-compatible LDraw format
    """

    def __init__(self):
        # All Minecraft blocks map to 1x1 Lego brick (3005) for accurate conversion
        # Default brick for all blocks - 3005 is the standard 1x1 brick
        self.default_brick = "3005"

        # Real Lego brick part numbers for optimization (width x length)
        # These are actual Lego brick sizes that exist
        self.brick_sizes = {
            # 1-wide bricks (sorted largest first for greedy algorithm)
            (1, 8): "3008",   # 1x8 brick
            (1, 6): "3009",   # 1x6 brick
            (1, 4): "3010",   # 1x4 brick
            (1, 3): "3622",   # 1x3 brick
            (1, 2): "3004",   # 1x2 brick
            (1, 1): "3005",   # 1x1 brick
            # 2-wide bricks
            (2, 8): "3007",   # 2x8 brick
            (2, 6): "2456",   # 2x6 brick
            (2, 4): "3001",   # 2x4 brick
            (2, 3): "3002",   # 2x3 brick
            (2, 2): "3003",   # 2x2 brick
        }

        # Wool data value to LDraw color mapping
        self.wool_color_mappings = {
            0: 15,   # White wool -> White
            1: 25,   # Orange wool -> Orange
            2: 13,   # Magenta wool -> Pink
            3: 9,    # Light Blue wool -> Light Blue
            4: 14,   # Yellow wool -> Yellow
            5: 27,   # Lime wool -> Lime
            6: 13,   # Pink wool -> Pink
            7: 8,    # Gray wool -> Dark Gray
            8: 7,    # Light Gray wool -> Light Gray
            9: 11,   # Cyan wool -> Light Cyan
            10: 5,   # Purple wool -> Magenta
            11: 1,   # Blue wool -> Blue
            12: 6,   # Brown wool -> Brown
            13: 2,   # Green wool -> Green
            14: 4,   # Red wool -> Red
            15: 0,   # Black wool -> Black
        }

        # Block ID to LDraw color mapping (default colors for blocks)
        # LDraw colors: 0=Black, 1=Blue, 2=Green, 4=Red, 5=Magenta, 6=Brown, 7=LtGray
        # 8=DkGray, 9=LtBlue, 10=BrightGreen, 11=LtCyan, 13=Pink, 14=Yellow, 15=White
        # 19=Tan, 25=Orange, 27=Lime, 28=DkTan, 33=TransDkBlue, 36=TransRed, 41=TransLtCyan
        # 42=TransLtBlue, 46=TransYellow, 47=TransClear, 70=ReddishBrown, 71=LtBluishGray
        # 72=DkBluishGray, 73=MedBlue, 85=DkPurple, 191=BrightLtOrange, 288=DkGreen
        # 320=DkRed, 326=BrightLtYellow, 378=SandGreen, 379=SandPurple, 484=DkOrange
        self.block_colors = {
            # Basic terrain
            1: 71,    # Stone -> Light Bluish Gray
            2: 10,    # Grass -> Bright Green
            3: 6,     # Dirt -> Brown
            4: 72,    # Cobblestone -> Dark Bluish Gray
            5: 70,    # Wooden Plank -> Reddish Brown
            6: 10,    # Sapling -> Bright Green
            7: 0,     # Bedrock -> Black
            8: 73,    # Water -> Medium Blue
            9: 73,    # Stationary Water -> Medium Blue
            10: 25,   # Lava -> Orange
            11: 25,   # Stationary Lava -> Orange
            12: 19,   # Sand -> Tan
            13: 71,   # Gravel -> Light Bluish Gray
            14: 14,   # Gold Ore -> Yellow
            15: 71,   # Iron Ore -> Light Bluish Gray
            16: 0,    # Coal Ore -> Black
            17: 70,   # Oak Log -> Reddish Brown
            18: 2,    # Oak Leaves -> Green
            19: 14,   # Sponge -> Yellow
            20: 47,   # Glass -> Trans Clear
            21: 1,    # Lapis Ore -> Blue
            22: 1,    # Lapis Block -> Blue
            23: 72,   # Dispenser -> Dark Bluish Gray
            24: 19,   # Sandstone -> Tan
            25: 70,   # Note Block -> Reddish Brown
            26: 4,    # Bed -> Red
            27: 14,   # Powered Rail -> Yellow
            28: 70,   # Detector Rail -> Reddish Brown
            29: 27,   # Sticky Piston -> Lime
            30: 15,   # Cobweb -> White
            31: 2,    # Tall Grass -> Green
            32: 6,    # Dead Bush -> Brown
            33: 70,   # Piston -> Reddish Brown
            34: 19,   # Piston Head -> Tan
            35: 15,   # Wool -> White (data value changes it)
            37: 14,   # Dandelion -> Yellow
            38: 4,    # Poppy -> Red
            39: 6,    # Brown Mushroom -> Brown
            40: 4,    # Red Mushroom -> Red
            41: 14,   # Gold Block -> Yellow
            42: 71,   # Iron Block -> Light Bluish Gray
            43: 71,   # Double Stone Slab -> Light Bluish Gray
            44: 71,   # Stone Slab -> Light Bluish Gray
            45: 320,  # Bricks -> Dark Red
            46: 4,    # TNT -> Red
            47: 70,   # Bookshelf -> Reddish Brown
            48: 378,  # Mossy Cobblestone -> Sand Green
            49: 0,    # Obsidian -> Black
            50: 25,   # Torch -> Orange
            51: 25,   # Fire -> Orange
            52: 9,    # Monster Spawner -> Light Blue
            53: 70,   # Oak Stairs -> Reddish Brown
            54: 70,   # Chest -> Reddish Brown
            55: 4,    # Redstone Wire -> Red
            56: 41,   # Diamond Ore -> Trans Light Cyan
            57: 41,   # Diamond Block -> Trans Light Cyan
            58: 70,   # Crafting Table -> Reddish Brown
            59: 326,  # Wheat -> Bright Light Yellow
            60: 6,    # Farmland -> Brown
            61: 72,   # Furnace -> Dark Bluish Gray
            62: 72,   # Lit Furnace -> Dark Bluish Gray
            63: 70,   # Sign -> Reddish Brown
            64: 70,   # Oak Door -> Reddish Brown
            65: 70,   # Ladder -> Reddish Brown
            66: 72,   # Rail -> Dark Bluish Gray
            67: 72,   # Cobblestone Stairs -> Dark Bluish Gray
            68: 70,   # Wall Sign -> Reddish Brown
            69: 72,   # Lever -> Dark Bluish Gray
            70: 71,   # Stone Pressure Plate -> Light Bluish Gray
            71: 71,   # Iron Door -> Light Bluish Gray
            72: 70,   # Wood Pressure Plate -> Reddish Brown
            73: 4,    # Redstone Ore -> Red
            74: 4,    # Lit Redstone Ore -> Red
            75: 4,    # Redstone Torch Off -> Red
            76: 4,    # Redstone Torch On -> Red
            77: 71,   # Stone Button -> Light Bluish Gray
            78: 15,   # Snow Layer -> White
            79: 41,   # Ice -> Trans Light Cyan
            80: 15,   # Snow Block -> White
            81: 288,  # Cactus -> Dark Green
            82: 71,   # Clay -> Light Bluish Gray
            83: 27,   # Sugar Cane -> Lime
            84: 70,   # Jukebox -> Reddish Brown
            85: 70,   # Fence -> Reddish Brown
            86: 25,   # Pumpkin -> Orange
            87: 320,  # Netherrack -> Dark Red
            88: 6,    # Soul Sand -> Brown
            89: 326,  # Glowstone -> Bright Light Yellow
            90: 85,   # Nether Portal -> Dark Purple
            91: 25,   # Jack o'Lantern -> Orange
            92: 15,   # Cake -> White
            93: 71,   # Redstone Repeater Off -> Light Bluish Gray
            94: 71,   # Redstone Repeater On -> Light Bluish Gray
            95: 47,   # Stained Glass -> Trans Clear (data value)
            96: 70,   # Trapdoor -> Reddish Brown
            97: 71,   # Monster Egg -> Light Bluish Gray
            98: 71,   # Stone Bricks -> Light Bluish Gray
            99: 6,    # Brown Mushroom Block -> Brown
            100: 4,   # Red Mushroom Block -> Red
            101: 72,  # Iron Bars -> Dark Bluish Gray
            102: 47,  # Glass Pane -> Trans Clear
            103: 10,  # Melon Block -> Bright Green
            104: 2,   # Pumpkin Stem -> Green
            105: 2,   # Melon Stem -> Green
            106: 2,   # Vines -> Green
            107: 70,  # Fence Gate -> Reddish Brown
            108: 320, # Brick Stairs -> Dark Red
            109: 71,  # Stone Brick Stairs -> Light Bluish Gray
            110: 379, # Mycelium -> Sand Purple
            111: 10,  # Lily Pad -> Bright Green
            112: 320, # Nether Brick -> Dark Red
            113: 320, # Nether Brick Fence -> Dark Red
            114: 320, # Nether Brick Stairs -> Dark Red
            115: 4,   # Nether Wart -> Red
            116: 41,  # Enchanting Table -> Trans Light Cyan
            117: 85,  # Brewing Stand -> Dark Purple
            118: 72,  # Cauldron -> Dark Bluish Gray
            119: 0,   # End Portal -> Black
            120: 378, # End Portal Frame -> Sand Green
            121: 326, # End Stone -> Bright Light Yellow
            122: 0,   # Dragon Egg -> Black
            123: 25,  # Redstone Lamp Off -> Orange
            124: 25,  # Redstone Lamp On -> Orange
            125: 70,  # Double Wood Slab -> Reddish Brown
            126: 70,  # Wood Slab -> Reddish Brown
            127: 2,   # Cocoa -> Green
            128: 19,  # Sandstone Stairs -> Tan
            129: 10,  # Emerald Ore -> Bright Green
            130: 85,  # Ender Chest -> Dark Purple
            131: 70,  # Tripwire Hook -> Reddish Brown
            132: 7,   # Tripwire -> Light Gray
            133: 10,  # Emerald Block -> Bright Green
            134: 70,  # Spruce Stairs -> Reddish Brown
            135: 191, # Birch Stairs -> Bright Light Orange
            136: 70,  # Jungle Stairs -> Reddish Brown
            137: 25,  # Command Block -> Orange
            138: 41,  # Beacon -> Trans Light Cyan
            139: 72,  # Cobblestone Wall -> Dark Bluish Gray
            140: 70,  # Flower Pot -> Reddish Brown
            141: 2,   # Carrots -> Green
            142: 2,   # Potatoes -> Green
            143: 70,  # Wood Button -> Reddish Brown
            144: 15,  # Mob Head -> White
            145: 72,  # Anvil -> Dark Bluish Gray
            146: 70,  # Trapped Chest -> Reddish Brown
            147: 14,  # Light Weighted Pressure Plate -> Yellow
            148: 71,  # Heavy Weighted Pressure Plate -> Light Bluish Gray
            149: 71,  # Redstone Comparator Off -> Light Bluish Gray
            150: 71,  # Redstone Comparator On -> Light Bluish Gray
            151: 70,  # Daylight Detector -> Reddish Brown
            152: 4,   # Redstone Block -> Red
            153: 320, # Nether Quartz Ore -> Dark Red
            154: 72,  # Hopper -> Dark Bluish Gray
            155: 15,  # Quartz Block -> White
            156: 15,  # Quartz Stairs -> White
            157: 70,  # Activator Rail -> Reddish Brown
            158: 72,  # Dropper -> Dark Bluish Gray
            159: 15,  # Stained Clay -> White (data value)
            160: 47,  # Stained Glass Pane -> Trans Clear (data value)
            161: 10,  # Acacia/Dark Oak Leaves -> Bright Green
            162: 70,  # Acacia/Dark Oak Log -> Reddish Brown
            163: 484, # Acacia Stairs -> Dark Orange
            164: 6,   # Dark Oak Stairs -> Brown
            165: 27,  # Slime Block -> Lime
            166: 47,  # Barrier -> Trans Clear
            167: 71,  # Iron Trapdoor -> Light Bluish Gray
            168: 11,  # Prismarine -> Light Cyan
            169: 41,  # Sea Lantern -> Trans Light Cyan
            170: 14,  # Hay Bale -> Yellow
            171: 15,  # Carpet -> White (data value)
            172: 28,  # Hardened Clay -> Dark Tan
            173: 0,   # Coal Block -> Black
            174: 41,  # Packed Ice -> Trans Light Cyan
            175: 2,   # Large Flowers -> Green
            176: 15,  # Standing Banner -> White
            177: 15,  # Wall Banner -> White
            178: 70,  # Inverted Daylight Detector -> Reddish Brown
            179: 484, # Red Sandstone -> Dark Orange
            180: 484, # Red Sandstone Stairs -> Dark Orange
            181: 484, # Double Red Sandstone Slab -> Dark Orange
            182: 484, # Red Sandstone Slab -> Dark Orange
            183: 70,  # Spruce Fence Gate -> Reddish Brown
            184: 191, # Birch Fence Gate -> Bright Light Orange
            185: 70,  # Jungle Fence Gate -> Reddish Brown
            186: 6,   # Dark Oak Fence Gate -> Brown
            187: 484, # Acacia Fence Gate -> Dark Orange
            188: 70,  # Spruce Fence -> Reddish Brown
            189: 191, # Birch Fence -> Bright Light Orange
            190: 70,  # Jungle Fence -> Reddish Brown
            191: 6,   # Dark Oak Fence -> Brown
            192: 484, # Acacia Fence -> Dark Orange
            193: 70,  # Spruce Door -> Reddish Brown
            194: 191, # Birch Door -> Bright Light Orange
            195: 70,  # Jungle Door -> Reddish Brown
            196: 484, # Acacia Door -> Dark Orange
            197: 6,   # Dark Oak Door -> Brown
            198: 4,   # End Rod -> Red
            199: 85,  # Chorus Plant -> Dark Purple
            200: 85,  # Chorus Flower -> Dark Purple
            201: 85,  # Purpur Block -> Dark Purple
            202: 85,  # Purpur Pillar -> Dark Purple
            203: 85,  # Purpur Stairs -> Dark Purple
            204: 85,  # Double Purpur Slab -> Dark Purple
            205: 85,  # Purpur Slab -> Dark Purple
            206: 326, # End Stone Bricks -> Bright Light Yellow
            207: 2,   # Beetroot -> Green
            208: 6,   # Grass Path -> Brown
            209: 0,   # End Gateway -> Black
            210: 25,  # Repeating Command Block -> Orange
            211: 27,  # Chain Command Block -> Lime
            212: 41,  # Frosted Ice -> Trans Light Cyan
            213: 25,  # Magma Block -> Orange
            214: 320, # Nether Wart Block -> Dark Red
            215: 320, # Red Nether Brick -> Dark Red
            216: 15,  # Bone Block -> White
            217: 85,  # Structure Void -> Dark Purple
            218: 72,  # Observer -> Dark Bluish Gray
            219: 15,  # White Shulker Box -> White
            220: 25,  # Orange Shulker Box -> Orange
            221: 5,   # Magenta Shulker Box -> Magenta
            222: 9,   # Light Blue Shulker Box -> Light Blue
            223: 14,  # Yellow Shulker Box -> Yellow
            224: 27,  # Lime Shulker Box -> Lime
            225: 13,  # Pink Shulker Box -> Pink
            226: 8,   # Gray Shulker Box -> Dark Gray
            227: 7,   # Light Gray Shulker Box -> Light Gray
            228: 11,  # Cyan Shulker Box -> Light Cyan
            229: 85,  # Purple Shulker Box -> Dark Purple
            230: 1,   # Blue Shulker Box -> Blue
            231: 6,   # Brown Shulker Box -> Brown
            232: 2,   # Green Shulker Box -> Green
            233: 4,   # Red Shulker Box -> Red
            234: 0,   # Black Shulker Box -> Black
            235: 15,  # White Glazed Terracotta -> White
            236: 25,  # Orange Glazed Terracotta -> Orange
            237: 5,   # Magenta Glazed Terracotta -> Magenta
            238: 9,   # Light Blue Glazed Terracotta -> Light Blue
            239: 14,  # Yellow Glazed Terracotta -> Yellow
            240: 27,  # Lime Glazed Terracotta -> Lime
            241: 13,  # Pink Glazed Terracotta -> Pink
            242: 8,   # Gray Glazed Terracotta -> Dark Gray
            243: 7,   # Light Gray Glazed Terracotta -> Light Gray
            244: 11,  # Cyan Glazed Terracotta -> Light Cyan
            245: 85,  # Purple Glazed Terracotta -> Dark Purple
            246: 1,   # Blue Glazed Terracotta -> Blue
            247: 6,   # Brown Glazed Terracotta -> Brown
            248: 2,   # Green Glazed Terracotta -> Green
            249: 4,   # Red Glazed Terracotta -> Red
            250: 0,   # Black Glazed Terracotta -> Black
            251: 15,  # Concrete -> White (data value)
            252: 15,  # Concrete Powder -> White (data value)
            255: 72,  # Structure Block -> Dark Bluish Gray
        }

    def load_schematic(self, filepath: str) -> Optional[Dict]:
        """
        Load a Minecraft schematic file (.schematic or .schem)

        Args:
            filepath: Path to the schematic file

        Returns:
            Dictionary containing schematic data or None if failed
        """
        try:
            print(f"Loading schematic: {filepath}")

            # Detect format by extension
            if filepath.lower().endswith('.schem'):
                return self._load_schem_format(filepath)
            else:
                return self._load_schematic_format(filepath)

        except Exception as e:
            print(f"Error loading schematic: {e}")
            return None

    def _load_schematic_format(self, filepath: str) -> Optional[Dict]:
        """Load old .schematic format (MCEdit, pre-1.13)"""
        nbt_file = nbtlib.load(filepath)

        # Extract basic dimensions
        width = int(nbt_file['Width'])
        height = int(nbt_file['Height'])
        length = int(nbt_file['Length'])

        print(f"Schematic dimensions: {width}x{height}x{length} (old format)")

        # Extract block data
        # Use int16 to handle signed bytes (Minecraft block IDs can be negative)
        blocks = np.array(list(nbt_file['Blocks']), dtype=np.int16)
        # Convert negative values to positive (unsigned interpretation)
        blocks = np.where(blocks < 0, blocks + 256, blocks)
        data = np.array(list(nbt_file['Data']), dtype=np.int16) if 'Data' in nbt_file else None
        if data is not None:
            data = np.where(data < 0, data + 256, data)

        # Reshape to 3D array (Y, Z, X) - Minecraft coordinate system
        blocks_3d = blocks.reshape((height, length, width))

        return {
            'width': width,
            'height': height,
            'length': length,
            'blocks': blocks_3d,
            'data': data,
            'nbt': nbt_file,
            'format': 'schematic'
        }

    def _load_schem_format(self, filepath: str) -> Optional[Dict]:
        """Load new .schem format (Sponge/WorldEdit, 1.13+)"""
        nbt_file = nbtlib.load(filepath)

        # .schem files may have data at root or under 'Schematic' tag
        root = nbt_file
        if 'Schematic' in nbt_file:
            root = nbt_file['Schematic']

        # Debug: print available keys to help diagnose structure
        print(f"NBT keys found: {list(root.keys())}")

        # Extract basic dimensions
        width = int(root['Width'])
        height = int(root['Height'])
        length = int(root['Length'])

        print(f"Schematic dimensions: {width}x{height}x{length} (new .schem format)")

        # Find palette and block data - different .schem versions store them differently
        palette = None
        block_data = None

        # Sponge Schematic v3: Blocks compound contains Palette and Data
        if 'Blocks' in root and hasattr(root['Blocks'], 'keys'):
            blocks_compound = root['Blocks']
            if 'Palette' in blocks_compound:
                palette = blocks_compound['Palette']
            if 'Data' in blocks_compound:
                block_data = blocks_compound['Data']
            print("Detected: Sponge Schematic v3 format")

        # Sponge Schematic v1/v2: Palette and BlockData at root level
        if palette is None and 'Palette' in root:
            palette = root['Palette']
            print("Detected: Sponge Schematic v1/v2 format")

        if block_data is None and 'BlockData' in root:
            block_data = root['BlockData']

        # If still no palette, try alternative locations
        if palette is None:
            # Check for 'palette' lowercase
            for key in root.keys():
                if key.lower() == 'palette':
                    palette = root[key]
                    break

        if palette is None:
            raise KeyError(f"Could not find Palette in .schem file. Available keys: {list(root.keys())}")

        if block_data is None:
            raise KeyError(f"Could not find BlockData in .schem file. Available keys: {list(root.keys())}")

        # Invert palette: index -> block name
        index_to_block = {}
        for block_name, index in palette.items():
            index_to_block[int(index)] = block_name

        print(f"Found {len(palette)} unique block types in palette")

        # BlockData may be varint encoded, handle both cases
        if hasattr(block_data, '__iter__'):
            raw_data = list(block_data)
        else:
            raw_data = block_data

        # Decode varint-encoded block data
        block_indices = self._decode_varint_array(raw_data, width * height * length)

        # Convert palette indices to our internal block ID system
        blocks = np.zeros(len(block_indices), dtype=np.int16)
        block_names = []  # Store block names for color lookup

        for i, idx in enumerate(block_indices):
            block_name = index_to_block.get(idx, "minecraft:air")
            # Convert block name to numeric ID for compatibility
            blocks[i] = self._block_name_to_id(block_name)
            block_names.append(block_name)

        # Reshape to 3D array (Y, Z, X)
        blocks_3d = blocks.reshape((height, length, width))

        return {
            'width': width,
            'height': height,
            'length': length,
            'blocks': blocks_3d,
            'data': None,  # .schem doesn't use separate data values
            'block_names': block_names,  # Store for color lookup
            'nbt': nbt_file,
            'format': 'schem'
        }

    def _decode_varint_array(self, data: List, expected_length: int) -> List[int]:
        """Decode varint-encoded block data from .schem format"""
        result = []
        i = 0
        while i < len(data) and len(result) < expected_length:
            value = 0
            shift = 0
            while True:
                if i >= len(data):
                    break
                byte = data[i] if data[i] >= 0 else data[i] + 256
                i += 1
                value |= (byte & 0x7F) << shift
                if (byte & 0x80) == 0:
                    break
                shift += 7
            result.append(value)
        return result

    def _block_name_to_id(self, block_name: str) -> int:
        """Convert Minecraft block name to numeric ID (for block type only, not color)"""
        name = block_name.replace("minecraft:", "")
        if "[" in name:
            name = name.split("[")[0]

        # Simple mapping for block types (color handled separately)
        name_to_id = {
            "air": 0, "stone": 1, "grass_block": 2, "dirt": 3, "cobblestone": 4,
            "bedrock": 7, "water": 8, "lava": 10, "sand": 12, "gravel": 13,
            "gold_ore": 14, "iron_ore": 15, "coal_ore": 16,
            "glass": 20, "glass_pane": 20, "tinted_glass": 20,
            "gold_block": 41, "iron_block": 42, "bricks": 45, "tnt": 46,
            "obsidian": 49, "diamond_ore": 56, "diamond_block": 57,
            "redstone_ore": 73, "ice": 79, "snow_block": 80, "clay": 82,
            "netherrack": 87, "glowstone": 89, "stone_bricks": 98,
            "emerald_block": 133, "redstone_block": 152, "quartz_block": 155,
            "coal_block": 173, "packed_ice": 174,
        }
        return name_to_id.get(name, 1)

    def _get_color_from_block_name(self, block_name: str) -> int:
        """Get LDraw color directly from Minecraft block name (for .schem format)"""
        name = block_name.replace("minecraft:", "")
        if "[" in name:
            name = name.split("[")[0]

        # Direct block name to LDraw color mapping
        # LDraw colors: 0=Black, 1=Blue, 2=Green, 4=Red, 7=LtGray, 8=DkGray, 14=Yellow, 15=White
        # 19=Tan, 25=Orange, 27=Lime, 47=TransClear, 41=TransLtCyan, 42=TransLtBlue, 73=MedBlue
        block_to_color = {
            # Basic blocks
            "air": -1,  # Skip
            "stone": 71, "cobblestone": 72, "mossy_cobblestone": 378,
            "granite": 25, "polished_granite": 25, "diorite": 7, "polished_diorite": 7,
            "andesite": 8, "polished_andesite": 8,
            "grass_block": 10, "dirt": 6, "coarse_dirt": 6, "podzol": 6,
            "bedrock": 0, "sand": 19, "red_sand": 25, "gravel": 71,
            "sandstone": 19, "red_sandstone": 484, "smooth_sandstone": 19,

            # Ores and minerals
            "gold_ore": 14, "deepslate_gold_ore": 14, "nether_gold_ore": 14,
            "iron_ore": 71, "deepslate_iron_ore": 71,
            "coal_ore": 0, "deepslate_coal_ore": 0,
            "diamond_ore": 41, "deepslate_diamond_ore": 41,
            "emerald_ore": 10, "deepslate_emerald_ore": 10,
            "lapis_ore": 1, "deepslate_lapis_ore": 1,
            "redstone_ore": 4, "deepslate_redstone_ore": 4,
            "copper_ore": 484, "deepslate_copper_ore": 484,

            # Metal/mineral blocks
            "gold_block": 14, "iron_block": 71, "diamond_block": 41, "emerald_block": 10,
            "lapis_block": 1, "redstone_block": 4, "coal_block": 0,
            "copper_block": 484, "raw_copper_block": 484, "raw_iron_block": 71, "raw_gold_block": 14,
            "netherite_block": 0, "ancient_debris": 6,
            "amethyst_block": 85, "budding_amethyst": 85,

            # Glass - TRANSPARENT
            "glass": 47, "glass_pane": 47, "tinted_glass": 8,
            "white_stained_glass": 47, "white_stained_glass_pane": 47,
            "orange_stained_glass": 182, "orange_stained_glass_pane": 182,
            "magenta_stained_glass": 113, "magenta_stained_glass_pane": 113,
            "light_blue_stained_glass": 41, "light_blue_stained_glass_pane": 41,
            "yellow_stained_glass": 46, "yellow_stained_glass_pane": 46,
            "lime_stained_glass": 35, "lime_stained_glass_pane": 35,
            "pink_stained_glass": 113, "pink_stained_glass_pane": 113,
            "gray_stained_glass": 40, "gray_stained_glass_pane": 40,
            "light_gray_stained_glass": 40, "light_gray_stained_glass_pane": 40,
            "cyan_stained_glass": 41, "cyan_stained_glass_pane": 41,
            "purple_stained_glass": 52, "purple_stained_glass_pane": 52,
            "blue_stained_glass": 33, "blue_stained_glass_pane": 33,
            "brown_stained_glass": 111, "brown_stained_glass_pane": 111,
            "green_stained_glass": 34, "green_stained_glass_pane": 34,
            "red_stained_glass": 36, "red_stained_glass_pane": 36,
            "black_stained_glass": 40, "black_stained_glass_pane": 40,

            # Wool - all 16 colors
            "white_wool": 15, "orange_wool": 25, "magenta_wool": 5, "light_blue_wool": 9,
            "yellow_wool": 14, "lime_wool": 27, "pink_wool": 13, "gray_wool": 8,
            "light_gray_wool": 7, "cyan_wool": 11, "purple_wool": 85, "blue_wool": 1,
            "brown_wool": 6, "green_wool": 2, "red_wool": 4, "black_wool": 0,

            # Concrete - all 16 colors
            "white_concrete": 15, "orange_concrete": 25, "magenta_concrete": 5, "light_blue_concrete": 9,
            "yellow_concrete": 14, "lime_concrete": 27, "pink_concrete": 13, "gray_concrete": 8,
            "light_gray_concrete": 7, "cyan_concrete": 11, "purple_concrete": 85, "blue_concrete": 1,
            "brown_concrete": 6, "green_concrete": 2, "red_concrete": 4, "black_concrete": 0,

            # Terracotta - all 16 colors
            "terracotta": 28, "white_terracotta": 15, "orange_terracotta": 25, "magenta_terracotta": 5,
            "light_blue_terracotta": 9, "yellow_terracotta": 14, "lime_terracotta": 27, "pink_terracotta": 13,
            "gray_terracotta": 8, "light_gray_terracotta": 7, "cyan_terracotta": 11, "purple_terracotta": 85,
            "blue_terracotta": 1, "brown_terracotta": 6, "green_terracotta": 2, "red_terracotta": 4,
            "black_terracotta": 0,

            # Wood types
            "oak_planks": 70, "spruce_planks": 6, "birch_planks": 19, "jungle_planks": 70,
            "acacia_planks": 484, "dark_oak_planks": 6, "mangrove_planks": 4, "cherry_planks": 13,
            "bamboo_planks": 14, "crimson_planks": 320, "warped_planks": 11,
            "oak_log": 70, "spruce_log": 6, "birch_log": 15, "jungle_log": 70,
            "acacia_log": 484, "dark_oak_log": 6, "mangrove_log": 70, "cherry_log": 13,
            "crimson_stem": 320, "warped_stem": 11, "bamboo_block": 14,

            # Leaves
            "oak_leaves": 2, "spruce_leaves": 288, "birch_leaves": 10, "jungle_leaves": 2,
            "acacia_leaves": 2, "dark_oak_leaves": 288, "mangrove_leaves": 2, "cherry_leaves": 13,
            "azalea_leaves": 2, "flowering_azalea_leaves": 13,

            # Nether blocks
            "netherrack": 320, "nether_bricks": 320, "red_nether_bricks": 320,
            "soul_sand": 6, "soul_soil": 6, "basalt": 8, "smooth_basalt": 8, "blackstone": 0,
            "polished_blackstone": 0, "polished_blackstone_bricks": 0,
            "glowstone": 326, "shroomlight": 326,
            "nether_wart_block": 320, "warped_wart_block": 11,
            "crying_obsidian": 85, "respawn_anchor": 0,

            # End blocks
            "end_stone": 326, "end_stone_bricks": 326, "purpur_block": 85, "purpur_pillar": 85,

            # Other
            "obsidian": 0, "bricks": 320, "stone_bricks": 71, "mossy_stone_bricks": 378,
            "cracked_stone_bricks": 72, "chiseled_stone_bricks": 71,
            "prismarine": 11, "prismarine_bricks": 11, "dark_prismarine": 288,
            "sea_lantern": 41, "ice": 41, "packed_ice": 41, "blue_ice": 41,
            "snow_block": 15, "snow": 15, "powder_snow": 15,
            "clay": 71, "mud": 6, "mud_bricks": 6, "packed_mud": 6,
            "water": 73, "lava": 25,
            "fire": 25, "soul_fire": 11,
            "tnt": 4, "bookshelf": 70, "hay_block": 14,
            "sponge": 14, "wet_sponge": 14,
            "melon": 10, "pumpkin": 25, "carved_pumpkin": 25, "jack_o_lantern": 25,
            "cactus": 288, "bamboo": 10,
            "moss_block": 10, "moss_carpet": 10, "sculk": 11, "sculk_catalyst": 11,
            "honeycomb_block": 14, "honey_block": 14,
            "slime_block": 27,

            # Deepslate variants
            "deepslate": 72, "cobbled_deepslate": 72, "polished_deepslate": 72,
            "deepslate_bricks": 72, "deepslate_tiles": 72, "chiseled_deepslate": 72,
            "reinforced_deepslate": 72,
            "tuff": 71, "calcite": 15, "dripstone_block": 19,

            # Quartz
            "quartz_block": 15, "quartz_bricks": 15, "quartz_pillar": 15, "chiseled_quartz_block": 15,
            "smooth_quartz": 15,
        }

        # Return the color, or default to light gray (7) if unknown
        return block_to_color.get(name, 7)

    def get_brick_info(self, block_id: int, data_value: int = 0) -> Tuple[str, int]:
        """
        Get Lego brick type and color for a Minecraft block

        Args:
            block_id: Minecraft block ID
            data_value: Block data value (for variants)

        Returns:
            Tuple of (brick_type, color_id)
        """
        # Use uniform 1x1 brick for all blocks (accurate 1:1 conversion)
        brick_type = self.default_brick

        # Get color from block_colors mapping (default to gray if unknown)
        color_id = self.block_colors.get(block_id, 7)

        # Blocks that use data value for color (like wool)
        # 35=Wool, 95=Stained Glass, 159=Stained Clay, 160=Stained Glass Pane,
        # 171=Carpet, 251=Concrete, 252=Concrete Powder
        color_data_blocks = {35, 95, 159, 160, 171, 251, 252}
        if block_id in color_data_blocks and data_value in self.wool_color_mappings:
            color_id = self.wool_color_mappings[data_value]

        return brick_type, color_id

    def convert_to_ldraw(self, schematic_data: Dict, optimize: bool = False) -> str:
        """
        Convert schematic data to LDraw format

        Args:
            schematic_data: Loaded schematic data
            optimize: If True, merge adjacent same-color blocks into larger bricks

        Returns:
            LDraw format string
        """
        blocks = schematic_data['blocks']
        width = schematic_data['width']
        height = schematic_data['height']
        length = schematic_data['length']

        ldraw_lines = []
        ldraw_lines.append("0 Untitled")
        ldraw_lines.append("0 Name: Converted from Minecraft")
        ldraw_lines.append("0 Author: CodeRunner IDE Converter")
        if optimize:
            ldraw_lines.append("0 Optimized: Yes (merged bricks)")
        ldraw_lines.append("")

        brick_count = 0

        if optimize:
            # Optimized conversion - merge adjacent same-color blocks
            brick_count = self._convert_optimized(schematic_data, ldraw_lines, width, height, length)
        else:
            # Standard 1x1 brick conversion
            brick_count = self._convert_standard(schematic_data, ldraw_lines, width, height, length)

        print(f"Converted to {brick_count} Lego bricks")
        return "\n".join(ldraw_lines)

    def _convert_standard(self, schematic_data: Dict, ldraw_lines: List, width: int, height: int, length: int) -> int:
        """Standard conversion - one 1x1 brick per Minecraft block"""
        blocks = schematic_data['blocks']
        brick_count = 0

        # Check if we have block names (.schem format)
        has_block_names = 'block_names' in schematic_data and schematic_data['block_names'] is not None
        block_names = schematic_data.get('block_names', [])

        for y in range(height):
            for z in range(length):
                for x in range(width):
                    block_id = blocks[y, z, x]

                    # Skip air blocks (ID 0)
                    if block_id == 0:
                        continue

                    # Get color based on format
                    if has_block_names:
                        # .schem format - use block name for accurate color
                        data_index = y * length * width + z * width + x
                        if data_index < len(block_names):
                            block_name = block_names[data_index]
                            color_id = self._get_color_from_block_name(block_name)
                            # Skip air blocks
                            if color_id == -1:
                                continue
                        else:
                            color_id = 7  # Default gray
                    else:
                        # Old .schematic format - use numeric ID and data value
                        data_value = 0
                        if schematic_data['data'] is not None:
                            data_index = y * length * width + z * width + x
                            if data_index < len(schematic_data['data']):
                                data_value = schematic_data['data'][data_index]
                        _, color_id = self.get_brick_info(block_id, data_value)

                    brick_type = self.default_brick

                    # Convert coordinates to LDraw units
                    # LDraw: Y is negative going UP, 20 LDU = 1 stud width, 24 LDU = 1 brick height
                    ldraw_x = (x - width/2) * 20
                    ldraw_y = -y * 24
                    ldraw_z = (z - length/2) * 20

                    # Create LDraw line for this brick
                    ldraw_line = f"1 {color_id} {ldraw_x:.2f} {ldraw_y:.2f} {ldraw_z:.2f} 1 0 0 0 1 0 0 0 1 {brick_type}.dat"
                    ldraw_lines.append(ldraw_line)
                    brick_count += 1

        return brick_count

    def _convert_optimized(self, schematic_data: Dict, ldraw_lines: List, width: int, height: int, length: int) -> int:
        """Optimized conversion - merge adjacent same-color blocks into larger bricks"""
        blocks = schematic_data['blocks']
        brick_count = 0

        # Check if we have block names (.schem format)
        has_block_names = 'block_names' in schematic_data and schematic_data['block_names'] is not None
        block_names = schematic_data.get('block_names', [])

        # Build color grid (stores color_id for each position, -1 for air)
        color_grid = np.full((height, length, width), -1, dtype=np.int16)

        print("🔍 Analyzing blocks for optimization...")

        for y in range(height):
            for z in range(length):
                for x in range(width):
                    block_id = blocks[y, z, x]
                    if block_id == 0:
                        continue

                    # Get color based on format
                    if has_block_names:
                        # .schem format - use block name for accurate color
                        data_index = y * length * width + z * width + x
                        if data_index < len(block_names):
                            block_name = block_names[data_index]
                            color_id = self._get_color_from_block_name(block_name)
                            if color_id == -1:  # Skip air
                                continue
                        else:
                            color_id = 7
                    else:
                        # Old .schematic format
                        data_value = 0
                        if schematic_data['data'] is not None:
                            data_index = y * length * width + z * width + x
                            if data_index < len(schematic_data['data']):
                                data_value = schematic_data['data'][data_index]
                        _, color_id = self.get_brick_info(block_id, data_value)

                    color_grid[y, z, x] = color_id

        # Track which cells have been used
        used = np.zeros((height, length, width), dtype=bool)

        # Available brick lengths (X direction), sorted largest first
        x_lengths = [8, 6, 4, 3, 2, 1]

        print("🧱 Merging bricks (this may take a moment)...")

        for y in range(height):
            for z in range(length):
                for x in range(width):
                    if used[y, z, x] or color_grid[y, z, x] == -1:
                        continue

                    color_id = color_grid[y, z, x]

                    # Try to find the longest run in X direction
                    best_x_len = 1
                    for x_len in x_lengths:
                        if x + x_len > width:
                            continue
                        # Check if all cells in this run are same color and unused
                        valid = True
                        for dx in range(x_len):
                            if used[y, z, x + dx] or color_grid[y, z, x + dx] != color_id:
                                valid = False
                                break
                        if valid:
                            best_x_len = x_len
                            break

                    # Try to extend in Z direction for 2-wide bricks
                    best_z_len = 1
                    if z + 1 < length and best_x_len >= 2:
                        # Check if we can make a 2-wide brick
                        can_extend_z = True
                        for dx in range(best_x_len):
                            if used[y, z + 1, x + dx] or color_grid[y, z + 1, x + dx] != color_id:
                                can_extend_z = False
                                break
                        if can_extend_z:
                            # Check if this 2-wide size exists
                            if (2, best_x_len) in self.brick_sizes:
                                best_z_len = 2

                    # Get the brick part number
                    brick_key = (best_z_len, best_x_len)
                    if brick_key in self.brick_sizes:
                        brick_type = self.brick_sizes[brick_key]
                    else:
                        # Fall back to 1x1 bricks
                        brick_type = self.default_brick
                        best_x_len = 1
                        best_z_len = 1

                    # Mark cells as used
                    for dz in range(best_z_len):
                        for dx in range(best_x_len):
                            used[y, z + dz, x + dx] = True

                    # Calculate position (center of the brick)
                    # LDraw positions are at the center of the brick
                    center_x = x + (best_x_len - 1) / 2
                    center_z = z + (best_z_len - 1) / 2

                    ldraw_x = (center_x - width/2) * 20
                    ldraw_y = -y * 24
                    ldraw_z = (center_z - length/2) * 20

                    # Create LDraw line
                    ldraw_line = f"1 {color_id} {ldraw_x:.2f} {ldraw_y:.2f} {ldraw_z:.2f} 1 0 0 0 1 0 0 0 1 {brick_type}.dat"
                    ldraw_lines.append(ldraw_line)
                    brick_count += 1

        return brick_count

    def save_ldraw_file(self, ldraw_content: str, output_path: str):
        """
        Save LDraw content to file

        Args:
            ldraw_content: LDraw format string
            output_path: Output file path
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(ldraw_content)
            print(f"Saved LDraw file: {output_path}")
        except Exception as e:
            print(f"Error saving LDraw file: {e}")

    def convert_file(self, input_path: str, output_path: str = None) -> bool:
        """
        Convert a single Minecraft schematic file to LDraw

        Args:
            input_path: Path to input schematic file
            output_path: Path to output LDraw file (auto-generated if None)

        Returns:
            True if conversion successful, False otherwise
        """
        if not os.path.exists(input_path):
            print(f"Input file not found: {input_path}")
            return False

        # Auto-generate output path if not provided
        if output_path is None:
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            output_path = f"{base_name}.ldr"

        # Load schematic
        schematic = self.load_schematic(input_path)
        if schematic is None:
            return False

        # Convert to LDraw
        ldraw_content = self.convert_to_ldraw(schematic)

        # Save LDraw file
        self.save_ldraw_file(ldraw_content, output_path)

        return True

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description="Convert Minecraft schematic files to Lego LDraw format")
    parser.add_argument("input", help="Input Minecraft schematic file (.schematic)")
    parser.add_argument("-o", "--output", help="Output LDraw file (.ldr)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    converter = MinecraftToLegoConverter()

    if args.verbose:
        print("Minecraft to Lego Converter")
        print("===========================")

    success = converter.convert_file(args.input, args.output)

    if success:
        print("Conversion completed successfully!")
        if args.output:
            print(f"Output saved to: {args.output}")
    else:
        print("Conversion failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
