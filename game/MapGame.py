import matplotlib.pyplot as plt
import matplotlib
# from matplotlib import mpl
import numpy as np
# import matplotlib.animation as animation
import random
import math

def loadMap():
    dataset="map.json"
    import json
    dataFile = open(dataset)
    s = dataFile.read()
    data = json.loads(s)
    dataFile.close()
    return data["map"]
    
# make values from -5 to 5, for this example
zvals = loadMap()

print zvals


class Map(object):
    
    def __init__(self, map):
        self._map = map
        self._agent = np.array([7,7])
        self._target = np.array([8,8])
        # self._map[self._target[0]][self._target[1]] = 1
        
        obstacles = []
        obstacles.append([2, 3])
        obstacles.append([3, 7])
        obstacles.append([-4, 6])
        obstacles.append([-7, -6])
        obstacles.append([-6, -6])
        
        self._obstacles = np.array(obstacles)+8.0 # shift coordinates
        
        self._bounds = np.array([[0,0], [15,15]])
        
        self._markerSize = 25
        
    def reset(self):
        self._agent = np.array([random.randint(0,15),random.randint(0,15)])
        
    def getAgentLocalState(self):
        """
            Returns a vector of value [-1,1]
        """
        
        st_ = self._map[(self._agent[0]-1)::2, (self._agent[1]-1)::2] # submatrix around agent location
        st_ = np.reshape(st_, (1,)) # Make vector
        return st_
        
    def move(self, action):
        """
        action in [0,1,2,3,4,5,6,7]
        """
        return {
            0: [-1,0],
            1: [-1,1],
            2: [0,1],
            3: [1,1],
            4: [1,0],
            5: [1,-1],
            6: [0,-1],
            7: [-1,-1],
            }.get(action, [-1,0]) 
            
    def act(self, action):
        move = np.array(self.move(action))
        # loc = self._agent + (move * random.uniform(0.5,1.0))
        loc = self._agent + (move)
        
        if (((loc[0] < self._bounds[0][0]) or (loc[0] > self._bounds[1][0]) or 
            (loc[1] < self._bounds[0][1]) or (loc[1] > self._bounds[1][1])) or
            self.collision(loc) or
            self.fall(loc)):
            # Can't move ouloct of map
            return self.reward() + -8
            
        # if self._map[loc[0]-1][loc[1]-1] == 1:
            # Can't walk onto obstacles
        #     return self.reward() +-5
        self._agent = loc
        return self.reward()
    
    def actContinuous(self, action):
        move = np.array(action)
        # loc = self._agent + (move * random.uniform(0.5,1.0))
        loc = self._agent + (move)
        
        if (((loc[0] < self._bounds[0][0]) or (loc[0] > self._bounds[1][0]) or 
            (loc[1] < self._bounds[0][1]) or (loc[1] > self._bounds[1][1])) or
            self.collision(loc) or
            self.fall(loc)):
            # Can't move out of map
            return -8
            
        # if self._map[loc[0]-1][loc[1]-1] == 1:
            # Can't walk onto obstacles
        #     return self.reward() +-5
        self._agent = loc
        return self.reward()
    
    def fall(self, loc):
        # Check to see if collision at loc with any obstacles
        # print int(math.floor(loc[0])), int(math.floor(loc[1]))
        if self._map[int(math.floor(loc[0]))][ int(math.floor(loc[1]))] < 0:
            return True
        return False
    
    def collision(self, loc):
        # Check to see if collision at loc with any obstacles
        for obs in self._obstacles:
            a=(loc - obs)
            d = np.sqrt((a*a).sum(axis=0))
            if d < 0.3:
                # print "Found collision"
                return True
        return False
    
    def reward(self):
        # More like a cost function for distance away from target
        # print "Agent Loc: " + str(self._agent)
        # print "Target Loc: " + str(self._target)
        a=(self._agent - self._target)
        d = np.sqrt((a*a).sum(axis=0))
        # print "Dist Vector: " + str(a) + " Distance: " + str(d)
        if d < 0.3:
            return 16.0
        return 0
    
    def getState(self):
        return self._agent
    
    def setState(self, st):
        self._agent = st
    
    def init(self, U, V, Q):
        colours = ['gray','black','blue']
        cmap = matplotlib.colors.ListedColormap(['gray','black','blue'])
        bounds=[-1,-1,1,1]
        norm = matplotlib.colors.BoundaryNorm(bounds, cmap.N)
        

        plt.ion()
        
        # Two subplots, unpack the axes array immediately
        self._fig, (self._map_ax, self._policy_ax) = plt.subplots(1, 2, sharey=False)
        self._fig.set_size_inches(18.5, 10.5, forward=True)
        self._map_ax.set_title('Map')
        self._particles, = self._map_ax.plot([self._agent[0]], [self._agent[1]], 'bo', ms=self._markerSize)
        
        self._map_ax.plot([self._target[0]], [self._target[1]], 'ro', ms=self._markerSize)
        
        self._map_ax.plot(self._obstacles[:,0], self._obstacles[:,1], 'gs', ms=28)
        # self._line1, = self._ax.plot(x, y, 'r-') # Returns a tuple of line objects, thus the comma        
        
        cmap2 = matplotlib.colors.LinearSegmentedColormap.from_list('my_colormap',
                                                  colours,
                                                 256)
        
        img1 = self._map_ax.imshow(self._map,interpolation='nearest',
                            cmap = cmap2,
                            origin='lower')
        img2 = self._policy_ax.imshow(np.array(self._map)*0.0,interpolation='nearest',
                            cmap = cmap2,
                            origin='lower')
        
        
        # make a color bar
        # self._map_ax.colorbar(img2,cmap=cmap,
        #               norm=norm,boundaries=bounds,ticks=[-1,0,1])
        self._map_ax.grid(True,color='white')
        # self._policy_ax.grid(True,color='white')
        
        # fig = plt.figure()
        #fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
        #ax = fig.add_subplot(111, aspect='equal', autoscale_on=False,
        #                    xlim=(-3.2, 3.2), ylim=(-2.4, 2.4))
        
        # particles holds the locations of the particles
        
        self._policy_ax.set_title('Policy')
        
        X,Y = np.mgrid[0:self._bounds[1][0]+1,0:self._bounds[1][0]+1]
        print X,Y
        # self._policy = self._policy_ax.quiver(X[::2, ::2],Y[::2, ::2],U[::2, ::2],V[::2, ::2], linewidth=0.5, pivot='mid', edgecolor='k', headaxislength=5, facecolor='None')
        textstr = """$\max q=%.2f$\n$\min q=%.2f$"""%(np.max(Q), np.min(Q))
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.75)
        
        # place a text box in upper left in axes coords
        self._policyText = self._policy_ax.text(0.05, 0.95, textstr, transform=self._policy_ax.transAxes, fontsize=14,
                verticalalignment='top', bbox=props)
        q_max = np.max(Q)
        q_min = np.min(Q)
        Q = (Q - q_min)/ (q_max-q_min)
        self._policy2 = self._policy_ax.quiver(X,Y,U,V,Q, alpha=.75, linewidth=1.0, pivot='mid', angles='xy', linestyles='-', scale=25.0)
        self._policy = self._policy_ax.quiver(X,Y,U,V, linewidth=0.5, pivot='mid', edgecolor='k', headaxislength=3, facecolor='None', angles='xy', linestyles='-', scale=25.0)
        
        # self._policy_ax.set_aspect(1.)
    
    def update(self):
        """perform animation step"""
        # update pieces of the animation
        # self._agent = self._agent + np.array([0.1,0.1])
        # print "Agent loc: " + str(self._agent)
        self._particles.set_data(self._agent[0], self._agent[1] )
        self._particles.set_markersize(self._markerSize)
        # self._line1.set_ydata(np.sin(x + phase))
        self._fig.canvas.draw()
        
    def updatePolicy(self, U, V, Q):
        # self._policy.set_UVC(U[::2, ::2],V[::2, ::2])
        textstr = """$\max q=%.2f$\n$\min q=%.2f$"""%(np.max(Q), np.min(Q))
        self._policyText.set_text(textstr)
        q_max = np.max(Q)
        q_min = np.min(Q)
        Q = (Q - q_min)/ (q_max-q_min)
        self._policy2.set_UVC(U, V, Q)
        # self._policy2.set_vmin(1.0)
        """
        self._policy2.update_scalarmappable()
        print "cmap " + str(self._policy2.cmap)  
        print "Face colours" + str(self._policy2.get_facecolor())
        colours = ['gray','black','blue']
        cmap2 = mpl.colors.LinearSegmentedColormap.from_list('my_colormap',
                                                   colours,
                                                   256)
        self._policy2.cmap._set_extremes()
        """
        self._policy.set_UVC(U, V)
        self._fig.canvas.draw()
        
    def reachedTarget(self):
        # Might be a little touchy because floats are used
        a=(self._agent - self._target)
        d = np.sqrt((a*a).sum(axis=0))
        return d <= 0.4

    def saveVisual(self, fileName):
        # plt.savefig(fileName+".svg")
        self._fig.savefig(fileName+".svg")