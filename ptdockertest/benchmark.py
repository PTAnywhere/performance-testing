"""
Created on 23/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Benchmark: run container, measure and close.
"""

import os
import time
import logging
import subprocess
from humanfriendly import Spinner, Timer, format_size, parse_size
from threading import Thread
from models import Container, CpuRequired, DiskRequired, MemoryRequired, ResponseTime, CreationTime


class RunMeasures(object):
    """
    It takes measures at run-level and stores them.
    This includes things that are only checked once (e.g., response time for the last created container) and
    differences between before and after a run.
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
                return parse_size(field[1])  # Value in bytes
        logging.error('"Data Space Used" field was not found in the data returned by Docker.')

    def _get_disk_size_du(self, docker_client):
        """Returns in Docker's root directory size in KBs."""
         # This function requires you to run the script as sudo
        directory = docker_client.info()['DockerRootDir']
        ret = subprocess.check_output(['sudo', 'du', '-sk', directory])
        return int(ret.split()[0]) # Value in KBs

    def _log_measure_comparison(self, info_measure, du_measure):
        logging.info('Additional disk that Docker demanded (measured with docker.info()): ' + format_size(info_measure) + '.')
        logging.info('Additional disk that Docker demanded (measured with du): ' + format_size(du_measure) + '.')
        difference = du_measure - info_measure
        if difference>1024:  # More than 1KB of difference
            logging.warning('du measures %s more than docker.info().' % format_size(difference))
        elif difference<-1024:  # Less than 1MB of difference
            logging.warning('du measures %s less than docker.info().' % format_size(difference*-1))

    def _save_disk_size(self, session, run_id, size):
        d = DiskRequired(run_id=run_id, size=size)
        session.add(d)
        session.commit()

    def measure_response_time(self, checker_jar_path, hostname, port, timeout, start_barrier, end_barrier):
        start_barrier.wait()
        logging.info('Measuring response time.')
        ret = subprocess.check_output(['java', '-jar', checker_jar_path, hostname, str(port), str(timeout)])
        self.response_time = int(ret)
        logging.info('Response time: ' + ret)
        end_barrier.wait()

    def _save_response_time(self, session, run_id):
        s = ResponseTime(run_id=run_id, time=self.response_time)
        session.add(s)
        session.commit()

    def save(self, session, run_id):
        folder_size_increase = self._get_disk_size(self.docker) - self.init_size
        folder_size_increase_du = self._get_disk_size_du(self.docker) - self.init_size_du
        self._log_measure_comparison(folder_size_increase, folder_size_increase_du * 1024)
        self._save_disk_size(session, run_id, folder_size_increase)
        self._save_response_time(session, run_id)


class RunningContainer(object):
    """
    It starts a container, takes measures and saves them.
    """
    def __init__(self, container_id, container_docker_id, docker_client):
        self.id = container_id
        self.docker_id = container_docker_id
        self.docker_client = docker_client

    def start(self):
        start = time.time()
        response = self.docker_client.start(self.docker_id)
        logging.info('Running container "%s".\n\t%s' % (self.docker_id, response))
        # naive measure
        self.elapsed = time.time() - start
        measure = next(self.docker_client.stats(self.docker_id, decode=True))
        self._previous_cpu = measure['cpu_stats']['cpu_usage']['total_usage']
        self._previous_system = measure['cpu_stats']['system_cpu_usage']

    def _save_cpu(self, session, total_cpu, percentual_cpu):
        c = CpuRequired(container_id=self.id, total_cpu=total_cpu, percentual_cpu=percentual_cpu)
        session.add(c)

    def _save_memory(self, session, mstats):
        percent = mstats['usage'] / float(mstats['limit']) * 100.0
        m = MemoryRequired(container_id=self.id, usage=mstats['usage'], percentual=percent, maximum=mstats['max_usage'])
        session.add(m)

    def _save_start_time(self, session):
        c = CreationTime(container_id=self.id, startup_time=self.elapsed)
        session.add(c)

    def _calculate_cpu_percent(self, currentMeasure):
        # translating it from calculateCPUPercent in https://github.com/docker/docker/blob/master/api/client/stats.go
        cpu_percent = 0.0
        cpu_delta = currentMeasure['cpu_stats']['cpu_usage']['total_usage'] - self._previous_cpu
        system_delta = currentMeasure['cpu_stats']['system_cpu_usage'] - self._previous_system
        if system_delta > 0.0 and cpu_delta > 0.0:
            cpu_percent = (cpu_delta / system_delta) * len(currentMeasure['cpu_stats']['cpu_usage']['percpu_usage']) * 100.0
        return cpu_percent

    def save_stats(self, session):
        stats_obj = self.docker_client.stats(self.docker_id, decode=True)
        logging.info('Measuring container "%s".' % self.docker_id)
        measure = next(stats_obj)
        self._save_cpu(session, measure['cpu_stats']['cpu_usage']['total_usage'], self._calculate_cpu_percent(measure))
        self._save_memory(session, measure['memory_stats'])
        self._save_start_time(session)
        session.commit()

    def stop(self):
        self.docker_client.stop(self.docker_id)
        logging.info('Stopping container "%s".' % (self.docker_id))

    def remove(self):  # Clear dist
        self.docker_client.remove_container(self.docker_id)
        logging.info('Removing container "%s".' % (self.docker_id))

    """
    Run container, measure it and close it.

    :param dao: benchmarking data access object
    :param init_barrier: Barrier which ensures that the creation of all containers
                            starts (approximately) at the same moment.
    :param save_barrier: Barrier which ensures that all containers are running
                            (i.e., they are all compiting for computing resources)
                            when their performance is measured.
    :param end_barrier: Barrier which ensures that no container is stopped
                            before all the measurements have been taken.
    """
    def run(self, dao, init_barrier, all_started_barrier, end_barrier, ready_barrier=None):
        init_barrier.wait()
        self.start()
        if ready_barrier:
             # Preference over other barriers to ensure that the response time measure thread starts first
            ready_barrier.wait()
        all_started_barrier.wait()
        self.save_stats(dao.create_session())
        end_barrier.wait()
        self.stop()


def run_and_measure(container_id, docker_id, docker_client, dao, thread_list, init_barrier, save_barrier, end_barrier, ready_barrier):
    benchmark = RunningContainer(container_id, docker_id, docker_client)
    args = (dao, init_barrier, save_barrier, end_barrier, ready_barrier)
    thread = Thread(target=benchmark.run, args=args)
    thread.daemon = True
    thread.start()
    thread_list.append(thread)
    return benchmark


def wait_at_least(seconds, start_barrier, end_barrier):
    start_barrier.wait()
    with Spinner(label="Waiting", total=5) as spinner:
        for progress in range(1, seconds + 1):  # Update each second
            spinner.step(progress)
            time.sleep(1)
    end_barrier.wait()

def wait_in_thread(seconds, start_barrier, end_barrier):
    waiting_thread = Thread(target=wait_at_least, args=(seconds, start_barrier, end_barrier))
    waiting_thread.daemon = True
    waiting_thread.start()


def measure_in_thread(run_measures, jar_path, hostname, port, timeout, start_barrier, end_barrier):
    t = Thread(target=run_measures.measure_response_time, args=(jar_path, hostname, port, timeout, start_barrier, end_barrier))
    t.daemon = True
    t.start()
