import cv2
from PIL import Image, ImageDraw, ImageOps
import numpy as np
from skimage.metrics import structural_similarity
from io import BytesIO
from pytesseract import image_to_string

def pil_to_bytes(pil_img):
    buf = BytesIO()
    pil_img.save(buf, format="PNG")
    return buf.getvalue()

def bytes_to_pil(bytes):
    buf = BytesIO(bytes)
    return Image.open(buf)

def pil_to_cv(pil_img):
    # Greyscale Image
    if pil_img.mode == "L":
        return np.array(pil_img) 
    return cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)

def cv_to_pil(cv_img):
    # Greyscale image
    if len(cv_img.shape) == 2:
        return Image.fromarray(cv_img)
    assert cv_img.shape[2] == 3
    return Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))

def extract_alpha(pil_img):
    assert pil_img.mode == "RGBA"
    return cv2.split(np.array(pil_img))[3]

def weighted_mchan_op_cv(cv_image_a, cv_image_b, op, weights=None):
    assert cv_image_a.shape[2] == cv_image_b.shape[2]

    if weights is None:
        weights = [1.0] * cv_image_a.shape[2]

    results = []
    for chan_a, chan_b, weight in zip(cv2.split(cv_image_a), cv2.split(cv_image_b), weights):
        results.append(op(chan_a, chan_b) * weight)
    return  sum(results) / sum(weights)

def ssim_mchan_cv(cv_image_a, cv_image_b, weights=None):
    assert cv_image_a.shape == cv_image_b.shape
    return weighted_mchan_op_cv(cv_image_a, cv_image_b, structural_similarity, weights)

def ssim_cv(cv_image_a, cv_image_b, weights=None):
    assert cv_image_a.shape == cv_image_b.shape
    if len(cv_image_a.shape) == 2:
        return structural_similarity(cv_image_a, cv_image_b)
    assert len(cv_image_a.shape) == 3
    return ssim_mchan_cv(cv_image_a, cv_image_b, weights)

def ssim(pil_image_a, pil_image_b, weights=None):
    return ssim_cv(pil_to_cv(pil_image_a), pil_to_cv(pil_image_b), weights)

def binarize(pil_image, threshold):
    l_img = pil_image.convert('L').point(lambda x: 255 if x > threshold else 0, mode='L')
    return l_img

def binarize_cv(cv_image, threshold):
    return cv2.threshold(cv_image, threshold, 255, cv2.THRESH_BINARY)[1]

def gray_cv(cv_image):
    return cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)

def canny(pil_image, *args):
    return cv_to_pil(cv2.Canny(pil_to_cv(pil_image), *args))

def color_distance_cv(cv_image, color):
    shape = cv_image.shape[:-1]
    chans = cv2.split(cv_image)
    diff_square_chans = list(map(lambda x:(x[0] - np.full(shape, x[1]))**2, zip(chans, color)))
    diff = np.sqrt(sum(diff_square_chans)) * 255 / 442
    return diff.astype(np.uint8)

def ocr_text(pil_image, threshold=200, lang="chi_sim"):
    binary = binarize(pil_image, threshold)
    binary_a = np.array(binary)
    n_w = np.sum(binary_a == 255)
    n_b = binary_a.size - n_w
    if n_w > n_b:
        return image_to_string(binary, lang=lang)
    else:
        return image_to_string(ImageOps.invert(binary), lang=lang)
    

def find_shapes(pil_image, reference_color=None, threshold=150, canny_args=None, kernel=5):
    cv_img = pil_to_cv(pil_image)
    if reference_color:
        cv_img = color_distance_cv(cv_img, reference_color)
    else:
        cv_img = gray_cv(cv_img)
    if canny_args:
        cv_img = cv2.Canny(cv_img, *canny_args)
    else:
        cv_img = binarize_cv(cv_img, threshold)
    cv_img = cv2.morphologyEx(cv_img, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (kernel, kernel)))
    ctrs, _ = cv2.findContours(cv_img, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    return list(map(lambda x: cv2.boundingRect(x), ctrs))

def draw_shapes(pil_image, shapes):
    drawn = pil_image.copy()
    draw = ImageDraw.Draw(drawn)
    for rect in shapes:
        x, y, w, h = rect
        draw.rectangle([x, y, x+w, y+h], outline=(255,0,0))
    return drawn

def filter_shapes(shapes, w, h, dw, dh):
    filtered = []
    for rect in shapes:
        _, _, rw, rh = rect
        if rw >= w and rw < w + dw and rh >= h and rh < h + dh:
            filtered.append(rect)
    return filtered
