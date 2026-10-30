#!/usr/bin/env python3
"""
Jonathan Rothberg's MineCraft to LEGO converter

Converts Minecraft schematic files (.schematic, .schem) to LDraw format (.ldr)
for viewing and editing in LeoCAD and other LEGO CAD software.

Author: Jonathan Rothberg
Created: 2026-01-04
"""

import os
import sys
import argparse
import json
import math
import re
import struct
import zipfile
import numpy as np
from typing import Dict, List, Tuple, Optional
import nbtlib  # For parsing Minecraft NBT files

# LDraw color id -> (name, red, green, blue). Brick colors are grouped into
# printer filaments by how close these colors are. Unknown ids use light gray.
LDRAW_COLORS = {
    0: ("Black", 5, 19, 29),
    1: ("Blue", 0, 85, 191),
    2: ("Green", 35, 120, 65),
    4: ("Red", 201, 26, 9),
    5: ("Dark Pink", 200, 112, 160),
    6: ("Brown", 88, 57, 39),
    7: ("Light Gray", 155, 161, 157),
    8: ("Dark Gray", 109, 110, 92),
    9: ("Light Blue", 180, 210, 227),
    10: ("Bright Green", 75, 159, 74),
    11: ("Light Turquoise", 85, 165, 175),
    13: ("Pink", 252, 151, 172),
    14: ("Yellow", 242, 205, 55),
    15: ("White", 255, 255, 255),
    19: ("Tan", 228, 205, 158),
    25: ("Orange", 254, 138, 24),
    27: ("Lime", 187, 233, 11),
    28: ("Dark Tan", 149, 138, 115),
    33: ("Trans Dark Blue", 0, 32, 160),
    36: ("Trans Red", 201, 26, 9),
    41: ("Trans Light Turquoise", 85, 165, 175),
    42: ("Trans Light Blue", 160, 197, 232),
    46: ("Trans Yellow", 245, 205, 47),
    47: ("Trans Clear", 252, 252, 252),
    70: ("Reddish Brown", 105, 64, 39),
    71: ("Light Bluish Gray", 160, 165, 169),
    72: ("Dark Bluish Gray", 108, 110, 104),
    73: ("Medium Blue", 90, 147, 219),
    85: ("Dark Purple", 63, 54, 145),
    191: ("Bright Light Orange", 248, 187, 61),
    288: ("Dark Green", 24, 70, 50),
    320: ("Dark Red", 114, 14, 15),
    326: ("Bright Light Yellow", 255, 240, 140),
    378: ("Sand Green", 160, 188, 172),
    379: ("Sand Purple", 132, 94, 132),
    484: ("Dark Orange", 169, 85, 0),
}

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

        # Non-solid blocks to skip — these don't fill a full block in Minecraft
        # and look wrong as 1x1 bricks. Removing them cleans up the model.
        self.skip_blocks = {
            # Torches and light sources
            "torch", "wall_torch", "soul_torch", "soul_wall_torch",
            "redstone_torch", "redstone_wall_torch", "lantern", "soul_lantern",
            "candle", "candle_cake",
            "white_candle", "orange_candle", "magenta_candle", "light_blue_candle",
            "yellow_candle", "lime_candle", "pink_candle", "gray_candle",
            "light_gray_candle", "cyan_candle", "purple_candle", "blue_candle",
            "brown_candle", "green_candle", "red_candle", "black_candle",
            # Signs
            "oak_sign", "spruce_sign", "birch_sign", "jungle_sign",
            "acacia_sign", "dark_oak_sign", "mangrove_sign", "cherry_sign",
            "bamboo_sign", "crimson_sign", "warped_sign",
            "oak_wall_sign", "spruce_wall_sign", "birch_wall_sign", "jungle_wall_sign",
            "acacia_wall_sign", "dark_oak_wall_sign", "mangrove_wall_sign", "cherry_wall_sign",
            "bamboo_wall_sign", "crimson_wall_sign", "warped_wall_sign",
            "oak_hanging_sign", "spruce_hanging_sign", "birch_hanging_sign",
            "jungle_hanging_sign", "acacia_hanging_sign", "dark_oak_hanging_sign",
            "mangrove_hanging_sign", "cherry_hanging_sign", "bamboo_hanging_sign",
            "crimson_hanging_sign", "warped_hanging_sign",
            # Buttons and pressure plates
            "stone_button", "oak_button", "spruce_button", "birch_button",
            "jungle_button", "acacia_button", "dark_oak_button", "mangrove_button",
            "cherry_button", "bamboo_button", "crimson_button", "warped_button",
            "polished_blackstone_button",
            "stone_pressure_plate", "oak_pressure_plate", "spruce_pressure_plate",
            "birch_pressure_plate", "jungle_pressure_plate", "acacia_pressure_plate",
            "dark_oak_pressure_plate", "mangrove_pressure_plate", "cherry_pressure_plate",
            "bamboo_pressure_plate", "crimson_pressure_plate", "warped_pressure_plate",
            "light_weighted_pressure_plate", "heavy_weighted_pressure_plate",
            "polished_blackstone_pressure_plate",
            # Redstone components
            "redstone_wire", "repeater", "comparator", "lever",
            "tripwire", "tripwire_hook",
            # Rails
            "rail", "powered_rail", "detector_rail", "activator_rail",
            # Doors and trapdoors (thin, don't fill block)
            "oak_door", "spruce_door", "birch_door", "jungle_door",
            "acacia_door", "dark_oak_door", "mangrove_door", "cherry_door",
            "bamboo_door", "crimson_door", "warped_door", "iron_door",
            "oak_trapdoor", "spruce_trapdoor", "birch_trapdoor", "jungle_trapdoor",
            "acacia_trapdoor", "dark_oak_trapdoor", "mangrove_trapdoor", "cherry_trapdoor",
            "bamboo_trapdoor", "crimson_trapdoor", "warped_trapdoor", "iron_trapdoor",
            # Flowers and small plants
            "dandelion", "poppy", "blue_orchid", "allium", "azure_bluet",
            "red_tulip", "orange_tulip", "white_tulip", "pink_tulip",
            "oxeye_daisy", "cornflower", "lily_of_the_valley", "wither_rose",
            "torchflower", "pitcher_plant",
            "sunflower", "lilac", "rose_bush", "peony",
            "grass", "tall_grass", "fern", "large_fern", "dead_bush",
            "seagrass", "tall_seagrass", "kelp", "kelp_plant",
            "sweet_berry_bush", "cave_vines", "cave_vines_plant",
            "hanging_roots", "spore_blossom", "glow_lichen", "sculk_vein",
            # Saplings
            "oak_sapling", "spruce_sapling", "birch_sapling", "jungle_sapling",
            "acacia_sapling", "dark_oak_sapling", "mangrove_propagule", "cherry_sapling",
            "bamboo_sapling",
            # Misc non-solid
            "ladder", "vine", "sugar_cane", "lily_pad",
            "cobweb", "string",
            "fire", "soul_fire",
            "end_rod", "lightning_rod", "chain",
            "scaffolding", "pointed_dripstone",
            "flower_pot", "potted_oak_sapling", "potted_spruce_sapling",
            "potted_birch_sapling", "potted_jungle_sapling", "potted_acacia_sapling",
            "potted_dark_oak_sapling", "potted_mangrove_propagule", "potted_cherry_sapling",
            "potted_fern", "potted_dandelion", "potted_poppy", "potted_blue_orchid",
            "potted_allium", "potted_azure_bluet", "potted_red_tulip",
            "potted_orange_tulip", "potted_white_tulip", "potted_pink_tulip",
            "potted_oxeye_daisy", "potted_cornflower", "potted_lily_of_the_valley",
            "potted_wither_rose", "potted_dead_bush",
            "potted_cactus", "potted_bamboo", "potted_crimson_fungus", "potted_warped_fungus",
            "potted_crimson_roots", "potted_warped_roots", "potted_azalea_bush",
            "potted_flowering_azalea_bush", "potted_torchflower",
            # Crops (thin)
            "wheat", "carrots", "potatoes", "beetroots", "nether_wart",
            "cocoa", "melon_stem", "pumpkin_stem",
            "attached_melon_stem", "attached_pumpkin_stem",
            # Heads, banners, beds (complex shapes that don't work as cubes)
            "skeleton_skull", "skeleton_wall_skull",
            "wither_skeleton_skull", "wither_skeleton_wall_skull",
            "zombie_head", "zombie_wall_head",
            "player_head", "player_wall_head",
            "creeper_head", "creeper_wall_head",
            "dragon_head", "dragon_wall_head",
            "piglin_head", "piglin_wall_head",
            "white_banner", "orange_banner", "magenta_banner", "light_blue_banner",
            "yellow_banner", "lime_banner", "pink_banner", "gray_banner",
            "light_gray_banner", "cyan_banner", "purple_banner", "blue_banner",
            "brown_banner", "green_banner", "red_banner", "black_banner",
            "white_wall_banner", "orange_wall_banner", "magenta_wall_banner",
            "light_blue_wall_banner", "yellow_wall_banner", "lime_wall_banner",
            "pink_wall_banner", "gray_wall_banner", "light_gray_wall_banner",
            "cyan_wall_banner", "purple_wall_banner", "blue_wall_banner",
            "brown_wall_banner", "green_wall_banner", "red_wall_banner", "black_wall_banner",
            # Brewing, enchanting, anvil (irregular shapes)
            "brewing_stand", "cauldron", "water_cauldron", "lava_cauldron",
            "powder_snow_cauldron", "anvil", "chipped_anvil", "damaged_anvil",
            # NOTE: Fences, fence gates, and walls are kept as full bricks.
            # They're thin in Minecraft but commonly serve as structural supports
            # (columns, railings, table legs, etc). Skipping them causes floating structures.
        }

        # Special parts for stairs and slabs
        # Note: Glass panes use regular translucent bricks
        self.special_parts = {
            "slab": "3024",      # 1x1 plate (for half blocks)
            "stair": "54200",    # 1x1x2/3 cheese slope - fits 1-stud grid
        }

        # Rotation matrices for LDraw (3x3 matrix as 9 values: a b c d e f g h i)
        # Format: "a b c d e f g h i" for matrix [[a,b,c],[d,e,f],[g,h,i]]
        self.rotations = {
            # Horizontal rotations (for stairs facing direction)
            "north": "1 0 0 0 1 0 0 0 1",       # Default, no rotation
            "east":  "0 0 -1 0 1 0 1 0 0",      # 90° clockwise
            "south": "-1 0 0 0 1 0 0 0 -1",     # 180°
            "west":  "0 0 1 0 1 0 -1 0 0",      # 90° counter-clockwise
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

    def _parse_block_state(self, block_name: str) -> Tuple[str, Dict[str, str]]:
        """Parse block name and state properties from full block string.
        
        Example: 'minecraft:oak_stairs[facing=east,half=bottom]' 
        Returns: ('oak_stairs', {'facing': 'east', 'half': 'bottom'})
        """
        name = block_name.replace("minecraft:", "")
        properties = {}
        
        if "[" in name:
            base_name = name.split("[")[0]
            props_str = name.split("[")[1].rstrip("]")
            for prop in props_str.split(","):
                if "=" in prop:
                    key, value = prop.split("=", 1)
                    properties[key] = value
            return base_name, properties
        
        return name, properties

    def _get_special_part_info(self, block_name: str) -> Optional[Dict]:
        """Get special part info for stairs, slabs, and panes.
        
        Returns dict with: part, rotation, y_offset, or None for regular blocks
        """
        base_name, props = self._parse_block_state(block_name)
        
        # Check for STAIRS FIRST (before slab check)
        if "stairs" in base_name or "stair" in base_name:
            facing = props.get("facing", "north")
            half = props.get("half", "bottom")
            # shape is straight / inner_left / inner_right / outer_left / outer_right.
            # WorldEdit stores it when the schematic was saved. If it is missing,
            # build_parts fills it in from the neighboring stairs.
            shape = props.get("shape", "")
            rotation = self.rotations.get(facing, self.rotations["north"])
            y_offset = 0
            if half == "top":
                rotation = self._flip_rotation_y(rotation)
                y_offset = 24  # Flip to bottom of block space
            return {
                "part": self.special_parts["stair"],
                "rotation": rotation,
                "y_offset": y_offset,
                "type": "stair",
                "facing": facing,
                "half": half,
                "shape": shape,
            }
        
        # Check if this is a slab
        if "slab" in base_name:
            slab_type = props.get("type", "bottom")
            # Double slab = full block, treat as regular brick
            if slab_type == "double":
                return None
            # In LDraw, positive Y is DOWN
            # Bottom slab: move plate down to bottom of brick space
            # Top slab: keep at top of brick space
            y_offset = 16  # Default: bottom slab (move down)
            if slab_type == "top":
                y_offset = 0  # Top slab stays at top
            return {
                "part": self.special_parts["slab"],
                "rotation": self.rotations["north"],
                "y_offset": y_offset,
                "type": "slab",
                "slab_type": slab_type,
            }

        # Check if this is a carpet (thin 1/3 height like a plate, sits on floor)
        if "carpet" in base_name:
            return {
                "part": self.special_parts["slab"],  # Use plate for carpet
                "rotation": self.rotations["north"],
                "y_offset": 16,  # Move down to floor level
                "type": "carpet",
            }
        
        # Glass panes and iron bars - just use regular translucent/gray bricks
        # (no special handling, return None so they use default brick)
        
        # Not a special block
        return None

    def _flip_rotation_y(self, rotation_str: str) -> str:
        """Flip a rotation matrix 180 degrees around the X axis (for inverted stairs).
        Negates the Y-row and Z-row of the 3x3 rotation matrix."""
        vals = list(map(float, rotation_str.split()))
        # Negate Y row (indices 3,4,5) and Z row (indices 6,7,8)
        for i in range(3, 9):
            vals[i] = -vals[i]
        return " ".join(str(int(v)) if v == int(v) else str(v) for v in vals)

    def _is_skip_block(self, block_name: str) -> bool:
        """Check if a block should be skipped (non-solid, doesn't fill a full cube)."""
        name = block_name.replace("minecraft:", "")
        if "[" in name:
            name = name.split("[")[0]
        return name in self.skip_blocks

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

            # Carpet - all 16 colors (same as wool)
            "white_carpet": 15, "orange_carpet": 25, "magenta_carpet": 5, "light_blue_carpet": 9,
            "yellow_carpet": 14, "lime_carpet": 27, "pink_carpet": 13, "gray_carpet": 8,
            "light_gray_carpet": 7, "cyan_carpet": 11, "purple_carpet": 85, "blue_carpet": 1,
            "brown_carpet": 6, "green_carpet": 2, "red_carpet": 4, "black_carpet": 0,
            "moss_carpet": 10,  # Moss carpet is green

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

            # STAIRS - all wood and stone types
            "oak_stairs": 70, "spruce_stairs": 6, "birch_stairs": 19, "jungle_stairs": 70,
            "acacia_stairs": 484, "dark_oak_stairs": 6, "mangrove_stairs": 70, "cherry_stairs": 13,
            "bamboo_stairs": 14, "crimson_stairs": 320, "warped_stairs": 11,
            "stone_stairs": 71, "cobblestone_stairs": 72, "mossy_cobblestone_stairs": 378,
            "stone_brick_stairs": 71, "mossy_stone_brick_stairs": 378,
            "granite_stairs": 25, "polished_granite_stairs": 25,
            "diorite_stairs": 7, "polished_diorite_stairs": 7,
            "andesite_stairs": 8, "polished_andesite_stairs": 8,
            "brick_stairs": 320, "sandstone_stairs": 19, "red_sandstone_stairs": 484,
            "smooth_sandstone_stairs": 19, "smooth_red_sandstone_stairs": 484,
            "prismarine_stairs": 11, "prismarine_brick_stairs": 11, "dark_prismarine_stairs": 288,
            "nether_brick_stairs": 320, "red_nether_brick_stairs": 320,
            "quartz_stairs": 15, "smooth_quartz_stairs": 15,
            "purpur_stairs": 85, "end_stone_brick_stairs": 326,
            "blackstone_stairs": 0, "polished_blackstone_stairs": 0, "polished_blackstone_brick_stairs": 0,
            "deepslate_brick_stairs": 72, "deepslate_tile_stairs": 72, "cobbled_deepslate_stairs": 72,
            "cut_copper_stairs": 484, "exposed_cut_copper_stairs": 378,
            "weathered_cut_copper_stairs": 10, "oxidized_cut_copper_stairs": 11,
            "mud_brick_stairs": 6,

            # SLABS - all types
            "oak_slab": 70, "spruce_slab": 6, "birch_slab": 19, "jungle_slab": 70,
            "acacia_slab": 484, "dark_oak_slab": 6, "mangrove_slab": 70, "cherry_slab": 13,
            "bamboo_slab": 14, "crimson_slab": 320, "warped_slab": 11,
            "stone_slab": 71, "cobblestone_slab": 72, "mossy_cobblestone_slab": 378,
            "stone_brick_slab": 71, "mossy_stone_brick_slab": 378,
            "granite_slab": 25, "polished_granite_slab": 25,
            "diorite_slab": 7, "polished_diorite_slab": 7,
            "andesite_slab": 8, "polished_andesite_slab": 8,
            "brick_slab": 320, "sandstone_slab": 19, "red_sandstone_slab": 484,
            "smooth_sandstone_slab": 19, "smooth_red_sandstone_slab": 484,
            "cut_sandstone_slab": 19, "cut_red_sandstone_slab": 484,
            "prismarine_slab": 11, "prismarine_brick_slab": 11, "dark_prismarine_slab": 288,
            "nether_brick_slab": 320, "red_nether_brick_slab": 320,
            "quartz_slab": 15, "smooth_quartz_slab": 15,
            "purpur_slab": 85, "end_stone_brick_slab": 326,
            "blackstone_slab": 0, "polished_blackstone_slab": 0, "polished_blackstone_brick_slab": 0,
            "deepslate_brick_slab": 72, "deepslate_tile_slab": 72, "cobbled_deepslate_slab": 72,
            "cut_copper_slab": 484, "exposed_cut_copper_slab": 378,
            "weathered_cut_copper_slab": 10, "oxidized_cut_copper_slab": 11,
            "mud_brick_slab": 6, "smooth_stone_slab": 71,

            # PANES and BARS
            "glass_pane": 47, "iron_bars": 72,
            "white_stained_glass_pane": 47, "orange_stained_glass_pane": 182,
            "magenta_stained_glass_pane": 113, "light_blue_stained_glass_pane": 41,
            "yellow_stained_glass_pane": 46, "lime_stained_glass_pane": 35,
            "pink_stained_glass_pane": 113, "gray_stained_glass_pane": 40,
            "light_gray_stained_glass_pane": 40, "cyan_stained_glass_pane": 41,
            "purple_stained_glass_pane": 52, "blue_stained_glass_pane": 33,
            "brown_stained_glass_pane": 111, "green_stained_glass_pane": 34,
            "red_stained_glass_pane": 36, "black_stained_glass_pane": 40,
        }

        # Strip block state for color lookup (e.g., "oak_stairs[facing=east]" -> "oak_stairs")
        lookup_name = name.split("[")[0] if "[" in name else name

        # Return the color, or default to light gray (7) if unknown
        return block_to_color.get(lookup_name, 7)

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

    # Real brick lengths, in studs. Scale 2 places these as 2-stud-wide parts
    # (one Minecraft block is 2 studs), so a run is measured in blocks there.
    _RUN_LEN_1X = (1, 2, 3, 4, 6, 8)
    _PART_1X = {1: "3005", 2: "3004", 3: "3622", 4: "3010", 6: "3009", 8: "3008"}
    _RUN_LEN_2X = (1, 2, 3, 4)  # blocks; each block is 2 studs, parts are 2x2 .. 2x8
    _PART_2X = {1: "3003", 2: "3001", 3: "2456", 4: "3007"}
    # Old schematic ids. Data: bits 0-1 facing (E,W,S,N), bit 2 = upside down.
    _OLD_STAIR_IDS = {53, 67, 108, 109, 114, 128, 134, 135, 136, 156, 163, 164, 180, 203}
    _OLD_STAIR_FACING = {0: "east", 1: "west", 2: "south", 3: "north"}
    _OLD_SLAB_IDS = {44, 126, 182, 205}

    def _high_quads(self, facing: str, shape: str):
        """Which 1-stud quadrants of a 2x2 stair are the HIGH part.

        facing is the full-block side (Minecraft's definition).
        Viewed from above, north is -Z and west is -X:

            NW NE
            SW SE

        straight facing north is the north row. inner_* adds the left or right
        arm (3 quadrants). outer_* keeps only the left or right corner.
        """
        facing = facing if facing in ("north", "south", "east", "west") else "north"
        straight = {
            "north": {"NW", "NE"},
            "south": {"SW", "SE"},
            "east": {"NE", "SE"},
            "west": {"NW", "SW"},
        }[facing]
        left = {"north": "west", "west": "south", "south": "east", "east": "north"}
        right = {"north": "east", "east": "south", "south": "west", "west": "north"}
        opp = {"north": "south", "south": "north", "east": "west", "west": "east"}
        corner = {
            frozenset(("north", "west")): "NW",
            frozenset(("north", "east")): "NE",
            frozenset(("south", "west")): "SW",
            frozenset(("south", "east")): "SE",
        }
        if shape == "inner_left":
            return set(straight) | {corner[frozenset((left[facing], opp[facing]))]}
        if shape == "inner_right":
            return set(straight) | {corner[frozenset((right[facing], opp[facing]))]}
        if shape == "outer_left":
            return {corner[frozenset((facing, left[facing]))]}
        if shape == "outer_right":
            return {corner[frozenset((facing, right[facing]))]}
        return set(straight)

    def _infer_stair_shape(self, facing, half, x, y, z, stair_at, width, length):
        """Minecraft's stair corner rule, used when a schematic has no shape= property.

        Same test as StairBlock: a stair on the full-block side that faces across
        us is an outer corner; a stair on the low side that faces across us is
        an inner corner. Left/right follow rotateYCounterclockwise.
        """
        opp = {"north": "south", "south": "north", "east": "west", "west": "east"}
        ccw = {"north": "west", "west": "south", "south": "east", "east": "north"}
        step = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}

        def other(direction):
            dx, dz = step[direction]
            nx, nz = x + dx, z + dz
            if not (0 <= nx < width and 0 <= nz < length):
                return None
            return stair_at.get((y, nz, nx))

        def different(direction):
            found = other(direction)
            return found is None or found[0] != facing or found[1] != half

        def other_axis(a, b):
            return (a in ("north", "south")) != (b in ("north", "south"))

        neighbor = other(facing)
        if neighbor and neighbor[1] == half and other_axis(neighbor[0], facing):
            if different(opp[neighbor[0]]):
                return "outer_left" if neighbor[0] == ccw[facing] else "outer_right"
        neighbor = other(opp[facing])
        if neighbor and neighbor[1] == half and other_axis(neighbor[0], facing):
            if different(neighbor[0]):
                return "inner_left" if neighbor[0] == ccw[facing] else "inner_right"
        return "straight"

    def _quad_parts(self, quads, facing, use_slope):
        """Turn a set of quadrants into 1x1 / 1x2 bricks, or one slope.

        A straight stair with nothing stacked on it uses slope 3040 (2x1),
        high edge on the full-block side, sloping down toward the step.
        Corners and anything that must hold a brick above stay flat bricks,
        because a slope has no studs on top.
        """
        pair = {
            "N": ({"NW", "NE"}, (0, -10), "north"),
            "S": ({"SW", "SE"}, (0, 10), "south"),
            "E": ({"NE", "SE"}, (10, 0), "east"),
            "W": ({"NW", "SW"}, (-10, 0), "west"),
        }
        shift_1 = {"NW": (-10, -10), "NE": (10, -10), "SW": (-10, 10), "SE": (10, 10)}
        rot_id = (1, 0, 0, 0, 1, 0, 0, 0, 1)
        # 3040 slopes down toward local +Z. Point that at the low side.
        slope_rot = {
            "south": rot_id,
            "north": (-1, 0, 0, 0, 1, 0, 0, 0, -1),
            "west": (0, 0, -1, 0, 1, 0, 1, 0, 0),
            "east": (0, 0, 1, 0, 1, 0, -1, 0, 0),
        }
        # 3004 is 2 studs along local X. Turn that along Z for the east/west pairs.
        rot_to_z = (0, 0, -1, 0, 1, 0, 1, 0, 0)
        opp = {"north": "south", "south": "north", "east": "west", "west": "east"}
        quads = set(quads)
        prefer = {"north": "N", "south": "S", "east": "E", "west": "W"}.get(facing, "N")
        order = [prefer] + [k for k in ("N", "S", "E", "W") if k != prefer]

        if use_slope and len(quads) == 2:
            qs, shift, high = pair[prefer]
            if quads == qs:
                low = opp[high]
                return [{
                    "part": "3040", "shift": shift, "rot": slope_rot[low],
                    "sx": 2, "sz": 1, "kind": "slope", "slope_low": low,
                    "quads": set(qs), "high": high,
                }]

        out = []
        remaining = set(quads)
        for key in order:
            qs, shift, _high = pair[key]
            if qs <= remaining and len(qs) == 2:
                along_x = key in ("N", "S")
                out.append({
                    "part": "3004", "shift": shift,
                    "rot": rot_id if along_x else rot_to_z,
                    "sx": 2 if along_x else 1, "sz": 1 if along_x else 2,
                    "kind": "box", "slope_low": None, "quads": set(qs), "high": None,
                })
                remaining -= qs
        for q in sorted(remaining):
            out.append({
                "part": "3005", "shift": shift_1[q], "rot": rot_id,
                "sx": 1, "sz": 1, "kind": "box", "slope_low": None,
                "quads": {q}, "high": None,
            })
        return out

    def _cover_layer(self, color, supported, scale, optimize):
        """Brick one horizontal layer.

        LEGO bricks do not clutch to the brick beside them, only to studs
        below. A block with air underneath is buildable only when it is part
        of a longer brick that also covers a supported block. Each piece is a
        real length (1, 2, 3, 4, 6, or 8 studs; at 2x, 1 to 4 blocks).
        """
        length, width = color.shape
        lengths = self._RUN_LEN_2X if scale == 2 else self._RUN_LEN_1X
        used = np.zeros_like(color, dtype=bool)

        def inside(z, x):
            return 0 <= z < length and 0 <= x < width

        def same(z, x, c):
            return inside(z, x) and int(color[z, x]) == c

        bricks = []

        def commit(cells, floating, anchored):
            xs = [x for _z, x in cells]
            zs = [z for z, _x in cells]
            bricks.append({
                "cells": cells,
                "color": int(color[cells[0][0], cells[0][1]]),
                "floating": floating,
                "anchored": anchored,
                "x": min(xs), "z": min(zs),
                "dx": max(xs) - min(xs) + 1,
                "dz": max(zs) - min(zs) + 1,
                "along": "z" if max(xs) == min(xs) and max(zs) != min(zs) else "x",
            })
            for z, x in cells:
                used[z, x] = True

        unsupported = []
        for z in range(length):
            for x in range(width):
                if int(color[z, x]) < 0 or supported[z, x]:
                    continue
                best = 99
                c = int(color[z, x])
                for dz, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    cz, cx = z, x
                    for step in range(1, 9):
                        cz += dz
                        cx += dx
                        if not same(cz, cx, c):
                            break
                        if supported[cz, cx] and not used[cz, cx]:
                            best = min(best, step)
                            break
                unsupported.append((best, z, x))
        # Farther overhangs first, so a long brick is reserved for them
        # instead of a nearer block using up the anchor.
        unsupported.sort(key=lambda item: (-item[0], item[1], item[2]))

        for _dist, z, x in unsupported:
            if used[z, x] or int(color[z, x]) < 0:
                continue
            c = int(color[z, x])
            best = None
            for axis in ("x", "z"):
                dirs = ((0, 1), (0, -1)) if axis == "x" else ((1, 0), (-1, 0))
                neg = []
                cz, cx = z + dirs[1][0], x + dirs[1][1]
                while same(cz, cx, c) and not used[cz, cx]:
                    neg.append((cz, cx))
                    cz += dirs[1][0]
                    cx += dirs[1][1]
                line = list(reversed(neg)) + [(z, x)]
                cz, cx = z + dirs[0][0], x + dirs[0][1]
                while same(cz, cx, c) and not used[cz, cx]:
                    line.append((cz, cx))
                    cz += dirs[0][0]
                    cx += dirs[0][1]
                idx = len(neg)
                n = len(line)
                for L in lengths:
                    if L > n:
                        continue
                    for start in range(0, n - L + 1):
                        if not (start <= idx < start + L):
                            continue
                        window = line[start:start + L]
                        n_sup = sum(1 for cz, cx in window if supported[cz, cx])
                        if n_sup < 1:
                            continue
                        n_over = L - n_sup
                        # Cover as many loose blocks as this brick can, then prefer the shorter piece.
                        rank = (n_over, -L)
                        if best is None or rank > best[0]:
                            best = (rank, window)
            if best is None:
                continue
            window = best[1]
            n_sup = sum(1 for cz, cx in window if supported[cz, cx])
            commit(window, floating=False, anchored=n_sup < len(window))

        def greedy(only_floating):
            for z in range(length):
                x = 0
                while x < width:
                    if used[z, x] or int(color[z, x]) < 0:
                        x += 1
                        continue
                    if bool(supported[z, x]) == only_floating:
                        x += 1
                        continue
                    c = int(color[z, x])
                    run = []
                    while x + len(run) < width and not used[z, x + len(run)] and int(color[z, x + len(run)]) == c:
                        if bool(supported[z, x + len(run)]) == only_floating:
                            break
                        run.append((z, x + len(run)))
                    if not run:
                        x += 1
                        continue
                    left = run
                    while left:
                        take = 1
                        for L in sorted(lengths, reverse=True):
                            if L <= len(left):
                                take = L
                                break
                        commit(left[:take], floating=only_floating, anchored=False)
                        left = left[take:]

        greedy(only_floating=True)
        if optimize or scale == 2:
            # 2x already uses a 2x2 brick per block; merging just makes longer ones.
            # At 1x, merging is the Optimize option.
            if optimize:
                greedy(only_floating=False)
            else:
                for z in range(length):
                    for x in range(width):
                        if not used[z, x] and int(color[z, x]) >= 0:
                            commit([(z, x)], floating=False, anchored=False)
        else:
            for z in range(length):
                for x in range(width):
                    if not used[z, x] and int(color[z, x]) >= 0:
                        commit([(z, x)], floating=False, anchored=False)

        if optimize and scale == 1:
            bricks = self._pair_bricks(bricks)
        return bricks

    def _pair_bricks(self, bricks):
        """Join two identical side-by-side runs into one 2-wide brick."""
        buckets = {}
        for i, b in enumerate(bricks):
            if b["along"] == "x" and b["dz"] == 1 and not b["floating"]:
                buckets.setdefault((b["z"], b["x"], b["dx"], b["color"]), []).append(i)
        used = set()
        out = []
        for i, b in enumerate(bricks):
            if i in used:
                continue
            partner = None
            if b["along"] == "x" and b["dz"] == 1 and not b["floating"]:
                ids = buckets.get((b["z"] + 1, b["x"], b["dx"], b["color"]), [])
                for j in ids:
                    if j not in used and j != i:
                        partner = j
                        break
            if partner is None:
                out.append(b)
                continue
            used.add(i)
            used.add(partner)
            other = bricks[partner]
            merged = dict(b)
            merged["cells"] = b["cells"] + other["cells"]
            merged["dz"] = 2
            merged["anchored"] = b["anchored"] or other["anchored"]
            merged["paired"] = True
            out.append(merged)
        return out

    def _lookup_cell(self, schematic_data, x, y, z):
        """Return (color, special_info or None) for one schematic cell. None color means skip."""
        blocks = schematic_data["blocks"]
        width = schematic_data["width"]
        length = schematic_data["length"]
        block_id = int(blocks[y, z, x])
        if block_id == 0:
            return None, None
        names = schematic_data.get("block_names")
        if names:
            index = y * length * width + z * width + x
            if index >= len(names):
                return None, None
            block_name = names[index]
            base = block_name.replace("minecraft:", "")
            if "[" in base:
                base = base.split("[")[0]
            if base == "air" or base.endswith("_air"):
                return None, None
            color = self._get_color_from_block_name(block_name)
            if color < 0 or self._is_skip_block(block_name):
                return None, None
            return color, self._get_special_part_info(block_name)
        data_value = 0
        if schematic_data.get("data") is not None:
            index = y * length * width + z * width + x
            if index < len(schematic_data["data"]):
                data_value = int(schematic_data["data"][index])
        _brick, color = self.get_brick_info(block_id, data_value)
        special = None
        if block_id in self._OLD_STAIR_IDS:
            special = {
                "type": "stair",
                "facing": self._OLD_STAIR_FACING.get(data_value & 3, "east"),
                "half": "top" if (data_value & 4) else "bottom",
                "shape": "",
            }
        elif block_id in self._OLD_SLAB_IDS:
            special = {
                "type": "slab",
                "slab_type": "top" if (data_value & 8) else "bottom",
            }
        return color, special

    def build_model(self, schematic_data: Dict, optimize: bool = False, scale: int = 1, progress=None) -> Dict:
        """Plan assemblable LEGO parts and the matching print grid.

        Scale 2 is the one that can show stairs: each block is 2 studs wide
        and 2 bricks tall. A bottom stair is a full brick on the bottom and
        either a slope or a flat step on the high half. Overhangs become one
        brick with the neighbor that holds them up.
        """
        def log(msg):
            print(msg)
            if progress:
                progress(msg)

        if scale not in (1, 2):
            scale = 1
        width = schematic_data["width"]
        height = schematic_data["height"]
        length = schematic_data["length"]
        log(f"Reading {width}x{height}x{length} blocks")

        # specials[(y,z,x)] = info dict. Missing key = air/skip.
        # kind is stair / slab / carpet / full.
        specials = {}
        colors = {}
        for y in range(height):
            for z in range(length):
                for x in range(width):
                    color, info = self._lookup_cell(schematic_data, x, y, z)
                    if color is None:
                        continue
                    colors[(y, z, x)] = color
                    specials[(y, z, x)] = info

        stair_at = {}
        for (y, z, x), info in specials.items():
            if info and info.get("type") == "stair":
                stair_at[(y, z, x)] = (info.get("facing", "north"), info.get("half", "bottom"))
        for (y, z, x), info in list(specials.items()):
            if not info or info.get("type") != "stair":
                continue
            if not info.get("shape"):
                info["shape"] = self._infer_stair_shape(
                    info.get("facing", "north"), info.get("half", "bottom"),
                    x, y, z, stair_at, width, length)

        lower = np.full((height, length, width), -1, dtype=np.int16)
        upper = np.full((height, length, width), -1, dtype=np.int16)
        # True where a partial piece (step, not a full cell) occupies that half.
        lower_partial = np.zeros((height, length, width), dtype=bool)
        upper_partial = np.zeros((height, length, width), dtype=bool)
        touches_above = np.zeros((height, length, width), dtype=bool)
        partials = []
        plates = []

        above_cache = {}

        def above_needs_studs(x, y, z):
            """True when the cell above rests on this cell's top studs."""
            if y + 1 >= height:
                return False
            key = (x, y + 1, z)
            if key in above_cache:
                return above_cache[key]
            info = specials.get((y + 1, z, x))
            if (y + 1, z, x) not in colors:
                above_cache[key] = False
                return False
            if info is None or info.get("type") == "full":
                above_cache[key] = True
                return True
            if info.get("type") == "slab" and info.get("slab_type") == "top":
                above_cache[key] = False
                return False
            # Stairs, bottom slabs, and carpet all have a piece at the bottom of their cell.
            above_cache[key] = True
            return True

        for (y, z, x), color in colors.items():
            info = specials.get((y, z, x))
            kind = info.get("type") if info else "full"
            if scale == 1:
                # One stud is too small for a step that still clutches. Stairs are
                # full bricks here so the build holds together. Slabs stay plates.
                if kind == "slab":
                    plates.append({
                        "x": x, "y": y, "z": z, "color": color,
                        "top": info.get("slab_type") == "top", "carpet": False,
                    })
                    if info.get("slab_type") == "top":
                        touches_above[y, z, x] = True
                elif kind == "carpet":
                    plates.append({"x": x, "y": y, "z": z, "color": color, "top": False, "carpet": True})
                else:
                    lower[y, z, x] = color
                    touches_above[y, z, x] = True
                continue

            # Scale 2. A full block is two bricks. A bottom slab is the lower brick only.
            if kind == "carpet":
                plates.append({"x": x, "y": y, "z": z, "color": color, "top": False, "carpet": True})
                continue
            if kind == "slab":
                if info.get("slab_type") == "top":
                    upper[y, z, x] = color
                    touches_above[y, z, x] = True
                else:
                    lower[y, z, x] = color
                continue
            if kind == "stair":
                facing = info.get("facing", "north")
                half = info.get("half", "bottom")
                shape = info.get("shape") or "straight"
                quads = self._high_quads(facing, shape)
                use_slope = (
                    half == "bottom" and shape == "straight"
                    and not above_needs_studs(x, y, z)
                )
                pieces = self._quad_parts(quads, facing, use_slope)
                if half == "bottom":
                    lower[y, z, x] = color
                    upper_partial[y, z, x] = True
                    touches_above[y, z, x] = True
                    for piece in pieces:
                        piece.update({"x": x, "y": y, "z": z, "color": color, "sub": "upper"})
                        partials.append(piece)
                else:
                    upper[y, z, x] = color
                    lower_partial[y, z, x] = True
                    touches_above[y, z, x] = True
                    # Upside-down: flat bricks on the bottom so the full brick can sit on them.
                    for piece in self._quad_parts(quads, facing, False):
                        piece.update({"x": x, "y": y, "z": z, "color": color, "sub": "lower"})
                        partials.append(piece)
                continue
            lower[y, z, x] = color
            upper[y, z, x] = color
            touches_above[y, z, x] = True

        # A column's lowest block sits on a baseplate, unless it is a lip
        # sticking out from a taller neighbor. Those lips are overhangs and
        # have to be part of a brick that reaches back to the wall.
        has_mass = (lower >= 0) | (upper >= 0) | lower_partial | upper_partial
        for plate in plates:
            has_mass[plate["y"], plate["z"], plate["x"]] = True
        lowest = np.full((length, width), -1, dtype=np.int16)
        for y in range(height):
            found = has_mass[y] & (lowest < 0)
            lowest[found] = y
        overhang = np.zeros((height, length, width), dtype=bool)
        seeds = []
        for z in range(length):
            for x in range(width):
                y = int(lowest[z, x])
                if y < 0:
                    continue
                for dz, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nz, nx = z + dz, x + dx
                    if 0 <= nz < length and 0 <= nx < width and 0 <= int(lowest[nz, nx]) < y:
                        overhang[y, z, x] = True
                        seeds.append((y, z, x))
                        break
        stack = seeds
        while stack:
            y, z, x = stack.pop()
            for dz, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nz, nx = z + dz, x + dx
                if not (0 <= nz < length and 0 <= nx < width):
                    continue
                if int(lowest[nz, nx]) == y and not overhang[y, nz, nx]:
                    overhang[y, nz, nx] = True
                    stack.append((y, nz, nx))

        def on_foundation(y, z, x):
            return int(lowest[z, x]) == y and not overhang[y, z, x]

        log("Placing bricks so overhangs stay attached")
        parts = []
        anchored = 0
        floating = 0

        def add_brick(spec, y, sub):
            nonlocal anchored, floating
            if spec["anchored"]:
                anchored += 1
            if spec["floating"]:
                floating += 1
            cells = spec["cells"]
            cx = sum(x for _z, x in cells) / len(cells)
            cz = sum(z for z, _x in cells) / len(cells)
            stud = 20 * scale
            lx = (cx - width / 2.0) * stud
            lz = (cz - length / 2.0) * stud
            ly = -y * (24 * scale)
            if scale == 2 and sub == "lower":
                ly += 24
            n = spec["dx"] if spec["along"] == "x" else spec["dz"]
            rot = (1, 0, 0, 0, 1, 0, 0, 0, 1)
            rot_to_z = (0, 0, -1, 0, 1, 0, 1, 0, 0)
            if scale == 2:
                part = self._PART_2X[n]
                if spec["along"] == "z":
                    rot = rot_to_z
            elif spec.get("paired") and spec["dx"] == 1:
                part = "3004"
                rot = rot_to_z
            elif spec.get("paired"):
                part = self.brick_sizes[(2, spec["dx"])]
            else:
                part = self._PART_1X[n]
                if spec["along"] == "z":
                    rot = rot_to_z
            parts.append({
                "part": part, "color": spec["color"], "x": lx, "y": ly, "z": lz,
                "rot": rot, "kind": "box", "sub": sub, "y_mc": y,
                "cells": [(y, z, x) for z, x in cells],
                "floating": spec["floating"], "anchored": spec["anchored"],
                "h_ldu": 24,
            })

        for y in range(height):
            lower_sup = np.zeros((length, width), dtype=bool)
            upper_sup = np.zeros((length, width), dtype=bool)
            for z in range(length):
                for x in range(width):
                    held_from_below = y > 0 and bool(touches_above[y - 1, z, x])
                    if int(lower[y, z, x]) >= 0:
                        lower_sup[z, x] = on_foundation(y, z, x) or held_from_below
                    if int(upper[y, z, x]) >= 0:
                        # The upper brick clutches to the lower brick of the same block.
                        upper_sup[z, x] = int(lower[y, z, x]) >= 0 or bool(lower_partial[y, z, x])
            if scale == 1:
                for spec in self._cover_layer(lower[y], lower_sup, scale, optimize):
                    add_brick(spec, y, "full")
            else:
                for spec in self._cover_layer(lower[y], lower_sup, scale, optimize):
                    add_brick(spec, y, "lower")
                for spec in self._cover_layer(upper[y], upper_sup, scale, optimize):
                    add_brick(spec, y, "upper")

        for piece in partials:
            y, x, z = piece["y"], piece["x"], piece["z"]
            if piece["sub"] == "upper":
                held = int(lower[y, z, x]) >= 0 or bool(lower_partial[y, z, x])
            else:
                held = on_foundation(y, z, x) or (y > 0 and bool(touches_above[y - 1, z, x]))
            if not held:
                floating += 1
            stud = 20 * scale
            lx = (x - width / 2.0) * stud + piece["shift"][0]
            lz = (z - length / 2.0) * stud + piece["shift"][1]
            ly = -y * (24 * scale)
            if piece["sub"] == "lower":
                ly += 24
            parts.append({
                "part": piece["part"], "color": piece["color"],
                "x": lx, "y": ly, "z": lz, "rot": piece["rot"],
                "kind": piece["kind"], "sub": piece["sub"], "y_mc": y,
                "cells": [(y, z, x)], "floating": not held, "anchored": False,
                "h_ldu": 24, "quads": piece["quads"], "high": piece.get("high"),
                "sx": piece["sx"], "sz": piece["sz"],
            })

        for plate in plates:
            x, y, z = plate["x"], plate["y"], plate["z"]
            held = on_foundation(y, z, x) or (y > 0 and bool(touches_above[y - 1, z, x]))
            # A top plate sits in the top of the cell, so it does not reach a brick below.
            if plate["top"]:
                held = False
            if not held:
                floating += 1
            stud = 20 * scale
            lx = (x - width / 2.0) * stud
            lz = (z - length / 2.0) * stud
            ly = -y * (24 * scale)
            if scale == 1:
                ly += 0 if plate["top"] else 16
                part = "3024"
            else:
                # 2x2 plate at the bottom of the 2-brick cell.
                ly += 40
                part = "3022"
            parts.append({
                "part": part, "color": plate["color"], "x": lx, "y": ly, "z": lz,
                "rot": (1, 0, 0, 0, 1, 0, 0, 0, 1), "kind": "plate",
                "sub": "plate", "y_mc": y, "cells": [(y, z, x)],
                "floating": not held, "anchored": False, "h_ldu": 8,
                "plate_top": plate["top"],
            })

        warnings = []
        if anchored:
            warnings.append(
                f"{anchored} overhanging bricks were joined to a neighbor that holds them up, so they can be snapped on."
            )
        if floating:
            warnings.append(
                f"{floating} pieces have nothing to attach to. They are still in the model, as their own loose pieces."
            )
        n_slope = sum(1 for p in parts if p["part"] == "3040")
        n_stair_bits = sum(1 for p in parts if p.get("quads"))
        for line in warnings:
            log(line)
        log(f"{len(parts)} LEGO pieces, {n_slope} slope bricks, {n_stair_bits} stair pieces")

        ldraw = self._parts_to_ldraw(parts, scale, optimize, warnings)
        plates_per = 3 * scale
        solid = np.zeros((height * plates_per, length * scale, width * scale), dtype=bool)
        # -1 is air. A filled cell keeps the LDraw color so the Bambu file can split by filament.
        paint = np.full(solid.shape, -1, dtype=np.int16)
        nostud = set()
        wedges = []
        self._fill_print_grid(parts, solid, nostud, wedges, scale, paint)
        return {
            "parts": parts,
            "ldraw": ldraw,
            "warnings": warnings,
            "solid": solid,
            "paint": paint,
            "nostud": nostud,
            "wedges": wedges,
            "scale": scale,
            "stats": {
                "bricks": len(parts),
                "anchored": anchored,
                "floating": floating,
                "slopes": n_slope,
            },
        }

    def _parts_to_ldraw(self, parts, scale, optimize, warnings) -> str:
        lines = [
            "0 Jonathan Rothberg's MineCraft to LEGO converter",
            "0 Name: Converted from Minecraft",
            "0 Author: Jonathan Rothberg",
        ]
        if optimize:
            lines.append("0 Optimized: Yes (merged bricks)")
        if scale > 1:
            lines.append(f"0 Scale: {scale}x (each MC block = {scale} studs and {scale} bricks tall)")
        lines.append("0 Stairs: stepped bricks; open straight stairs use slope 3040")
        lines.append("0 Overhangs: one brick with the neighbor that supports them")
        for note in warnings:
            lines.append(f"0 Note: {note}")
        lines.append("")
        for p in parts:
            rot = " ".join(str(int(v)) for v in p["rot"])
            lines.append(
                f"1 {p['color']} {p['x']:.2f} {p['y']:.2f} {p['z']:.2f} {rot} {p['part']}.dat"
            )
        return "\n".join(lines) + "\n"

    def _fill_print_grid(self, parts, solid, nostud, wedges, scale, paint=None):
        """Fill a plate-and-stud grid from the same parts the LDraw file uses.

        One plate is 3.2 mm, one stud is 8 mm. A slope is not a box: it is
        recorded as a wedge so the printed stair actually slopes.
        paint stores the LDraw color of each filled cell for the Bambu file.
        """
        ny, nz, nx = solid.shape
        plates_per = 3 * scale
        qstud = {"NW": (0, 0), "NE": (1, 0), "SW": (0, 1), "SE": (1, 1)}

        def fill_studs(ix, iz, iy0, iy1, color):
            for iy in range(iy0, iy1):
                if 0 <= iy < ny and 0 <= iz < nz and 0 <= ix < nx:
                    solid[iy, iz, ix] = True
                    if paint is not None:
                        paint[iy, iz, ix] = color

        for p in parts:
            y = p["y_mc"]
            if p["kind"] == "slope":
                ixs, izs = [], []
                for q in p["quads"]:
                    dx, dz = qstud[q]
                    # Slopes are only emitted at 2x, where a quadrant is one stud.
                    ixs.append(p["cells"][0][2] * scale + dx)
                    izs.append(p["cells"][0][1] * scale + dz)
                for ix, iz in zip(ixs, izs):
                    # The slope covers the studs of the brick underneath it.
                    # Highest solid plate under the slope is the top plate of the lower brick.
                    nostud.add((ix, iz, y * plates_per + 2))
                wedges.append({
                    "x0": min(ixs) * 8.0,
                    "x1": (max(ixs) + 1) * 8.0,
                    "z0": min(izs) * 8.0,
                    "z1": (max(izs) + 1) * 8.0,
                    "y_base": (y * plates_per + 3) * 3.2,
                    "high": p.get("high") or "north",
                    "color": p["color"],
                })
                continue
            if p["kind"] == "plate":
                for y_mc, z, x in p["cells"]:
                    iy = y_mc * plates_per + (plates_per - 1 if p.get("plate_top") else 0)
                    for dz in range(scale):
                        for dx in range(scale):
                            fill_studs(x * scale + dx, z * scale + dz, iy, iy + 1, p["color"])
                continue
            if p.get("quads"):
                iy0 = y * plates_per + (3 if p["sub"] == "upper" else 0)
                for q in p["quads"]:
                    dx, dz = qstud[q]
                    x = p["cells"][0][2]
                    z = p["cells"][0][1]
                    fill_studs(x * scale + dx, z * scale + dz, iy0, iy0 + 3, p["color"])
                continue
            # Full bricks: 3 plates per brick layer, every stud of each cell.
            if scale == 1 or p["sub"] == "full":
                iy0 = y * plates_per
            elif p["sub"] == "lower":
                iy0 = y * plates_per
            else:
                iy0 = y * plates_per + 3
            for y_mc, z, x in p["cells"]:
                for dz in range(scale):
                    for dx in range(scale):
                        fill_studs(x * scale + dx, z * scale + dz, iy0, iy0 + 3, p["color"])

    def write_stl(self, path: str, model: Dict) -> int:
        """Write a binary STL in millimeters, Y up, base on the bed.

        The body is one watertight shell. Studs and slopes overlap it by
        0.2 mm so a slicer joins them into a single printable solid.
        """
        solid = model["solid"]
        nostud = model["nostud"]
        wedges = model["wedges"]
        tris = []
        self._mesh_voxels(solid, tris)
        self._mesh_studs(solid, nostud, tris)
        self._mesh_wedges(wedges, tris)
        self._mesh_base(solid, tris)
        if not tris:
            raise RuntimeError("STL is empty — the schematic had no solid blocks")
        volume = 0.0
        for a, b, c in tris:
            volume += float(np.dot(a, np.cross(b, c)))
        if volume < 0:
            tris = [(a, c, b) for a, b, c in tris]
        min_y = min(p[1] for tri in tris for p in tri)
        shifted = []
        for a, b, c in tris:
            shifted.append(tuple((p[0], p[1] - min_y, p[2]) for p in (a, b, c)))
        self._write_binary_stl(path, shifted)
        print(f"Saved STL: {path} ({len(shifted)} triangles)")
        return len(shifted)

    def _mesh_voxels(self, solid, tris):
        """One quad per exposed plate face.

        Merging those quads into bigger rectangles makes T-junctions where a
        long edge meets two short ones, and slicers treat that as a hole.
        Faces are found with numpy so a full schematic stays quick.
        """
        if solid.size == 0 or not solid.any():
            return
        ny, nz, nx = solid.shape
        sy, sz, sx = 3.2, 8.0, 8.0

        def quad(p0, p1, p2, p3):
            tris.append((p0, p1, p2))
            tris.append((p0, p2, p3))

        def emit(iys, izs, ixs, face):
            for iy, iz, ix in zip(iys.tolist(), izs.tolist(), ixs.tolist()):
                x0, x1 = ix * sx, (ix + 1) * sx
                z0, z1 = iz * sz, (iz + 1) * sz
                y0, y1 = iy * sy, (iy + 1) * sy
                if face == "+y":
                    quad((x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0))
                elif face == "-y":
                    quad((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1))
                elif face == "+x":
                    quad((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1))
                elif face == "-x":
                    quad((x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0))
                elif face == "+z":
                    quad((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))
                else:
                    quad((x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0))

        # +Y: the voxel below an empty cell, plus the very top layer.
        emit(*np.where(solid[:-1] & ~solid[1:]), "+y")
        cap_z, cap_x = np.where(solid[-1])
        emit(np.full(cap_z.shape, ny - 1), cap_z, cap_x, "+y")
        # -Y: voxel iy>=1 with air under it. where() on the sliced array is iy-1.
        below_y, below_z, below_x = np.where(solid[1:] & ~solid[:-1])
        emit(below_y + 1, below_z, below_x, "-y")
        bot_z, bot_x = np.where(solid[0])
        emit(np.zeros(bot_z.shape, dtype=int), bot_z, bot_x, "-y")
        # +X / -X. A slice along X shifts the index of the far side by 1.
        # The grid edge is always exposed, so the first and last columns are capped.
        emit(*np.where(solid[:, :, :-1] & ~solid[:, :, 1:]), "+x")
        edge_y, edge_z = np.where(solid[:, :, -1])
        emit(edge_y, edge_z, np.full(edge_y.shape, nx - 1), "+x")
        neg_y, neg_z, neg_x = np.where(solid[:, :, 1:] & ~solid[:, :, :-1])
        emit(neg_y, neg_z, neg_x + 1, "-x")
        edge_y, edge_z = np.where(solid[:, :, 0])
        emit(edge_y, edge_z, np.zeros(edge_y.shape, dtype=int), "-x")
        emit(*np.where(solid[:, :-1, :] & ~solid[:, 1:, :]), "+z")
        edge_y, edge_x = np.where(solid[:, -1, :])
        emit(edge_y, np.full(edge_y.shape, nz - 1), edge_x, "+z")
        neg_y, neg_z, neg_x = np.where(solid[:, 1:, :] & ~solid[:, :-1, :])
        emit(neg_y, neg_z + 1, neg_x, "-z")
        edge_y, edge_x = np.where(solid[:, 0, :])
        emit(edge_y, np.zeros(edge_y.shape, dtype=int), edge_x, "-z")

    def _mesh_studs(self, solid, nostud, tris):
        if solid.size == 0 or not solid.any():
            return
        # Highest filled plate in each stud column.
        top = solid.shape[0] - 1 - np.argmax(solid[::-1], axis=0)
        has = solid.any(axis=0)
        izs, ixs = np.where(has)
        for iz, ix in zip(izs.tolist(), ixs.tolist()):
            iy = int(top[iz, ix])
            if (ix, iz, iy) in nostud:
                continue
            self._add_stud(tris, ix * 8.0 + 4.0, iz * 8.0 + 4.0, (iy + 1) * 3.2)

    def _add_stud(self, tris, cx, cz, yb):
        radius = 2.4
        height = 1.8
        y0 = yb - 0.2
        y1 = yb + height
        n = 8
        bottom, top = [], []
        for i in range(n):
            ang = 2.0 * math.pi * i / n
            bottom.append((cx + radius * math.cos(ang), y0, cz + radius * math.sin(ang)))
            top.append((cx + radius * math.cos(ang), y1, cz + radius * math.sin(ang)))
        center_b = (cx, y0, cz)
        center_t = (cx, y1, cz)
        for i in range(n):
            j = (i + 1) % n
            tris.append((bottom[i], top[i], top[j]))
            tris.append((bottom[i], top[j], bottom[j]))
            tris.append((center_t, top[i], top[j]))
            tris.append((center_b, bottom[j], bottom[i]))

    def _mesh_wedges(self, wedges, tris):
        def quad(p0, p1, p2, p3):
            tris.append((p0, p1, p2))
            tris.append((p0, p2, p3))

        for w in wedges:
            x0, x1 = w["x0"], w["x1"]
            z0, z1 = w["z0"], w["z1"]
            yb = w["y_base"] - 0.2
            yh = w["y_base"] + 9.6
            high = w["high"]
            # Bottom overlaps the brick under the slope. High edge is full
            # brick height; the low edge meets the step.
            if high == "north":
                h0, h1 = (x0, yh, z0), (x1, yh, z0)
                b0, b1 = (x0, yb, z0), (x1, yb, z0)
                l0, l1 = (x0, yb, z1), (x1, yb, z1)
            elif high == "south":
                h0, h1 = (x0, yh, z1), (x1, yh, z1)
                b0, b1 = (x0, yb, z1), (x1, yb, z1)
                l0, l1 = (x0, yb, z0), (x1, yb, z0)
            elif high == "west":
                h0, h1 = (x0, yh, z0), (x0, yh, z1)
                b0, b1 = (x0, yb, z0), (x0, yb, z1)
                l0, l1 = (x1, yb, z0), (x1, yb, z1)
            else:
                h0, h1 = (x1, yh, z0), (x1, yh, z1)
                b0, b1 = (x1, yb, z0), (x1, yb, z1)
                l0, l1 = (x0, yb, z0), (x0, yb, z1)
            quad(b0, b1, l1, l0)
            quad(b0, h0, h1, b1)
            quad(h0, l0, l1, h1)
            tris.append((b0, l0, h0))
            tris.append((b1, h1, l1))

    def _mesh_base(self, solid, tris):
        """A flat plate under the lowest blocks, so the print has a bed to sit on."""
        ny, nz, nx = solid.shape
        min_iy = None
        xs, zs = [], []
        for iy in range(ny):
            if solid[iy].any():
                min_iy = iy
                for iz in range(nz):
                    for ix in range(nx):
                        if solid[iy, iz, ix]:
                            xs.append(ix)
                            zs.append(iz)
                break
        if min_iy is None:
            return
        x0, x1 = min(xs) * 8.0, (max(xs) + 1) * 8.0
        z0, z1 = min(zs) * 8.0, (max(zs) + 1) * 8.0
        y1 = min_iy * 3.2 + 0.15
        y0 = min_iy * 3.2 - 3.2

        def quad(p0, p1, p2, p3):
            tris.append((p0, p1, p2))
            tris.append((p0, p2, p3))

        quad((x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0))
        quad((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1))
        quad((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1))
        quad((x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0))
        quad((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))
        quad((x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0))

    def _write_binary_stl(self, path, tris):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(b"Minecraft to LEGO".ljust(80, b"\0"))
            handle.write(struct.pack("<I", len(tris)))
            for a, b, c in tris:
                normal = np.cross(np.subtract(b, a), np.subtract(c, a))
                length = float(np.linalg.norm(normal))
                if length > 0:
                    normal = normal / length
                else:
                    normal = np.zeros(3)
                handle.write(struct.pack("<3f", float(normal[0]), float(normal[1]), float(normal[2])))
                for p in (a, b, c):
                    handle.write(struct.pack("<3f", float(p[0]), float(p[1]), float(p[2])))
                handle.write(struct.pack("<H", 0))

    def _color_rgb(self, color_id):
        item = LDRAW_COLORS.get(int(color_id))
        if item:
            return item[1], item[2], item[3]
        return 155, 161, 157

    def _color_name(self, color_id):
        item = LDRAW_COLORS.get(int(color_id))
        return item[0] if item else f"Color {int(color_id)}"

    def _filament_groups(self, paint, wedges, max_colors):
        """Keep the most common brick colors, up to max_colors. The rest join the nearest one."""
        counts = {}
        used = paint[paint >= 0]
        if used.size:
            values, amounts = np.unique(used, return_counts=True)
            for value, amount in zip(values.tolist(), amounts.tolist()):
                counts[int(value)] = counts.get(int(value), 0) + int(amount)
        for wedge in wedges:
            counts[int(wedge["color"])] = counts.get(int(wedge["color"]), 0) + 1
        if not counts:
            return []
        ranked = sorted(counts, key=lambda color: counts[color], reverse=True)
        anchors = ranked[:max_colors]

        def nearest(color):
            cr, cg, cb = self._color_rgb(color)
            return min(anchors, key=lambda anchor: sum(
                (a - b) ** 2 for a, b in zip((cr, cg, cb), self._color_rgb(anchor))
            ))

        groups = []
        for anchor in anchors:
            members = [color for color in ranked if nearest(color) == anchor]
            groups.append((anchor, members, sum(counts[color] for color in members)))
        return groups

    def _mesh_studs_split(self, solid, nostud, paint):
        """Studs on the exposed top only, filed under that cell's color."""
        buckets = {}
        if solid.size == 0 or not solid.any():
            return buckets
        top = solid.shape[0] - 1 - np.argmax(solid[::-1], axis=0)
        has = solid.any(axis=0)
        izs, ixs = np.where(has)
        for iz, ix in zip(izs.tolist(), ixs.tolist()):
            iy = int(top[iz, ix])
            if (ix, iz, iy) in nostud:
                continue
            color = int(paint[iy, iz, ix])
            dest = buckets.setdefault(color, [])
            self._add_stud(dest, ix * 8.0 + 4.0, iz * 8.0 + 4.0, (iy + 1) * 3.2)
        return buckets

    def _base_color(self, paint):
        for iy in range(paint.shape[0]):
            used = paint[iy]
            used = used[used >= 0]
            if used.size:
                values, amounts = np.unique(used, return_counts=True)
                return int(values[int(np.argmax(amounts))])
        return 7

    def _orient_closed(self, tris):
        if not tris:
            return tris
        volume = 0.0
        for a, b, c in tris:
            volume += float(np.dot(a, np.cross(b, c)))
        if volume < 0:
            return [(a, c, b) for a, b, c in tris]
        return tris

    def write_bambu(self, path: str, model: Dict, max_colors: int = 4):
        """Write one Bambu Studio 3MF. Each filament is an object in the same place.

        An STL cannot carry color, and separate STL files land apart on the plate.
        This file keeps the colors stacked and assigns each group to a filament slot.
        """
        max_colors = max(1, min(8, int(max_colors)))
        paint = model["paint"]
        groups = self._filament_groups(paint, model["wedges"], max_colors)
        if not groups:
            raise RuntimeError("Bambu file is empty — the schematic had no solid blocks")
        studs = self._mesh_studs_split(model["solid"], model["nostud"], paint)
        base_tris = []
        self._mesh_base(model["solid"], base_tris)
        base_color = self._base_color(paint)
        objects = []
        notes = []
        for slot, (anchor, members, _count) in enumerate(groups, start=1):
            member_set = set(members)
            mask = np.isin(paint, list(member_set))
            tris = []
            self._mesh_voxels(mask, tris)
            for color in member_set:
                tris.extend(studs.get(color, []))
            wedges = [wedge for wedge in model["wedges"] if int(wedge["color"]) in member_set]
            self._mesh_wedges(wedges, tris)
            if base_color in member_set:
                tris.extend(base_tris)
            tris = self._orient_closed(tris)
            if not tris:
                continue
            name = self._color_name(anchor)
            also = [self._color_name(color) for color in members if color != anchor]
            if also:
                notes.append(f"Filament {slot} {name} — also {', '.join(also)}")
            else:
                notes.append(f"Filament {slot} {name}")
            objects.append({
                "slot": slot,
                "name": f"{slot} {name}",
                "rgb": self._color_rgb(anchor),
                "also": also,
                "tris": tris,
            })
        if not objects:
            raise RuntimeError("Bambu file is empty — the schematic had no solid blocks")
        objects = self._drop_meshes_onto_bed(objects)
        self._write_bambu_3mf(path, objects)
        for note in notes:
            print(note)
        print(f"Saved Bambu 3MF: {path} ({len(objects)} filaments)")
        return notes

    def _rgb_from_name(self, name):
        """'1 Brown' or 'Brown' back to the LDraw red, green, and blue."""
        cleaned = re.sub(r"^\d+\s+", "", name or "").strip()
        for _color_id, (color_name, red, green, blue) in LDRAW_COLORS.items():
            if color_name == cleaned:
                return red, green, blue
        return 155, 161, 157

    def read_bambu(self, path):
        """Read a 3MF this program wrote. Each spool keeps its mesh and suggested color."""
        spools = []
        with zipfile.ZipFile(path) as archive:
            settings = archive.read("Metadata/model_settings.config").decode("utf-8")
            for obj_id, body in re.findall(r'<object id="(\d+)">(.*?)</object>', settings, re.S):
                head = body.split("<part", 1)[0]
                meta = dict(re.findall(r'<metadata key="([^"]+)" value="([^"]*)"', head))
                raw_name = meta.get("name") or f"Spool {obj_id}"
                label = re.sub(r"^\d+\s+", "", raw_name).strip() or raw_name
                rgb_text = meta.get("color_rgb", "")
                parts = rgb_text.split(",")
                if len(parts) == 3:
                    try:
                        rgb = tuple(int(part) for part in parts)
                    except ValueError:
                        rgb = self._rgb_from_name(label)
                else:
                    rgb = self._rgb_from_name(label)
                also = [item.strip() for item in meta.get("color_also", "").split(",") if item.strip()]
                mesh_name = f"3D/Objects/object_{obj_id}.model"
                if mesh_name not in archive.namelist():
                    raise RuntimeError(f"Bambu file is missing {mesh_name}")
                xml = archive.read(mesh_name).decode("utf-8")
                vertices = [
                    (float(x), float(y), float(z))
                    for x, y, z in re.findall(
                        r'x="([\d.eE+-]+)" y="([\d.eE+-]+)" z="([\d.eE+-]+)"', xml
                    )
                ]
                faces = [
                    (int(a), int(b), int(c))
                    for a, b, c in re.findall(r'v1="(\d+)" v2="(\d+)" v3="(\d+)"', xml)
                ]
                spools.append({
                    "label": label,
                    "rgb": rgb,
                    "also": also,
                    "vertices": vertices,
                    "faces": faces,
                })
        if not spools:
            raise RuntimeError("That Bambu file has no color objects")
        return spools

    def plan_spool_groups(self, spools, max_colors):
        """Keep the biggest spool colors, up to max_colors. The others join the nearest color."""
        max_colors = max(1, min(8, int(max_colors)))
        ranked = sorted(spools, key=lambda spool: len(spool["faces"]), reverse=True)
        anchors = ranked[:max_colors]

        def nearest(spool):
            red, green, blue = spool["rgb"]
            return min(anchors, key=lambda anchor: sum(
                (left - right) ** 2
                for left, right in zip((red, green, blue), anchor["rgb"])
            ))

        groups = []
        for anchor in anchors:
            members = [spool for spool in ranked if nearest(spool) is anchor]
            if members:
                groups.append(members)
        return groups

    def save_regrouped_bambu(self, path, spools, max_colors):
        """Write a new 3MF with fewer filaments. Meshes stay in the same place."""
        groups = self.plan_spool_groups(spools, max_colors)
        objects = []
        notes = []
        for slot, members in enumerate(groups, start=1):
            anchor = max(members, key=lambda spool: len(spool["faces"]))
            vertices = []
            faces = []
            offset = 0
            also = []
            for member in members:
                vertices.extend(member["vertices"])
                faces.extend(
                    (a + offset, b + offset, c + offset) for a, b, c in member["faces"]
                )
                offset += len(member["vertices"])
                if member is not anchor:
                    also.append(member["label"])
                also.extend(member.get("also") or [])
            seen = set()
            also_unique = []
            for name in also:
                if name and name != anchor["label"] and name not in seen:
                    seen.add(name)
                    also_unique.append(name)
            if also_unique:
                note = f"Spool {slot}  {anchor['label']} — also {', '.join(also_unique)}"
            else:
                note = f"Spool {slot}  {anchor['label']}"
            notes.append(note)
            objects.append({
                "slot": slot,
                "name": f"{slot} {anchor['label']}",
                "rgb": anchor["rgb"],
                "also": also_unique,
                "vertices": vertices,
                "faces": faces,
            })
        self._write_bambu_3mf(path, objects)
        for note in notes:
            print(note)
        print(f"Saved Bambu 3MF: {path} ({len(objects)} filaments)")
        return notes

    def _drop_meshes_onto_bed(self, objects):
        """Turn Y-up millimeters into Z-up, and use one shift so every color stays stacked."""
        converted = []
        mins = [float("inf"), float("inf"), float("inf")]
        for obj in objects:
            tris = []
            for a, b, c in obj["tris"]:
                pts = []
                for point in (a, b, c):
                    # Y was up. Bambu Studio uses Z up.
                    moved = (point[0], -point[2], point[1])
                    mins[0] = min(mins[0], moved[0])
                    mins[1] = min(mins[1], moved[1])
                    mins[2] = min(mins[2], moved[2])
                    pts.append(moved)
                tris.append(tuple(pts))
            converted.append(tris)
        dropped = []
        for obj, tris in zip(objects, converted):
            shifted = []
            for a, b, c in tris:
                shifted.append(tuple((p[0] - mins[0], p[1] - mins[1], p[2] - mins[2]) for p in (a, b, c)))
            item = dict(obj)
            item["tris"] = shifted
            dropped.append(item)
        return dropped

    def _write_bambu_3mf(self, path, objects):
        """Bambu Studio project 3MF: one mesh per filament, identical placement, slot in model_settings."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        identity = "1 0 0 0 1 0 0 0 1 0 0 0"
        mesh_xml = []
        main_objects = []
        rels = []
        settings = []
        instances = []
        assemble = []
        for index, obj in enumerate(objects, start=1):
            # A regrouped file already has welded vertices. A new export still has triangles.
            if obj.get("faces") is not None:
                vertices, faces = obj["vertices"], obj["faces"]
            else:
                vertices, faces = self._weld_triangles(obj["tris"])
            mesh_xml.append(self._bambu_object_model(index, vertices, faces, obj.get("rgb")))
            main_objects.append(
                f'  <object id="{index}" p:UUID="{index:08d}-61cb-4c03-9d28-80fed5dfa1dc" type="model">\n'
                f'   <components>\n'
                f'    <component p:path="/3D/Objects/object_{index}.model" objectid="1" '
                f'p:UUID="{index:08d}-b206-40ff-9872-83e8017abed1" transform="{identity}"/>\n'
                f'   </components>\n'
                f'  </object>'
            )
            rels.append(
                f' <Relationship Target="/3D/Objects/object_{index}.model" Id="rel-{index}" '
                f'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
            )
            safe = (obj["name"].replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;"))
            red, green, blue = obj.get("rgb") or (155, 161, 157)
            also = ", ".join(obj.get("also") or [])
            also_safe = also.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")
            # color_rgb and color_also let a saved file be opened later and merged into fewer spools.
            settings.append(
                f'  <object id="{index}">\n'
                f'    <metadata key="name" value="{safe}"/>\n'
                f'    <metadata key="extruder" value="{obj["slot"]}"/>\n'
                f'    <metadata key="color_rgb" value="{red},{green},{blue}"/>\n'
                f'    <metadata key="color_also" value="{also_safe}"/>\n'
                f'    <part id="1" subtype="normal_part">\n'
                f'      <metadata key="name" value="{safe}"/>\n'
                f'      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n'
                f'      <metadata key="extruder" value="{obj["slot"]}"/>\n'
                f'      <mesh_stat face_count="{len(faces)}" edges_fixed="0" degenerate_facets="0" '
                f'facets_removed="0" facets_reversed="0" backwards_edges="0"/>\n'
                f'    </part>\n'
                f'  </object>'
            )
            instances.append(
                f'    <model_instance>\n'
                f'      <metadata key="object_id" value="{index}"/>\n'
                f'      <metadata key="instance_id" value="0"/>\n'
                f'      <metadata key="identify_id" value="{1000 + index}"/>\n'
                f'    </model_instance>'
            )
            assemble.append(
                f'   <assemble_item object_id="{index}" instance_id="0" transform="{identity}" offset="0 0 0" />'
            )
        build_items = "\n".join(
            f'  <item objectid="{index}" p:UUID="{index:08d}-b1ec-4553-aec9-835e5b724bb4" '
            f'transform="{identity}" printable="1"/>'
            for index in range(1, len(objects) + 1)
        )
        # Same transform on every item, so the colors stay in one stack.
        model_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<model unit="millimeter" xml:lang="en-US" '
            'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
            'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
            'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">\n'
            ' <metadata name="Application">BambuStudio-02.00.02.01</metadata>\n'
            ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
            ' <resources>\n'
            + "\n".join(main_objects) + "\n"
            ' </resources>\n'
            ' <build p:UUID="2c7c17d8-22b5-4d84-8835-1976022ea369">\n'
            + build_items + "\n"
            ' </build>\n</model>\n'
        )
        settings_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n'
            + "\n".join(settings) + "\n"
            '  <plate>\n'
            '    <metadata key="plater_id" value="1"/>\n'
            '    <metadata key="plater_name" value=""/>\n'
            '    <metadata key="locked" value="false"/>\n'
            '    <metadata key="first_layer_print_sequence" value="1 2 3 4 5 6 7 8"/>\n'
            '    <metadata key="filament_map_mode" value="Auto For Flush"/>\n'
            '    <metadata key="filament_maps" value="1 1 1 1 1 1 1 1"/>\n'
            + "\n".join(instances) + "\n"
            '  </plate>\n'
            '  <assemble>\n'
            + "\n".join(assemble) + "\n"
            '  </assemble>\n</config>\n'
        )
        content_types = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
            ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
            ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
            '</Types>\n'
        )
        root_rels = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
            '</Relationships>\n'
        )
        model_rels = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            + "\n".join(rels) + "\n"
            '</Relationships>\n'
        )
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", content_types)
            archive.writestr("_rels/.rels", root_rels)
            archive.writestr("3D/3dmodel.model", model_xml)
            archive.writestr("3D/_rels/3dmodel.model.rels", model_rels)
            archive.writestr("Metadata/model_settings.config", settings_xml)
            # Without this, Bambu Studio says the config is invalid and drops the spool colors.
            project_settings = self._bambu_project_settings(objects)
            if project_settings:
                archive.writestr("Metadata/project_settings.config", project_settings)
            for index, xml in enumerate(mesh_xml, start=1):
                archive.writestr(f"3D/Objects/object_{index}.model", xml)

    def _weld_triangles(self, tris):
        index = {}
        vertices = []
        faces = []
        for tri in tris:
            ids = []
            for point in tri:
                key = (round(float(point[0]), 4), round(float(point[1]), 4), round(float(point[2]), 4))
                slot = index.get(key)
                if slot is None:
                    slot = len(vertices)
                    index[key] = slot
                    vertices.append(key)
                ids.append(slot)
            if len(set(ids)) == 3:
                faces.append(ids)
        return vertices, faces

    def _bambu_project_settings(self, objects):
        """Printer config from this Mac's Bambu Studio, with the spool colors filled in.

        The app ships an 8-filament H2D project. Reusing it keeps filament_extruder_variant
        and filament_self_index in the shape this Bambu Studio version accepts.
        """
        template = "/Applications/BambuStudio.app/Contents/Resources/calib/pressure_advance/auto_pa_line_dual.3mf"
        if not os.path.isfile(template):
            return None
        with zipfile.ZipFile(template) as archive:
            data = json.loads(archive.read("Metadata/project_settings.config"))
        colours = list(data.get("filament_colour") or [])
        for index, obj in enumerate(objects):
            if index >= len(colours):
                break
            red, green, blue = obj.get("rgb") or (155, 161, 157)
            colours[index] = f"#{int(red):02X}{int(green):02X}{int(blue):02X}"
        for index in range(len(objects), len(colours)):
            colours[index] = "#D0D0D0"
        data["filament_colour"] = colours
        return json.dumps(data, indent=4) + "\n"

    def _bambu_object_model(self, index, vertices, faces, rgb=None):
        verts = "\n".join(
            f'     <vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in vertices
        )
        triangles = "\n".join(
            f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in faces
        )
        materials = ""
        color_attr = ""
        if rgb:
            red, green, blue = rgb
            materials = (
                '  <basematerials id="1">\n'
                f'   <base name="spool" displaycolor="#{int(red):02X}{int(green):02X}{int(blue):02X}"/>\n'
                '  </basematerials>\n'
            )
            color_attr = ' pid="1" pindex="0"'
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<model unit="millimeter" xml:lang="en-US" '
            'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
            'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
            'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">\n'
            ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
            ' <resources>\n'
            + materials
            + f'  <object id="1"{color_attr} p:UUID="{index:08d}-81cb-4c03-9d28-80fed5dfa1dc" type="model">\n'
            '   <mesh>\n    <vertices>\n'
            + verts + "\n    </vertices>\n    <triangles>\n"
            + triangles + "\n    </triangles>\n   </mesh>\n  </object>\n"
            ' </resources>\n</model>\n'
        )

    def convert_to_ldraw(self, schematic_data: Dict, optimize: bool = False, scale: int = 1) -> str:
        """
        Convert schematic data to LDraw format.

        Args:
            schematic_data: Loaded schematic data
            optimize: If True, merge adjacent same-color blocks into larger bricks
            scale: Scale factor (1 = 1 stud per block, 2 = 2 studs per block)

        Returns:
            LDraw format string
        """
        model = self.build_model(schematic_data, optimize=optimize, scale=scale)
        self.last_model = model
        print(f"Converted to {model['stats']['bricks']} Lego bricks")
        return model["ldraw"]

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

    def convert_file(self, input_path: str, output_path: str = None, optimize: bool = False, scale: int = 1, stl_path: str = None, bambu_path: str = None, bambu_colors: int = 4) -> bool:
        """
        Convert a single Minecraft schematic file to LDraw and, optionally, STL.

        Args:
            input_path: Path to input schematic file
            output_path: Path to output LDraw file (auto-generated if None)
            optimize: If True, merge adjacent same-color blocks into larger bricks
            scale: Scale factor (1 = 1 stud per block, 2 = 2 studs per block)
            stl_path: If set, also write a printable STL of the same model
            bambu_path: If set, also write a Bambu Studio 3MF with one object per filament
            bambu_colors: How many filaments to group the brick colors into (1-8)

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

        # One plan feeds both the LEGO file and the printable mesh.
        model = self.build_model(schematic, optimize=optimize, scale=scale)
        self.last_model = model
        self.save_ldraw_file(model["ldraw"], output_path)
        if stl_path:
            self.write_stl(stl_path, model)
        if bambu_path:
            self.write_bambu(bambu_path, model, bambu_colors)
        print(f"Converted to {model['stats']['bricks']} Lego bricks")
        return True

