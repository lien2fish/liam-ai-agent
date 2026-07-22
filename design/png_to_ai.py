"""透明 PNG 內嵌成 PDF 相容 .ai：畫板=影像原尺寸，drawImage mask='auto' 保留透明 SMask。"""

import sys
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

src, out = sys.argv[1], sys.argv[2]
im = Image.open(src)
w, h = im.size
c = canvas.Canvas(out, pagesize=(w, h))
c.drawImage(
    ImageReader(im), 0, 0, width=w, height=h, mask="auto", preserveAspectRatio=True
)
c.showPage()
c.save()
print("saved", out, (w, h))
