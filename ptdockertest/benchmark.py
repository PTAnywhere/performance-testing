"""
Created on 23/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Benchmark: run container, measure and close.
"""

import os
import time
import logging
import subprocess
import humanfriendly
from models import CpuRequired, DiskRequired, MemoryRequired, CreationTime


class RunMeasures(object):
    """
    It takes measures at run-level (differences between before and after a run) and stores them.
    """
    def __init__(self, docker_client):
        self.docker = docker_client
        self.init_size = self._get_disk_size(docker_client)
        self.init_size_du = self._get_disk_size_du(docker_client)

    def _get_disk_size(self, docker_client):
        """Returns data used by Docker in bytes."""
        # docker.info() returns an awful data structure...
        for field in docker_client.info()['DriverStatus']:
            if field[0]=='Data Space Used':
                return humanfriendly.parse_size(field[1])  # Value in bytes
        logging.error('"Data Space Used" field was not found in the data returned by Docker.')

    def _get_disk_size_du(self, docker_client):
        """Returns in Docker's root directory size in KBs."""
         # This function requires you to run the script as sudo
        directory = docker_client.info()['DockerRootDir']
        ret = subprocess.check_output(['sudo', 'du', '-sk', directory])
        return int(ret.split()[0]) # Value in KBs

    def _log_measure_comparison(self, info_measure, du_measure):
        logging.info('Additional disk that Docker demanded (measured with docker.info()): ' + humanfriendly.format_size(info_measure) + '.')
        logging.info('Additional disk that Docker demanded (measured with du): ' + humanfriendly.format_size(du_measure) + '.')
        difference = du_measure - info_measure
        if difference>1024:  # More than 1KB of difference
            logging.warning('du measures %s more than docker.info().' % humanfriendly.format_size(difference))
        elif difference<-1024:  # Less than 1MB of difference
            logging.warning('du measures %s less than docker.info().' % humanfriendly.format_size(difference*-1))

    def _save_disk_size(self, session, run_id, size):
        d = DiskRequired(run_id=run_id, size=size)
        session.add(d)
        session.commit()

    def save(self, session, run_id):
        folder_size_increase = self._get_disk_size(self.docker) - self.init_size
        folder_size_increase_du = self._get_disk_size_du(self.docker) - self.init_size_du
        self._log_measure_comparison(folder_size_increase, folder_size_increase_du * 1024)
        self._save_disk_size(session, run_id, folder_size_increase)  


class RunningContainer(object):
    """
    It starts a container, takes measures and saves them.
    """
    def __init__(self, container_id, docker_client):
        self.container_id = container_id
        self.docker_client = docker_client

    def start(self):
        start = time.time()
        response = self.docker_client.start(self.container_id)
        self.elapsed = time.time() - start
        logging.info('Running container "%s".\n\t%s' % (self.container_id, response))

    def _save_cpu(self, session, total_cpu, percentual_cpu):
        c = CpuRequired(container_id=self.container_id, total_cpu=total_cpu, percentual_cpu=percentual_cpu)
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
        total_usage = measure['cpu_stats']['cpu_usage']['total_usage']
        percentual_usage = total_usage * 100.0 / measure['cpu_stats']['system_cpu_usage']
        self._save_cpu(session, total_usage, percentual_usage)
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
