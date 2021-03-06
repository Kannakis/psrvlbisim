#!/usr/bin/env python
import os,sys, argparse, copy
import numpy as np
import pandas as pd
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
        self.rauncertainty = np.sqrt(self.rauncertainty**2 + (rauncertaintymas/(15000.0*np.cos(self.position.dec.value*np.pi/180)))**2)
        self.decuncertainty = np.sqrt(self.decuncertainty**2 + (decuncertaintymas/1000.0)**2)

    def setUncertainty(self, rauncertaintymas, decuncertaintymas):
        self.rauncertainty = rauncertaintymas/(15000.0*np.cos(self.position.dec.value*np.pi/180))
        self.decuncertainty = decuncertaintymas/1000.0

    def to_string(self):
        rastring = self.position.to_string(decimal=False,sep=':',unit=u.hourangle,pad=True,precision=7).split()[0]
        decstring = self.position.to_string(decimal=False,sep=':',unit=u.deg, pad=True,precision=7).split()[1]
        return("{0:0.4f} {1} {2} {3} {4}".format(self.date, rastring, self.rauncertainty, decstring, self.decuncertainty))

class PmparFitResult:
    def __init__(self, filename, nepochs):
        self.nepochs = nepochs
        if not os.path.exists(filename):
            print(filename + " doesn't exist, aborting)")
            sys.exit()
        lines = open(filename).readlines()
        self.name = "???"
        toadd = 0
        if "Name" in lines[0]:
            self.name = lines[0].split('=')[1].strip()
            toadd = 1
        self.epochmjdstring = lines[0+toadd].split('=')[1].strip()
        self.position = SkyCoord(lines[1+toadd].split('=')[1].strip().split()[0], lines[2+toadd].split('=')[1].strip().split()[0], frame='icrs', unit=(u.hourangle, u.deg))
        self.glstring = lines[3+toadd].split('=')[1].strip()
        self.gbstring = lines[4+toadd].split('=')[1].strip()
        self.pmrastring = lines[5+toadd].split('=')[1].strip().split('(')[0].strip()
        self.pmdecstring = lines[6+toadd].split('=')[1].strip()
        self.pmglstring = lines[7+toadd].split('=')[1].strip()
        self.pmgbstring = lines[8+toadd].split('=')[1].strip()
        self.pxstring = lines[9+toadd].split('=')[1].strip()
        self.px = float(self.pxstring.split()[0])
        self.pxerr = float(self.pxstring.split()[2])
        self.diststring = lines[10+toadd].split('=')[1].strip()
        self.vtstring = lines[11+toadd].split('=')[1].strip()
        self.scatterx = float(lines[14+toadd].split()[2])
        self.scattery = float(lines[15+toadd].split()[2])
        self.rchisqstring = lines[16+toadd].split()[3]
        self.rchisq = 9999999999.99
        if not self.rchisqstring == "inf":
            self.rchisq = float(self.rchisqstring)
        self.rchisqstring = self.rchisqstring
        self.pmramas = float(self.pmrastring.split()[0])
        self.pmdecmas = float(self.pmdecstring.split()[0])
        self.pmramaserr = float(self.pmrastring.split()[2])
        self.pmdecmaserr = float(self.pmdecstring.split()[2])

    def storedata(self, df, dfindex):
        df['Parallax'][dfindex] = self.px
        df['ParallaxUncertainty'][dfindex] = self.pxerr
        df['PMRA'][dfindex] = self.pmramas
        df['PMRAUncertainty'][dfindex] = self.pmramaserr
        df['PMDec'][dfindex] = self.pmdecmas
        df['PMDecUncertainty'][dfindex] = self.pmdecmaserr

def writePmparFile(pmparfilename, obslist, otherlines):
    pmparout = open(pmparfilename, "w")
    for line in otherlines:
        pmparoutout.write(line)
    for obs in obslist:
        pmparout.write("{0}\n".format(obs.to_string()))
    pmparout.close()

