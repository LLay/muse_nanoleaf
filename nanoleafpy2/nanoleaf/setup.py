from __future__ import absolute_import
import requests
import socket
import select
import time

# Setup functions for discovering and authenticating your Auroras
# For instructions or bug reports, please visit
# https://github.com/software-2/nanoleaf


def find_auroras(seek_time = 30):
    u"""
    Returns a list of the IP addresses of all Auroras found on the network

    Discovery will take about 30 seconds by default.
    If your Auroras are not found, try increasing the seek time to 90 seconds.
    """
    SSDP_IP = u"239.255.255.250"
    SSDP_PORT = 1900
    SSDP_MX = 3
    SSDP_ST = u"nanoleaf_aurora:light"

    req = [u'M-SEARCH * HTTP/1.1',
           u'HOST: ' + SSDP_IP + u':' + unicode(SSDP_PORT),
           u'MAN: "ssdp:discover"',
           u'ST: ' + SSDP_ST,
           u'MX: ' + unicode(SSDP_MX)]
    req = u'\r\n'.join(req).encode(u'utf-8')

    aurora_locations = []
    broken_auroras = []

    def get_deviceid(r):
        for line in r.split(u"\n"):
            if u"deviceid:" in line:
                return line.replace(u"nl-deviceid:", u"").strip()

    def check_if_new_aurora(r):
        if SSDP_ST not in r:
            return
        for line in r.split(u"\n"):
            if u"Location:" in line:
                new_location = line.replace(u"Location:", u"").strip() \
                                  .replace(u"http://", u"") \
                                  .replace(u":16021", u"")
                if new_location not in aurora_locations:
                    # BUG: As of firmware 2.1.0, the Aurora's Location may not include an IP address.
                    if new_location == u"":
                        broken = get_deviceid(r)
                        if broken not in broken_auroras:
                            broken_auroras.append(broken)
                            print u"New Aurora found (deviceid: " + broken + u"). But the device does not have an IP address."
                        return
                    aurora_locations.append(new_location)
                    print u"New Aurora found at " + new_location + u" - deviceid:" + get_deviceid(r)
                return

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, SSDP_MX)
    sock.bind((socket.gethostname(), 9090))
    sock.sendto(req, (SSDP_IP, SSDP_PORT))
    sock.setblocking(False)

    timeout = time.time() + seek_time
    print u"Starting discovery. This will continue for " + unicode(seek_time) + u" seconds."
    while time.time() < timeout:
        try:
            ready = select.select([sock], [], [], 5)
            if ready[0]:
                response = sock.recv(1024).decode(u"utf-8")
                check_if_new_aurora(response)
        except socket.error, err:
            print u"Socket error while discovering SSDP devices!"
            print err
            print u"If you are sure your network connection is working,"
            print u"please post an issue on the GitHub page: https://github.com/software-2/nanoleaf/issues"
            print u"Please include as much information as possible, including your OS,"
            print u"how your computer is connected to your network, etc."
            sock.close()
            break

    if len(aurora_locations) == 0:
        print u"Discovery complete, but no Auroras found!"
        return aurora_locations
    print u"Discovery complete! Found " + unicode(len(aurora_locations)) + u" Auroras."
    return aurora_locations


def generate_auth_token(ip_address):
    u"""
    Generates an auth token for the Aurora at the given IP address.

    You must first press and hold the power button on the Aurora for about 5-7 seconds,
    until the white LED flashes briefly.
    """
    url = u"http://" + ip_address + u":16021/api/v1/new"
    r = requests.post(url)
    if r.status_code == 200:
        print u"Auth token for " + ip_address + u" successfully generated!  " + unicode(r.json())
        return r.json()[u'auth_token']
    if r.status_code == 401:
        print u"Not Authorized! I don't even know how this happens. "
        print      u"Please post an issue on the GitHub page: https://github.com/software-2/nanoleaf/issues"
    if r.status_code == 403:
        print u"Forbidden! Press and hold the power button for 5-7 seconds first! (Light will begin flashing)"
    if r.status_code == 422:
        print u"Unprocessable Entity! I'm blaming your network on this one."
    return None
