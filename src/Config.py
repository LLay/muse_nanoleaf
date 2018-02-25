
# How often we update the lights. Measured in seconds. Minimum of 0.1 (You can go lower, but we only get data from the muse at 10Hz)
LIGHT_UPDATE_INTERVAL = 0.01
# How often we internally render an new frame of the default animation
DEFAULT_ANIMATION_RENDER_RATE = 0.01
# Number of second over which we average eeg signals.
ROLLING_EEG_WINDOW = 6
# Number of second over which fade between user input and the default light animation.
USER_TO_DEFAULT_FADE_WINDOW = 3
# The delay in seconds between loss of signal on all contacts and ..doing something about it
CONTACT_LOS_TIMEOUT = 3
# the default brightness of the lights when the user is connected
USER_LIGHT_BRIGHTNESS = 255
# the default brightness of the Default animation
DEFAULT_COLOR_ANIMATION_BRIGHTNESS = 255
DEFAULT_SPOTLIGHT_ANIMATION_BRIGHTNESS = 255
DEFAULT_SPOTLIGHT_ANIMATION_BRIGHTNESS_RANGE = 50

# Light group addresses
EEG_LIGHT_GROUP_ADDRESS= 1
SPOTLIGHT_LIGHT_GROUP_ADDRESS = 8

# How often to print the log message in seconds
LOG_PRINT_RATE = 1

# Correct decimal place for relevant values. XXX Don't change me!
ROLLING_EEG_WINDOW *= 10
CONTACT_LOS_TIMEOUT *= 10
USER_TO_DEFAULT_FADE_WINDOW = USER_TO_DEFAULT_FADE_WINDOW / LIGHT_UPDATE_INTERVAL or 1
