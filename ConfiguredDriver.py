from ArkDriver.Driver import ArkDriver
from time import sleep, time
from datetime import datetime
from random import randint

class UnexpectedState(Exception):
    pass

class Unsupported(Exception):
    pass

FAIL_RETRY = 5
RETRY_INTERN = 15

class ConfiguredDriver(ArkDriver):
    def __init__(self):
        ArkDriver.__init__(self)
        self.load_from_file()
        self.current_san = 0
        self.current_cost = 0
        self.current_map_name = ""
        self.current_map_name_chi = ""

    def handle_popup(self):
        pass


    def interrupt_user(self, check_intern=60):
        while self.is_in_battle():
            print("  Navigation: wait {} secs for running battle".format(check_intern))
        if self.tap_battle_finished():
            print("  Leaving battle finished page")

    def goto_missions(self, check_intern=60):
        failure_timer = 0
        while failure_timer < FAIL_RETRY:
            self.refresh_screen()
            if self.validate_component("missions.main_story.selected"):
                return True

            print("- Navigating to missions page")
            self.interrupt_user(check_intern)

            if self.tap_refresh_component("main.missions"):
                return True
            if self.tap_refresh_component("menu") and self.tap_refresh_component("menu.main") and self.tap_refresh_component("main.missions"):
                return True
            
            print("  State recognition failure: {}/{}".format(failure_timer + 1, FAIL_RETRY))
            failure_timer += 1
        return False

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
        return self.tap_refresh_component("map_selected.start", delay=15)

    def tap_start_battle(self):
        self.refresh_screen()
        return self.tap_refresh_component("prepare.start", delay=30)

    def refresh_map_info(self):
        self.refresh_screen()
        info = self.query_set("map_selected.info")
        if info:
            self.current_map_name_chi = info[0].replace(" ", "")
            self.current_map_name = info[1]
            self.current_cost = int(info[2].strip("-"))
            self.current_san = int(info[3].split("/")[0])
            return True
        return False
    
    def goto_map(self, map_name, check_intern=60):
        if self.refresh_map_info():
            if self.current_map_name == map_name:
                print("  Currently already on map {}, skipping navigation".format(map_name))
                return

        if not self.goto_missions(check_intern=check_intern):
            raise UnexpectedState()

        print("- Navigating to map {}".format(map_name))
        # Obsidian Festival Retrospect
        if map_name.startswith("OF-"):
            if not self.tap_refresh_component("missions.of_r"):
                raise UnexpectedState()
            if map_name.startswith("OF-F"):
                if not self.tap_refresh_component("missions.of_r.fest"):
                    raise UnexpectedState()
            else:
                if not self.tap_refresh_component("missions.of_r.main"):
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


    def farm_map(self, map_name, times=None, sanity_recovery=True, check_intern=60, wait_time=(30, 60)):
        # Special cases
        # Force sanity recovery off for Obsidian Festival stages
        if map_name.startswith("OF-F"):
            sanity_recovery = False

        count = 0
        while True:
            self.goto_map(map_name, check_intern=check_intern)
            print("- Farming {} {}: Round {}/{}".format(self.current_map_name, self.current_map_name_chi, count + 1, times if times else "INF"))
            print("  Current san: {} / Needed: {}".format(self.current_san, self.current_cost))
            if self.current_san < self.current_cost:
                if sanity_recovery:
                    wait_min = (self.current_cost - self.current_san) * 6 
                    print("  Not enough san, waiting for recovery: ", wait_min, "min")
                    next_run_ts = int(time()) + wait_min * 60
                    print("- Next scheduled check time: ", datetime.fromtimestamp(next_run_ts))
                    sleep(60 * wait_min)
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
                if wait_time:
                    wait_secs = randint(*wait_time)
                    print("  Wait for {} seconds in result page before proceeding".format(wait_secs))
                else:
                    wait_secs = 0
                if self.tap_battle_finished(wait_secs):
                    print("  Battle finished")
                    break
                else:
                    print("  State recognition failure: {}/{}".format(failure_timer + 1, FAIL_RETRY))
                    failure_timer += 1
                    if failure_timer >= FAIL_RETRY:
                        raise UnexpectedState()
                    print("  Retrying after {} secs".format(RETRY_INTERN))
                    sleep(RETRY_INTERN)
            count += 1
            if times and count >= times:
                print("- Farm Finished")
                return
    


