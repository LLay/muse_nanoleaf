import time
import random 
from Orcan2 import Orcan2, Mode
from LightManager import Orcan2LightManager
from StoppableThread import StoppableThread

# To setup a device
# run olad -l 3
# Then find your device using ola_dev_info, you now need to connect the device's port to your universe
# Then ola_patch  -d {device number} -p {device port} -u {universe} e.g ola_patch  -d 1 -p 0 -u 1c
if __name__ == "__main__":
	try:
		lightMan = Orcan2LightManager(tickInterval = .001)
		thread = StoppableThread(target = lightMan.run)
		thread.start()
		while(1):
			red=random.randint(0,255)
			green=random.randint(0,255)
			blue=random.randint(0,255)
			lightMan.light.setRGB(red,green,blue)
			time.sleep(1)
	except (KeyboardInterrupt, SystemExit):
		thread.stop()
		sys.exit()