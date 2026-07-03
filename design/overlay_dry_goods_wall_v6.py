#!/usr/bin/env python3
"""惜食廚房一樓志工牆 v6 — 廚師5位(最右=主廚，拿掉行政) + 志工50格(10欄x5列)
在既有 dry_goods_wall_v5_final.png 上精準擦除舊卡片、保留插畫邊框與標題後重繪。
"""
import os
from PIL import Image, ImageDraw, ImageFont

DESK = "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/一樓乾貨牆-志工名單（可拆換）"
SRC = os.path.join(DESK, "dry_goods_wall_v5_final.png")
OUT = os.path.join(DESK, "dry_goods_wall_v6_final.png")
FONT_BOLD = "/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc"

GREEN=(108,168,74); AMBER=(255,201,113); WHITE=(255,255,255)
GRAY=(224,224,224); SILH=(190,190,190); NUM_COLOR=(245,163,60)
CREAM=(253,239,201)

img=Image.open(SRC).convert("RGB"); W,H=img.size
d=ImageDraw.Draw(img)

def rr(box,r,fill): d.rounded_rectangle(box,radius=r,fill=fill)
def silh(box):
    x0,y0,x1,y1=box; w,h=x1-x0,y1-y0; cx=(x0+x1)/2
    hr=h*0.18; hcy=y0+h*0.32
    d.ellipse((cx-hr,hcy-hr,cx+hr,hcy+hr),fill=SILH)
    bw=w*0.4; bt=hcy+hr*0.6
    d.rounded_rectangle((cx-bw/2,bt,cx+bw/2,y1-h*0.08),radius=h*0.06,fill=SILH)
def ctext(box,t,f,fill):
    x0,y0,x1,y1=box; bb=d.textbbox((0,0),t,font=f); w,h=bb[2]-bb[0],bb[3]-bb[1]
    d.text((x0+((x1-x0)-w)/2-bb[0], y0+((y1-y0)-h)/2-bb[1]),t,font=f,fill=fill)

MARGIN=60; GAP=14; TITLE_H=110; CHEF_H=300
CONTENT_W=W-2*MARGIN
chef_top=MARGIN+TITLE_H+GAP
vol_top=chef_top+CHEF_H+GAP
A5=210/148

# ---- 擦除舊卡片：廚師帶 + 舊志工格bbox(10x4) ----
# 舊志工幾何
old_rows=4; old_remain=H-2*MARGIN-TITLE_H-GAP-CHEF_H-GAP-(old_rows-1)*GAP
old_vh=old_remain/old_rows; old_vw=old_vh*A5
old_gw=10*old_vw+9*GAP; old_sp=(CONTENT_W-old_gw)/2
old_gx0=MARGIN+old_sp; old_gy0=vol_top
d.rectangle((MARGIN, chef_top, W-MARGIN, chef_top+CHEF_H), fill=CREAM)           # 廚師帶
d.rectangle((old_gx0-2, old_gy0-2, old_gx0+old_gw+2, old_gy0+old_vh*old_rows+(old_rows-1)*GAP+2), fill=CREAM)  # 舊志工格

# ---- 重繪 廚師5位(含主廚) ----
TOP=[("廚師1",GREEN),("廚師2",GREEN),("廚師3",GREEN),("廚師4",GREEN),("主廚",GREEN)]
n=len(TOP); tw=(CONTENT_W-(n-1)*GAP)/n
cf=ImageFont.truetype(FONT_BOLD,48)
for i,(lab,col) in enumerate(TOP):
    x0=MARGIN+i*(tw+GAP); x1=x0+tw; y0=chef_top; y1=chef_top+CHEF_H
    rr((x0,y0,x1,y1),20,WHITE); hh=CHEF_H*0.16
    rr((x0,y0,x1,y0+hh),20,col); d.rectangle((x0,y0+hh-20,x1,y0+hh),fill=col)
    ctext((x0,y0,x1,y0+hh),lab,cf,WHITE)
    pb=(x0+14,y0+hh+14,x1-14,y1-60); rr(pb,14,GRAY); silh(pb)
    d.line((x0+36,y1-26,x1-36,y1-26),fill=(210,200,190),width=4)

# ---- 重繪 志工50格 (10欄 x 5列) ----
VC,VR=10,5
remain=H-2*MARGIN-TITLE_H-GAP-CHEF_H-GAP-(VR-1)*GAP
vh=remain/VR; vw=vh*A5
gw=VC*vw+(VC-1)*GAP; sp=(CONTENT_W-gw)/2; vl=MARGIN+sp
bf=ImageFont.truetype(FONT_BOLD,28)
num=1
for r in range(VR):
    for c in range(VC):
        x0=vl+c*(vw+GAP); y0=vol_top+r*(vh+GAP); x1=x0+vw; y1=y0+vh
        rr((x0,y0,x1,y1),14,WHITE); hh=vh*0.16
        rr((x0,y0,x1,y0+hh),14,AMBER); d.rectangle((x0,y0+hh-14,x1,y0+hh),fill=AMBER)
        bd=hh*0.85; bx1=x1-8; byc=y0+hh/2
        d.ellipse((bx1-bd,byc-bd/2,bx1,byc+bd/2),fill=WHITE)
        t=str(num); bb=d.textbbox((0,0),t,font=bf)
        d.text((bx1-bd/2-(bb[2]-bb[0])/2-bb[0], byc-(bb[3]-bb[1])/2-bb[1]),t,font=bf,fill=NUM_COLOR)
        pb=(x0+8,y0+hh+8,x1-8,y1-28); rr(pb,10,GRAY); silh(pb)
        d.line((x0+16,y1-14,x1-16,y1-14),fill=(210,200,190),width=3)
        num+=1

img.save(OUT)
mm=3420/W
print(f"已存 {OUT}  {img.size}")
print(f"廚師卡 {tw*mm:.0f}x{CHEF_H*mm:.0f}mm  志工卡 {vw*mm:.1f}x{vh*mm:.1f}mm  共{num-1}格")
