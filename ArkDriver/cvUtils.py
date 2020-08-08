import cv2
from PIL import Image
import numpy as np
from skimage.metrics import structural_similarity

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

def binarize(pil_image):
    l_img = img.convert('L').point(lambda x: 255 if x > threshhold else 0, mode='L')
    return l_img.convert('1')