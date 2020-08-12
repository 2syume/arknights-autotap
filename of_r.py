from ConfiguredDriver import ConfiguredDriver


driver = ConfiguredDriver()

try:
    while True:
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
except KeyboardInterrupt:
    pass