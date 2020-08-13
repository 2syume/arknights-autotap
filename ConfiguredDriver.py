from ArkDriver.Driver import ArkDriver
from time import sleep, time
from datetime import datetime
from random import randint

class UnexpectedState(Exception):
    def __init__(self, *args, **argv):
        super().__init__(*args, **argv)

class Unsupported(Exception):
    def __init__(self, *args, **argv):
        super().__init__(*args, **argv)

class ConfiguredDriver(ArkDriver):
    def __init__(self, *args, **argv):
        super().__init__(*args, **argv)
        self.load_from_file()
        self.current_san = 0
        self.current_cost = 0
        self.current_map_name = ""
        self.current_map_name_chi = ""
        self.exc_log = {}

    def handle_popup(self, delay=15, retries=3, retry_intern=5):
        print("- Handling possible popups")
        handled = False
        self.refresh_screen()

        count = 0
        while not self.is_navigable():
            # Communication stuck
            if self.validate_component("communicating"):
                handled = True
                print("  Communicating, wait for {} secs".format(delay))
                sleep(delay)
                self.refresh_screen()
                continue
            if self.tap_refresh_component("popup.loading", delay):
                handled = True
                print("  Handled loading popup")
                continue
            if self.tap_refresh_component("popup.got_rewards", delay):
                handled = True
                print("  Handled rewards popup")
                continue
            if self.tap_refresh_component("popup.signin.close", delay):
                handled = True
                print("  Handled signin popup")
                continue
            if self.tap_refresh_component("popup.announcement.close", delay):
                handled = True
                print("  Handled announcement popup")
                continue
            if self.validate_component("popup.relogin.reauth"):
                handled = True
                print("  Re-login needed, triggering")
                if not self.tap_refresh_component("popup.generic_info.confirm", delay):
                    raise UnexpectedState()
                if not self.re_login():
                    raise UnexpectedState()
                continue
            if self.validate_component("popup.error.autopilot_sync_failure"):
                handled = True
                print("  Auth may be outdated, trying to go to base to trigger a refresh")
                if not self.tap_refresh_component("popup.generic_info.confirm", delay):
                    raise UnexpectedState()
                self.goto_base()
                continue
            if self.tap_refresh_component("popup.generic_info.confirm", delay):
                handled = True
                print("  Handled an unknown generic info popup")
                continue
            print("  State recognition failure: {}/{}".format(count + 1, retries))
            if count >= retries:
                break
            count += 1
            print("  Waiting {} secs before next try".format(retry_intern))
            sleep(retry_intern)
            self.refresh_screen()

        return handled

    def is_navigable(self):
        return self.validate_component("main.settings") \
            or self.validate_component("menu.main") \
            or self.validate_component("menu") \
            or self.validate_component("back") \
            or self.validate_component("in_battle.enemy_icon") \
            or self.validate_component("battle_finished.title")
    
    # -> None: Successful recovery
    # -> Others: Failure to recover, should raise return value immediately
    def recover_from_exc(self, exc_info, retries=5, retry_intern=15):
        if self.handle_popup():
            return None

        exc_type, exc, tb = exc_info
        while tb.tb_next is not None:
            tb = tb.tb_next
        f = tb.tb_frame
        lineno = tb.tb_lineno
        filename = f.f_code.co_filename

        if filename != __file__:
            return exc

        count = self.exc_log.get((filename, lineno), 0)
        if count >= retries:
            return exc
        print("> Recovering from exception in {}:{} : {}({}) Retries: {}/{}".format(filename, lineno, exc_type.__name__, exc, count+1, retries))
        count += 1
        self.exc_log[(filename, lineno)] = count
        print("  Waiting for {} secs before attempting recovery".format(retry_intern))
        sleep(retry_intern)
        return None

    def interrupt_user(self, check_intern=30):
        while self.is_in_battle():
            print("  Navigation: wait {} secs for running battle".format(check_intern))
            sleep(check_intern)
        if self.tap_battle_finished():
            print("  Leaving battle finished page")

    def re_login(self, check_intern=30, delay=15, max_check=20):
        print("- Re-logging in")
        self.refresh_screen()

        count = 0
        while not self.is_navigable():
            if self.tap_refresh_component("login.start", delay):
                print("  Logged in")
                continue
            if self.validate_component("popup.relogin.outdated"):
                if not self.tap_refresh_component("popup.generic_info.confirm", delay):
                    raise UnexpectedState()
                print("  Updating data")
                continue
            if self.handle_popup(retries=0):
                print("  Handled popups")
                continue
            if count >= max_check:
                return False
            print(" Waiting {} secs for login process : {}/{}".format(check_intern, count+1, max_check))
            count += 1
            sleep(check_intern)
        return True



    def home(self, delay=15):
        self.interrupt_user()
        print("- Navigating to main page")
        self.refresh_screen()
        while True:
            while self.validate_component("communicating"):
                print("  Communicating, wait for {} secs".format(delay))
                sleep(delay)
                self.refresh_screen()
            if self.tap_refresh_component("menu.main", delay):
                continue 
            if self.tap_refresh_component("menu") and \
                self.tap_refresh_component("menu.main", delay):
                continue 
            if self.tap_refresh_component("back"):
                continue
            if self.validate_component("main.settings"):
                return True
            return False

    def goto_missions(self):
        self.refresh_screen()
        if self.validate_component("missions.main_story.inner"):
            return True
        if not self.home():
            return False
        print("- Navigating to missions page")
        if not self.ensure_tap("main.missions", "missions.main_story.inner"):
            return False
        return True

    def goto_base(self, delay=15):
        self.refresh_screen()
        if self.validate_component("base.main.overview"):
            return True
        print("- Navigating to base page")
        if self.ensure_tap("menu.base", "base.main.overview", delay):
            return True
        if self.ensure_tap("menu", "menu.base") and \
            self.ensure_tap("menu.base", "base.main.overview", delay):
            return True
        print("  Through main page")
        if not self.home():
            return False
        print("  Now from main to base")
        if self.ensure_tap("main.base", "base.main.overview", delay):
            return True
        return False

    def ensure_tap(self, tap, next_page, delay=2.5):
        while True:
            if not self.tap_refresh_component(tap, delay):
                return False
            if self.validate_component(next_page):
                return True

    def is_in_battle(self):
        self.refresh_screen()
        return self.validate_component("in_battle.enemy_icon")
    
    def is_in_autopilot_battle(self):
        self.refresh_screen()
        return self.validate_component("in_battle.autopilot.take_over")
    
    def tap_battle_finished(self, wait=0):
        self.refresh_screen()
        if not self.validate_component("battle_finished.title"):
            return False
        sleep(wait)
        self.tap_refresh_component("battle_finished.title", delay=15)
        return True
    
    def tap_prepare_battle(self):
        self.refresh_screen()
        return self.ensure_tap("map_selected.start", "prepare.start", delay=15)

    def tap_start_battle(self):
        self.refresh_screen()
        return self.ensure_tap("prepare.start", "in_battle.autopilot.take_over", delay=30)

    def refresh_map_info(self):
        self.refresh_screen()
        info = self.query_set("map_selected.info")
        if info:
            self.current_map_name_chi = info[0].replace(" ", "")
            self.current_map_name = info[1]
            try:
                self.current_cost = int(info[2].strip("-"))
                self.current_san = int(info[3].split("/")[0])
            except ValueError:
                return False
            return True
        return False
    
    def goto_map(self, map_name):
        if self.refresh_map_info():
            if self.current_map_name == map_name:
                print("  Currently already on map {}, skipping navigation".format(map_name))
                return

        if not self.goto_missions():
            raise UnexpectedState()

        print("- Navigating to map {}".format(map_name))
        # Obsidian Festival Retrospect
        if map_name.startswith("OF-"):
            if not self.ensure_tap("missions.of_r", "missions.of_r.main"):
                raise UnexpectedState()
            if map_name.startswith("OF-F"):
                if not self.ensure_tap("missions.of_r.fest", "missions.of_r.maps.fest.selected"):
                    raise UnexpectedState()
            else:
                if not self.ensure_tap("missions.of_r.main", "missions.of_r.maps.main.selected"):
                    raise UnexpectedState()
            search_result = self.search("maps.map_entry", lambda r: (r[0] and map_name in r[0]) or (r[1] and map_name in r[1]))
            if len(search_result) != 1:
                raise UnexpectedState()
            self.tap_refresh(*search_result[0][2])
            if not self.refresh_map_info():
                raise UnexpectedState()
            if self.current_map_name != map_name:
                raise UnexpectedState()
            return
        raise Unsupported()


    def farm_map(self, map_name, times=None, sanity_recovery=True,
        check_intern=30,
        battle_finish_wait_time=(10, 70),
        recovery_wait_time=(30, 600),
        retries=5, retry_intern=15):
        # Special cases
        # Force sanity recovery off for Obsidian Festival stages
        if map_name.startswith("OF-F"):
            sanity_recovery = False

        count = 0
        while True:
            self.goto_map(map_name)
            print("- Farming {} {}: Round {}/{}".format(self.current_map_name, self.current_map_name_chi, count + 1, times if times else "INF"))
            print("  Current san: {} / Needed: {}".format(self.current_san, self.current_cost))
            if self.current_san < self.current_cost:
                if sanity_recovery:
                    wait_min = (self.current_cost - self.current_san) * 6 
                    print("  Not enough san, waiting for recovery: ", wait_min, "min")
                    recovery_wait_sec = randint(*recovery_wait_time)
                    print("  Adding {} secs as additional recovery time".format(recovery_wait_sec))
                    wait_sec = 60 * wait_min + recovery_wait_sec
                    next_run_ts = int(time()) + wait_sec
                    print("- Next scheduled check time: ", datetime.fromtimestamp(next_run_ts))
                    sleep(wait_sec)
                    continue
                else:
                    print("- San used up")
                    return
            if not self.tap_prepare_battle():
                raise UnexpectedState()
            if not self.tap_start_battle():
                raise UnexpectedState()

            print("  Battle started")
            failure_timer = 0
            while True:
                if self.is_in_autopilot_battle():
                    print("  Battle still running, wait {} secs".format(check_intern))
                    sleep(check_intern)
                    continue
                if battle_finish_wait_time:
                    wait_secs = randint(*battle_finish_wait_time)
                    print("  Wait for {} seconds in result page before proceeding".format(wait_secs))
                else:
                    wait_secs = 0
                if self.tap_battle_finished(wait_secs):
                    print("  Battle finished")
                    break
                else:
                    print("  State recognition failure: {}/{}".format(failure_timer + 1, retries))
                    if failure_timer >= retries:
                        raise UnexpectedState()
                    failure_timer += 1
                    print("  Retrying after {} secs".format(retry_intern))
                    sleep(retry_intern)
            count += 1
            if times and count >= times:
                print("- Farm Finished")
                return
    


