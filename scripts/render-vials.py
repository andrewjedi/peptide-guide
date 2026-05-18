#!/usr/bin/env python3
import ast, re, textwrap, zipfile, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'public' / 'jedi-research-vials'
ZIP = ROOT / 'public' / 'jedi-research-vials.zip'
BUILD = ROOT / 'scripts' / 'build.mjs'

FONT_BOLD = '/System/Library/Fonts/SFNS.ttf'
FONT_MONO = '/System/Library/Fonts/SFNSMono.ttf'
FONT_SERIF = '/System/Library/Fonts/NewYork.ttf'

def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def parse_rows():
    src = BUILD.read_text()
    block = src.split('const rows = [', 1)[1].split('\n];', 1)[0]
    rows = []
    for line in block.splitlines():
        for m in re.finditer(r"\[([^\]]+)\]", line):
            arr = ast.literal_eval('[' + m.group(1) + ']')
            if len(arr) == 5:
                rows.append(arr)
    return rows

def safe_name(s):
    s = s.replace('+', ' plus ').replace('/', ' ').replace('静', 'iv')
    s = re.sub(r'[^A-Za-z0-9]+', '-', s).strip('-').lower()
    return re.sub(r'-+', '-', s)[:120]

def amount_label(amount):
    a = amount.replace(' total', '').replace(' · ', ' ')
    return a.upper().replace('IU', ' IU').replace('MCG', ' MCG').replace('MG', ' MG').replace('ML', ' ML')

def wrap(draw, text, fnt, max_width, max_lines=2):
    words = text.split()
    lines=[]; cur=''
    for w in words:
        test = (cur + ' ' + w).strip()
        if draw.textbbox((0,0), test, font=fnt)[2] <= max_width or not cur:
            cur = test
        else:
            lines.append(cur); cur = w
            if len(lines) == max_lines - 1:
                break
    if cur and len(lines) < max_lines:
        remaining = ' '.join(words[sum(len(x.split()) for x in lines):])
        cur = remaining if remaining else cur
        while draw.textbbox((0,0), cur, font=fnt)[2] > max_width and len(cur) > 3:
            cur = cur[:-4].rstrip() + '…'
        lines.append(cur)
    return lines[:max_lines]

def gradient_rect(size, left, right):
    w,h=size
    img=Image.new('RGBA', size)
    px=img.load()
    for x in range(w):
        t=x/(w-1 or 1)
        # metallic band highlight near middle-left
        shine = max(0, 1-abs(t-.48)/.13) * .55
        col=[]
        for i in range(3):
            v=int(left[i]*(1-t)+right[i]*t + 255*shine)
            col.append(max(0,min(255,v)))
        for y in range(h): px[x,y]=(*col,255)
    return img

def rounded_mask(size, radius):
    m=Image.new('L', size, 0)
    d=ImageDraw.Draw(m)
    d.rounded_rectangle((0,0,size[0]-1,size[1]-1), radius, fill=255)
    return m

