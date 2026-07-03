#!/usr/bin/env python3
"""志工牆 v9 = v7版面(廚師5含主廚縮小、志工50放大) 但【拿掉所有數字】+ 官網QR(右下)+LINE群組QR(右上,去背)"""
import os, qrcode
from PIL import Image, ImageDraw, ImageFont
import numpy as np
DESK="/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/一樓乾貨牆-志工名單（可拆換）"
SRC=DESK+"/dry_goods_wall_v5_final.png"; OUT=DESK+"/dry_goods_wall_v9_final.png"
FONT="/System/Library/Fonts/ヒラギノ角ゴシック W7.ttc"
ZHF=FONT
GREEN=(108,168,74); AMBER=(255,201,113); WHITE=(255,255,255)
GRAY=(224,224,224); SILH=(190,190,190); CREAM=(253,239,201); DGREEN=(6,104,44); DK=(60,55,45)
img=Image.open(SRC).convert("RGB"); W,H=img.size; d=ImageDraw.Draw(img)
def rr(b,r,f): d.rounded_rectangle(b,radius=r,fill=f)
def silh(b):
    x0,y0,x1,y1=b; w,h=x1-x0,y1-y0; cx=(x0+x1)/2; hr=h*0.18; hcy=y0+h*0.32
    d.ellipse((cx-hr,hcy-hr,cx+hr,hcy+hr),fill=SILH); bw=w*0.4; bt=hcy+hr*0.6
    d.rounded_rectangle((cx-bw/2,bt,cx+bw/2,y1-h*0.08),radius=h*0.06,fill=SILH)
def ctext(b,t,f,fill):
    x0,y0,x1,y1=b; bb=d.textbbox((0,0),t,font=f); w,h=bb[2]-bb[0],bb[3]-bb[1]
    d.text((x0+((x1-x0)-w)/2-bb[0],y0+((y1-y0)-h)/2-bb[1]),t,font=f,fill=fill)

MARGIN=60; GAP=14; TITLE_H=110; A5=210/148; CONTENT_W=W-2*MARGIN
chef_top=MARGIN+TITLE_H+GAP
# 擦除舊 v5 卡片
OCH=300; oro=4; orem=H-2*MARGIN-TITLE_H-GAP-OCH-GAP-(oro-1)*GAP; ovh=orem/oro; ovw=ovh*A5
ogw=10*ovw+9*GAP; osp=(CONTENT_W-ogw)/2; ogx=MARGIN+osp; ogy=chef_top+OCH+GAP
d.rectangle((MARGIN,chef_top,W-MARGIN,chef_top+OCH),fill=CREAM)
d.rectangle((ogx-2,ogy-2,ogx+ogw+2,ogy+ovh*oro+(oro-1)*GAP+2),fill=CREAM)
# 版面
vh=(H-2*MARGIN-TITLE_H-GAP-GAP-4*GAP)/6.0; vw=vh*A5
VC,VR=10,5; gw=VC*vw+(VC-1)*GAP; sp=(CONTENT_W-gw)/2; vl=MARGIN+sp; vol_top=chef_top+vh+GAP
# 廚師5(拿掉數字：全部「廚師」+主廚)
TOP=["廚師","廚師","廚師","廚師","主廚"]; n=len(TOP); cgap=(gw-n*vw)/(n-1)
chf=ImageFont.truetype(FONT,int(vh*0.24))
for i,lab in enumerate(TOP):
    x0=vl+i*(vw+cgap); x1=x0+vw; y0=chef_top; y1=chef_top+vh
    rr((x0,y0,x1,y1),12,WHITE); hh=vh*0.26
    rr((x0,y0,x1,y0+hh),12,GREEN); d.rectangle((x0,y0+hh-12,x1,y0+hh),fill=GREEN)
    ctext((x0,y0,x1,y0+hh),lab,chf,WHITE)
    pb=(x0+8,y0+hh+8,x1-8,y1-24); rr(pb,10,GRAY); silh(pb)
    d.line((x0+16,y1-12,x1-16,y1-12),fill=(210,200,190),width=3)
# 志工50(拿掉編號徽章)
for r in range(VR):
    for c in range(VC):
        x0=vl+c*(vw+GAP); y0=vol_top+r*(vh+GAP); x1=x0+vw; y1=y0+vh
        rr((x0,y0,x1,y1),12,WHITE); hh=vh*0.16
        rr((x0,y0,x1,y0+hh),12,AMBER); d.rectangle((x0,y0+hh-12,x1,y0+hh),fill=AMBER)
        pb=(x0+8,y0+hh+8,x1-8,y1-24); rr(pb,9,GRAY); silh(pb)
        d.line((x0+14,y1-12,x1-14,y1-12),fill=(210,200,190),width=3)

# ===== 官網 QR (右下角，白底面板) =====
def mkqr(url,size,border=2):
    q=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H,box_size=10,border=border)
    q.add_data(url); q.make(fit=True); return q.make_image(fill_color="black",back_color="white").convert("RGB").resize((size,size),Image.NEAREST)
QS=214; PAD=18; CAPH=74; PW=QS+2*PAD; PH=PAD+QS+CAPH
x1=W-30; y1=H-30; x0=x1-PW; y0=y1-PH
d.rounded_rectangle((x0,y0,x1,y1),radius=20,fill=WHITE,outline=DGREEN,width=4)
img.paste(mkqr("https://www.savefood.org.tw",QS),(x0+PAD,y0+PAD))
f1=ImageFont.truetype(ZHF,34); f2=ImageFont.truetype(ZHF,26); cx=x0+PW/2
def cc(cx,y,t,f,fl):
    bb=d.textbbox((0,0),t,font=f); d.text((cx-(bb[2]-bb[0])/2-bb[0],y),t,font=f,fill=fl)
cc(cx,y0+PAD+QS+8,"惜食廚房官網",f1,DGREEN); cc(cx,y0+PAD+QS+46,"savefood.org.tw",f2,DK)

# ===== LINE 群組 QR (右上角，去背) =====
LINEQR="/Users/lien/.claude/image-cache/27364b38-7859-4bc7-a409-cd2479506678/2.jpeg"
q=np.asarray(Image.open(LINEQR).convert("RGB"))
alpha=np.where(q.min(axis=2)>200,0,255).astype(np.uint8)
qim=Image.fromarray(np.dstack([q,alpha])).resize((240,240),Image.NEAREST)
lx1=W-28; lx0=lx1-240; ly0=224; ly1=ly0+240
d.rectangle((lx0-16,172,lx1+12,ly1+8),fill=CREAM)
fl=ImageFont.truetype(ZHF,36); lab="加入志工群組"; bb=d.textbbox((0,0),lab,font=fl)
d.text(((lx0+lx1)/2-(bb[2]-bb[0])/2-bb[0],178),lab,font=fl,fill=DGREEN)
img.paste(qim,(lx0,ly0),qim)
img.save(OUT); print("已存",OUT)
