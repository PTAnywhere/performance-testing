"""
Created on 22/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Script to run benchmarks.
"""

import logging
from argparse import ArgumentParser
from threading import Thread
from datetime.datetime import now
from threading3 import Barrier
from docker import Client
from models import PerformanceTestDAO, Test, Run, Container
from benchmark import RunMeasures, RunningContainer
from benchmark import run as run_benchmark


def create_run(session, test):
    run = Run(test=test)
    session.add(run)
    session.commit()
    return run

def create_container(session, container, run):
    c = Container(docker_id=container.get('Id'), run=run)
    session.add(c)
    session.commit()
    return c

def run_and_measure(container_id, docker_id, docker_client, dao, thread_list, init_barrier, save_barrier, end_barrier):
    benchmark = RunningContainer(container_id, docker_id, docker_client)
    args = (benchmark, dao, init_barrier, save_barrier, end_barrier)
    thread = Thread(target=run_benchmark, args=args)
    thread.daemon = True
    thread.start()
    thread_list.append(thread)
    return benchmark

def run_test(docker_client, dao, test):
    if not test.ended:
        logging.info('Running test %d.' % test.id)
        session = dao.create_session()
        for _ in range(test.repetitions):
            logging.info('Create repetition with %d containers.' % test.number_of_containers)
            run = create_run(session, test)
            run_measures = RunMeasures(docker_client)
            init_barrier = Barrier(test.number_of_containers)
            save_barrier = Barrier(test.number_of_containers)
            end_barrier = Barrier(test.number_of_containers)
            threads = []
            benchmarks = []
            for _ in range(test.number_of_containers):
                container = docker_client.create_container(image=test.image_id)
                cont = create_container(session, container, run)
                logging.info('Container "%s" created.' % cont.docker_id)
                benchmarks.append(run_and_measure(cont.id, cont.docker_id, docker_client,
                                            dao, threads, init_barrier, save_barrier, end_barrier))
            for thread in threads:
                thread.join()

            # while they are running container consume less disk
            run_measures.save(session, run.id)

            for benchmark in benchmarks:
                benchmark.remove()

            logging.info('Run finished.')
        test.ended = now()
        logging.info('Finished test %d.' % test.id)
    else:
        logging.info('Skipping already run test %d.' % test.id)

def run_all(docker_client, dao):
    for test in session.query(Test):
        run_test(docker_client, dao, test)


def entry_point():
    parser = ArgumentParser(description='Run benchmark.')
    parser.add_argument('-docker', default='unix://var/run/docker.sock', dest='url', help='Docker socket URL.')
    parser.add_argument('-db', default='/tmp/benchmark.db', dest='database', help='Database file.')
    parser.add_argument('-log', default='/tmp/benchmark.log', dest='log', help='Log file.')
    parser.add_argument('-testId', default=False, dest='testId', help='Benchmark identifier.' +
                            'If it is not provided, all the pending benchmarks will be run.')
    args = parser.parse_args()

    FORMAT = '%(asctime)-15s %(message)s'
    logging.basicConfig(filename=log_file,level=logging.DEBUG, format=FORMAT)

    dao = PerformanceTestDAO(database_file)
    docker = Client(docker_url)

    if not args.testId:
        run_all(docker, dao)
    else:
        benchmark = session.query(Test).get(args.testId)
        run_test(docker, dao, benchmark)


if __name__ == "__main__":
    entry_point()
