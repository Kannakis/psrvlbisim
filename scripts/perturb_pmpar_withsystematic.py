#!/usr/bin/env python
import os,sys, argparse
import numpy as np
from numpy.random import default_rng
from astropy import units as u
from astropy.coordinates import SkyCoord

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

    def setUncertainty(self, rauncertaintymas, decuncertaintymas):
        self.rauncertainty = rauncertaintymas/(15000.0*np.cos(self.position.dec.value))
        self.decuncertainty = decuncertaintymas/1000.0

    def to_string(self):
        rastring = self.position.to_string(decimal=False,sep=':',unit=u.hourangle,pad=True,precision=7).split()[0]
        decstring = self.position.to_string(decimal=False,sep=':',unit=u.deg, pad=True,precision=7).split()[1]
        return("{0:0.4f} {1} {2} {3} {4}".format(self.date, rastring, self.rauncertainty, decstring, self.decuncertainty))

if __name__ == "__main__":
    # Get some info on what we are expected to do
    parser = argparse.ArgumentParser(description='Read an existing pmpar file and perturb the positions.')
    parser.add_argument('--statisticalsigmara', default=0.5, type=float, help="Standard deviation in mas of the fake observations in R.A.")
    parser.add_argument('--statisticalsigmadec', default=1., type=float, help="Standard deviation in mas of the fake observations in Decl.")
    parser.add_argument('--distribution', default="gaussian", help='Distribution type of the systematic uncertainty to add')
    parser.add_argument('--extent', default=1.0, type=float, help='Extent or std dev of the systematic uncertainty distribution in milliarcseconds')
    parser.add_argument('pmparfile', default="", type=str, nargs=1)

    # Parse the arguments
    args = parser.parse_args()

    # Open the pmpar file
    lines = open(args.pmparfile[0]).readlines()

    # Create a list where we will store the observations
    obslist = []

    # Create a list to store the lines that are not observation lines from the pmpar file
    otherlines = []

    # read in the lines
    for line in lines:
        # Check if it is an observation (length 5)
        if len(line.split()) == 5:
            obslist.append(Observation(line))
        else:
            otherlines.append(line)

    # Now go through the observations with a for loop, adding a random offset and setting the statistical uncertainty to fake an observation
    rng = default_rng() # rng is your random number generator.  See e.g. https://numpy.org/doc/stable/reference/random/index.html for how to use it.

    # Use setUncertainty and perturbposition to set statistical uncertainty and fake a reasonable observation
    for obs in obslist:
        rg1 = rng.random() #picks a random offset for the RA
        rg2 = rng.random() #picks a random offset for the Dec
        obs.perturbposition(args.statisticalsigmara*rg1, args.statisticalsigmadec*rg2)
        obs.setUncertainty(args.statisticalsigmara, args.statisticalsigmadec)

    #added in loop for adding in systematic errors
    for obs in obslist: 
        systematicra = rng.normal(0,args.extent)#chooses a random number from a normal (gaussian) distribution with args.extent bring 1 standard deviation: for the systematic error offset in the RA
        systematicdec = rng.normal(0,args.extent) #same thing as the previous line but for Dec
    # Then write the result back out - first all the "otherlines", then each observation, using the to_string() method
        obs.perturbposition(args.statisticalsigmara*systematicra, args.statisticalsigmadec*systematicdec)


    perturbedout = open(args.pmparfile[0] + ".withsystematic", "w")
    for line in otherlines:
        perturbedout.write(line)
    for obs in obslist:
        perturbedout.write("{0}\n".format(obs.to_string()))
    perturbedout.close()

    # Now loop through the observations again and add an additional perturbation to the position, based on args.extent and args.distribution
    # It's fine to just handle distribution == gaussian for now
    # But don't adjust the uncertainty with setUncertainty


    # Then write this further changed result out into a file called args.pmparfile[0] + ".withsystematic"


