from .AndroidDev import AndroidDev
from .cvUtils import *
from pprint import pprint
from time import sleep
import yaml, pickle
import cv2

class ArkDriver(object):
    def __init__(self, android_dev=None):
        if android_dev:
            self._dev = android_dev
        else:
            self._dev = AndroidDev()
        self.config = {"geometry": self._dev.get_geometry(), "components":{}, "boxes": {}, "query_sets": {}, "searches": {}}
        self.geometry = self._dev.get_geometry()
        self.ref_data = {"components":{}, "queries": {}, "subimages":{}}
        self.component_validation_cache = {}
        self.box_cache = {}
        self.query_set_cache = {}
        self.last_log = {}

    def load_from_file(self, config_fn="config.yaml", ref_data_fn="ref.data"):
        with open(config_fn) as f:
            self.config = yaml.load(f, Loader=yaml.CLoader)
        with open(ref_data_fn, "rb") as f:
            self.ref_data = pickle.load(f)
    
    def save_to_file(self, config_fn="config.yaml", ref_data_fn="ref.data"):
        with open(config_fn, "w") as f:
            yaml.dump(self.config, f, Dumper=yaml.CDumper)
        with open(ref_data_fn, "wb") as f:
            pickle.dump(self.ref_data, f)

    def set_component(self, name, component):
        self.config["components"][name] = component
    
    def set_component_ref_data(self, name, data):
        self.ref_data["components"][name] = data
    
    def set_subimages_ref_data(self, name, data):
        self.ref_data["subimages"][name] = data
    
    def set_box(self, name, box):
        self.config["boxes"][name] = box

    def set_query_set(self, name, q_set):
        self.config["query_sets"][name] = q_set
    
    def set_search(self, name, search):
        self.config["searches"][name] = search
    
    def tap_refresh(self, x, y, delay=2.5):
        self._dev.tap(x, y)
        sleep(delay)
        self.refresh_screen()

    def swipe_refresh(self, x, y, dx, dy, t, delay=2.5):
        self._dev.swipe(x, y, dx, dy, t)
        sleep(delay)
        self.refresh_screen()

    def print_last_log(self, last_log=None, show_img=True):
        if last_log is None:
            last_log = self.last_log
        log = dict((k, v) for k,v in last_log.items() if not k.endswith("_img"))
        pprint(log)
        if show_img:
            for name, img in [(k,v) for k,v in last_log.items() if k.endswith("_img")]:
                img.show(title=name)
    
    def clear_caches(self):
        self.component_validation_cache.clear()
        self.box_cache.clear()
        self.query_set_cache.clear()
    
    def refresh_screen(self):
        self.clear_caches()
        return self._dev.refresh_screen()
    
    def validate_component(self, name):
        if name in self.component_validation_cache:
            return self.component_validation_cache[name] 
        if not name in self.config["components"]:
            return False
        config = self.config["components"][name]
        
        if config["type"] == "ssim":
            ref = bytes_to_pil(self.ref_data["components"][name])
            ref, mask = extract_alpha(ref)

            cropped = self._dev.get_screen().crop(config["crop"])
            cropped, _ = extract_alpha(cropped)
            if mask:
                cropped = Image.composite(cropped, Image.new(cropped.mode, cropped.size), mask)
                ref = Image.composite(ref, Image.new(ref.mode, ref.size), mask)
            if config.get("threshold", None):
                cropped = binarize(cropped, config["threshold"])
            if config.get("canny_args", None):
                cropped = canny(cropped, *config["canny_args"])
            conf = ssim(cropped, ref)
            result = conf >= config["min_conf"]

            self.last_log = {
                "name": name,
                "result": result,
                "src_img": cropped,
                "ref_img": ref
            }

            if result:
                self.component_validation_cache[name] = True
                return True
            else:
                self.component_validation_cache[name] = False
                return False
        
        if config["type"] == "ocr":
            cropped = self._dev.get_screen().crop(config["crop"])
            text = ocr_text(cropped, config["threshold"], config["lang"], config["config"])
            result = text == config["text"]

            self.last_log = {
                "name": name,
                "result": result,
                "src_img": cropped,
                "src_text": text,
                "ref_text": config["text"]
            }

            if result:
                self.component_validation_cache[name] = True
                return True
            else:
                self.component_validation_cache[name] = False
                return False
    
    def tap_refresh_component(self, name, delay=2.5):
        if not self.validate_component(name):
            return False
        config = self.config["components"][name]

        tap_position = (config["crop"][0] + config["tap_offset"][0],
                        config["crop"][1] + config["tap_offset"][1])
        self.tap_refresh(*tap_position, delay)
        return True

    def find_box(self, name, draw=False):
        if name in self.box_cache:
            return self.box_cache[name]
        if not name in self.config["boxes"]:
            return None
        config = self.config["boxes"][name]

        for dep in config["deps"]:
            if not self.validate_component(dep):
                return None
        if config["type"] == "float":
            floats = find_floats(self._dev.get_screen(), config["crop"], config["shape"],
                config.get("ref_color", None),
                config.get("threshold", 150),
                config.get("canny_args", None),
                config.get("kernel", 5),
                config.get("repeat", None))
            drawn = draw_shapes(self._dev.get_screen(), floats)
            if draw:
                drawn.show()
            
            self.last_log = {
                "name": name,
                "result": floats,
                "boxes_img": drawn
            }

            self.box_cache[name] = floats
            return floats
        
        if config["type"] == "fixed":
            rects = config["rects"]
            drawn = draw_shapes(self._dev.get_screen(), rects)
            if draw:
                drawn.show()
            
            self.last_log = {
                "name": name,
                "result": rects,
                "boxes_img": drawn
            }

            self.box_cache[name] = rects
            return rects
        
        if config["type"] == "subimage":
            subs = [bytes_to_pil(self.ref_data["subimages"][name]) for name in config["subimages"]]
            boxes = match_sub_image(self._dev.get_screen(), subs, config["crop"],
                config.get("method", cv2.TM_CCOEFF_NORMED),
                config.get("match_th", 0.2),
                config.get("ssim_th", 0.6),
                config.get("weights", (1.0,1.0,1.0)))
            drawn = draw_shapes(self._dev.get_screen(), boxes)
            if draw:
                drawn.show()
            
            self.last_log = {
                "name": name,
                "result": boxes,
                "boxes_img": drawn
            }

            self.box_cache[name] = boxes
            return boxes
    
    def query_set(self, name):
        if name in self.query_set_cache:
            return self.query_set_cache[name]
        if not name in self.config["query_sets"]:
            return None
        config = self.config["query_sets"][name]

        for dep in config["deps"]:
            if not self.validate_component(dep):
                return None

        if config["type"] == "fixed":
            result = [self.query(q) for q in config["queries"]]

            self.last_log = {
                "name": name,
                "result": result
            }

            self.query_set_cache[name] = result
            return result
        if config["type"] == "float":
            boxes = self.find_box(config["box"])
            result = [[self.query(q, (b[0], b[1])) for q in config["queries"]] for b in boxes]

            self.last_log = {
                "name": name,
                "result": result
            }

            self.query_set_cache[name] = result
            return result
        
    def query(self, query_config, offset=None):
        if query_config["type"] == "ocr":
            crop = query_config["crop"]
            if offset:
                if crop[2] + offset[0] > self.geometry[0] or crop[3] + offset[1] > self.geometry[1]:
                    return None
                crop = (crop[0] + offset[0], crop[1] + offset[1], crop[2] + offset[0], crop[3] + offset[1])
            cropped = self._dev.get_screen().crop(crop)
            text = ocr_text(cropped,
                query_config.get("threshold", 200),
                query_config.get("lang", "chi_sim"),
                query_config.get("config", None))
            return text
        if query_config["type"] == "ssim":
            crop = query_config["crop"]
            if offset:
                if crop[2] + offset[0] > self.geometry[0] or crop[3] + offset[1] > self.geometry[1]:
                    return None
                crop = (crop[0] + offset[0], crop[1] + offset[1], crop[2] + offset[0], crop[3] + offset[1])
            cropped = self._dev.get_screen().crop(crop)
            query_dict = self.ref_data["queries"][query_config["query_dict"]]
            results = []
            for name in query_dict:
                ref = bytes_to_pil(query_dict[name])
                ref, mask = extract_alpha(ref)
                preprocessed, _ = extract_alpha(ref)

                if mask:
                    preprocessed = Image.composite(preprocessed, Image.new(preprocessed.mode, preprocessed.size), mask)
                    ref = Image.composite(ref, Image.new(ref.mode, ref.size), mask)
                if config.get("threshold", None):
                    preprocessed =  binarize(preprocessed, config["threshold"])
                if query_config.get("canny_args", None):
                    preprocessed = canny(preprocessed, *query_config["canny_args"])

                results.append((ssim(ref, preprocessed), name))

            results = [r for r in results if r >= query_config.get("min_conf", 0.8)]
            results.sort(key=lambda x: x[0])
            results.reverse()
            return results
        if query_config["type"] == "tap":
            tap_offset = query_config["tap_offset"]
            if offset:
                if tap_offset[0] + offset[0] > self.geometry[0] or tap_offset[1] + offset[1] > self.geometry[1]:
                    return None
                tap_offset = (tap_offset[0] + offset[0], tap_offset[1] + offset[1])
            return tap_offset

    def search(self, name, callback):
        if not name in self.config["searches"]:
            return None
        config = self.config["searches"][name]

        for dep in config["deps"]:
            if not self.validate_component(dep):
                return None


        count = -1
        last_query_result = None
        search_log = []
        while True:
            query_result = self.query_set(config["query_set"])
            search_log.append(query_result)
            result = [r for r in query_result if callback(r)]
            if result:
                status = "Found"
                break
            
            if last_query_result == query_result:
                result = []
                status = "Repeated result"
                break
            last_query_result = query_result

            if count == -1:
                self.swipe_refresh(*config["init_swipe"])
            else:
                self.swipe_refresh(*config["next_swipe"])
            count += 1
            if count > config["bound"]:
                result = []
                status = "Reached bound"
                break

        self.last_log = {
            "name": name,
            "result": result,
            "search_log": search_log,
            "status": status
        }
        return result


    def new_ssim_component(self, crop,
        min_conf=0.8, threshold=None, canny_args=None,
        tap_offset=None, show_ref=True):
        cropped = self._dev.get_screen().crop(crop)
        if threshold:
            cropped = binarize(cropped, threshold)
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
                "threshold": threshold,
                "tap_offset": tap_offset
            }
            , pil_to_bytes(cropped)
        )

    
    def new_ocr_component(self, crop,
        threshold=200, lang="chi_sim", config=None,
        tap_offset=None, print_ref=True):
        cropped = self._dev.get_screen().crop(crop)
        text = ocr_text(cropped, threshold, lang, config)
        if print_ref:
            print(text)
        return {
            "type": "ocr",
            "crop": crop,
            "text": text,
            "threshold": threshold,
            "lang":lang,
            "config": config,
            "tap_offset": tap_offset
        }

    def new_float_box(self, deps, crop, shape, ref_color=None, threshold=150, canny_args=None, kernel=5, repeat=None, draw=True):
        spec = {
            "type": "float",
            "deps": deps,
            "crop": crop,
            "shape": shape,
            "ref_color": None,
            "threshold": threshold,
            "canny_args": canny_args,
            "kernel": kernel,
            "repeat": repeat
        }
        if draw:
            floats = find_floats(self._dev.get_screen(), crop, shape, ref_color, threshold, canny_args, kernel, repeat)
            draw_shapes(self._dev.get_screen(), floats).show()
        return spec
    
    def new_fixed_box(self, deps, rects, draw=True) :
        spec = {
            "type": "fixed",
            "deps": deps,
            "rects": rects
        }
        if draw:
            draw_shapes(self._dev.get_screen(), rects).show()
        return spec

    def new_subimage_box(self, deps, crop, subimages,
            method=cv2.TM_CCOEFF_NORMED, match_th=0.2,
            ssim_th=0.6, weights=(1.0, 1.0, 1.0), draw=True):
        spec = {
            "type": "subimage",
            "deps":deps,
            "crop":crop,
            "subimages": subimages,
            "method": method,
            "match_th": match_th,
            "ssim_th": ssim_th,
            "weights": weights
        }
        if draw:
            subs = [bytes_to_pil(self.ref_data["subimages"][name]) for name in subimages]
            boxes = match_sub_image(self._dev.get_screen(), subs, crop, method, match_th, ssim_th, weights)
            draw_shapes(self._dev.get_screen(), boxes).show()
        return spec


    def new_fixed_query_set(self, deps):
        spec = {
            "deps": deps,
            "type": "fixed",
            "queries": []
        }
        return spec
    
    def new_float_query_set(self, deps, box):
        spec = {
            "deps": deps,
            "type": "float",
            "box": box,
            "queries": []
        }
        return spec
    
    def new_ocr_query(self, crop, threshold=200, lang="chi_sim", config=None, print_ref=True, test_offset=None):
        spec = {
            "type": "ocr",
            "crop": crop,
            "threshold": threshold,
            "lang": lang,
            "config": config
        }
        text = self.query(spec, test_offset)
        if print_ref:
            print(text)
        return spec
    
    def new_ssim_query(self, crop, query_dict, min_conf=0.8, threshold=None, canny_args=None, show_ref=True, test_offset=None):
        spec = {
            "type": "ssim",
            "crop": crop,
            "query_dict": query_dict,
            "min_conf": min_conf,
            "threshold": threshold,
            "canny_args": canny_args
        }
        if test_offset:
            crop = (crop[0] + test_offset[0], crop[1] + test_offset[1],
                    crop[2] + test_offset[0], crop[3] + test_offset[1])
        cropped = self._dev.get_screen().crop(crop)
        if threshold:
            cropped = binarize(cropped, threshold)
        if canny_args:
            cropped = canny(cropped, *canny_args)
        if show_ref:
            cropped.show()
            results = self.query(spec, test_offset)
            print(results)
        return spec

    def new_tap_query(self, tap_offset):
        spec = {
            "type":"tap",
            "tap_offset": tap_offset
        }
        return spec
    
    def new_search(self, deps, init_swipe, next_swipe, query_set, bound=20):
        spec = {
            "deps": deps,
            "init_swipe": init_swipe,
            "next_swipe": next_swipe,
            "query_set": query_set,
            "bound": bound
        }
        return spec