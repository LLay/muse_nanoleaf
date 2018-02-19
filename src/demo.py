import time
import random 
from Orcan2 import Orcan2, Mode
from LightManager import DMXLightManager
from StoppableThread import StoppableThread

# To setup a device
# run olad -l 3
# Then find your device using ola_dev_info, you now need to connect the device's port to your universe
# Then ola_patch  -d {device number} -p {device port} -u {universe} e.g ola_patch  -d 1 -p 0 -u 1c
if __name__ == "__main__":
	try:
		light = Orcan2()
		light.setMode(Mode.DMX_CONTROL)
		light.setBrightness(255)
		light.setFunctionSpeed(255)
		light.setRGB(255, 255, 0)
		lightMan = Orcan2LightManager(lightAddress=1,light=light,tickInterval = .001)
		thread = StoppableThread(target = lightMan.run)
		thread.start()
		while(1):
			pass
	except (KeyboardInterrupt, SystemExit):
		thread.stop()
		sys.exit()