import os
import numpy as np

URDU = {
    "OKAY": "ٹھیک ہے",
    "FAIL": "فیل",
    "MISLABEL": "غلط لیبل",
    "RE-LAY": "دوبارہ رکھیں"
}

def banner(img, verdict):
    if not verdict:
        return img
    # Terminal bell for audio feedback
    print("\a" if verdict == "OKAY" else "\a\a", end="", flush=True)
    font_path = os.environ.get("MANAR_URDU_FONT")
    if not font_path:
        return img
    try:
        from PIL import Image, ImageDraw, ImageFont
        font = ImageFont.truetype(font_path, 64)
        im = Image.fromarray(img[..., ::-1])
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, im.width, 110], fill=(0, 0, 0))
        d.text((im.width - 420, 18), URDU.get(verdict, verdict),
               font=font, fill=(0, 200, 0) if verdict == "OKAY" else (255, 60, 60))
        return np.ascontiguousarray(im)[..., ::-1]
    except Exception:
        return img
