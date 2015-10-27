"""
Created on 22/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Script to run benchmarks.
"""

import numpy
from argparse import ArgumentParser
from collections import OrderedDict
from models import PerformanceTestDAO, Test


PER_CONTAINER_SUFFIX = '_per_container'
SIZE = 'size'
RESPONSE_TIME = 'response'
CPU_TOTAL = 'cpu_total'
CPU_TOTAL_PC = CPU_TOTAL + PER_CONTAINER_SUFFIX
CPU_PERC = 'cpu_percentage'
CPU_PERC_PC = CPU_PERC + PER_CONTAINER_SUFFIX
MEMORY = 'memory'
MEMORY_PC = MEMORY + PER_CONTAINER_SUFFIX
MEMORY_MAX = 'memory_max'
MEMORY_MAX_PC = MEMORY_MAX + PER_CONTAINER_SUFFIX
MEMORY_PERC = 'memory_percentage'
MEMORY_PERC_PC = MEMORY_PERC + PER_CONTAINER_SUFFIX
ALL_FIELDS = (SIZE, RESPONSE_TIME, CPU_TOTAL, CPU_TOTAL_PC, CPU_PERC, CPU_PERC_PC, MEMORY, MEMORY_PC, MEMORY_MAX, MEMORY_MAX_PC, MEMORY_PERC, MEMORY_PERC_PC)


def generate_data_json(measures):
    print '{'
    for indicator, imeasures in measures.items():
        print '\t"' + indicator + '": ['
        print '\t\t{x: 0, y: 0.0},'
        for num_containers, measure in imeasures.items():
            print '\t\t{x: %d, y: %f},' % (num_containers, measure)
        print '\t],'
    print '}'

def create_dictionary(contains_dicts=True, fields=ALL_FIELDS):
    ret = {}
    for field in fields:
        if contains_dicts:
            ret[field] = OrderedDict()
        else:
            ret[field] = []
    return ret

def main(database_file, log_file):
    print "Generating plots..."
    dao = PerformanceTestDAO(database_file)
    session = dao.get_session()
    measures = create_dictionary()
    for test in session.query(Test).order_by(Test.number_of_containers):
        per_run = create_dictionary(contains_dicts=False)
        for run in test.runs:
            if run.ended:  # Ignore runs which have not ended
                per_container = create_dictionary(contains_dicts=False, fields=(CPU_TOTAL, CPU_PERC, MEMORY, MEMORY_MAX, MEMORY_PERC))
                for container in run.containers:
                    if not container.error:
                        per_container[CPU_TOTAL].append(container.cpu.total_cpu)
                        per_container[CPU_PERC].append(container.cpu.percentual_cpu)
                        per_container[MEMORY].append(container.memory.usage)
                        per_container[MEMORY_MAX].append(container.memory.maximum)
                        per_container[MEMORY_PERC].append(container.memory.percentual)
                per_run[SIZE].append(run.disk.size)
                per_run[RESPONSE_TIME].append(run.response_time.time)
                per_run[CPU_TOTAL].append(numpy.sum(per_container[CPU_TOTAL]))
                per_run[CPU_TOTAL_PC].append(numpy.mean(per_container[CPU_TOTAL]))
                per_run[CPU_PERC].append(numpy.sum(per_container[CPU_PERC]))
                per_run[CPU_PERC_PC].append(numpy.mean(per_container[CPU_PERC]))
                per_run[MEMORY].append(numpy.sum(per_container[MEMORY]))
                per_run[MEMORY_PC].append(numpy.mean(per_container[MEMORY]))
                per_run[MEMORY_MAX].append(numpy.sum(per_container[MEMORY_MAX]))
                per_run[MEMORY_MAX_PC].append(numpy.mean(per_container[MEMORY_MAX]))
                per_run[MEMORY_PERC].append(numpy.sum(per_container[MEMORY_PERC]))
                per_run[MEMORY_PERC_PC].append(numpy.mean(per_container[MEMORY_PERC]))
        for key in measures:
            measures[key][test.number_of_containers] = numpy.mean(per_run[key])
    generate_data_json(measures)



def entry_point():
    parser = ArgumentParser(description='Generate plots for a benchmark.')
    parser.add_argument('-db', default='/tmp/benchmark.db', dest='database', help='Database file.')
    parser.add_argument('-output', default='/tmp/plots', dest='plot_folder', help='Folder where plots will be saved.')
    args = parser.parse_args()
    main(args.database, args.plot_folder)


if __name__ == "__main__":
    entry_point()
