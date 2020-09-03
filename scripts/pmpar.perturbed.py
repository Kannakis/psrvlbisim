#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os,sys, argparse
import numpy as np
from numpy.random import default_rng
from astropy import units as u
from astropy.coordinates import SkyCoord
import random
from numpy.random import Generator, PCG64


# In[2]:


#defining the classes 
class Observation:
    def __init__(self, line):
        splitline = line.split()
        self.date = float(splitline[0])
        self.rauncertainty = float(splitline[2]) # This is in "seconds", which is arcseconds / (15 * cos(declination)
        self.decuncertainty = float(splitline[4]) # This is in arcseconds
        self.position = SkyCoord(splitline[1], splitline[3], frame='icrs', unit=(u.hourangle, u.deg))

    def perturbposition(self, deltaramas, deltadecmas):
        self.position = SkyCoord(self.position.ra + deltaramas*u.mas, self.position.dec + deltadecmas * u.mas)

    def addUncertainty(self, rauncertaintymas, decuncertaintymas):
        self.rauncertainty = np.sqrt(self.rauncertainty**2 + (rauncertaintymas/(15000.0*np.cos(self.position.dec.value)))**2)
        self.decuncertainty = np.sqrt(self.decuncertainty**2 + (decuncertaintymas/1000.0)**2)

    def to_string(self):
        rastring = self.position.to_string(decimal=False,sep=':',unit=u.hourangle,pad=True,precision=7).split()[0]
        decstring = self.position.to_string(decimal=False,sep=':',unit=u.deg, pad=True,precision=7).split()[1]
        return("{0:0.4f} {1} {2} {3} {4}".format(self.date, rastring, self.rauncertainty, decstring, self.decuncertainty))


# In[3]:


delta_ra = 3 #scale of perturbations in the RA
delta_dec = -2 #scale of perturbations in the Dec 

newcoords = [] #array for observations
otherlines = [] #array for original coordinates


pmpar1 = open('new.pmpar.in','r') #opens the data file 
pmpar2 = pmpar1.readline() #reads the first line
obs1 = Observation(pmpar2) #defines the line as an observation
print(obs1.to_string()) 
otherlines.append(pmpar2) #writes the original coordinates into the array 
print(otherlines) 

#this is where the code decides whether or not to perturb the positions 
q = [0,1] #choices that the code has
w = [0.5,0.5] #the weight (probability) of each choice 
Z = random.choices(q,w) #the code chooses 
print(Z) #we can see what the code chooses

if Z == [1]:
    RNG = Generator(PCG64(1)) #starts up the random number generator 
    rg1 = RNG.random() #picks a random offset for the RA
    rg2 = RNG.random() #picks a random offset for the Dec
    obs1.perturbposition(rg1*delta_ra, rg2*delta_dec)#perturbs the position by the random offset 
    newcoords.append(obs1.to_string())#adds the perturbed positions into the observations array 
    
else: 
    c = obs1.to_string() #if 0 is picked then the line isn't perturbed
    newcoords.append(c)

print(newcoords)
    


# In[4]:


#repeating loop for all data points
for i in range(32):
    pmpar2 = pmpar1.readline()
    obs1 = Observation(pmpar2)
    otherlines.append(pmpar2)
    
    q = [0,1]
    w = [0.5,0.5]
    Z = random.choices(q,w)
    if Z == [1]:
        RNG = Generator(PCG64(1))
        rg1 = RNG.random()
        rg2 = RNG.random()
        obs1.perturbposition(rg1*delta_ra, rg2*delta_dec)
        newcoords.append(obs1.to_string())
    else: 
        c = obs1.to_string()
        newcoords.append(c)


# In[5]:


newcoords #printing out the new coordinates line by line


# In[6]:


otherlines #printing out the oringal coordinates line by line 


# In[7]:


perturbedout = open("new.pmpar.in" + ".perturbed", "w") #writing and saving a new file named "new.pmpar.in.perturbed"
for obs in newcoords: #then comes the new coordinates
    perturbedout.write("{0}\n".format(obs))
perturbedout.close()


# In[9]:


#seeing if the lines wrote as expected 
c1 = open("new.pmpar.in.perturbed",'r')
c2 = c1.readlines()
c2


# In[ ]:




