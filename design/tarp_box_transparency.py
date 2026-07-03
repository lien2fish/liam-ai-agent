# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont
import numpy as np
Image.MAX_IMAGE_PIXELS=None
DIR="/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/外牆防水布"
ZHF="/System/Library/Fonts/STHeiti Medium.ttc"
WHITE=(255,255,255); DK=(26,40,30); DGREEN=(6,104,44)
boxfont=ImageFont.truetype(ZHF,72,index=0)
FS=72; PADX=50; PADY=34; MARGIN=60; TOP=60; BORDER=5; BOXH=FS+2*PADY; RAD=20
A_OLD=200.0/255.0; A_NEW=140.0/255.0   # 78% -> 55%
_t=Image.new("RGB",(4,4)); BOXW=int(ImageDraw.Draw(_t).textlength("國際扶輪3523地區捐贈",font=boxfont)+2*PADX)

def panels(dv,total):
    e=[0]+dv+[total]; return [(e[i],e[i+1]) for i in range(len(e)-1)]
def box_rect(L,R):
    x2=R-MARGIN; x1=x2-BOXW; y1=TOP; y2=y1+BOXH
    if x1<L+MARGIN: x1=L+MARGIN; x2=x1+BOXW
    return (x1,y1,x2,y2)

def retrans(path,out,items):
    img=Image.open(path).convert("RGB"); arr=np.asarray(img).astype(np.float32)
    for (x1,y1,x2,y2),_ in items:
        # rounded-rect 遮罩(只處理框內填色區)
        mk=Image.new("L",(x2-x1,y2-y1),0); ImageDraw.Draw(mk).rounded_rectangle([0,0,x2-x1-1,y2-y1-1],radius=RAD,fill=255)
        m=(np.asarray(mk)>0)
        reg=arr[y1:y2,x1:x2]
        photo=np.clip((reg-A_OLD*255)/(1-A_OLD),0,255)      # 反算原照片
        new=A_NEW*255+(1-A_NEW)*photo                        # 以55%重新合成
        reg[m]=new[m]; arr[y1:y2,x1:x2]=reg
    img=Image.fromarray(np.clip(arr,0,255).astype(np.uint8))
    d=ImageDraw.Draw(img)
    for (x1,y1,x2,y2),text in items:
        d.rounded_rectangle([x1,y1,x2,y2],radius=RAD,outline=DGREEN,width=BORDER)
        if text:
            tw=d.textlength(text,font=boxfont); d.text((x1+(BOXW-tw)/2,y1+PADY-8),text,font=boxfont,fill=DK)
    img.save(out); print("已存",out.split("/")[-1])

districts=[3523,3522,3521,3482,3481,3490,3501]
main_items=[(box_rect(L,R),f"國際扶輪{n}地區捐贈") for (L,R),n in zip(panels([3700,7000,10300,13600,16900,20700],25500),districts)]
sec_items=[(box_rect(L,R),None) for (L,R) in panels([3600,7600,10450],14450)]
retrans(f"{DIR}/外牆防水布_主牆25m5_扶輪捐贈版.png", f"{DIR}/外牆防水布_主牆25m5_扶輪捐贈版.png", main_items)
retrans(f"{DIR}/外牆防水布_次牆14m45_扶輪捐贈版.png", f"{DIR}/外牆防水布_次牆14m45_扶輪捐贈版.png", sec_items)
