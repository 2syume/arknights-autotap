from .AndroidDev import AndroidDev
from .cvUtils import *
from pprint import pprint

class ArkDriver(object):
    def __init__(self, android_dev=None):
        if android_dev:
            self._dev = android_dev
        else:
            self._dev = AndroidDev()
        self.config = {"pages":{}, "components":{}}
        self.ref_data = {"components":{}}
    
    def set_page(self, name, page):
        self.config["pages"][name] = page
    
    def set_component(self, name, component):
        self.config["components"][name] = component
    
    def set_component_ref_data(self, name, data):
        self.ref_data["components"][name] = data
    
    def refresh_screen(self):
        return self._dev.refresh_screen()
    
    def validate_component(self, name):
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
                return True
            else:
                return False

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

    

        