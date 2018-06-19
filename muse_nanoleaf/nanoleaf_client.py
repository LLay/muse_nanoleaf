from StoppableThread import StoppableThread
from threading import Thread, Event

import array
import sys
import colorsys
import file

from pathlib import Path
from nanoleaf import setup, Aurora
from multiprocessing import Pool

SEARCH_TIME = 10

# contains class property `auroras`, which is an array of nanoleaf aurora objects
# supplied by the `nanoleaf` package that provide an interface to the nanoleaf API
class NanoleafClient:
    def __init__(self, should_find_new_auroras: Boolean):
        auroraCredentialsPath = Path("./.auroraCredentials.csv")
        if not auroraCredentialsPath.is_file() or should_find_new_auroras:
            self.find_auroras(auroraCredentialsPath)

        self.connect_to_auroras(auroraCredentialsPath)

    def find_auroras(self, auroraCredentialsPath: Path):
        auroraCredentialsPath.unlink()
        auroraCredentialsPath.touch()
        self.auroras = []
        print "Retrieving auroras. This will take" + SEARCH_TIME + "second(s)"
        for auroraIpAddress in setup.find_auroras(SEARCH_TIME):
            auth_token = setup.generate_auth_token(ip)
            print("Found aurora at ip: " + ip + " with token: " + auth_token)
            auroraCredentialsPath.write(ip + "," + auth_token)

    def connect_to_auroras(self, path: Path):
        fileContents = path.open("r").read()
        lines = fileContents.split("\n")
        for line in lines:
            tokens = line.split(",")
            ip = tokens[0]
            auth_token = tokens[1]

            print("Instantiating Aurora object for aurora at ip: {1} with token: {2}".format(ip, auth_token))
            aurora = Aurora(ip, auth_token)
            aurora['aurora'].on = True
            self.auroras += [{
                'aurora': aurora,
                'panelIDs': [x.panelId for x in self.aurora.panel_positions()],
            }]

    def updateAurora(self, aurora, effect):
        print("Updating aurora {}".format(aurora))
        print("Response", aurora['aurora'].effect_set_raw(effect))
        return 0 # TODO remove return?

    def updateLights(self, r, g, b, brightness):
        # TODO Modify RGB values by brightness. Experimental:
        r = int(r * (brightness / 255.0))
        g = int(g * (brightness / 255.0))
        b = int(b * (brightness / 255.0))

        threads = []
        for aurora in self.auroras:
            try:
                effect = self.getStaticEffect(aurora, r,g,b)
                t = Thread(target=self.updateAurora, args=(aurora, effect,))
                # t.setDaemon(True)
                threads.append(t)
                # lightServerThreadNanoleaf = StoppableThread(self.updateAurora)
                # lightServerThreadNanoleaf.start()
                # aurora['aurora'].effect_set_raw(effect)

                # result = self.pool.apply_async(self.updateAurora, [aurora, effect])
                # print "result", result, result.get()

            except Exception, err:
                print "Exception in NanoleafClient.updateLights(): ", err.__class__.__name__, err.message

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    def getStaticEffect(self, aurora, r, g, b):
        panelIDs = aurora['panelIDs']
        numFrames = 1
        transitionTime = 1 # Decaseconds

        # animData is of the form: <numPanels> <panelId0> <numFrames0> <RGBWT01> <RGBWT02> ... <RGBWT0n(0)> <panelId1> <numFrames1> <RGBWT11> <RGBWT12> ... <RGBWT1n(1)> ... ... <panelIdN> <numFramesN> <RGBWTN1> <RGBWTN2> ... <RGBWTNn(N)>
        animData = "%d " % (len(panelIDs))
        for panelID in panelIDs:
            animData += "%d %d %d %d %d 0 %d " % (panelID, numFrames, r, g, b, transitionTime)

        return {
            "command": "add",
            "animName": "myanimation",
            "animType": "static",
            "animData": animData,
            "loop": False
        }

    def kill(self):
        pass
