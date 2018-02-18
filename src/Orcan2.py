from enum import Enum

class Mode(Enum):
	MODE_DMX_CONTROL = 0
	MODE_JUMP = 51
	MODE_FADE = 101
	MODE_PULSE = 151
	MODE_SOUND = 201

class Orcan2:
	BRIGHTNESS_DEFAULT = 125
	STROBE_INTENSITY_DEFAULT = 0
	MODE_DEFAULT = Mode.MODE_DMX_CONTROL
	FUN_SPEED_DEFAULT = 0
	RED_INTENSITY_DEFAULT = 255
	GREEN_INTENSITY_DEFAULT = 255
	BLUE_INTENSITY_DEFAULT = 255
	
	def __init__(self, brightness = BRIGHTNESS_DEFAULT, strobeIntensity = STROBE_INTENSITY_DEFAULT, functionMode=MODE_DEFAULT, functionSpeed = FUN_SPEED_DEFAULT, redIntensity = RED_INTENSITY_DEFAULT, greenIntensity = GREEN_INTENSITY_DEFAULT, blueIntensity = BLUE_INTENSITY_DEFAULT):
		self.brightness = brightness
		self.strobeIntensity = strobeIntensity
		self.functionMode = functionMode
		self.functionSpeed = functionSpeed
		self.redIntensity = redIntensity
		self.greenIntensity = greenIntensity
		self.blueIntensity = blueIntensity

	def getStateAsArray(self):
		return [self.brightness, self.strobeIntensity, self.functionMode,
		 self.functionSpeed, self.redIntensity, self.greenIntensity, self.blueIntensity]

	def update(self, **kwargs):
		for attr, value in kwargs.items():
			setattr(self,attr,value) 

	def checkRange(self, val, lower=0, upper=255):
		if val < lower or val > upper:
			raise ValueError("{} needs to be between {} and {}".format(val,lower,upper))

	def setBrightness(self, brightness):
		self.checkRange(brightness)
		self.brightness = brightness

	def setRed(self, red):
		self.checkRange(red)
		self.redIntensity = red

	def setGreen(self, green):
		self.checkRange(green)
		self.greenIntensity = green

	def setBlue(self, blue):
		self.checkRange(blue)
		self.blueIntensity = blue

	def setRGB(self, red, green, blue):
		self.setRed(red)
		self.setGreen(green)
		self.setBlue(blue)

	def setMode(self, mode):
		if not isinstance(mode,Mode):
			raise TypeError("Please use the Mode Enum")
		self.mode = mode

	def setStrobeIntensity(self, strobeIntensity):
		checkRange(strobeIntensity)
		self.strobeIntensity = strobeIntensity

	def setFunctionSpeed(self, speed):
		checkRange(speed)
		self.functionSpeed = speed
