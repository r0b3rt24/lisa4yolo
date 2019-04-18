from __future__ import division
import os
import argparse
from collections import namedtuple
from itertools import groupby
from pprint import pprint
import matplotlib.pyplot as plt
from scipy import integrate
import numpy as np

from evaluateDetections import computeMatchStatistics, MatchStats

def interpolateResults(results, numPoints = 101):
    # Make sure results are sorted, so we interpolate between the correct pairs
    sortedResults = sorted(results, key=lambda x: x.precision)
    interpolated = []

    # Verify that all reported results come from the same number of tests:
    if len(set([x.numAnnotations for x in sortedResults])) > 1:
        print("Error: When interpolating between results, all must be from the same test (i.e. have the same numAnnotations!")
        exit()
    numAnnotations = sortedResults[0].numAnnotations

    ## Add proper endpoints, if they are not there naturally.
    # At low precision we simulate perfect recall (this can be
    # achieved in practive by just accepting every search window as a
    # detection).
    # At perfect precision we simulate a very low recall (this can be
    # achieved in practice by accepting just one search windows as a
    # detection - the one we're most certain about.
    if sortedResults[0].precision != 0:
        sortedResults = [MatchStats(numAnnotations,
                                    numAnnotations,
                                    numAnnotations*1000,
                                    numAnnotations/(numAnnotations+numAnnotations*1000),
                                    1, [])] + sortedResults
    if sortedResults[-1].precision != 1:
        sortedResults.append(MatchStats(numAnnotations,
                                        1,
                                        0,
                                        1,
                                        1/numAnnotations, []))

    # Interpolate between each input pair
    for pair in zip(sortedResults[:-1], sortedResults[1:]):
        points = round(numPoints*(pair[1].precision-pair[0].precision))+1
        tpCounts = np.linspace(pair[0].tpCount, pair[1].tpCount, points)
        fpCounts = np.linspace(pair[0].fpCount, pair[1].fpCount, points)
        precisions = tpCounts/(tpCounts+fpCounts)
        recalls = tpCounts/numAnnotations
        
        # Add the original measurement point to the output followed by the interpolated ones
        interpolated.append(pair[0])
        interpolated += [MatchStats(numAnnotations, *x, widthsFound = []) for x in zip(tpCounts, fpCounts, precisions, recalls)[1:-1]]

    interpolated[-1] = sortedResults[-1]
    return interpolated
    

def computeAUCs(resultSets, plot = True, plotTitle = "", legendNames = None, savePlot = None, interpolate = True):
    legend = []
    aucs = []
    if (plot or savePlot != None) and (legendNames == None or len(legendNames) != len(resultSets)):
        print("Warning: Not the same number of legend entries as curves. Using generic names.")
        legendNames = ["Detector %d" % x for x in range(1, len(resultSets)+1)]
    for i, results in enumerate(resultSets):
        if interpolate:
            results = interpolateResults(results)

        _, _, _, precisions, recalls, _ = map(list, zip(*[x.values() for x in map(vars, results)]))

        if not interpolate:
            # Add proper endpoints, if they are not there naturally.
            # Only relevant for non-interpolated input, as the interpolator add these automatically.
            if precisions[0] != 0:
                precisions = [0] + precisions
                recalls = [1] + recalls
            if precisions[-1] != 1:
                precisions = precisions + [1]
                recalls = recalls + [0]
                
        auc = integrate.cumtrapz(recalls, precisions)*100
        aucs.append(auc[-1])
        if plot or savePlot != None:
            # Endpoints for plotting purposes only
            precisions = [0] + precisions + [1]
            recalls = [1] + recalls + [0]
            plt.plot(precisions, recalls, '-', linewidth=2)
            legend.append("%s (AUC: %0.2f%%)" % (legendNames[i], auc[-1]))

    if plot or savePlot != None:
        plt.legend(legend, loc="lower left")
        plt.subplots_adjust(top=0.85)
        plt.xlabel("Precision", fontsize = 16)
        plt.ylabel("Recall", fontsize = 16)
        plt.xlim([-0.01,1.01])
        plt.ylim([-0.01,1.01])
        plt.title(plotTitle)
        if savePlot != None:
            plt.savefig(savePlot)
        if plot:
            plt.show()
    return aucs

def main(args):
    if not os.path.isfile(args.groundTruth):
        print("Error: The annotation file %s  does not exist." % args.groundTruth)
        exit()
    annotationFile = open(os.path.abspath(args.groundTruth), 'r')
    header = annotationFile.readline() # Discard the header-line.
    annotations = annotationFile.readlines()

    resultSets = []
    for detector in args.detectionPaths:
        resultSets.append([])
        for rFile in detector:
            if not os.path.isfile(rFile):
                print("Error: The detection file %s does not exist." % rFile)
                exit()
            detectionFile = open(os.path.abspath(rFile), 'r')
            detections = detectionFile.readlines()
            statistics, _, _ = computeMatchStatistics(annotations, detections, args.pascal)
            resultSets[-1].append(statistics)

        # Sort so precision is monotonically increasing (otherwise plots become weird)
        resultSets[-1].sort(key=lambda x: x.precision)
        # Remove any duplicate precision entries (integrate.simps chokes on those)
        resultSets[-1] = [group.next() for key, group in groupby(resultSets[-1], lambda x: x.precision)]

    print("\n".join(map(str, computeAUCs(resultSets, plot=args.plot, plotTitle=args.title, legendNames=args.legend, savePlot=args.savePlot, interpolate=(not args.noInterpolation)))))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate a precision-recall curve and compute the area under the curve (AUC) from multiple detection results and an annotation file.')
    
    parser.add_argument('-gt', '--groundTruth', metavar='annotations.csv', type=str, help='The path to the csv-file containing ground truth annotations.')
    parser.add_argument('-d', '--detectionPaths', metavar='detections.csv', nargs='+', action='append', type=str, help='Paths to multiple the csv-files containing detections. Each line formatted as filenameNoPath;upperLeftX;upperLeftY;lowerRightX;lowerRightY. No header line. The files should be produced with different parameters in order to create multiple precision/recall data points. This flag can be given several times to plot multiple detectors against the ground truth.')
    parser.add_argument('-t', '--title', default="PRC plot", metavar="\"PRC plot\"", help='Title put on the plot.')
    parser.add_argument('-l', '--legend', default=None, nargs='*', metavar="\"Team, algorithm\"", help='Legend for each curve in the plot. Must have the same number of entries as there are curves if given. If not given, generic titles are used.')
    parser.add_argument('-p', '--pascal', metavar=0.5, type=float, default=0.5, help='Define Pascal overlap fraction.')
    parser.add_argument('-o', '--plot', action='store_true', help='Show plot of the computed PR curve.')
    parser.add_argument('-s', '--savePlot', default=None, metavar="prcPlot.png", help='Save the computed PR curve to the file prcPlot.png.')
    parser.add_argument('--noInterpolation', action='store_true', help='By default the PR curves are interpolated according to Davis & Goadrich "The Relationship Between Precision-Recall and ROC Curves. If this flag is given, interpolation is disabled.')
    args = parser.parse_args()

    main(args)









