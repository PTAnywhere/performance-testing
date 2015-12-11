"""
Created on 23/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Benchmark: run container, measure and close.
"""

import os
import time
import logging
from requests.exceptions import Timeout
from docker.errors import APIError
from humanfriendly import Spinner
from threading import Thread
from threading3 import Barrier
from measures import ResponseTimeMeter, DockerMeter
from models import Container, CpuRequired, DiskRequired, MemoryRequired, ResponseTime, CreationTime, ExecutionError


class TestRun(object):
    """
    It takes measures at run-level and stores them.
    This includes things that are only checked once (e.g., response time for the last created container) and
    differences between before and after a run.
    """
    def __init__(self, docker_factory, number_of_containers, image_id, volumes_from, ipc_port, checker_jar_path):
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
        self.docker_factory = docker_factory
        self.allocate = self.docker_factory.create()
        self.image_id = image_id
        self._volumes_from = volumes_from
        self._ipc_port = ipc_port
        self._rmeter = ResponseTimeMeter(checker_jar_path, self._ipc_port)
        self._dmeter = DockerMeter(self.allocate)

    def _save_container(self, dao, container, run_id):
        session = dao.get_session()
        c = Container(docker_id=container.get('Id'), run_id=run_id)
        session.add(c)
        session.commit()
        return c

    def _start_container_and_measure(self, container_id, docker_id, docker_factory, ready_barrier):
        container = RunningContainer(container_id, docker_id, docker_factory.create(), self._dmeter.get_container_meter(docker_id))
        args = (self._barriers['before_save'], self._barriers['end'], ready_barrier)
        thread = start_daemon(target=container.run, args=args, begin_barrier=self._barriers['init'])
        return thread, container

    def _run_container(self, last_container, dao, run_id):
        # For Docker: run = create + start
        volumes_from = [] if not self._volumes_from else [v for v in self._volumes_from.split(',')]
        ports = { 39000: self._ipc_port, 5900: None } if last_container else {}
        with self.allocate() as docker:
            host_config = docker.create_host_config(port_bindings = ports, volumes_from=volumes_from)
            container = docker.create_container(image = self.image_id,
                                                ports = list(ports.keys()),
                                                host_config = host_config)
        db_cont = self._save_container(dao, container, run_id)
        logging.info('Container "%s" created.' % db_cont.docker_id)
        if container.get('Warnings'):
            logging.debug('Warnings on the creation: ' + container.get('Warnings'))
        return self._start_container_and_measure( db_cont.id, db_cont.docker_id, self.docker_factory,
                                                    self._barriers['ready'] if last_container else None )

    def run(self, dao, run_id):
        thread_containers = []  # Array of tuples (thread, container)
        self._record_init_disk_size()
        for n in range(self.number_of_containers):
            # n+1 is the last created container, we measure its response time
            # to see if it takes more time for it to give a response as the scale increases.
            last_container = n+1==self.number_of_containers
            thread_containers.append( self._run_container(last_container, dao, run_id) )

        start_daemon(self._rmeter.measure, args=(20,),
                        begin_barrier=self._barriers['ready'],
                        end_barrier=self._barriers['end'])
        # It ensures that containers run for at least 5 seconds
        start_daemon(target=wait_at_least, args=(5,),
                        begin_barrier=self._barriers['init'],
                        end_barrier=self._barriers['before_save'])

        session = dao.get_session()
        # Waits for the rest of the threads
        for thread, container in thread_containers:
            thread.join()
            if container.thrown_exception:
                container.save_error(session)
            else:
                container.save_measures(session)

        # while it is running a container consumes less disk
        self._save(session, run_id)

        for _, container in thread_containers:
            container.remove()

    def _record_init_disk_size(self):
        self._dmeter.record_init_disk_size()

    def _save_disk_size(self, session, run_id, size):
        d = DiskRequired(run_id=run_id, size=size)
        session.add(d)
        session.commit()

    def _save_response_time(self, session, run_id, response_time):
        s = ResponseTime(run_id=run_id, time=response_time)
        session.add(s)
        session.commit()

    def _save(self, session, run_id):
        self._save_disk_size(session, run_id, self._dmeter.get_disk_size_increase())
        self._save_response_time(session, run_id, self._rmeter.response_time)


