class MuseState(object):
    def __init__(self):
        # waves
        self.alpha = 0
        self.beta = 0
        self.delta = 0
        self.gamma = 0
        self.theta = 0
        # is the muse on the users head?
        self.touching_forehead = 0
        # 'connected' is a computed value. see horseshoe_callback() for implementation
        self.connected = 0
        # The current level of connectivity. 0-1
        self.connectionScore = 0
