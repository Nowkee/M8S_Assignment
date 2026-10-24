# Makes the README figures from the NetLogo exports in results/ (run after run-experiment).
# It only crops and arranges images. No numbers are computed here.

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

res = Path(__file__).parent / "results"

# Figure 1: the "Healing over time" plot widget from the export-interface image
full = Image.open(res / "healing_curves.png")
if full.width > 424:  # still the whole interface, not yet cropped
    full.crop((728, 308, 1152, 592)).save(res / "healing_curves.png")

# Figure 2: 3x4 grid of seed-3 snapshots
modes, steps = ["signal", "random", "none"], [0, 30, 60, 150]
tile, label_h, pad = 360, 34, 12
font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 22)
small = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 20)
legend = [((240, 239, 236), "healthy"), ((42, 120, 214), "damaged"), ((235, 104, 52), "infected"),
          ((27, 175, 122), "healing"), ((250, 210, 0), "scout"), ((20, 20, 20), "cleaner"),
          ((130, 40, 170), "carrier")]
legend_h = 56
W = pad + len(steps) * (tile + pad)
H = pad + len(modes) * (label_h + tile + pad) + legend_h
out = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(out)
for r, m in enumerate(modes):
    for c, t in enumerate(steps):
        x = pad + c * (tile + pad)
        y = pad + r * (label_h + tile + pad)
        text = f"{m}, step {t}"
        tw = d.textlength(text, font=font)
        d.text((x + (tile - tw) / 2, y + 2), text, fill="black", font=font)
        img = Image.open(res / f"snapshot-{m}-{t}.png").convert("RGB").resize((tile, tile), Image.NEAREST)
        out.paste(img, (x, y + label_h))
        d.rectangle((x - 1, y + label_h - 1, x + tile, y + label_h + tile), outline=(150, 150, 150))

# Legend line: "grey = healthy, blue = damaged, ..." drawn as swatches with names
names = ["grey", "blue", "orange", "green", "yellow", "black", "purple"]
items = [(col, f"{n} = {lab}") for (col, lab), n in zip(legend, names)]
gap, sw = 26, 20
total = sum(sw + 6 + d.textlength(t, font=small) for _, t in items) + gap * (len(items) - 1)
x = (W - total) / 2
y = H - legend_h + 14
for col, t in items:
    d.rectangle((x, y + 4, x + sw, y + 4 + sw), fill=col, outline=(100, 100, 100))
    x += sw + 6
    d.text((x, y), t, fill="black", font=small)
    x += d.textlength(t, font=small) + gap
out.save(res / "snapshots.png")
print(out.size)
