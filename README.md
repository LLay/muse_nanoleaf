# muse_dmx
A tool to visualize eeg waves captured by a Muse headband on a network of DMX lights

![alt text](https://github.com/LLay/muse_light_installation/blob/master/resources/IMG_20180224_220502.jpg)

### Dependencies
- [museSDK](http://developer.choosemuse.com/sdk/ios) (which includes [museIO](http://developer.choosemuse.com/tools/museio))
- [pyliblo](http://das.nasophon.de/pyliblo/)
- [our fork of OLA](https://github.com/Etragas/ola) ⚠️ (Only for the brave of heart)
- DMX Drivers
- python 2.7

### Set up a light

- run `olad -l 3`
- Then find your device using ola_dev_info, you now need to connect the device's port to your universe
- Then `ola_patch  -d {device number} -p {device port} -u {universe} e.g ola_patch  -d 1 -p 0 -u 1c`

See demo.py for more info

### Run it
- Connect the muse to your laptops bluetooth
- run `run olad -l 3`
- run `muse-io --osc osc.udp://localhost:5000` (in a separate window) to serve the muse data on port 5000 (if you wish to server the same data across multiple ports just add those as well: `muse-io --osc osc.udp://localhost:5000;osc.udp://localhost:5001`)
- run the museServer (in a separate window) `python src/museServer.py`

### Code
Developed on OSX 10.13.3 High Sierra

We used [this example](http://developer.choosemuse.com/research-tools-example/grabbing-data-from-museio-a-few-simple-examples-of-muse-osc-servers#python) to get started with pyliblo

### Resources
- [Muse api](http://developer.choosemuse.com/tools/available-data)
- [OLA API](https://www.openlighting.org/ola/developer-documentation/python-api/)
- [pyliblo](http://das.nasophon.de/pyliblo/) (for OSC messages)
- [ENTEC Driver](http://www.ftdichip.com/Drivers/D2XX.htm)
