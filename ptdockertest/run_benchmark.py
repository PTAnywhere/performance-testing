"""
Created on 22/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Script to run benchmarks.
"""

import logging
from argparse import ArgumentParser
from threading import Thread, Barrier
from gateway import DockerClient
from models import PerformanceTestDAO, Test, Run, Container
from benchmark import RunningContainer
from benchmark import run as run_benchmark


def create_run(session, test):
    run = Run(test=test)
    session.add(run)
    session.commit()
    return run

def create_container(session, container, run):
    c = Container(container_id=container.get('Id'), run=run)
    session.add(c)
    session.commit()
    return c

def run_and_measure(container_id, docker_client, thread_list, init_barrier, save_barrier, end_barrier):
    benchmark = RunningContainer(container_id, docker_client)
    args = (benchmark, init_barrier, save_barrier, end_barrier)
    thread = Thread(target=run_benchmark, args=args, daemon=True)
    thread.start()
    thread_list.append(thread)
    return benchmark

def main(docker_url, database_file, log_file, testId):
    logging.basicConfig(filename=log_file,level=logging.DEBUG)
    dao = PerformanceTestDAO(database_file)
    session = dao.create_session()
    test = session.query(Test).first()

    docker = DockerClient(docker_url)
    logging.info('Running test %d' % test.id)
    for _ in range(test.repetitions):
        logging.info('Create repetition with %d containers.' % test.number_of_containers)
        run = create_run(session, test)
        init_barrier = Barrier(test.number_of_containers)
        save_barrier = Barrier(test.number_of_containers)
        end_barrier = Barrier(test.number_of_containers)
        threads = []
        for _ in range(test.number_of_containers):
            container = docker.create_container(test.image_id)
            cont = create_container(session, container, run)
            logging.info('Container "%s" created.' % cont.container_id)
            benchmark = run_and_measure(cont.container_id, docker, threads,
                                        init_barrier, save_barrier, end_barrier)
        for thread in threads:
            thread.join()
        logging.info('Run finished.')


def entry_point():
    parser = ArgumentParser(description='Run benchmark.')
    parser.add_argument('-docker', default='unix://var/run/docker.sock', dest='docker', help='Docker socket URL.')
    parser.add_argument('-db', default='/tmp/benchmark.db', dest='database', help='Database file.')
    parser.add_argument('-log', default='/tmp/benchmark.log', dest='log', help='Log file.')
    parser.add_argument('testId', help='Benchmark identifier.')
    args = parser.parse_args()
    main(args.docker, args.database, args.log, args.testId)


if __name__ == "__main__":
    entry_point()
