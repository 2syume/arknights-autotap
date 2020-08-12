from ConfiguredDriver import ConfiguredDriver, UnexpectedState
import sys

driver = ConfiguredDriver()

try:
    while True:
        try:
            driver.farm_map("OF-F3")

            driver.refresh_screen()
            obsidian_query = driver.query_set("of_r.maps.obsidian_count")
            if not obsidian_query:
                driver.goto_map("OF-6")
                obsidian_query = driver.query_set("of_r.maps.obsidian_count")
            obs_count = int(obsidian_query[0])
            print("- Current Obsidian count: {}".format(obs_count))

            farm_plan = ("OF-6", 3)
            if obs_count >= 1060:
                farm_plan = ("OF-8", 1)
            driver.farm_map(*farm_plan)
        except UnexpectedState:
            last_log = driver.last_log
            exc = driver.recover_from_exc(sys.exc_info())
            if exc is not None:
                print(">>> Last log of failure w/ image")
                driver.print_last_log(last_log=last_log)
                print("<<<")
                raise exc
            else:
                print(">>> Last log of failure")
                driver.print_last_log(last_log=last_log, show_img=False)
                print("<<<")
except KeyboardInterrupt:
    pass