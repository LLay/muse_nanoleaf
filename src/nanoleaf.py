import sys
sys.path.insert(0, '/Users/lay/workspace/dmx-lib/muse_controller/nanoleafpy2')
from nanoleaf import setup, Aurora

# print "Retrieving auroras..."
# ipAddressList = setup.find_auroras()
# print "Auroras found:", ipAddressList

# ipAddressList = [u'192.168.128.31', u'192.168.128.19', u'192.168.128.32']
# print "Selecting only whitelisted auroras..."
# ipWhitelist = []
# ipAddressList = [x for x in ipAddressList if x in ipWhitelist]
# print "Auroras used:", ipAddressList

# print "Retrieving auth tokens..."
# ipAuthMap = {}
# for ip in ipAddressList:
#     token = setup.generate_auth_token(ip)
#     print "considering token", token
#     if token is not None:
#         ipAuthMap[ip] = token
# print "Tokens generated:", ipAuthMap

ipAuthMap = {
    u'192.168.128.31': u'jcjYtfzt4zusn82lSJ5eHLOPzuiOgoDP',
    u'192.168.128.32': u'WTq3eIKY8fdfgGZjQlvbbe7E7fkKYDW4'
}
print "Instatiating Aurora Objects..."
auroras = []
for ip in ipAuthMap:
    auroras += [{'aurora': Aurora(ip, ipAuthMap[ip])}]
print "Finished Instatiating Aurora Objects..."

print "Initiating Aurora Metadata..."
for aurora in auroras:
    aurora['panelIDs'] = [x['panelId'] for x in aurora['aurora'].panel_positions]
    # print "aura panel meta data", aurora['panelIDs']
print "Finished Initiating Aurora Metadata..."

print "Turning on Auroras"
for aurora in auroras:
    aurora['aurora'].on = True
    # aurora['aurora'].effect = ANIMATION_ID
print "Finished Turning on Auroras"

# print "Setting lights to white"
# updateLights(255, 30, 255, 100)
# print "Finished setting lights to white"

# print "Identifying Auroras..."
# for aurora in auroras:
#     aurora['aurora'].identify()
