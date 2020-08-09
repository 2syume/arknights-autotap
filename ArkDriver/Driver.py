from .AndroidDev import AndroidDev
from .cvUtils import *
from pprint import pprint

class ArkDriver(object):
    def __init__(self, android_dev=None):
        if android_dev:
            self._dev = android_dev
        else:
            self._dev = AndroidDev()
        self.config = {"geometry": self._dev.get_geometry(), "pages":{}, "components":{}}
        self.ref_data = {"components":{}}
        self.component_validation_cache = set()
    
    def set_page(self, name, page):
        self.config["pages"][name] = page
    
    def set_component(self, name, component):
        self.config["components"][name] = component
    
    def set_component_ref_data(self, name, data):
        self.ref_data["components"][name] = data
    
    def clear_caches(self):
        self.component_validation_cache.clear()
    
    def refresh_screen(self):
        self.clear_caches()
        return self._dev.refresh_screen()
    
    def validate_component(self, name):
        if name in self.component_validation_cache:
            return True
        if not name in self.config["components"]:
            return False
        config = self.config["components"][name]
        
        if config["type"] == "ssim":
            ref = bytes_to_pil(self.ref_data["components"][name])

            cropped = self._dev.get_screen().crop(config["crop"])
            if config.get("canny_args", None):
                cropped = canny(cropped, *config["canny_args"])
            conf = ssim(cropped, ref)
            if conf >= config["min_conf"]:
                self.component_validation_cache.add(name)
                return True
            else:
                return False
        
        if config["type"] == "ocr":
            cropped = self._dev.get_screen().crop(config["crop"])
            cropped = binarize(cropped, config["threshold"])
            text = ocr_text(cropped)
            if text == config["text"]:
                self.component_validation_cache.add(name)
                return True
            else:
                return False
    
    def tap_component(self, name):
        if not self.validate_component(name):
            return False
        config = self.config["components"][name]

        tap_position = (config["crop"][0] + config["tap_offset"][0],
                        config["crop"][1] + config["tap_offset"][1])
        self._dev.tap(*tap_position)
        return True
        

    def new_ssim_component(self, crop,
        min_conf=0.8, canny_args=None,
        tap_offset=None, show_ref=True):
        cropped = self._dev.get_screen().crop(crop)
        if canny_args:
            cropped = canny(cropped, *canny_args)
        if show_ref:
            cropped.show()
        return (
            {
                "type": "ssim",
                "crop": crop,
                "min_conf": min_conf,
                "canny_args": canny_args,
                "tap_offset": tap_offset
            }
            , pil_to_bytes(cropped)
        )

    
    def new_ocr_component(self, crop,
        threshold=200,
        tap_offset=None, print_ref=True):
        cropped = self._dev.get_screen().crop(crop)
        cropped = binarize(cropped, threshold)
        text = ocr_text(cropped)
        if print_ref:
            print(text)
        return {
            "type": "ocr",
            "crop": crop,
            "text": text,
            "threshold": threshold,
            "tap_offset": tap_offset
        }

        