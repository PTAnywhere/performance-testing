"""
Created on 22/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Script to run benchmarks.
"""

import time
import logging
from threading import Thread
from argparse import ArgumentParser
from datetime import datetime
from humanfriendly import Spinner, Timer
from threading3 import Barrier
from docker import Client
from models import PerformanceTestDAO, Test, Run, Container
from benchmark import RunMeasures, RunningContainer
from benchmark import run as run_benchmark


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

def run_and_measure(container_id, docker_id, docker_client, dao, thread_list, init_barrier, save_barrier, end_barrier):
    benchmark = RunningContainer(container_id, docker_id, docker_client)
    args = (benchmark, dao, init_barrier, save_barrier, end_barrier)
    thread = Thread(target=run_benchmark, args=args)
    thread.daemon = True
    thread.start()
    thread_list.append(thread)
    return benchmark

def wait_for_stats(seconds, start_barrier, end_barrier):
    start_barrier.wait()
    with Spinner(label="Waiting", total=5) as spinner:
        for progress in range(1, seconds + 1):  # Update each second
            spinner.step(progress)
            time.sleep(1)
    end_barrier.wait()

def run_execution(docker_client, dao, session, run, number_of_containers, image_id):
    run_measures = RunMeasures(docker_client)
    init_barrier = Barrier(number_of_containers + 1)
    save_barrier = Barrier(number_of_containers + 1)
    end_barrier = Barrier(number_of_containers)
    threads = []
    benchmarks = []
    for _ in range(number_of_containers):
        container = docker_client.create_container(image=image_id)
        cont = create_container(session, container, run)
        logging.info('Container "%s" created.' % cont.docker_id)
        benchmarks.append(run_and_measure(cont.id, cont.docker_id, docker_client,
                                          dao, threads, init_barrier, save_barrier, end_barrier))

    wait_for_stats(5, init_barrier, save_barrier)
    for thread in threads:
        thread.join()

    # while they are running container consume less disk
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
