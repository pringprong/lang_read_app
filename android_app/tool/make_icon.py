from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

RES = Path('/home/pringprong/lang_read_app/android_app/android/app/src/main/res')
SIZES = {'mdpi': 48, 'hdpi': 72, 'xhdpi': 96, 'xxhdpi': 144, 'xxxhdpi': 192}
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
BG = (0, 105, 92)       # teal 800, matches the app seed color 0xFF00695C
FG = (255, 255, 255)

canvas = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
d = ImageDraw.Draw(canvas)
# rounded square
d.rounded_rectangle([16, 16, 496, 496], radius=96, fill=BG)
# book glyph: two pages + spine
d.rounded_rectangle([116, 132, 248, 396], radius=18, outline=FG, width=14)
d.rounded_rectangle([264, 132, 396, 396], radius=18, outline=FG, width=14)
d.line([256, 140, 256, 396], fill=FG, width=14)
# character 读 on the lower right (small badge-style)
font = ImageFont.truetype(FONT, 150)
bbox = d.textbbox((0, 0), '读', font=font)
w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
d.text((396 - w - 34 + 40, 396 - h - 30), '读', font=font, fill=(255, 255, 255, 235))

canvas.save(Path('/home/pringprong/lang_read_app/android_app/assets') / 'icon.png') if (Path('/home/pringprong/lang_read_app/android_app/assets')).exists() else None
for bucket, size in SIZES.items():
    out = RES / f'mipmap-{bucket}' / 'ic_launcher.png'
    canvas.resize((size, size), Image.LANCZOS).save(out)
    print(f'wrote {out} ({size}x{size})')
