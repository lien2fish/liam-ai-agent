#!/usr/bin/env python3
"""在 v8 上移除數字：廚師1-4→廚師、志工格移除編號徽章（同色表頭覆蓋，無縫）"""
from PIL import Image, ImageDraw, ImageFont
DESK="/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/一樓乾貨牆-志工名單（可拆換）"
SRC=DESK+"/dry_goods_wall_v8_final.png"; OUT=DESK+"/dry_goods_wall_v9_final.png"
FONT="/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc"
GREEN=(108,168,74); AMBER=(255,201,113); WHITE=(255,255,255)
img=Image.open(SRC).convert("RGB"); W,H=img.size; d=ImageDraw.Draw(img)
def rr(b,r,f): d.rounded_rectangle(b,radius=r,fill=f)
def ctext(b,t,f,fill):
    x0,y0,x1,y1=b; bb=d.textbbox((0,0),t,font=f); w,h=bb[2]-bb[0],bb[3]-bb[1]
    d.text((x0+((x1-x0)-w)/2-bb[0],y0+((y1-y0)-h)/2-bb[1]),t,font=f,fill=fill)
MARGIN=60; GAP=14; TITLE_H=110; A5=210/148; CONTENT_W=W-2*MARGIN
chef_top=MARGIN+TITLE_H+GAP
vh=(H-2*MARGIN-TITLE_H-GAP-GAP-4*GAP)/6.0; vw=vh*A5
VC,VR=10,5; gw=VC*vw+(VC-1)*GAP; sp=(CONTENT_W-gw)/2; vl=MARGIN+sp; vol_top=chef_top+vh+GAP
# 廚師表頭重畫(1-4→廚師)
TOP=["廚師","廚師","廚師","廚師","主廚"]; n=5; cgap=(gw-n*vw)/(n-1)
chf=ImageFont.truetype(FONT,int(vh*0.24))
for i,lab in enumerate(TOP[:4]):   # 只改前4個(主廚不動)
    x0=vl+i*(vw+cgap); x1=x0+vw; y0=chef_top; hh=vh*0.26
    rr((x0,y0,x1,y0+hh),12,GREEN); d.rectangle((x0,y0+hh-12,x1,y0+hh),fill=GREEN)
    ctext((x0,y0,x1,y0+hh),lab,chf,WHITE)
# 志工表頭重畫(移除編號徽章)
for r in range(VR):
    for c in range(VC):
        x0=vl+c*(vw+GAP); y0=vol_top+r*(vh+GAP); x1=x0+vw; hh=vh*0.16
        rr((x0,y0,x1,y0+hh),12,AMBER); d.rectangle((x0,y0+hh-12,x1,y0+hh),fill=AMBER)
img.save(OUT); print("已存",OUT)
