"""
Created on 22/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Script to run benchmarks.
"""

import logging
from argparse import ArgumentParser
from datetime import datetime
from docker import Client
from models import PerformanceTestDAO, Test, Run
from benchmark import TestRun


def create_run(session, test):
    # Run(test=test) requires the same session as test for adding it
    run = Run(test_id=test.id)
    session.add(run)
    session.commit()
    return run

def make_execution(docker_client, dao, session, db_test, db_run):
    r = TestRun(docker_client, db_test.number_of_containers, db_test.image_id)
    r.run(dao, db_run.id)
    db_run.ended = datetime.now()
    session.commit()
    logging.info('Run finished.')

def run_test(docker_client, dao, session, test):
    logging.info('Running test %d.' % test.id)
    repetitions = 0
    for run in test.runs:
        repetitions += 1
        if not run.ended:
            make_execution(docker_client, dao, session, test, run)
        else:
            logging.info('Skipping already run test %d.' % test.id)

    for _ in range(repetitions, test.repetitions):
        logging.info('Create repetition with %d containers.' % test.number_of_containers)
        run = create_run(session, test)
        make_execution(docker_client, dao, session, test, run)
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