class RunningContainer(object):
    """
    It starts a container, takes measures and saves them.
    """
    def __init__(self, container_id, container_docker_id, docker_client, container_meter):
        self.id = container_id
        self.docker_id = container_docker_id
        self.allocate = docker_client
        self._meter = container_meter
        self.thrown_exception = None

    def start(self):
        start = time.time()
        with self.allocate() as docker:
            response = docker.start(self.docker_id)
        logging.info('Running container "%s".\n\t%s' % (self.docker_id, response))
        # naive measure
        self.elapsed = time.time() - start
        self._meter.initial_measure()

    def take_measures(self):
        logging.info('Measuring container "%s".' % self.docker_id)
        self._meter.final_measure()

    def _save_cpu(self, session):
        c = CpuRequired( container_id = self.id,
                         total_cpu = self._meter.get_cpu_total(),
                         percentual_cpu = self._meter.get_cpu_percent() )
        session.add(c)

    def _save_memory(self, session):
        m = MemoryRequired( container_id = self.id,
                            usage = self._meter.get_memory_usage(),
                            percentual = self._meter.get_memory_percent(),
                            maximum = self._meter.get_memory_maximum() )
        session.add(m)

    def _save_start_time(self, session):
        c = CreationTime(container_id=self.id, startup_time=self.elapsed)
        session.add(c)

    def save_measures(self, session):
        logging.info('Saving container "%s" measures.' % self.docker_id)
        self._save_cpu(session)
        self._save_memory(session)
        self._save_start_time(session)
        session.commit()

    def save_error(self, session):
        logging.info('Saving errors in container "%s".' % self.docker_id)
        e = ExecutionError(container_id=self.id, message=self.thrown_exception)
        session.add(e)
        session.commit()

    def stop(self):
        with self.allocate() as docker:
            docker.stop(self.docker_id)
        logging.info('Stopping container "%s".' % (self.docker_id))

    def remove(self):  # Clear dist
        # Force just in case stop hadn't be called properly due to an exception
        with self.allocate() as docker:
            docker.remove_container(self.docker_id, force=True)
        logging.info('Removing container "%s".' % (self.docker_id))

    def _wait(self, barrier, waiting_list):
        barrier.wait()
        waiting_list.remove(barrier)

    """
    Run container, measure it and close it.

    :param dao: benchmarking data access object
    :param all_started_barrier: Barrier which ensures that all containers are running
                            (i.e., they are all compiting for computing resources)
                            when their performance is measured.
    :param end_barrier: Barrier which ensures that no container is stopped
                            before all the measurements have been taken.
    """
    def run(self, all_started_barrier, end_barrier, ready_barrier=None):
        to_wait = [all_started_barrier, end_barrier]
        if ready_barrier: to_wait.insert(0, ready_barrier)  # The order is important here
        try:
            self.start()
            # Preference over other barriers to ensure that the response time measure thread starts first
            if ready_barrier:
                self._wait(ready_barrier, to_wait)
            self._wait(all_started_barrier, to_wait)
            self.take_measures()
            self._wait(end_barrier, to_wait)
            self.stop()
        except Timeout as e:
            logging.error('Docker timeout: %s.' % e.message)
            self.thrown_exception = 'Docker client timeout'
        except APIError as ae:
            logging.error('Docker API exception. %s.' % ae)
            self.thrown_exception = str(ae)
        except Exception as others:
            logging.error('Unexpected exception: %s.' % others)
            print 'Prepare yourself because everything will crash now.'
            import sys, traceback
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)
        finally:
            # Other threads might be still waiting for this barriers to be opened:
            for w in to_wait: w.wait()


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
