import os
import argparse
import random

parser = argparse.ArgumentParser(description='Filter an annotation file by tag or category. Optionally split the filtered file randomly into two (useful for cross validation). Output is places in the same folder as the input file. If no split is specified, the output file is called filtered.csv (with the optional prefix), otherwise the two files will be called split1.csv and split2.csv (with prefix).')
parser.add_argument('percentage', nargs='?', metavar='splitPercentage', type=int, default=100, help='The percentage which will be put in split1.csv. The rest of the lines will be put in split2.csv.')
parser.add_argument('path', metavar='annotationFile.csv', type=str, help='The path to the csv-file containing the annotations.')
parser.add_argument('-f', '--filter', metavar='acceptedTag', type=str, help='If given, only annotations with this tag will be processed.')
parser.add_argument('-c', '--category', metavar='category', type=str, help='If given, the file categories.txt will be loaded and only signs with a tag that belongs to the given category are processed. categories.txt should be formatted with one category on each line in the format categoryName: tag1[, tag2, ... tagN]. It must be placed in the working directory.')
parser.add_argument('-p', '--prefix', metavar='fileNamePrefix', type=str, help='If given, this string will be put in front of the output filename(s).')


args = parser.parse_args()

if not os.path.isfile(args.path):
    print("Error: The given annotation file does not exist.\nSee extractAnnotations.py -h for more info.")
    exit()
    
if args.category != None and not os.path.isfile('categories.txt'):
    print("Error: A category was given, but categories.txt does not exist in the working directory.\nTo use this functionality, create the file with a line for each category in the format\ncategoryName: tag1[, tag2, ... tagN]")
    exit()
    
if not 0 < args.percentage <= 100:
    print("Error: The split percentage must be more than 0 and less than or equal to 100.")
    exit()

categories = {}
if args.category != None:
    categories = {k.split(':')[0] : [tag.strip() for tag in k.split(':')[1].split(',')] for k in open('categories.txt', 'r').readlines()}
    if args.category not in categories:
        print("Error: The category '%s' does not exist in categories.txt." % args.category)
        exit()

csv = open(os.path.abspath(args.path), 'r')
header = csv.readline()
allAnnotations = []

for line in csv:
    fields = line.split(";")
    
    if args.filter != None and args.filter != fields[1]:
        continue
        
    if args.category != None and fields[1] not in categories[args.category]:
        continue
        
    allAnnotations.append(line)

if args.percentage == 100:
    outNames = ['filtered.csv']
    split = [allAnnotations]
else:
    random.shuffle(allAnnotations)
    splitPosition = int(round(args.percentage/100.0*len(allAnnotations)))
    split = [allAnnotations[0:splitPosition], allAnnotations[splitPosition:]]
    outNames = ['split1.csv', 'split2.csv']


basePath = os.path.dirname(args.path)
if args.prefix != None:
    outNames = ['%s-%s' % (args.prefix, name) for name in outNames]
out = [open(os.path.join(basePath, name), 'w') for name in outNames]

for i, o in enumerate(out):
    o.write(header)
    o.writelines(split[i])
