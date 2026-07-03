# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
Image.MAX_IMAGE_PIXELS=None
DIR="/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/外牆防水布"
ZHF="/System/Library/Fonts/STHeiti Medium.ttc"
WHITE=(255,255,255); DK=(26,40,30); DGREEN=(6,104,44)
boxfont=ImageFont.truetype(ZHF,72,index=0)
FS=72; PADX=50; PADY=34; MARGIN=60; TOP=60; BORDER=5; BOXH=FS+2*PADY
BOX_ALPHA=140  # 55% 不透明
_t=Image.new("RGB",(4,4)); BOXW=int(ImageDraw.Draw(_t).textlength("國際扶輪3523地區捐贈",font=boxfont)+2*PADX)

def panels(dv,total):
    e=[0]+dv+[total]; return [(e[i],e[i+1]) for i in range(len(e)-1)]

def box_rect(L,R):
    x2=R-MARGIN; x1=x2-BOXW; y1=TOP; y2=y1+BOXH
    if x1<L+MARGIN: x1=L+MARGIN; x2=x1+BOXW
    return (x1,y1,x2,y2)

def replace_word(img,cx,ynew,new_text,halfw,wf):
    a=np.asarray(img); x0,x1=int(cx-halfw),int(cx+halfw); y0,y1=ynew-95,ynew+95
    ring=np.concatenate([a[y0-40:y0-5,x0:x1].reshape(-1,3),a[y1+5:y1+40,x0:x1].reshape(-1,3)])
    col=tuple(int(v) for v in np.median(ring,axis=0))
    layer=Image.new("RGBA",img.size,(0,0,0,0)); ImageDraw.Draw(layer).rounded_rectangle([x0,y0,x1,y1],radius=60,fill=col+(255,))
    mask=layer.split()[3].filter(ImageFilter.GaussianBlur(30)); img.paste(Image.new("RGB",img.size,col),(0,0),mask)
    d=ImageDraw.Draw(img); tw=d.textlength(new_text,font=wf); bb=d.textbbox((0,0),new_text,font=wf)
    d.text((cx-tw/2,ynew-(bb[3]+bb[1])/2),new_text,font=wf,fill=WHITE)

def add_boxes(im, items):
    im=im.convert("RGBA")
    ov=Image.new("RGBA",im.size,(0,0,0,0)); od=ImageDraw.Draw(ov)
    for rect,_ in items: od.rounded_rectangle(rect,radius=20,fill=(255,255,255,BOX_ALPHA))
    im=Image.alpha_composite(im,ov)
    d=ImageDraw.Draw(im)
    for rect,text in items:
        d.rounded_rectangle(rect,radius=20,outline=DGREEN,width=BORDER)
        if text:
            x1,y1,x2,y2=rect; tw=d.textlength(text,font=boxfont)
            d.text((x1+(BOXW-tw)/2,y1+PADY-8),text,font=boxfont,fill=DK)
    return im.convert("RGB")

# 主牆
im=Image.open(f"{DIR}/外牆防水布_主牆25m5_設計稿v1.png").convert("RGB")
wf=ImageFont.truetype(ZHF,138,index=0)
replace_word(im,16900+3800/6,712,"珍惜食材",320,wf)
replace_word(im,16900+3800*5/6,712,"關懷弱勢",320,wf)
districts=[3523,3522,3521,3482,3481,3490,3501]
items=[(box_rect(L,R),f"國際扶輪{n}地區捐贈") for (L,R),n in zip(panels([3700,7000,10300,13600,16900,20700],25500),districts)]
add_boxes(im,items).save(f"{DIR}/外牆防水布_主牆25m5_扶輪捐贈版.png"); print("主牆 OK (半透明框)")
# 次牆
im=Image.open(f"{DIR}/外牆防水布_次牆14m45_設計稿v1_final.png").convert("RGB")
items=[(box_rect(L,R),None) for (L,R) in panels([3600,7600,10450],14450)]
add_boxes(im,items).save(f"{DIR}/外牆防水布_次牆14m45_扶輪捐贈版.png"); print("次牆 OK (半透明空白框)")
