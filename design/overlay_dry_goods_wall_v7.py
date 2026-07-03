#!/usr/bin/env python3
"""志工牆 v7 — 廚師5位(含主廚)縮到與志工格同高、志工50格放大。從 v5_final 乾淨重繪。"""
import os
from PIL import Image, ImageDraw, ImageFont

DESK="/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/一樓乾貨牆-志工名單（可拆換）"
SRC=os.path.join(DESK,"dry_goods_wall_v5_final.png")
OUT=os.path.join(DESK,"dry_goods_wall_v7_final.png")
FONT="/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc"
GREEN=(108,168,74); AMBER=(255,201,113); WHITE=(255,255,255)
GRAY=(224,224,224); SILH=(190,190,190); NUM=(245,163,60); CREAM=(253,239,201)

img=Image.open(SRC).convert("RGB"); W,H=img.size; d=ImageDraw.Draw(img)
def rr(b,r,f): d.rounded_rectangle(b,radius=r,fill=f)
def silh(b):
    x0,y0,x1,y1=b; w,h=x1-x0,y1-y0; cx=(x0+x1)/2; hr=h*0.18; hcy=y0+h*0.32
    d.ellipse((cx-hr,hcy-hr,cx+hr,hcy+hr),fill=SILH)
    bw=w*0.4; bt=hcy+hr*0.6
    d.rounded_rectangle((cx-bw/2,bt,cx+bw/2,y1-h*0.08),radius=h*0.06,fill=SILH)
def ctext(b,t,f,fill):
    x0,y0,x1,y1=b; bb=d.textbbox((0,0),t,font=f); w,h=bb[2]-bb[0],bb[3]-bb[1]
    d.text((x0+((x1-x0)-w)/2-bb[0],y0+((y1-y0)-h)/2-bb[1]),t,font=f,fill=fill)

MARGIN=60; GAP=14; TITLE_H=110; A5=210/148
CONTENT_W=W-2*MARGIN
chef_top=MARGIN+TITLE_H+GAP

# ---- 擦除舊 v5 卡片(廚師帶300 + 志工格10x4 bbox)，保留插畫邊框與標題 ----
OLD_CHEF_H=300
old_rows=4; oremain=H-2*MARGIN-TITLE_H-GAP-OLD_CHEF_H-GAP-(old_rows-1)*GAP
ovh=oremain/old_rows; ovw=ovh*A5; ogw=10*ovw+9*GAP; osp=(CONTENT_W-ogw)/2
ogx=MARGIN+osp; ogy=chef_top+OLD_CHEF_H+GAP
d.rectangle((MARGIN,chef_top,W-MARGIN,chef_top+OLD_CHEF_H),fill=CREAM)
d.rectangle((ogx-2,ogy-2,ogx+ogw+2,ogy+ovh*old_rows+(old_rows-1)*GAP+2),fill=CREAM)

# ---- v7 版面：廚師列高 = 志工格高 = vh ----
# 60+110+14 + vh + 14 + (5*vh+4*14) + 60 = H
vh=(H-2*MARGIN-TITLE_H-GAP-GAP-4*GAP)/6.0
vw=vh*A5
VC,VR=10,5
gw=VC*vw+(VC-1)*GAP; sp=(CONTENT_W-gw)/2; vl=MARGIN+sp
vol_top=chef_top+vh+GAP

# ---- 廚師5位(含主廚)：與志工同尺寸，橫向平均分佈對齊志工格左右邊 ----
TOP=["廚師1","廚師2","廚師3","廚師4","主廚"]
n=len(TOP); cgap=(gw-n*vw)/(n-1)
chef_hf=ImageFont.truetype(FONT,int(vh*0.24))
for i,lab in enumerate(TOP):
    x0=vl+i*(vw+cgap); x1=x0+vw; y0=chef_top; y1=chef_top+vh
    rr((x0,y0,x1,y1),12,WHITE); hh=vh*0.26
    rr((x0,y0,x1,y0+hh),12,GREEN); d.rectangle((x0,y0+hh-12,x1,y0+hh),fill=GREEN)
    ctext((x0,y0,x1,y0+hh),lab,chef_hf,WHITE)
    pb=(x0+8,y0+hh+8,x1-8,y1-24); rr(pb,10,GRAY); silh(pb)
    d.line((x0+16,y1-12,x1-16,y1-12),fill=(210,200,190),width=3)

# ---- 志工50格 (10x5) 放大 ----
bf=ImageFont.truetype(FONT,int(vh*0.19))
num=1
for r in range(VR):
    for c in range(VC):
        x0=vl+c*(vw+GAP); y0=vol_top+r*(vh+GAP); x1=x0+vw; y1=y0+vh
        rr((x0,y0,x1,y1),12,WHITE); hh=vh*0.16
        rr((x0,y0,x1,y0+hh),12,AMBER); d.rectangle((x0,y0+hh-12,x1,y0+hh),fill=AMBER)
        bd=hh*0.85; bx1=x1-8; byc=y0+hh/2
        d.ellipse((bx1-bd,byc-bd/2,bx1,byc+bd/2),fill=WHITE)
        t=str(num); bb=d.textbbox((0,0),t,font=bf)
        d.text((bx1-bd/2-(bb[2]-bb[0])/2-bb[0],byc-(bb[3]-bb[1])/2-bb[1]),t,font=bf,fill=NUM)
        pb=(x0+8,y0+hh+8,x1-8,y1-24); rr(pb,9,GRAY); silh(pb)
        d.line((x0+14,y1-12,x1-14,y1-12),fill=(210,200,190),width=3)
        num+=1
img.save(OUT)
mm=3420/W
print(f"已存 {OUT} {img.size}")
print(f"廚師卡={vw*mm:.0f}x{vh*mm:.0f}mm  志工卡={vw*mm:.0f}x{vh*mm:.0f}mm (同尺寸)  共{num-1}格")
print(f"(v6志工卡約 207x146px；v7={vw:.0f}x{vh:.0f}px 放大約{(vh/146-1)*100:.0f}%)")