def _edge_problems(tris):
    """A watertight mesh uses every edge exactly twice."""
    from collections import Counter
    counts = Counter()
    for tri in tris:
        pts = [tuple(round(float(v), 3) for v in p) for p in tri]
        for i in range(3):
            edge = tuple(sorted((pts[i], pts[(i + 1) % 3])))
            counts[edge] += 1
    return [n for n in counts.values() if n != 2]

def run_geometry_self_test() -> bool:
    """Build a tiny schematic with a step, an upside-down stair, both corners, and a one-block overhang.

    Checks that the overhang is one brick with the wall, that open stairs slope,
    that a stair under a block stays flat so the block can sit on it, and that
    the STL is a closed mesh.
    """
    width, height, length = 6, 4, 6
    names = ["minecraft:air"] * (width * height * length)
    blocks = np.zeros((height, length, width), dtype=np.int16)

    def put(x, y, z, name):
        names[y * length * width + z * width + x] = name
        blocks[y, z, x] = 1

    # Floor, with a hole under the overhang column (x=2, z=2).
    for z in range(length):
        for x in range(width):
            if (x, z) != (2, 2):
                put(x, 0, z, "minecraft:stone")
    # Wall the overhang and the sticking-out stair attach to.
    for y in (1, 2):
        put(1, y, 2, "minecraft:stone")
        put(5, y, 2, "minecraft:stone")
    put(2, 2, 2, "minecraft:stone")  # one-block overhang, air below
    put(5, 2, 3, "minecraft:stone_stairs[facing=south,half=bottom,shape=straight]")
    put(4, 1, 1, "minecraft:oak_stairs[facing=north,half=bottom,shape=straight]")
    put(4, 1, 2, "minecraft:oak_stairs[facing=north,half=bottom,shape=straight]")
    put(4, 2, 2, "minecraft:stone")  # sits on the stair, so that stair must keep its studs
    put(4, 1, 4, "minecraft:oak_stairs[facing=east,half=top,shape=straight]")
    put(0, 1, 4, "minecraft:oak_stairs[facing=north,half=bottom,shape=inner_left]")
    put(0, 1, 5, "minecraft:oak_stairs[facing=north,half=bottom,shape=outer_left]")

    schematic = {
        "width": width, "height": height, "length": length,
        "blocks": blocks, "data": None, "block_names": names, "format": "schem",
    }
    converter = MinecraftToLegoConverter()
    model = converter.build_model(schematic, optimize=False, scale=2)
    parts = model["parts"]
    failed = []

    def covers(part, x, y, z, sub):
        return part["sub"] == sub and (y, z, x) in part["cells"]

    overhang = [p for p in parts if covers(p, 2, 2, 2, "lower") and covers(p, 1, 2, 2, "lower")]
    if len(overhang) != 1 or overhang[0]["part"] != "3001" or overhang[0]["floating"]:
        failed.append(f"overhang lower brick: {[(p['part'], p['cells'], p['floating']) for p in parts if covers(p, 2, 2, 2, 'lower')]}")
    stair_anchor = [p for p in parts if covers(p, 5, 2, 3, "lower") and covers(p, 5, 2, 2, "lower")]
    if len(stair_anchor) != 1 or stair_anchor[0]["floating"]:
        failed.append("stair overhang did not join the wall under it")

    slopes = [p for p in parts if p["part"] == "3040"]
    open_slope = [p for p in slopes if covers(p, 4, 1, 1, "upper")]
    if len(open_slope) != 1 or open_slope[0].get("high") != "north":
        failed.append(f"open stair should be one north-high slope, got {open_slope}")
    capped = [p for p in parts if covers(p, 4, 1, 2, "upper")]
    if any(p["part"] == "3040" for p in capped) or not any(p["part"] == "3004" for p in capped):
        failed.append("stair under a block must be a flat 3004, not a slope")

    upside = [p for p in parts if covers(p, 4, 1, 4, "lower") and p.get("quads")]
    upside_top = [p for p in parts if covers(p, 4, 1, 4, "upper") and p["part"] == "3003"]
    if not upside or not upside_top:
        failed.append("upside-down stair needs a low step and a full brick on top")
    if upside and set().union(*[p["quads"] for p in upside]) != {"NE", "SE"}:
        failed.append(f"upside-down high side should be east, got {[p['quads'] for p in upside]}")

    inner = [p for p in parts if covers(p, 0, 1, 4, "upper") and p.get("quads")]
    inner_quads = set().union(*[p["quads"] for p in inner]) if inner else set()
    if inner_quads != {"NW", "NE", "SW"}:
        failed.append(f"inner corner quadrants {inner_quads}")
    outer = [p for p in parts if covers(p, 0, 1, 5, "upper") and p.get("quads")]
    outer_quads = set().union(*[p["quads"] for p in outer]) if outer else set()
    if outer_quads != {"NW"}:
        failed.append(f"outer corner quadrants {outer_quads}")

    if model["stats"]["floating"] != 0:
        failed.append(f"expected no loose pieces, got {model['stats']['floating']}")
    if model["stats"]["anchored"] < 2:
        failed.append(f"expected anchored overhangs, got {model['stats']['anchored']}")

    for p in parts:
        # Studs are 20 LDU apart. A 1-stud piece sitting on one half of a
        # 2-stud block is shifted by 10. Brick height is 24, so Y is not a stud.
        for value in (p["x"], p["z"]):
            if abs(value / 10 - round(value / 10)) > 1e-6:
                failed.append(f"part {p['part']} is off the stud grid at {value}")
                break
        if abs(p["y"] / 8 - round(p["y"] / 8)) > 1e-6:
            failed.append(f"part {p['part']} height {p['y']} is not a plate multiple")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "geometry_test.stl")
    ldr = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "geometry_test.ldr")
    converter.save_ldraw_file(model["ldraw"], ldr)
    ntris = converter.write_stl(out, model)
    if ntris < 100 or os.path.getsize(out) < 1000:
        failed.append("STL is too small to be a real mesh")
    # Rebuild triangles the same way write_stl does, to check the shell is closed.
    probe = []
    converter._mesh_voxels(model["solid"], probe)
    body_bad = _edge_problems(probe)
    if body_bad:
        failed.append(f"printed body is not closed ({len(body_bad)} bad edges)")
    studs = []
    converter._mesh_studs(model["solid"], model["nostud"], studs)
    if _edge_problems(studs):
        failed.append("studs are not closed")
    wedges = []
    converter._mesh_wedges(model["wedges"], wedges)
    if not wedges or _edge_problems(wedges):
        failed.append("slope wedges are missing or not closed")
    # The open stair's high half is a slope, so those upper plates stay empty.
    # Cell (x=4, z=1, y=1): lower plates are iy 6..8, studs ix 8..9 and iz 2..3.
    # North (high) row is iz 2.
    solid = model["solid"]
    if not bool(solid[6:9, 2:4, 8:10].all()):
        failed.append("open stair is missing its lower brick")
    if solid[9:12, 2, 8:10].any():
        failed.append("open stair filled the sloped half with a box")

    if failed:
        print("SELF-TEST FAILED")
        for line in failed:
            print(" -", line)
        return False
    print(f"SELF-TEST PASSED ({model['stats']['bricks']} pieces, {ntris} triangles)")
    print(f"STL: {out}")
    return True

