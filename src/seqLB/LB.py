import numpy as np
import matplotlib.pyplot as plt
import os 

PLOTDIR = os.path.join(os.getcwd() + '/src/plots')

"""
Skeleton code of Lattice Boltzmann class holding all parameters 
and providing basic streaming and collision simulation  
"""
class LB(): 

    rho = None 
    ux = None  
    uy = None

    # Visualization of density grid 
    densityFig, densityAx, densityFigureMesh = None, None, None 
    # Visualization for velocity field using a streamplot 
    velocityFig, velocityAx, velocityStreamPlot = None, None, None 
    
    # initialize density and figures for plotting 
    # default F is all ones but can be initialized arbitrarily 
    def __init__(self, F=[]):
        if F == []:
            self.F = np.ones((self.Ny,self.Nx,self.NL))
        else: 
            self.F = F 
        self.rho = self.calculateDensity()
        self.ux, self.uy = self.calculateVelocity()
        self.xaxis = np.linspace(0, self.Nx, self.Nx)
        self.yaxis = np.linspace(0, self.Ny, self.Ny)
        self.X, self.Y = np.meshgrid(self.xaxis, self.yaxis)
        self.densityFig, self.densityAx = plt.subplots()
        self.densityFigureMesh = self.densityAx.pcolormesh(self.X, self.Y, self.rho, shading='auto')
        self.densityFig.savefig(f'{PLOTDIR}/basic/density_timestep{0}.png')
        self.velocityFig, self.velocityAx = plt.subplots()
        self.velocityStreamPlot = self.velocityAx.streamplot(self.X, self.Y, self.ux, self.uy, density = 2)
        self.velocityFig.savefig(f'{PLOTDIR}/basic/velocity_timestep{0}.png')

    # call if parameters are changed to recalc density and velocities
    def fitParams(self): 
        self.__init__()

    # Grid size in x and y directions 
    Nx = 50
    Ny = 50

    # omega used for collision calculation to control the time needed to reach equilibrium state 
    # equivalent to 1/tau
    # smaller omega --> slower collisions to reach eq --> high viscosity (dickflüssig)
    # larger omega --> faster collisions
    omega = 1

    # we are modeling LB with 9 directions, setting index will be handy later 
    NL = 9
    idxs = np.arange(NL)

    # velocity vectors, splitted into x and y components
    cxs = np.array([0, 0, 1, 1, 1, 0,-1,-1,-1])
    cys = np.array([0, 1, 1, 0,-1,-1,-1, 0, 1])

    # weights we use
    weights = np.array([4/9,1/9,1/36,1/9,1/36,1/9,1/36,1/9,1/36]) 
    # weights should add up to one
    assert(np.sum(weights) == 1)

    """
    F is the matrix used to calculate density and velocity field 
    The first axis represents the y coordinate of the grid, the second represents the x coordinate (CARE: its (y,x) so the representation is more intuitive)
    Further the third axis represents the directions (degrees of freedom) we use, that means each lattice points has an array of 9 used for calculations later  

    [       x0         x1         x2
    [ [ [0..8] ] [ [0..8] ] [ [0..8] ] ] y0
    [ [ [0..8] ] [ [0..8] ] [ [0..8] ] ] y1
    [ [ [0..8] ] [ [0..8] ] [ [0..8] ] ] y2
    ]

    Example visualization of F
    """

    # Initialization of F 
    F = np.ones((Ny,Nx,NL))

    # calculates density for each lattice point over third axis of F 
    # that means to sum up the 9 density values of each lattice point 
    def calculateDensity(self): 
        self.rho = np.sum(self.F,2)
        return self.rho

    # calculates the velocity at each lattice point by doint the same calculation as for density but multiplied by our 
    # velocity vectors and dividing by the density 
    # returns tuple of array which hold x respectively y value for each lattice point 
    def calculateVelocity(self):
        self.ux = np.sum(self.F*self.cxs,2) / self.rho
        self.uy = np.sum(self.F*self.cys,2) / self.rho
        return (self.ux, self.uy)

    # mass of the fluid, can be used to verify mass conservation between timesteps
    def mass(self):
        return np.sum(self.rho)

    # used for plotting 
    xaxis = np.linspace(0, Nx, Nx)
    yaxis = np.linspace(0, Ny, Ny)
    X, Y = np.meshgrid(xaxis, yaxis)

    # function to update the density meshgrid 
    def updateDensityFigure(self, density, timestep = 0):
        self.densityAx.set_title(f"timestep: {timestep} omega: {self.omega}")
        self.densityFigureMesh.update({'array':density})
        self.densityFig.savefig(f'{PLOTDIR}/basic/density_timestep{timestep}.png')

    # function to update the velocity field grid 
    def updateVelocityFigure(self, ux, uy, timestep = 0):
        self.velocityAx.set_title(f"timestep: {timestep} omega: {self.omega}")
        self.velocityAx.cla()
        self.velocityAx.streamplot(self.X, self.Y, ux, uy, density = 2)  
        self.velocityFig.savefig(f'{PLOTDIR}/basic/velocity_timestep{timestep}.png')


    # Streaming function
    # For each lattice point and each direction i, the value in Fi is shifted to the neighbor lattice side 
    def streaming(self):     
        for i, cx, cy in zip(self.idxs, self.cxs, self.cys):
            self.F[:,:,i] = np.roll(self.F[:,:,i], cx, axis=1)
            self.F[:,:,i] = np.roll(self.F[:,:,i], cy, axis=0)

    def collision(self):
        # simulate collisions 
        # calculate the local equilibrium for each lattice point by given equation
        # basically each lattice point gets added a fraction of its difference to the equilibrium  
        # the fraction is controlled by the omega value with the following interpretation 
        # smaller omega --> slower collisions to reach eq --> high viscosity
        # larger omega --> faster collisions
        Feq = self.calcFeq(self.rho, self.ux, self.uy)
        self.F += self.omega * (Feq - self.F)

    def calcFeq(self, rho, ux, uy): 
        # calculate the local equilibrium for each lattice point 
        Feq = np.zeros(self.F.shape)
        for i, cx, cy, w in zip(self.idxs, self.cxs, self.cys, self.weights):
            Feq[:,:,i] = rho*w* (1 + 3*(cx*ux+cy*uy) + 9*(cx*ux+cy*uy)**2/2 - 3*(ux**2+uy**2)/2)
        return Feq
    

    # Basic simulation function  
    def simulate(self, timesteps=1000):
        
        for _ in range(timesteps):
            # apply drift/stream
            self.streaming()

            # Recalc local variables 
            self.rho = self.calculateDensity()
            self.ux, self.uy  = self.calculateVelocity()

            # apply collision
            self.collision()