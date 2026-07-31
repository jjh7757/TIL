"""Pack the loose sprite PNGs into the two atlases game.js loads.

The asset pack ships every animation frame as its own file (183+ PNGs), which
would mean that many requests at runtime. This flattens them into:

    assets/atlas_chars.png   4 frames x N characters   (64 x 16N)
    assets/atlas_props.png   4 frames x 5 props         (64 x 80)

Row order here IS the index order game.js uses -- CHARACTERS[] in game.js and
the P_* constants must stay in sync with the lists below. Also copies the
tileset to a space-free path so no URL escaping is needed.

    python tools/build_atlases.py
"""
import os
import shutil

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
TILE = 16

CHAR_BASE = os.path.join(ASSETS, "Character_animation")


def from_pattern(pattern):
    """4 separate 16x16 frame files, e.g. 'priest2_v1_%d.png'."""
    def loader(frame):
        path = pattern % (frame + 1)
        if not os.path.exists(path):
            raise SystemExit(f"missing frame: {path}")
        return Image.open(path).convert("RGBA")
    return loader


def _colorkey(img, bg):
    """Some hand-arranged sheets ship with a flat matte background instead of
    real alpha (e.g. Ye_Oldy_Girl_02.png's magenta) -- punch it to transparent
    before trimming so getbbox() sees the actual character silhouette."""
    img = img.convert("RGBA")
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if (r, g, b) == bg:
                px[x, y] = (r, g, b, 0)
    return img


