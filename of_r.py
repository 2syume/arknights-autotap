from ConfiguredDriver import ConfiguredDriver


driver = ConfiguredDriver()

while True:
    driver.farm_map("OF-6", times=3)
    driver.farm_map("OF-F3")