"""
Created on 22/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Script to run benchmarks.
"""

import numpy
from argparse import ArgumentParser
from models import PerformanceTestDAO, Test


def generate_data_json(measures):
    print '{'
    for indicator, measures in measures.items():
        print '\t"' + indicator + '": ['
        for num_containers, measure in measures.items():
            print '\t\t{0: 0.0},'
            for num_containers, measure in measures.items():
                print '\t\t{%d: %f},' % (num_containers, measure)
        print '\t]'
    print '}'

def main(database_file, log_file):
    print "Generating plots..."
    dao = PerformanceTestDAO(database_file)
    session = dao.create_session()
    measures = {
        'size': {},
        'cpu_total': {},
        'cpu_percentage': {},
        'memory': {}
    }
    for test in session.query(Test):
        per_run = {
            'size': [],
            'cpu_total': [],
            'cpu_percentage': [],
            'memory': []
        }
        for run in test.runs:
            per_container = {
                'cpu_total': [],
                'cpu_percentage': [],
                'memory': []
            }
            for container in run.containers:
                per_container['cpu_total'].append(container.cpu.total_cpu)
                per_container['cpu_percentage'].append(container.cpu.percentual_cpu)
                per_container['memory'].append(container.memory.size)
            per_run['size'].append(run.disk.size)
            per_run['cpu_total'].append(numpy.mean(per_container['cpu_total']))
            per_run['cpu_percentage'].append(numpy.mean(per_container['cpu_percentage']))
            per_run['memory'].append(numpy.mean(per_container['memory']))
        measures['size'][test.number_of_containers] = numpy.mean(per_run['size'])
        measures['cpu_total'][test.number_of_containers] = numpy.mean(per_run['cpu_total'])
        measures['cpu_percentage'][test.number_of_containers] = numpy.mean(per_run['cpu_percentage'])
        measures['memory'][test.number_of_containers] = numpy.mean(per_run['memory'])

    generate_data_json(measures)



def entry_point():
    parser = ArgumentParser(description='Generate plots for a benchmark.')
    parser.add_argument('-db', default='/tmp/benchmark.db', dest='database', help='Database file.')
    parser.add_argument('-output', default='/tmp/plots', dest='plot_folder', help='Folder where plots will be saved.')
    args = parser.parse_args()
    main(args.database, args.plot_folder)


if __name__ == "__main__":
    entry_point()
