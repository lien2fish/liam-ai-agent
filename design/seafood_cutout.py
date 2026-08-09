"""白底海鮮橫幅去背：u2net 顯著性遮罩 ∪ 非白遮罩，取交集邏輯避免吃掉冰塊。"""

import sys

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageFilter

SRC, OUT = sys.argv[1], sys.argv[2]

img = Image.open(SRC).convert("RGB")
W, H = img.size

sess = ort.InferenceSession(
    "/Users/lien/.cache/u2net.onnx", providers=["CPUExecutionProvider"]
)
inp = np.asarray(img.resize((320, 320), Image.LANCZOS), dtype=np.float32) / 255.0
mean, std = np.array([0.485, 0.456, 0.406]), np.array([0.229, 0.224, 0.225])
inp = ((inp - mean) / std).transpose(2, 0, 1)[None].astype(np.float32)
pred = sess.run(None, {sess.get_inputs()[0].name: inp})[0][0, 0]
pred = (pred - pred.min()) / (pred.max() - pred.min() + 1e-8)
sal = (
    np.asarray(
        Image.fromarray((pred * 255).astype(np.uint8)).resize((W, H), Image.LANCZOS),
        dtype=np.float32,
    )
    / 255.0
)

arr = np.asarray(img, dtype=np.float32)
mx, mn = arr.max(axis=2), arr.min(axis=2)
whiteness = (mn / 255.0) * (1.0 - (mx - mn) / 255.0 * 2.2)
not_white = np.clip((0.86 - whiteness) * 7.0, 0, 1)

alpha = np.clip(np.maximum(not_white, sal * 1.15) * 1.35, 0, 1)
alpha[sal < 0.05] *= 0.15

a = Image.fromarray((alpha * 255).astype(np.uint8)).filter(
    ImageFilter.GaussianBlur(1.2)
)
out = img.convert("RGBA")
out.putalpha(a)
out.save(OUT)
bb = out.getchannel("A").point(lambda v: 255 if v > 12 else 0).getbbox()
print("saved", OUT, out.size, "alpha bbox", bb)