def fitEQuad(obslist, otherlines):
    writePmparFile("pmpar.equad.trial", obslist, otherlines)
    os.system("pmpar pmpar.equad.trial > pmpar.results.trial".format(args.pmparfile[0])) 
    equadtrialresult = PmparFitResult("pmpar.results.trial", len(obslist))
    sysestimate = 0.0
    scalefactor = 0.1 # Set this to a reasonable number so that we don't get out of control swings
    while np.abs(equadtrialresult.rchisq - 1.0) > 0.0001: 
        sysestimate = sysestimate + (equadtrialresult.rchisq - 1.0)*scalefactor
        trialobslist = copy.deepcopy(obslist)
        for obs in trialobslist:
            obs.addUncertainty(sysestimate, sysestimate)
        writePmparFile("pmpar.equad.trial", trialobslist, otherlines)
        os.system("pmpar pmpar.equad.trial > pmpar.results.trial".format(args.pmparfile[0]))
        equadtrialresult = PmparFitResult("pmpar.results.trial", len(obslist))
    return equadtrialresult

if __name__ == "__main__":
    # Get some info on what we are expected to do
    parser = argparse.ArgumentParser(description='Read an existing pmpar file and perturb the positions.')
    parser.add_argument('--statisticalsigmara', default=0.5, type=float, help="Standard deviation in mas of the fake observations in R.A.")
    parser.add_argument('--statisticalsigmadec', default=1.0, type=float, help="Standard deviation in mas of the fake observations in Decl.")
    parser.add_argument('--distribution', default="gaussian", help='Distribution type of the systematic uncertainty to add')
    parser.add_argument('--extentra', default=1.0, type=float, help='Extent or std dev of the systematic uncertainty distribution for R.A. in milliarcseconds')
    parser.add_argument('--extentdec', default=1.0, type=float, help='Extent or std dev of the systematic uncertainty distribution for Decl. in milliarcseconds')
    parser.add_argument('--parallax', default=1.0, type=float, help='The true parallax in the simulation pmpar file, in mas')
    parser.add_argument('--pmra', default=10.0, type=float, help='The true proper motion (right ascension) in the simulation pmpar file, in mas/yr')
    parser.add_argument('--pmdec', default=-5.0, type=float, help='The true proper motion (declination) in the simulation pmpar file, in mas/yr')
    parser.add_argument('--niter', default=100, type=int, help='Number of repeats to run')
    parser.add_argument('pmparfile', default="", type=str, nargs=1, help='The simulated observation file containing ideal positions, no errors')

    # Parse the arguments
    args = parser.parse_args()

    # Open the pmpar file that contains the perfect simulated observations (at the ideal positions for each date, given the model)
    lines = open(args.pmparfile[0]).readlines()

    # Create a list where we will store the observations
    obslist = []

    # Create a list to store the lines that are not observation lines from the pmpar file
    otherlines = []

    # Create a random number generator to use later
    rng = default_rng() # rng is your random number generator.  See e.g. https://numpy.org/doc/stable/reference/random/index.html for how to use it.

    # Create some places to store results from simulations
    colnames = ["Parallax", "ParallaxUncertainty", "PMRA", "PMRAUncertainty", "PMDec", "PMDecUncertainty"] # This is what we will store from each trial
    systematiccorrectionmethods = ["none", "efac", "equad"] # These are the different methods of compensating systematic errors: nothing, unity chi sq (scale factor), unity chi sq (quadrature).  More will be added later, including bootstrap.
    results = {}
    for method in systematiccorrectionmethods:
        results[method] = pd.DataFrame(np.zeros(len(colnames) * args.niter).reshape(args.niter, len(colnames)), columns=colnames)

    # read in the lines
    for line in lines:
        # Check if it is an observation (length 5)
        if len(line.split()) == 5:
            obslist.append(Observation(line))
        else:
            otherlines.append(line)

    # Now we loop over niter times, creating a new fake observation each time
    for i in range(args.niter):
        # Create a copy of the original, unperturbed observations to work on in this trial
        trialobslist = copy.deepcopy(obslist)

        # Go through the observations with a for loop, adding a random offset and setting the statistical uncertainty to fake an observation
        # Use setUncertainty and perturbposition to set statistical uncertainty and fake a reasonable observation
        for obs in trialobslist:
            rg1 = rng.standard_normal() #picks a random offset for the RA
            rg2 = rng.standard_normal() #picks a random offset for the Dec
            obs.perturbposition(args.statisticalsigmara*rg1, args.statisticalsigmadec*rg2)
            obs.setUncertainty(args.statisticalsigmara, args.statisticalsigmadec)
    
        # At this point, the original (perfect) simulated observations have had gaussian errors added to simulate statistical noise, which also set the simulated uncertainties
        # Write this out to a file with suffix ".statistical"
        writePmparFile(args.pmparfile[0] + ".statistical", trialobslist, otherlines)
    
        # Now we run through a loop adding in systematic errors, which perturb the positions but don't change the simulated uncertainties
        for obs in trialobslist: 
            if args.distribution == "gaussian": # We want the simulated systematic errors to be drawn from a gaussian distribution - args.extent is the standard deviation
                systematicra = rng.normal(0,args.extentra) # Select a random offset for RA
                systematicdec = rng.normal(0,args.extentdec) # Same thing as the previous line but for Dec
            elif args.distribution == "uniform": # We want the simulated systematic errors to be drawn from a uniform distribution
                systematicra = rng.uniform(-args.extentra, args.extentra)
                systematicdec = rng.uniform(-args.extentdec, args.extentdec)
            obs.perturbposition(systematicra, systematicdec) # Perturb the position with the generated number
    
        # Now write the final simulated observation set out - first all the "otherlines", then each observation, using the to_string() method
        writePmparFile(args.pmparfile[0] + ".withsystematic", trialobslist, otherlines)
    
        # Now run pmpar on this simulated observation, without trying any estimated compensation for the systematic uncertainty
        os.system("rm -f pmpar.results.uncorrected")
        os.system("pmpar {0}.withsystematic > pmpar.results.uncorrected".format(args.pmparfile[0]))
    
        # Read in the results from that 
        rawresult = PmparFitResult("pmpar.results.uncorrected", len(trialobslist))

        # Save these into method #1 (no compensation)
        rawresult.storedata(results["none"], i)

        # Method #2 is easy - it is just the results of no compensation, with uncertainties scaled by sqrt(reduced chi squared)
        rawresult.storedata(results["efac"], i)
        results["efac"]["ParallaxUncertainty"][i] *= np.sqrt(rawresult.rchisq)
        results["efac"]["PMRAUncertainty"][i] *= np.sqrt(rawresult.rchisq)
        results["efac"]["PMDecUncertainty"][i] *= np.sqrt(rawresult.rchisq)

        # Method #3 requires some trial and error to find the right amount of estimated systematic error to add in quadrature to each observation
        equadresult = fitEQuad(trialobslist, otherlines)
        equadresult.storedata(results["equad"], i)

    # Now that we're done, let's print some summary statistics.  Focus just on parallax now (can do others later)
    print("PARALLAX")
    for method in systematiccorrectionmethods:
        print("\n", method)
        print("Median difference between fitted parallax and actual:", np.median(np.abs(results[method]["Parallax"] - args.parallax)))
        print("Median value of reported uncertainty:", np.median(results[method]["ParallaxUncertainty"]))
        print("Fraction of times that the best-fit was outside 1sigma (which should be around 32% if correctly estimated)", 100*np.sum(np.abs(results[method]["Parallax"] - args.parallax) > results[method]["ParallaxUncertainty"])/float(args.niter), "%")
