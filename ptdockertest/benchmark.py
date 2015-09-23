"""
Created on 23/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Benchark: run container, measure and close.
"""

import logging

class RunningContainer(object):
    def __init__(self, container_id, docker_client):
        self.container_id = container_id
        self.docker_client = docker_client

    def start(self):
        logging.info('Running container "%s".' % self.container_id)

    def save_stats(self):
        logging.info('Measuring container "%s".' % self.container_id)


"""
Run container, measure it and close it.

:param benchmark: RunningContainer object
:param init_barrier: Barrier which ensures that the creation of all containers
                        starts (approximately) at the same moment.
:param save_barrier: Barrier which ensures that all containers are running
                        (i.e., they are all compiting for computing resources)
                        when their performance is measured.
:param end_barrier: Barrier which ensures that no container is stopped
                        before all the measurements have been taken.
"""
def run(benchmark, init_barrier, save_barrier, end_barrier):
    init_barrier.wait()
    benchmark.start()
    save_barrier.wait()
    benchmark.save_stats()
    end_barrier.wait()
