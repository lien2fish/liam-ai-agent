# -*- coding: utf-8 -*-
"""其餘10面文字放大（面7已完成）。座標為各面內部座標，套用時加上面的左界。"""
import shutil
from PIL import Image
from enlarge_text import apply_ops

Image.MAX_IMAGE_PIXELS = None
DIR = "/Users/lien/Desktop/鉅鑫管理顧問/鉅鑫專案/惜食廚房/惜食廚房輸出/外牆防水布"

MB = [0, 3698, 6998, 10298, 13598, 16898, 20698]
SB = [0, 3598, 7598, 10448, 14450]

MAIN_OPS = {
    1: [
        {"box": (650, 348, 3045, 593), "scale": 1.20, "feather": 18},  # 主標
        {"box": (1340, 794, 2360, 910), "scale": 1.45, "feather": 15},  # SAVE FOOD...
    ],
    2: [
        {
            "box": (1035, 782, 2270, 967),
            "scale": 1.25,
            "feather": 18,
        },  # 全球1/3食物被浪費
        {"box": (1240, 1050, 2065, 1141), "scale": 1.50, "feather": 12},  # One third...
    ],
    3: [
        {"box": (890, 218, 2420, 431), "scale": 1.20, "feather": 18},
        {"box": (1200, 583, 2105, 686), "scale": 1.50, "feather": 12},
        {"box": (1260, 811, 2040, 930), "scale": 1.35, "feather": 15},
    ],
    4: [
        {"box": (1015, 218, 2290, 431), "scale": 1.20, "feather": 18},
        {"box": (1265, 583, 2040, 686), "scale": 1.50, "feather": 12},
        {"box": (1335, 811, 1970, 929), "scale": 1.35, "feather": 15},
    ],
    5: [
        {"box": (1010, 217, 2295, 431), "scale": 1.20, "feather": 18},
        {"box": (1220, 583, 2085, 685), "scale": 1.50, "feather": 12},
        {"box": (1150, 811, 2155, 929), "scale": 1.35, "feather": 15},
    ],
    6: [
        {"box": (1530, 140, 2273, 318), "scale": 1.20, "feather": 18},  # 我們做的事
        {"box": (340, 623, 3460, 801), "scale": 1.15, "feather": 15},  # 三項+箭頭
        {
            "box": (1540, 1025, 2265, 1114),
            "scale": 1.50,
            "feather": 12,
        },  # Rescue→Cook→Share
    ],
}

SUB_OPS = {
    1: [
        {"box": (835, 350, 2767, 594), "scale": 1.20, "feather": 18},
        {"box": (1395, 794, 2206, 912), "scale": 1.45, "feather": 15},
    ],
    2: [
        {"box": (1235, 53, 2766, 199), "scale": 1.15, "feather": 15},  # 惜食5招標頭
        {"box": (85, 765, 435, 965), "scale": 1.30, "feather": 12},
        {"box": (955, 765, 1310, 965), "scale": 1.30, "feather": 12},
        {"box": (1785, 765, 2215, 965), "scale": 1.30, "feather": 12},
        {"box": (2695, 765, 3050, 965), "scale": 1.30, "feather": 12},
        {"box": (3525, 765, 3955, 965), "scale": 1.30, "dx": -45, "feather": 12},
    ],
    3: [
        {"box": (860, 219, 1989, 431), "scale": 1.20, "feather": 18},
        {"box": (1055, 584, 1802, 686), "scale": 1.50, "feather": 12},
        {"box": (1220, 811, 1625, 929), "scale": 1.35, "feather": 15},
    ],
    4: [
        {"box": (1145, 243, 2858, 466), "scale": 1.15, "feather": 18},
        {"box": (1450, 639, 2550, 757), "scale": 1.45, "feather": 12},
        {"box": (1140, 886, 2864, 1005), "scale": 1.30, "feather": 15},
    ],
}

SOLO_OPS = [
    {"box": (1690, 712, 2958, 880), "scale": 1.25, "feather": 12},  # 橘色副標
]


def shift(ops, dx):
    out = []
    for op in ops:
        o = dict(op)
        x0, y0, x1, y1 = o["box"]
        o["box"] = (x0 + dx, y0, x1 + dx, y1)
        out.append(o)
    return out


if __name__ == "__main__":
    shutil.copy(
        f"{DIR}/外牆防水布_次牆14m45_扶輪捐贈版.png",
        f"{DIR}/備份_20260703/外牆防水布_次牆14m45_加大字體前_20260717.png",
    )
    shutil.copy(
        f"{DIR}/防水布_惜食台灣行動協會_3.6x1.25m.png",
        f"{DIR}/備份_20260703/防水布_惜食台灣行動協會_加大字體前_20260717.png",
    )

    main = Image.open(f"{DIR}/外牆防水布_主牆25m5_招募志工版.png")
    for i, ops in MAIN_OPS.items():
        apply_ops(main, shift(ops, MB[i - 1]))
    main.save(f"{DIR}/外牆防水布_主牆25m5_招募志工版.png")
    for i in MAIN_OPS:
        L, R = MB[i - 1], MB[i]
        main.crop((L, 0, R, 1300)).resize((int((R - L) * 0.35), 455)).save(
            f"nv_main{i}.png"
        )

    sub = Image.open(f"{DIR}/外牆防水布_次牆14m45_扶輪捐贈版.png")
    for i, ops in SUB_OPS.items():
        apply_ops(sub, shift(ops, SB[i - 1]))
    sub.save(f"{DIR}/外牆防水布_次牆14m45_扶輪捐贈版.png")
    for i in SUB_OPS:
        L, R = SB[i - 1], SB[i]
        sub.crop((L, 0, R, 1300)).resize((int((R - L) * 0.35), 455)).save(
            f"nv_sub{i}.png"
        )

    solo = Image.open(f"{DIR}/防水布_惜食台灣行動協會_3.6x1.25m.png")
    apply_ops(solo, SOLO_OPS)
    solo.save(f"{DIR}/防水布_惜食台灣行動協會_3.6x1.25m.png")
    solo.resize((1260, 437)).save("nv_solo.png")
    print("all faces updated")
