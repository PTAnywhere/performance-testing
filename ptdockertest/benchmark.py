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
from threading3 import Barrier
from models import Container, CpuRequired, DiskRequired, MemoryRequired, ResponseTime, CreationTime


class TestRun(object):
    """
    It takes measures at run-level and stores them.
    This includes things that are only checked once (e.g., response time for the last created container) and
    differences between before and after a run.
    """
    def __init__(self, docker_client, number_of_containers, image_id, checker_jar_path):
        self.number_of_containers = number_of_containers
        self._barriers = {
            # Barrier which ensures that the creation of all containers starts
            #(approximately) at the same moment.
            # (it is probably unuseful as container creation takes no so much time)
            'init': Barrier(number_of_containers + 1),  # Waiting thread
            # No container will start before passing it
            'before_save': Barrier(number_of_containers + 1),  # Waiting thread
            # No container will be stopped before passing it
            'end': Barrier(number_of_containers + 1),  # Response time measuring thread
            'ready': Barrier (2),  # Response time measuring thread
        };
        self.docker = docker_client
        self.image_id = image_id
        self._ipc_port = 39999
        self._checker_jar_path = '/home/agg96/JPTChecker-jar-with-dependencies.jar'

    def _save_container(self, dao, container, run_id):
        session = dao.create_session()
        c = Container(docker_id=container.get('Id'), run_id=run_id)
        session.add(c)
        session.commit()
        return c

    def _start_container_and_measure(self, container_id, docker_id, docker_client, dao, ready_barrier):
        container = RunningContainer(container_id, docker_id, docker_client)
        args = (dao, self._barriers['before_save'], self._barriers['end'], ready_barrier)
        thread = start_daemon(target=container.run, args=args, begin_barrier=self._barriers['init'])
        return container, thread

    def _run_container(self, last_container, dao, run_id):
        # For Docker: run = create + start
        if last_container:
            port_bindings = { 39000: self._ipc_port, 5900: None }
            container = self.docker.create_container(image=self.image_id, ports=list(port_bindings.keys()),
                            host_config=self.docker.create_host_config(port_bindings=port_bindings))
        else:
            container = self.docker.create_container(image=self.image_id)
        db_cont = self._save_container(dao, container, run_id)
        logging.info('Container "%s" created.' % db_cont.docker_id)
        return self._start_container_and_measure( db_cont.id, db_cont.docker_id,
                            self.docker, dao,
                            self._barriers['ready'] if last_container else None )

    def run(self, dao, run_id):
        threads = []
        containers = []
        self._record_init_disk_size()
        for n in range(self.number_of_containers):
            # n+1 is the last created container, we measure its response time
            # to see if it takes more time for it to give a response as the scale increases.
            last_container = n+1==self.number_of_containers
            container, thread = self._run_container(last_container, dao, run_id)
            threads.append(thread)
            containers.append(container)

        start_daemon(self._measure_response_time, args=(20,),
                        begin_barrier=self._barriers['ready'],
                        end_barrier=self._barriers['end'])
        # It ensures that containers run for at least 5 seconds
        start_daemon(target=wait_at_least, args=(5,),
                        begin_barrier=self._barriers['init'],
                        end_barrier=self._barriers['before_save'])

        # Waits for the rest of the threads
        for thread in threads: thread.join()

        # while it is running a container consumes less disk
        self._save(dao, run_id)

        for container in containers: container.remove()

    def _measure_response_time(self, timeout):
        logging.info('Measuring response time.')
        ret = subprocess.check_output(['java', '-jar', self._checker_jar_path, 'localhost', str(self._ipc_port), str(timeout)])
        self.response_time = int(ret)
        logging.info('Response time: ' + ret)

    def _get_disk_size(self):
        """Returns data used by Docker in bytes."""
        # docker.info() returns an awful data structure...
        for field in self.docker.info()['DriverStatus']:
            if field[0]=='Data Space Used':
                return parse_size(field[1])  # Value in bytes
        logging.error('"Data Space Used" field was not found in the data returned by Docker.')

    def _get_disk_size_du(self):
        """Returns in Docker's root directory size in KBs."""
         # This function requires you to run the script as sudo
        directory = self.docker.info()['DockerRootDir']
        ret = subprocess.check_output(['sudo', 'du', '-sk', directory])
        return int(ret.split()[0]) # Value in KBs

    def _record_init_disk_size(self):
        self.init_size = self._get_disk_size()
        self.init_size_du = self._get_disk_size_du()

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

    def _save_response_time(self, session, run_id):
        s = ResponseTime(run_id=run_id, time=self.response_time)
        session.add(s)
        session.commit()

    def _save(self, dao, run_id):
        session = dao.create_session()
        folder_size_increase = self._get_disk_size() - self.init_size
        folder_size_increase_du = self._get_disk_size_du() - self.init_size_du
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
    :param all_started_barrier: Barrier which ensures that all containers are running
                            (i.e., they are all compiting for computing resources)
                            when their performance is measured.
    :param end_barrier: Barrier which ensures that no container is stopped
                            before all the measurements have been taken.
    """
    def run(self, dao, all_started_barrier, end_barrier, ready_barrier=None):
        self.start()
        # Preference over other barriers to ensure that the response time measure thread starts first
        if ready_barrier: ready_barrier.wait()
        all_started_barrier.wait()
        self.save_stats(dao.create_session())
        end_barrier.wait()
        self.stop()


def wait_at_least(seconds):
    with Spinner(label="Waiting", total=5) as spinner:
        for progress in range(1, seconds + 1):  # Update each second
            spinner.step(progress)
            time.sleep(1)

def run_with_barrier(target, args, begin_barrier, end_barrier):
    if begin_barrier: begin_barrier.wait()
    target(*args)
    if end_barrier: end_barrier.wait()

def start_daemon(target, args, begin_barrier=None, end_barrier=None):
    t = Thread(target=run_with_barrier, args=(target, args, begin_barrier, end_barrier))
    t.daemon = True
    t.start()
    return t
