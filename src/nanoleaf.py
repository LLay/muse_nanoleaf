import sys
sys.path.insert(0, '/Users/lay/workspace/dmx-lib/muse_controller/nanoleafpy2')
from nanoleaf import setup, Aurora

print "Retrieving auroras..."
ipAddressList = setup.find_auroras()
print "Auroras found:", ipAddressList

# print "Selecting only whitelisted auroras..."
# ipWhitelist = []
# ipAddressList = [x for x in ipAddressList if x in ipWhitelist]
# print "Auroras used:", ipAddressList

print "Retrieving auth tokens..."
ipAuthMap = {}
for ip in ipAddressList:
    ipAuthMap[ip] = setup.generate_auth_token(ip)
print "Tokens generated:", ipAuthMap

print "Instatiating Aurora Objects..."
self.auroras = []
for ip in ipAuthMap:
    self.auroras += [{'aurora': Aurora(ip, ipAuthMap[ip])}]
print "Finished Instatiating Aurora Objects..."

print "Initiating Aurora Metadata..."
self.auroras = {}
for aurora in self.auroras:
    aurora['panelIDs'] = [x.panelId for x in self.aurora.panel_positions()]
print "Finished Initiating Aurora Metadata..."

print "Turning on Auroras"
for aurora in self.auroras:
    aurora['aurora'].on = True
    # aurora['aurora'].effect = ANIMATION_ID
print "Finished Turning on Auroras"

print "Setting lights to white"
self.updateLights(255, 30, 255, 100)
print "Finished setting lights to white"

print "Identifying Auroras..."
for aurora in self.auroras:
    aurora.identify()
