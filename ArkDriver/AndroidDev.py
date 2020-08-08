from time import sleep
from adbutils import adb
from io import BytesIO
from PIL import Image
from .Logging import WARN

class AndroidDev(object):
    def __init__(self, serial=None):
        if serial:
            self._dev = adb.device(serial=serial)
        else:
            self._dev = adb.device()
        self._screenshot_retry_wait = 0.5
        self._screenshot_on_dev_path = "/sdcard/screen.png"
        self._screen = None
        self._geometry = None

    
    def tap(self, x, y):
        self._dev.shell(["input", "tap", str(x), str(y)])

    def swipe(self, x, y, dx, dy, t):
        self._dev.shell(["input", "swipe", str(x), str(y), str(x + dx), str(y + dy), str(t)])

    def set_screenshot_retry_wait(self, time):
        self._screenshot_retry_wait = time
    
    def set_screenshot_on_dev_path(self, path):
        self._screenshot_on_dev_path = path
    
    def get_screen(self):
        return self._screen
    
    def get_geometry(self):
        if not self._geometry:
            size_str = self._dev.shell(["wm", "size"])
            self._geometry = tuple(map(int, size_str.partition(":")[2].strip().split("x")))
        return self._geometry

    def take_screen(self):
        while True:
            try:
                self._dev.shell(["screencap", "-p", self._screenshot_on_dev_path])
                return
            except Exception as e:
                WARN("Exception when taking screenshot:", e, ",Retrying")
                sleep(self._screenshot_retry_wait)

    def pull_screen(self):
        while True:
            try:
                binary_data = b''.join(self._dev.sync.iter_content(self._screenshot_on_dev_path))
                self._screen = Image.open(BytesIO(binary_data))
                return
            except Exception as e:
                WARN("Exception when pulling screenshot:", e, ",Retrying")
                sleep(self._screenshot_retry_wait)
    
    def refresh_screen(self):
        self.take_screen()
        self.pull_screen()
        return self._screen
    
    

