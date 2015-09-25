"""
Created on 22/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Script to run benchmarks.
"""

import logging
from subprocess import check_output
import humanfriendly
from argparse import ArgumentParser
from threading import Thread
from threading3 import Barrier
from docker import Client
from models import PerformanceTestDAO, Test, Run, Container, DiskRequired
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

def get_disk_size(docker_client):
    # docker.info() returns an awful data structure...
    for field in docker_client.info()['DriverStatus']:
        if field[0]=='Data Space Used':
            print field[1]
            return humanfriendly.parse_size(field[1])  # Value in bytes
    logging.error('"Data Space Used" field was not found in the data returned by Docker.')

def get_disk_size_du(docker_client):  # This function requires you to run the script as root
    directory = docker_client.info()['DockerRootDir']
    ret = check_output(['sudo', 'du', '-sk', directory])
    return int(ret.split()[0]) # Value in KBs
    

def save_disk_size(session, run_id, size):
    d = DiskRequired(run_id=run_id, size=size)
    session.add(d)
    session.commit()

def run_and_measure(container_id, docker_client, dao, thread_list, init_barrier, save_barrier, end_barrier):
    benchmark = RunningContainer(container_id, docker_client)
    args = (benchmark, dao, init_barrier, save_barrier, end_barrier)
    thread = Thread(target=run_benchmark, args=args)
    thread.daemon = True
    thread.start()
    thread_list.append(thread)
    return benchmark

def main(docker_url, database_file, log_file, testId):
    FORMAT = '%(asctime)-15s %(message)s'
    logging.basicConfig(filename=log_file,level=logging.DEBUG, format=FORMAT)
    dao = PerformanceTestDAO(database_file)
    session = dao.create_session()
    test = session.query(Test).first()

    docker = Client(docker_url)
    logging.info('Running test %d' % test.id)
    for _ in range(test.repetitions):
        logging.info('Create repetition with %d containers.' % test.number_of_containers)
        run = create_run(session, test)
        init_folder_size = get_disk_size_du(docker)
        init_barrier = Barrier(test.number_of_containers)
        save_barrier = Barrier(test.number_of_containers)
        end_barrier = Barrier(test.number_of_containers)
        threads = []
        for _ in range(test.number_of_containers):
            container = docker.create_container(image=test.image_id)
            cont = create_container(session, container, run)
            logging.info('Container "%s" created.' % cont.container_id)
            benchmark = run_and_measure(cont.container_id, docker, dao, threads,
                                        init_barrier, save_barrier, end_barrier)        
        for thread in threads:
            thread.join()

        # while they are running container consume less disk
        folder_size_increase = get_disk_size_du(docker) - init_folder_size
        save_disk_size(session, run.id, folder_size_increase)

        logging.info('Run finished.')


def entry_point():
    parser = ArgumentParser(description='Run benchmark.')
    parser.add_argument('-docker', default='unix://var/run/docker.sock', dest='url', help='Docker socket URL.')
    parser.add_argument('-db', default='/tmp/benchmark.db', dest='database', help='Database file.')
    parser.add_argument('-log', default='/tmp/benchmark.log', dest='log', help='Log file.')
    parser.add_argument('testId', help='Benchmark identifier.')
    args = parser.parse_args()
    main(args.url, args.database, args.log, args.testId)


if __name__ == "__main__":
    entry_point()
