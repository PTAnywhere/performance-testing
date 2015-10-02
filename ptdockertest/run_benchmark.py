"""
Created on 22/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Script to run benchmarks.
"""

import time
import logging
from argparse import ArgumentParser
from datetime import datetime
from threading3 import Barrier
from docker import Client
from models import PerformanceTestDAO, Test, Run, Container
from benchmark import RunMeasures, run_and_measure, wait_in_thread, measure_in_thread


def create_run(session, test):
    # Run(test=test) requires the same session as test for adding it
    run = Run(test_id=test.id)
    session.add(run)
    session.commit()
    return run

def create_container(session, container, run):
    c = Container(docker_id=container.get('Id'), run_id=run.id)
    session.add(c)
    session.commit()
    return c

def run_execution(docker_client, dao, session, run, number_of_containers, image_id):
    run_measures = RunMeasures(docker_client)
    # Probably unuseful as container creation takes no so much time
    init_barrier = Barrier(number_of_containers + 1)  # Waiting thread
    # No container will start before passing before_save_barrier
    before_save_barrier = Barrier(number_of_containers + 1)  # Waiting thread
    # No container will be stopped before passing end_barrier
    end_barrier = Barrier(number_of_containers + 1)   # Waiting thread + response time measuring thread
    ready_barrier = Barrier (2)  # Response time measuring thread

    threads = []
    benchmarks = []
    ipc_port = 39999
    for n in range(number_of_containers):
        # n+1 is the last created container, we measure its response time
        # to see if it takes more time for it to give a response as the scale increases.
        last_container = n+1==number_of_containers
        if last_container:
            port_bindings = {
               39000: ipc_port,
               5900: None
            }
            container = docker_client.create_container(image=image_id, ports=list(port_bindings.keys()),
                            host_config=docker_client.create_host_config(port_bindings=port_bindings))
        else:
            container = docker_client.create_container(image=image_id)
        cont = create_container(session, container, run)
        logging.info('Container "%s" created.' % cont.docker_id)
        benchmarks.append( run_and_measure(cont.id, cont.docker_id, docker_client, dao,
                                          threads, init_barrier, before_save_barrier, end_barrier,
                                          ready_barrier if last_container else None) )

    measure_in_thread(run_measures, '/home/agg96/JPTChecker-jar-with-dependencies.jar', 'localhost', ipc_port, 10, ready_barrier, end_barrier)
    wait_in_thread(5, init_barrier, before_save_barrier) # It ensures that containers run for at least 5 seconds

    # Waits for the rest of the threads
    for thread in threads:
        thread.join()

    # while it is running a container consumes less disk
    run_measures.save(session, run.id)

    for benchmark in benchmarks:
        benchmark.remove()

    run.ended = datetime.now()
    session.commit()
    logging.info('Run finished.')

def run_test(docker_client, dao, session, test):
    logging.info('Running test %d.' % test.id)
    repetitions = 0
    for run in test.runs:
        repetitions += 1
        if not run.ended:
            run_execution(docker_client, dao, session, run, test.number_of_containers, test.image_id)
        else:
            logging.info('Skipping already run test %d.' % test.id)
            
    for _ in range(repetitions, test.repetitions):
        logging.info('Create repetition with %d containers.' % test.number_of_containers)
        run = create_run(session, test)
        run_execution(docker_client, dao, session, run, test.number_of_containers, test.image_id)
    logging.info('Finished test %d.' % test.id)

def run_all(docker_client, dao):
    session = dao.create_session()
    for test in session.query(Test):
        run_test(docker_client, dao, session, test)

def entry_point():
    parser = ArgumentParser(description='Run benchmark.')
    parser.add_argument('-docker', default='unix://var/run/docker.sock', dest='url', help='Docker socket URL.')
    parser.add_argument('-db', default='/tmp/benchmark.db', dest='database', help='Database file.')
    parser.add_argument('-log', default='/tmp/benchmark.log', dest='log', help='Log file.')
    parser.add_argument('-testId', default=False, dest='testId', help='Benchmark identifier.' +
                            'If it is not provided, all the pending benchmarks will be run.')
    args = parser.parse_args()

    FORMAT = '%(asctime)-15s %(message)s'
    logging.basicConfig(filename=args.log,level=logging.DEBUG, format=FORMAT)

    dao = PerformanceTestDAO(args.database)
    docker = Client(args.url)

    if not args.testId:
        run_all(docker, dao)
    else:
        session = dao.create_session()
        test = session.query(Test).get(args.testId)
        run_test(docker, dao, test)


if __name__ == "__main__":
    entry_point()
