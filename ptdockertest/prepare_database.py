"""
Created on 22/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Script to create database.
"""

from argparse import ArgumentParser

def main(database_file):
    print "Creating database '%s'..." % database_file

def entry_point():
    parser = ArgumentParser(description='Create database and create data for the benchmark.')
    parser.add_argument('-db', default='/tmp/benchmark.db', dest='database', help='Database file.')
    args = parser.parse_args()
    main(args.database)


if __name__ == "__main__":
    entry_point()
