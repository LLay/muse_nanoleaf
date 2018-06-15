from StoppableThread import StoppableThread
from threading import Thread, Event

import array
import sys
import colorsys

from nanoleaf import setup, Aurora

from multiprocessing import Pool

ANIMATION_ID = "myanimation"

class NanoleafLightManager:
    def __init__(self):

        # TODO this shit needs to be automated
        ipAuthMap = {
            u'192.168.128.31': u'jcjYtfzt4zusn82lSJ5eHLOPzuiOgoDP',
            u'192.168.128.32': u'WTq3eIKY8fdfgGZjQlvbbe7E7fkKYDW4'
        }
        print "Instatiating Aurora Objects..."
        self.auroras = []
        for ip in ipAuthMap:
            print "ip:", ip
            print "token:", ipAuthMap[ip]
            self.auroras += [{'aurora': Aurora(ip, ipAuthMap[ip])}]
        print "Finished Instatiating Aurora Objects..."

        print "Initiating Aurora Metadata..."
        for aurora in self.auroras:
            aurora['panelIDs'] = [x['panelId'] for x in aurora['aurora'].panel_positions]
        print "Finished Initiating Aurora Metadata..."

        print "Turning on Auroras"
        for aurora in self.auroras:
            aurora['aurora'].on = True
            # aurora['aurora'].effect = ANIMATION_ID
        print "Finished Turning on Auroras"

        # self.pool = Pool(processes=2) # Start a worker processes.

# +++++++++++++++++++++++
        # print "Retrieving auroras..."
        # ipAddressList = setup.find_auroras()
        # print "Auroras found:", ipAddressList
        #
        # # print "Selecting only whitelisted auroras..."
        # # ipWhitelist = []
        # # ipAddressList = [x for x in ipAddressList if x in ipWhitelist]
        # # print "Auroras used:", ipAddressList
        #
        # print "Retrieving auth tokens..."
        # ipAuthMap = {}
        # for ip in ipAddressList:
        #     ipAuthMap[ip] = setup.generate_auth_token(ip)
        # print "Tokens generated:", ipAuthMap
        #
        # print "Instatiating Aurora Objects..."
        # self.auroras = []
        # for ip in ipAuthMap:
        #     self.auroras += [{'aurora': Aurora(ip, ipAuthMap[ip])}]
        # print "Finished Instatiating Aurora Objects..."
        #
        # print "Initiating Aurora Metadata..."
        # self.auroras = {}
        # for aurora in self.auroras:
        #     aurora['panelIDs'] = [x.panelId for x in self.aurora.panel_positions()]
        # print "Finished Initiating Aurora Metadata..."
        #
        # print "Turning on Auroras"
        # for aurora in self.auroras:
        #     aurora['aurora'].on = True
        #     # aurora['aurora'].effect = ANIMATION_ID
        # print "Finished Turning on Auroras"
        #
        # print "Setting lights to white"
        # self.updateLights(255, 255, 255, 100)
        # print "Finished setting lights to white"

    def updateAurora(self, aurora, effect):
        print("Updating aurora {}".format(aurora))
        print("Response", aurora['aurora'].effect_set_raw(effect))
        return 0

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
            "animName": ANIMATION_ID,
            "animType": "static",
            "animData": animData,
            "loop": False
        }

    def kill(self):
        pass
