#!/usr/bin/env python3
import argparse 
import random
from adbutils import adb
from time import sleep, time
from datetime import datetime
from PIL import Image
from PIL.ImageOps import invert
from pytesseract import image_to_string
from io import BytesIO
import sh

class OCRValidationException(Exception):
    def __init__(self, excepted, got):
        super().__init__(self, "Excepted:'{}', got:'{}'".format(excepted, got))

class OCRUnsupportedPageException(Exception):
    pass

OFFSET_X = 0
OFFSET_Y = 0
BAR_HEIGHT=42
def offset_point(*p):
    return (p[0]+OFFSET_X, p[1]+OFFSET_Y, p[2]+OFFSET_X, p[3]+OFFSET_Y)
def offset_tap(*s):
    return [s[0], s[1], str(s[2]+OFFSET_X), str(s[3]+OFFSET_Y)]

def get_screenshot(dev):
    while True:
        try:
            dev.shell(["screencap", "-p", "/sdcard/screen.png"])
            img = b''.join(dev.sync.iter_content("/sdcard/screen.png"))
            return BytesIO(img)
        except Exception as e:
            print("Exception when pulling screenshot:", e)
            print("Retrying")
            sleep(0.5)

def save_last_screenshot(dev):
    while True:
        try:
            dev.sync.pull("/sdcard/screen.png", "arknights-screen.png")
            return
        except Exception as e:
            print("Exception when pulling screenshot:", e)
            print("Retrying")
            sleep(0.5)

def monochrome_threshold(img, threshhold, invert_img=False):
    l_img = img.convert('L').point(lambda x: 255 if x > threshhold else 0, mode='L')
    if invert_img:
        l_img = invert(l_img)
    return l_img.convert("1")

def get_sanity(dev):
    img = get_screenshot(dev)
    img_obj = Image.open(img)
    sanity_crop = img_obj.crop(offset_point(1120, 20, 1250, 60))
    mono_crop = monochrome_threshold(sanity_crop, 200, True)
    sanity_str = image_to_string(mono_crop)
    return int(sanity_str.split("/")[0])

def validate_task_page(dev):
    img = get_screenshot(dev)
    img_obj = Image.open(img)
    text_crop = img_obj.crop(offset_point(1130, 575, 1240, 610))
    mono_crop = monochrome_threshold(text_crop, 150)
    text = image_to_string(mono_crop, lang='chi_sim')
    if not '代 理 指 挥' in text:
        raise OCRValidationException('代 理 指 挥', text)

def is_currently_on_level_up_page(dev):
    for i in range(3):
        img = get_screenshot(dev)
        img_obj = Image.open(img)
        text_crop = img_obj.crop(offset_point(290, 350, 475, 400))
        mono_crop = monochrome_threshold(text_crop, 250, True)
        text = image_to_string(mono_crop, lang='chi_sim')
        if '等 级 提 升' in text:
            return True
    return False


def is_battle_page(img_obj):
    text_crop = img_obj.crop(offset_point(505, 640, 605, 670))
    mono_crop = monochrome_threshold(text_crop, 200, True)
    text = image_to_string(mono_crop, lang='chi_sim')
    return '接 管 作 战' in text

def is_result_page(img_obj):
    text_crop = img_obj.crop(offset_point(25, 575, 425, 685))
    mono_crop = monochrome_threshold(text_crop, 200, True)
    text = image_to_string(mono_crop, lang='chi_sim')
    return '行 动 结 束' in text

def is_annihilation_summary_page(img_obj):
    text_crop = img_obj.crop(offset_point(75, 175, 200, 215))
    mono_crop = monochrome_threshold(text_crop, 200, True)
    text = image_to_string(mono_crop, lang='chi_sim')
    return '作 战 简 报' in text