def main():
    """Main function for command-line usage. The window in convert_interactive.py is the normal way to run this."""
    parser = argparse.ArgumentParser(description="Convert Minecraft schematic files to Lego LDraw and STL")
    parser.add_argument("input", help="Input Minecraft schematic file (.schematic or .schem)")
    parser.add_argument("-o", "--output", help="Output LDraw file (.ldr)")
    parser.add_argument("--stl", help="Also write a printable STL")
    parser.add_argument("--bambu", help="Also write a Bambu Studio 3MF, one object per filament, already lined up")
    parser.add_argument("--colors", type=int, default=4, help="Filaments in the Bambu file, from 1 to 8")
    parser.add_argument("--optimize", action="store_true", help="Merge adjacent same-color blocks into larger bricks")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--scale", type=int, choices=[1, 2], default=2,
                        help="Scale factor: 2 = steps, slopes, and overhangs (default), 1 = one stud per block")

    args = parser.parse_args()

    converter = MinecraftToLegoConverter()

    if args.verbose:
        print("Minecraft to Lego Converter")
        print("===========================")
        print(f"Scale: {args.scale}x")

    success = converter.convert_file(
        args.input, args.output, optimize=args.optimize, scale=args.scale, stl_path=args.stl,
        bambu_path=args.bambu, bambu_colors=args.colors)

    if success:
        print("Conversion completed successfully!")
        if args.output:
            print(f"Output saved to: {args.output}")
    else:
        print("Conversion failed!")
        sys.exit(1)

if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(0 if run_geometry_self_test() else 1)
    main()