def from_sheet_pose(path, box, bg=None):
    """One hand-placed pose lifted out of a bigger multi-pose reference sheet
    (Valkyrie.png, Ye_Oldy_Girl_02.png) -- these aren't clean grids, so `box`
    is a generously-sized crop around just the one pose we want. Trims to
    content, pads to square (same reasoning as from_illustration: don't let
    the downscale squash the character), and reuses it across all 4 slots."""
    img = Image.open(path).convert("RGBA")
    if bg is not None:
        img = _colorkey(img, bg)
    region = img.crop(box)
    bbox = region.getbbox()
    if bbox:
        region = region.crop(bbox)
    side = max(region.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(region, ((side - region.width)//2, (side - region.height)//2))
    frame = square.resize((TILE, TILE), Image.BOX)
    return lambda _frame: frame


def from_sheet_frames(path, boxes):
    """Several hand-placed poses cropped out of a reference sheet, one per
    box, used directly as the idle frames (e.g. Ye_Oldy_Knight_Guy.png's own
    idle-bob row, or 16x16witch-spritesheet.png's already-16px idle row) --
    no square padding, these are already close enough to tile proportions."""
    img = Image.open(path).convert("RGBA")
    frames = [img.crop(b).resize((TILE, TILE), Image.BOX) for b in boxes]
    def loader(frame):
        return frames[frame % len(frames)]
    return loader


# Each character's source pack includes 2-3 variants that are the SAME body
# with only the held weapon (or idle-timing) changed -- priest1/2/3 differ only
# by mace/empty-hands/dagger. Treating those as separate characters read as
# duplicates in the picker, so only one variant per body is kept.
#
# knight/shieldmaiden/dwarf/plucky_girl/witch replaced an earlier lineup
# (knight/rogue/dwarf/viking/shieldmaiden, plus a skeleton monster) that came
# from illustrations or reference sheets 20x+ larger than the 16px tile --
# BOX-downscaling that much blurred the silhouette into a mosaic (see the
# CLAUDE.md writeup). These sources are much closer to native 16px, so the
# downscale (if any) is mild.
CT = os.path.join(ASSETS, "character and tileset")
CHARACTERS = [
    ("priest",   from_pattern(os.path.join(CHAR_BASE, "priests_idle", "priest2", "v1", "priest2_v1_%d.png"))),
    ("skull",    from_pattern(os.path.join(CHAR_BASE, "monsters_idle", "skull", "v1", "skull_v1_%d.png"))),
    ("vampire",  from_pattern(os.path.join(CHAR_BASE, "monsters_idle", "vampire", "v1", "vampire_v1_%d.png"))),
    # Ye_Oldy_Knight_Guy.png (Disthron, CC0, "Classic-Knight [Animated]") is a
    # hand-arranged sheet, not a clean grid -- columns 1-4 of row 1 are 4
    # genuine idle-bob frames (16x23 each) found by eye, everything else on
    # the sheet is other animations (run/attack/death) we don't use.
    ("knight", from_sheet_frames(os.path.join(CT, "Ye_Oldy_Knight_Guy.png"), [
        (33, 3, 49, 26), (49, 3, 65, 26), (65, 3, 81, 26), (81, 3, 97, 26),
    ])),
    # Valkyrie.png (DezrasDragons, CC0, "Viking Shieldmaiden [Animated]") --
    # same "hand-arranged, not a grid" situation. box picks out just the
    # first (standing/spear-up) pose; the rest of the sheet is a walk/attack
    # cycle that doesn't read as "idle".
    ("shieldmaiden", from_sheet_pose(os.path.join(CT, "Valkyrie.png"), box=(9, 3, 27, 26))),
    # dwarf-1.0/ (Svetlana Kushnariova "Cabbit" et al., CC-BY 3.0/4.0 --
    # ATTRIBUTION REQUIRED, see README below) -- dwarf-m-001.png is a 3x4 grid
    # of 24x32 frames (columns = walk-left/idle/walk-right, rows = N/E/S/W).
    # Row index 2 is the front-facing (bearded face visible) row; its middle
    # column is the idle pose.
    ("dwarf", from_sheet_pose(os.path.join(CT, "dwarf-1.0", "PNG", "24x32", "dwarf-m-001.png"), box=(24, 64, 48, 96))),
    # Ye_Oldy_Girl_02.png (Disthron, CC0, "Plucky Girl Adventuror [Animated]")
    # -- RGB with a flat magenta matte instead of real alpha, so it needs
    # colorkeying before the usual crop-to-bbox treatment. box picks out the
    # 2nd standing pose (cleanest crop of the bunch).
    ("plucky_girl", from_sheet_pose(os.path.join(CT, "Ye_Oldy_Girl_02.png"), box=(49, 15, 67, 38), bg=(245, 81, 255))),
    # 16x16witch-spritesheet.png (PidrouDays, itch.io, free) is already a
    # clean native-16px 8x7 grid -- row 0 is the idle bob, no downscale at all.
    ("witch", from_sheet_frames(os.path.join(CT, "16x16witch-spritesheet.png"), [
        (0, 0, 16, 16), (16, 0, 32, 16), (32, 0, 48, 16), (48, 0, 64, 16),
    ])),
]

TRAP_BASE = os.path.join(ASSETS, "items and trap_animation")
PROPS = [
    ("peaks",      from_pattern(os.path.join(TRAP_BASE, "peaks", "peaks_%d.png"))),
    ("torch",      from_pattern(os.path.join(TRAP_BASE, "torch", "torch_%d.png"))),
    ("side_torch", from_pattern(os.path.join(TRAP_BASE, "torch", "side_torch_%d.png"))),
    ("flag",       from_pattern(os.path.join(TRAP_BASE, "flag", "flag_%d.png"))),
    ("coin",       from_pattern(os.path.join(TRAP_BASE, "coin", "coin_%d.png"))),
]


def pack(rows, out_name):
    atlas = Image.new("RGBA", (4 * TILE, len(rows) * TILE), (0, 0, 0, 0))
    for i, (name, loader) in enumerate(rows):
        for frame in range(4):
            img = loader(frame)
            if img.size != (TILE, TILE):
                img = img.resize((TILE, TILE), Image.BOX)
            atlas.paste(img, (frame * TILE, i * TILE))
    out = os.path.join(ASSETS, out_name)
    atlas.save(out)
    print(f"{out_name}: {atlas.size[0]}x{atlas.size[1]}  rows={[r[0] for r in rows]}")


pack(CHARACTERS, "atlas_chars.png")
pack(PROPS, "atlas_props.png")

src = os.path.join(ASSETS, "character and tileset", "Dungeon_Tileset.png")
shutil.copyfile(src, os.path.join(ASSETS, "tileset.png"))
print("tileset.png: copied from 'character and tileset/' (space-free path)")

music_src = os.path.join(ASSETS, "music", "99020D4C5DABDEDA23.mp3")
music_dst = os.path.join(ASSETS, "music", "theme.mp3")
if os.path.exists(music_src):
    shutil.copyfile(music_src, music_dst)
    print("music/theme.mp3: copied (clean name for the hash-named source file)")
