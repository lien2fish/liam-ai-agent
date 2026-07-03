# -*- coding: utf-8 -*-
import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
Image.MAX_IMAGE_PIXELS=None
DIR="/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/外牆防水布"
F=f"{DIR}/外牆防水布_主牆25m5_扶輪捐贈版.png"
ZHF="/System/Library/Fonts/STHeiti Medium.ttc"
WHITE=(255,255,255); DK=(26,40,30); DGREEN=(6,104,44)

def mkqr(url,size):
    q=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H,box_size=10,border=2)
    q.add_data(url); q.make(fit=True)
    im=q.make_image(fill_color="black",back_color="white").convert("RGB")
    return im.resize((size,size),Image.NEAREST)

QS=300
qr_web=mkqr("https://www.savefood.org.tw",QS)
qr_fb =mkqr("https://www.facebook.com/profile.php?id=100064320807131",QS)

img=Image.open(F).convert("RGB"); d=ImageDraw.Draw(img)

def erase(x0,y0,x1,y1):
    a=np.asarray(img)
    ring=np.concatenate([a[y0-40:y0-5,x0:x1].reshape(-1,3),a[y1+5:y1+40,x0:x1].reshape(-1,3)])
    col=tuple(int(v) for v in np.median(ring,axis=0))
    layer=Image.new("RGBA",img.size,(0,0,0,0)); ImageDraw.Draw(layer).rounded_rectangle([x0,y0,x1,y1],radius=40,fill=col+(255,))
    mask=layer.split()[3].filter(ImageFilter.GaussianBlur(28)); img.paste(Image.new("RGB",img.size,col),(0,0),mask)

def ctext(cx,y,t,f,fill,stroke=0,sc=DK):
    bb=d.textbbox((0,0),t,font=f); d.text((cx-(bb[2]-bb[0])/2-bb[0],y),t,font=f,fill=fill,stroke_width=stroke,stroke_fill=sc)

# 1) 清掉原底部舊字(www...FB...捐款帳號)
erase(21300,1185,24800,1262)

# 2) 中間：聯繫文字(白字+深色描邊)
f_contact=ImageFont.truetype(ZHF,66,index=0)
ctext(23100, 600, "歡迎與我們聯繫，02-22502388", f_contact, WHITE, stroke=4, sc=(20,25,20))

# 3) 下端：白卡 + 兩個QR + 標籤
cx=23100
q1cx=cx-210; q2cx=cx+210
qy0=742; qy1=qy0+QS
cardx0=q1cx-QS//2-60; cardx1=q2cx+QS//2+60
cardy0=700; cardy1=1200
d.rounded_rectangle([cardx0,cardy0,cardx1,cardy1],radius=24,fill=WHITE,outline=DGREEN,width=5)
img.paste(qr_web,(q1cx-QS//2,qy0)); img.paste(qr_fb,(q2cx-QS//2,qy0))
f_lab=ImageFont.truetype(ZHF,44,index=0)
ctext(q1cx, qy1+18, "惜食廚房官網", f_lab, DGREEN)
ctext(q2cx, qy1+18, "臉書粉絲專頁", f_lab, DGREEN)

img.save(F); print("CTA 面板已更新")
