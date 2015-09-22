"""
Created on 22/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Script to run benchmarks.
"""

from argparse import ArgumentParser

def main(db, log, testId):
    print "Running..."

def entry_point():
    parser = ArgumentParser(description='Run benchmark.')
    parser.add_argument('-db', default='/tmp/benchmark.db', dest='database', help='Database file.')
    parser.add_argument('-log', default='/tmp/benchmark.log', dest='log', help='Log file.')
    parser.add_argument('testId', help='Benchmark identifier.')
    args = parser.parse_args()
    main(args.database, args.log, args.testId)


if __name__ == "__main__":
    entry_point()
