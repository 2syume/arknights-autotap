from PIL import Image
import numpy as np
from skimage.metrics import structural_similarity 

def split_chan(img):
    return np.squeeze(np.dsplit(img, img.shape[-1]), axis=-1)

def merge_chan(chans):
    return np.dstack(chans)

def split_pil_alpha(pil_i):
    img_a = np.array(pil_i)
    split = split_chan(img_a)
    return (merge_chan(split[:3]), split[3])

def mask_alpha(image_a, alpha_a, image_b=None, alpha_b=None):
    if not image_b is None:
        assert image_a.shape == image_b.shape
    assert image_a.shape[:-1] == alpha_a.shape
    if alpha_b is None:
        alpha_b = np.full(alpha_a.shape, 255, np.uint8)
    alpha = np.multiply(alpha_a/255, alpha_b/255) 
    
    split_a = split_chan(image_a)
    masked_a = merge_chan(list(map(lambda channel: np.multiply(channel, alpha).astype(np.uint8) , split_a)))
    if image_b is None:
        return masked_a
    split_b = split_chan(image_b)
    masked_b = merge_chan(list(map(lambda channel: np.multiply(channel, alpha).astype(np.uint8) , split_b)))
    return (masked_a, masked_b)


def weighted_rgb(image_a, image_b, op, weights=(1.0, 1.0, 1.0)):
    assert image_a.shape[2] == image_b.shape[2]
    assert image_a.shape[2] == 3

    results = []
    for chan_a, chan_b, weight in zip(split_chan(image_a), split_chan(image_b), weights):
        results.append(op(chan_a, chan_b) * weight)
    return  sum(results) / sum(weights)

def ssim_rgb(image_a, image_b, weights=(1.0, 1.0, 1.0)):
    return weighted_rgb(image_a, image_b, structural_similarity, weights)