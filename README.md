# muse_dmx
A tool to visualize eeg waves captured by a Muse headband on a network of DMX lights

### Dependencies
- [museSDK](http://developer.choosemuse.com/sdk/ios) (which includes [museIO](http://developer.choosemuse.com/tools/museio))
- [pyliblo](http://das.nasophon.de/pyliblo/)
- [our fork of OLA](https://github.com/Etragas/ola)
- DMX Drivers 
- python 2.7

### Run it
- Connect the muse to your laptops bluetooth
- run `muse-io --osc osc.udp://localhost:5000` to serve the muse data on port 5000 (if you wish to server the same data across multiple ports just add those as well: `muse-io --osc osc.udp://localhost:5000;osc.udp://localhost:5001`)
- run this server (in a seperate window) `python museServer.py`

### Code
Developed on OSX 10.13.3 High Sierra

We used [this example](http://developer.choosemuse.com/research-tools-example/grabbing-data-from-museio-a-few-simple-examples-of-muse-osc-servers#python) to get started with pyliblo

### Resources
[Muse api](http://developer.choosemuse.com/tools/available-data)
[OLA API](https://www.openlighting.org/ola/developer-documentation/python-api/)
