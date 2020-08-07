import numpy as np
import argparse
import cv2
import imutils
import match
from PIL import Image

parser = argparse.ArgumentParser()
parser.add_argument("-t", "--template", required=True, help="Path to template")
parser.add_argument("-i", "--image", required=True, help="Path to image to be matched against")
parser.add_argument("-r", "--resize", action="store_true", default=False, help="Find resized templates")
parser.add_argument("-m", "--mask", action="store_true", default=False, help="Use template alpha channel as mask")

args = parser.parse_args()

(template, alpha) = match.split_pil_alpha(Image.open(args.template))
(tH, tW) = template.shape[:2]
if args.mask:
    mask = alpha
else:
    template = match.mask_alpha(template, alpha)
    mask = None

image, alpha = match.split_pil_alpha(Image.open(args.image))
image = match.mask_alpha(image, alpha)

found = None
match_func = lambda x, y : cv2.matchTemplate(x, y, cv2.TM_CCOEFF_NORMED)
if args.resize:
    for scale in np.linspace(0.2, 1.0, 20)[::-1]:
        resized = imutils.resize(image, width = int(image.shape[1] * scale))
        r = image.shape[1] / resized.shape[1]

        if resized.shape[0] < tH or resized.shape[1] < tW:
            break
        result = match.weighted_rgb(image, template, match_func)
        (_, maxVal, _, maxLoc) = cv2.minMaxLoc(result)

        if found is None or maxVal > found[0]:
            found = (maxVal, maxLoc, r)
else:
    result = match.weighted_rgb(image, template, match_func)
    (_, maxVal, _, maxLoc) = cv2.minMaxLoc(result)
    found = (maxVal, maxLoc, 1.0)


(correlation, maxLoc, r) = found
matched_ref = imutils.resize(template, width = int(tW * r))

(startX, startY) = (int(maxLoc[0] * r), int(maxLoc[1] * r))
(endX, endY) = (startX + matched_ref.shape[1], startY + matched_ref.shape[0])
matched_region = image[startY:endY, startX:endX]

if not mask is None:
    matched_mask = imutils.resize(mask, width = int(tW * r))
    matched_ref, matched_region = match.mask_alpha(matched_ref, matched_mask, matched_region)
confidence = match.ssim_rgb(matched_region, matched_ref)

print("Matched corelation:", correlation)
print("SSIM Confidence: ", confidence)
cv2.rectangle(image, (startX, startY), (endX, endY), (255,0,0), 2)
Image.fromarray(image).show()