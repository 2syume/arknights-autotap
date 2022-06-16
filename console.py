# coding: utf-8
%load_ext autoreload
%autoreload 2
from adbutils import adb
import autotap
d = adb.device()
def show_crop(x, y, xp, yp, th=200, chi=True, inv=False):
    crop = autotap.crop_screen(d, (x, y, xp, yp))
    crop.show()
    mono_crop = autotap.monochrome_threshold(crop, th, inv)
    mono_crop.show()
    if chi:
        text = autotap.image_to_string(mono_crop, config="--psm 7", lang='chi_sim')
    else:
        text = autotap.image_to_string(mono_crop, config="--psm 7")
    return text