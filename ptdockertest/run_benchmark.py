"""
Created on 22/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Script to run benchmarks.
"""

import logging
from argparse import ArgumentParser
from gateway import DockerClient
from models import PerformanceTestDAO, Test


def main(docker_url, database_file, log_file, testId):
    logging.basicConfig(filename=log_file,level=logging.DEBUG)
    dao = PerformanceTestDAO(database_file)
    session = dao.create_session()
    test = session.query(Test).first()

    docker = DockerClient(docker_url)
    logging.info('Running test %d' % test.id)
    for _ in range(test.repetitions):
        logging.info('Create repetition with %d containers.' % test.number_of_containers)
        for _ in range(test.number_of_containers):
            container = docker.create_container(test.image_id)
            logging.info('Container "%s" created.' % container)


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
