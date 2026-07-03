# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
Image.MAX_IMAGE_PIXELS=None
DIR="/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/外牆防水布"
F=f"{DIR}/外牆防水布_主牆25m5_扶輪捐贈版.png"
ZHF="/System/Library/Fonts/STHeiti Medium.ttc"
WHITE=(255,255,255)
img=Image.open(F).convert("RGB"); d=ImageDraw.Draw(img)

def erase(x0,y0,x1,y1):
    a=np.asarray(img)
    ring=np.concatenate([a[max(0,y0-45):y0-8,x0:x1].reshape(-1,3),a[y1+8:y1+45,x0:x1].reshape(-1,3)])
    col=tuple(int(v) for v in np.percentile(ring,30,axis=0))  # 取較深的背景色
    layer=Image.new("L",img.size,0); ImageDraw.Draw(layer).rounded_rectangle([x0,y0,x1,y1],radius=45,fill=255)
    mask=layer.filter(ImageFilter.GaussianBlur(16))
    img.paste(Image.new("RGB",img.size,col),(0,0),mask)

# 清掉：壓字的聯繫文字+Donate英文；底部殘字
erase(21500, 588, 24500, 700)
erase(21200, 1172, 24900, 1268)

# 重寫聯繫文字(取代原Donate英文位置)
f=ImageFont.truetype(ZHF,70,index=0); t="歡迎與我們聯繫，02-22502388"
bb=d.textbbox((0,0),t,font=f)
d.text((23100-(bb[2]-bb[0])/2-bb[0], 616), t, font=f, fill=WHITE, stroke_width=5, stroke_fill=(18,22,18))
img.save(F); print("CTA 修正完成")