def main():
    parser = argparse.ArgumentParser(description="Arknights auto tapper")
    parser.add_argument("sanity_per_run", type=int, help="Sanity needed per run")
    parser.add_argument("-S", "--serial", dest="serial", type=str, default="", help="Device serial number")
    parser.add_argument("-n", "--num", dest="num", type=int, default=0, help="Number of runs to perform, 0 for infinite")
    parser.add_argument("-g", "--gap", dest="gap", type=int, default=1, help="Fixed gap time in minutes between iterations")
    parser.add_argument("-R", "--random", dest="random", type=int, default=6, help="Randomized gap time upper bound in minutes between runs")
    parser.add_argument("-b", "--battle_check_interval", dest="battle_check_interval", type=int, default=1, help="Time in minutes between checks on if the battle has finished")
    parser.add_argument("-t", "--total_time", dest="total_time", type=int, default=0, help="Total time bound in minutes for the whole process")
    parser.add_argument("-r", "--recover_to", dest="recover_to", type=int, default=0,
        help="Wait for sanity to recover to this value before next run when sanity is not enough, put 0 to recover to sanity_per_run")
    parser.add_argument("-w", "--no_wait", dest="no_wait", action="store_true", help="Run up to all sanity is used, do not wait for sanity recovery")
    parser.add_argument("-o", "--offset_mode", dest="offset_mode", default=False, action="store_true", help="Run in multi window offset mode")
    args = parser.parse_args()

    if args.serial:
        dev = adb.device(serial=args.serial)
    else:
        dev = adb.device()
    
    finished_runs = 0
    start_time = int(time())
    if args.offset_mode:
        global OFFSET_X, OFFSET_Y

        print("Finding window ID")
        anbox_wins = sh.xdotool("search", "--class", "anbox").stdout.decode().strip().split()
        anbox_win_id = None
        for win in anbox_wins:
            if sh.xdotool("getwindowname", win).stdout.decode().strip() == "arknights":
                anbox_win_id = int(win)
        if not anbox_win_id:
            raise Exception("Anbox arknights window not found")
        print("WIN ID: {}".format(anbox_win_id))

        print("Resizing window in place")
        sh.wmctrl("-i", "-r", "{0:#0{1}x}".format(anbox_win_id, 10), "-e", "0,-1,-1,{},{}".format(1280, 720+BAR_HEIGHT))

        print("Reading window position")
        result = sh.xdotool("getwindowgeometry", "--shell", str(anbox_win_id))
        lines = result.stdout.decode().strip().split()
        x = int(lines[1].partition("=")[2])
        y = int(lines[2].partition("=")[2])
        OFFSET_X = x
        OFFSET_Y = y + BAR_HEIGHT
        print("Tapping to ensure running in front")
        dev.shell(offset_tap("input", "tap", 1090, 260))

    try:
        while True:
            if args.total_time > 0 and (int(time()) - start_time) > args.total_time * 60:
                print("Exceeding total time bound, quit.")
                break
            validate_task_page(dev)
            sanity = get_sanity(dev)
            print("Current sanity:", sanity)
            if sanity >= args.sanity_per_run:
                print("Running for", finished_runs+1)

                print("Tapping prepare")
                dev.shell(offset_tap("input", "tap", 1100, 650))
                sleep(15)
                print("Tapping start")
                dev.shell(offset_tap("input", "tap", 1100, 500))
                sleep(30)

                check_failures = 0
                while True:
                    print("Checking status")
                    img = get_screenshot(dev)
                    img_obj = Image.open(img)
                    if is_battle_page(img_obj):
                        check_failures = 0
                        print("Battle running, waiting for", args.battle_check_interval, "min")
                        sleep(args.battle_check_interval * 60)
                        continue
                    if is_result_page(img_obj):
                        print("Battle finished")
                        break
                    if is_annihilation_summary_page(img_obj):
                        print("Annihilation summary, tapping out")
                        dev.shell(offset_tap("input", "tap", 1000, 200))
                        sleep(15)
                        continue
                    if is_currently_on_level_up_page(dev):
                        print("Leveled up, tapping out")
                        dev.shell(offset_tap("input", "tap", 1000, 200))
                        sleep(15)
                        continue
                    else:
                        # To avoid screenshotting during transition creating failures
                        if check_failures >= 5:
                            save_last_screenshot(dev)
                            raise OCRUnsupportedPageException()
                        else:
                            print("Failed to recognize page, trying again later")
                            check_failures += 1
                            sleep(15)

                print("Tapping out")
                dev.shell(offset_tap("input", "tap", 1000, 200))

                finished_runs += 1
                print("Run for", finished_runs, "finished")
                if args.num > 0 and finished_runs >= args.num:
                    print("Designated runs finished, quit.")
                    break
            else:
                if args.no_wait:
                    print("Not enough sanity, quit.")
                    break
                if args.recover_to > 0:
                    wait_min = (args.recover_to - sanity) * 6
                else:
                    wait_min = (args.sanity_per_run - sanity) * 6
                print("Not enough sanity, waiting for recovery: ", wait_min, "min")
                next_run_ts = int(time()) + wait_min * 60
                print("Next scheduled check time: ", datetime.fromtimestamp(next_run_ts))
                sleep(60 * wait_min)
            random_min = random.randint(0, args.random) 
            print("Random waiting gap in min:", random_min)
            sleep(60 * random_min)
            print("Fixed waiting gap in min:", args.gap)
            sleep(60 * args.gap)
    except KeyboardInterrupt:
        print("Interrupted, quit.")

if __name__ == "__main__":
    main()
