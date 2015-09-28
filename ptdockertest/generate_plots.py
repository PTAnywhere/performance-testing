"""
Created on 22/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Script to run benchmarks.
"""

import numpy
from argparse import ArgumentParser
from models import PerformanceTestDAO, Test


def generate_disk_size(measures):
    print '['
    for num_containers, average_size in measures.items():
        print '{%d: %f},' % (num_containers, average_size)
    print ']'


def main(database_file, log_file):
    print "Generating plots..."
    dao = PerformanceTestDAO(database_file)
    session = dao.create_session()
    measures = {
        'size': {}
    }
    for test in session.query(Test):
        size_measures = []
        for run in test.runs:
            size_measures.append(run.disk.size)
            #for container in run.containers:
                #print container.container_id
        measures['size'][test.number_of_containers] = numpy.mean(size_measures)
    generate_disk_size(measures['size'])



def entry_point():
    parser = ArgumentParser(description='Generate plots for a benchmark.')
    parser.add_argument('-db', default='/tmp/benchmark.db', dest='database', help='Database file.')
    parser.add_argument('-output', default='/tmp/plots', dest='plot_folder', help='Folder where plots will be saved.')
    args = parser.parse_args()
    main(args.database, args.plot_folder)


if __name__ == "__main__":
    entry_point()
