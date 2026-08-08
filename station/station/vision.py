import cv2
import numpy as np

D = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_100)
try:
    DET = cv2.aruco.ArucoDetector(D, cv2.aruco.DetectorParameters())

    def detect(gray):
        corners, ids, _ = DET.detectMarkers(gray)
        return corners, ids
except AttributeError:
    def detect(gray):
        corners, ids, _ = cv2.aruco.detectMarkers(gray, D)
        return corners, ids

def homography(profile, corners, ids):
    if ids is None or len(ids) == 0:
        return None, None, None
    centers = {int(i): c[0].mean(axis=0)
               for i, c in zip(ids.flatten(), corners)}
    obj, pix = [], []
    for mid, xy in profile["markers_mm"].items():
        if int(mid) in centers:
            obj.append(xy)
            pix.append(centers[int(mid)])
    if len(obj) < 4:
        return None, None, None
    H, _ = cv2.findHomography(np.array(pix, np.float32),
                              np.array(obj, np.float32), cv2.RANSAC, 2.0)
    if H is None:
        return None, None, None
    mids = sorted(centers)
    a, b = str(mids[0]), str(mids[1])
    if a in profile["markers_mm"] and b in profile["markers_mm"]:
        mm_d = np.hypot(*np.subtract(profile["markers_mm"][b], profile["markers_mm"][a]))
        pxmm = np.linalg.norm(centers[int(b)] - centers[int(a)]) / mm_d
    else:
        pxmm = 8.0  # fallback DPI

    return H, np.linalg.inv(H), pxmm

def to_px(H_inv, pts):
    return cv2.perspectiveTransform(np.array([pts], np.float32), H_inv)[0]

def garment_mask(img, H_inv, profile, pxmm):
    w, h = profile["outer_mm"]
    b = profile.get("border_mm", 80)
    fmask = np.zeros(img.shape[:2], np.uint8)
    cv2.fillPoly(fmask, [to_px(H_inv, [(b, b), (w - b, b),
                 (w - b, h - b), (b, h - b)]).astype(np.int32)], 255)
    spots = [(w * .2, h * .3), (w * .8, h * .3),
             (w * .2, h * .8), (w * .8, h * .8)]
    samples = [img[int(y), int(x)] for x, y in to_px(H_inv, spots)]
    field = np.median(samples, axis=0)
    dist = np.linalg.norm(img.astype(np.float32) - field, axis=2)
    mask = cv2.bitwise_and(((dist > 60).astype(np.uint8)) * 255, fmask)
    k = max(3, int(6 * pxmm))
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))

def gross_dims(contour, H):
    pts = cv2.perspectiveTransform(
        contour.reshape(-1, 1, 2).astype(np.float32), H).reshape(-1, 2)
    return (pts[:, 0].max() - pts[:, 0].min(),
            pts[:, 1].max() - pts[:, 1].min())