def draw_vial(code, name, amount, vials, price, path):
    W=H=1024
    im=Image.new('RGB',(W,H),(235,234,231))
    d=ImageDraw.Draw(im)
    # background vignette
    for r in range(500, 40, -8):
        alpha=(500-r)/500
        c=int(242-22*alpha)
        d.ellipse((512-r,480-r,512+r,480+r), fill=(c,c,c))
    # shadow
    sh=Image.new('RGBA',(W,H),(0,0,0,0)); sd=ImageDraw.Draw(sh)
    sd.ellipse((310,825,714,900), fill=(0,0,0,90)); sh=sh.filter(ImageFilter.GaussianBlur(24)); im=Image.alpha_composite(im.convert('RGBA'),sh)
    d=ImageDraw.Draw(im)
    # vial glass body
    body=(322,190,702,864)
    glass=Image.new('RGBA',(W,H),(0,0,0,0)); gd=ImageDraw.Draw(glass)
    gd.rounded_rectangle(body, radius=76, fill=(255,255,255,72), outline=(95,105,110,160), width=4)
    gd.rounded_rectangle((348,240,676,832), radius=42, outline=(255,255,255,120), width=3)
    gd.line((379,210,379,820), fill=(255,255,255,160), width=10)
    gd.line((635,215,635,820), fill=(0,0,0,35), width=7)
    gd.rectangle((342,765,682,838), fill=(65,75,77,50))
    im=Image.alpha_composite(im, glass)
    d=ImageDraw.Draw(im)
    # neck
    d.rounded_rectangle((396,118,628,282), radius=38, fill=(232,232,228,88), outline=(85,90,94,130), width=3)
    d.line((420,200,604,200), fill=(30,34,36), width=4)
    d.line((424,210,600,210), fill=(30,34,36), width=3)
    # cap
    cap=gradient_rect((380,88),(120,124,126),(216,216,210))
    mask=rounded_mask((380,88),28)
    cap.putalpha(mask)
    im.alpha_composite(cap,(322,72))
    d.rounded_rectangle((322,70,702,162), radius=29, outline=(19,30,43), width=3)
    d.rounded_rectangle((300,42,724,108), radius=28, fill=(6,23,38))
    # label
    label_x,label_y,label_w=322,412,380
    d.rectangle((label_x,label_y,label_x+label_w,label_y+100), fill=(248,248,246))
    # brand icon
    d.regular_polygon((374,462,42), n_sides=6, rotation=30, outline=(45,48,50), width=4)
    d.line((356,436,392,488), fill=(45,48,50), width=3)
    d.line((392,436,356,488), fill=(45,48,50), width=3)
    d.arc((360,440,388,456), 0, 180, fill=(45,48,50), width=3)
    d.arc((360,468,388,484), 180, 360, fill=(45,48,50), width=3)
    brand=font(FONT_BOLD,48); small=font(FONT_MONO,20)
    d.text((430,424),'JEDI',font=brand,fill=(8,12,16))
    d.text((430,470),'RESEARCH',font=font(FONT_MONO,27),fill=(8,12,16),spacing=6)
    # dark product area
    band=gradient_rect((label_w,276),(8,28,45),(42,66,82))
    im.alpha_composite(band,(label_x,label_y+100))
    d=ImageDraw.Draw(im)
    prod_font=font(FONT_BOLD,54 if len(name)<=18 else 43 if len(name)<=28 else 34)
    lines=wrap(d,name.upper(),prod_font,label_w-60,2)
    y=label_y+130
    for line in lines:
        d.text((label_x+32,y),line,font=prod_font,fill=(255,255,255))
        y += prod_font.size + 4
    amt=amount_label(amount)
    amt_font=font(FONT_BOLD,32 if len(amt)<=14 else 25)
    box_y=label_y+230
    box_w=max(126, min(300, d.textbbox((0,0), amt, font=amt_font)[2]+32))
    d.rectangle((label_x+32,box_y,label_x+32+box_w,box_y+54), outline=(230,238,242), width=3)
    d.text((label_x+48,box_y+9),amt,font=amt_font,fill=(255,255,255))
    fine=font(FONT_BOLD,18); fine2=font(FONT_MONO,17)
    d.text((label_x+32,label_y+292),'99% Purity',font=fine,fill=(255,255,255))
    d.text((label_x+32,label_y+317),'FOR RESEARCH USE ONLY',font=fine2,fill=(255,255,255))
    d.text((label_x+32,label_y+342),'jediresearch.shop',font=fine2,fill=(255,255,255))
    d.text((label_x+270,label_y+342),code,font=font(FONT_MONO,15),fill=(210,220,226))
    # bottom glass/reflection
    overlay=Image.new('RGBA',(W,H),(0,0,0,0)); od=ImageDraw.Draw(overlay)
    od.rounded_rectangle((335,782,689,862), radius=36, fill=(255,255,255,35), outline=(30,36,38,60), width=2)
    od.arc((360,780,664,872), 0, 180, fill=(0,0,0,55), width=4)
    im=Image.alpha_composite(im,overlay)
    im=im.convert('RGB')
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, quality=94, optimize=True)


def main():
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    rows=parse_rows()
    manifest=[]
    for code,name,amount,vials,price in rows:
        fn=f"{safe_name(name)}__{safe_name(code)}__{safe_name(amount)}.png"
        draw_vial(code,name,amount,vials,price,OUT/fn)
        manifest.append({'code':code,'name':name,'amount':amount,'vials':vials,'price':price,'file':fn})
    (OUT/'manifest.json').write_text(__import__('json').dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    if ZIP.exists(): ZIP.unlink()
    with zipfile.ZipFile(ZIP,'w',zipfile.ZIP_DEFLATED) as z:
        for f in sorted(OUT.glob('*')):
            z.write(f, f'jedi-research-vials/{f.name}')
    print(f'Rendered {len(rows)} vial PNGs to {OUT}')
    print(f'Zip: {ZIP}')

if __name__ == '__main__': main()
