"""
Created on 22/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Script to run benchmarks.
"""

from argparse import ArgumentParser

def main(db, log, testId):
    print "Generating plots..."

def entry_point():
    parser = ArgumentParser(description='Generate plots for a benchmark.')
    parser.add_argument('-db', default='/tmp/benchmark.db', dest='database', help='Database file.')
    parser.add_argument('-output', default='/tmp/plots', dest='plot_folder', help='Folder where plots will be saved.')
    parser.add_argument('testId', help='Benchmark identifier.')
    args = parser.parse_args()
    main(args.database, args.plot_folder, args.testId)


if __name__ == "__main__":
    entry_point()
