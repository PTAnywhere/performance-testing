"""
Created on 23/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Benchark: run container, measure and close.
"""

import time
import logging
from models import CpuRequired, MemoryRequired, CreationTime


class RunningContainer(object):
    def __init__(self, container_id, docker_client):
        self.container_id = container_id
        self.docker_client = docker_client

    def start(self):
        start = time.time()
        response = self.docker_client.start(self.container_id)
        self.elapsed = time.time() - start
        logging.info('Running container "%s".\n\t%s' % (self.container_id, response))

    def _save_cpu(self, session, total_cpu):
        c = CpuRequired(container_id=self.container_id, total_cpu=total_cpu)
        session.add(c)

    def _save_memory(self, session, max_usage):
        m = MemoryRequired(container_id=self.container_id, size=max_usage)
        session.add(m)

    def _save_start_time(self, session):
        c = CreationTime(container_id=self.container_id, startup_time=self.elapsed)
        session.add(c)

    def save_stats(self, session):
        stats_obj = self.docker_client.stats(self.container_id, decode=True)
        logging.info('Measuring container "%s".' % self.container_id)
        measure = next(stats_obj)
        self._save_cpu(session, measure['cpu_stats']['cpu_usage']['total_usage'])
        self._save_memory(session, measure['memory_stats']['max_usage'])
        self._save_start_time(session)
        session.commit()

    def stop(self):
        response = self.docker_client.stop(self.container_id)
        logging.info('Stopping container "%s".\n\t%s' % (self.container_id, response))

"""
Run container, measure it and close it.

:param benchmark: RunningContainer object
:param dao: benchmarking data access object
:param init_barrier: Barrier which ensures that the creation of all containers
                        starts (approximately) at the same moment.
:param save_barrier: Barrier which ensures that all containers are running
                        (i.e., they are all compiting for computing resources)
                        when their performance is measured.
:param end_barrier: Barrier which ensures that no container is stopped
                        before all the measurements have been taken.
"""
def run(benchmark, dao, init_barrier, save_barrier, end_barrier):
    init_barrier.wait()
    benchmark.start()
    save_barrier.wait()
    benchmark.save_stats(dao.create_session())
    end_barrier.wait()
    benchmark.stop()
