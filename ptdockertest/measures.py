"""
Created on 30/10/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Classes to take measures.
"""

import logging
import subprocess
from humanfriendly import format_size, parse_size


class ResponseTimeMeter(object):
    
    def __init__(self, checker_jar_path, ipc_port):
        self.response_time = None
        self._jar_path = checker_jar_path
        self._port = ipc_port

    def measure(self, timeout):
        logging.info('Measuring response time.')
        ret = subprocess.check_output(['java', '-jar', self._jar_path, 'localhost', str(self._port), str(timeout)])
        self.response_time = int(ret)
        logging.info('Response time: ' + ret)


class DockerMeter(object):

    def __init__(self, allocate_docker):
        self.allocate = allocate_docker
        self.init_size = None
        self.init_size_du = None

    def _get_disk_size(self):
        """Returns data used by Docker in bytes."""
        # docker.info() returns an awful data structure...
        with self.allocate() as docker:
            for field in docker.info()['DriverStatus']:
                if field[0]=='Data Space Used':
                    return parse_size(field[1])  # Value in bytes
            logging.error('"Data Space Used" field was not found in the data returned by Docker.')

    def _get_disk_size_du(self):
        """Returns in Docker's root directory size in KBs."""
         # This function requires you to run the script as sudo
        directory = None
        with self.allocate() as docker:
            directory = docker.info()['DockerRootDir']
        try:
            ret = subprocess.check_output(['sudo', 'du', '-sk', directory])
            return int(ret.split()[0]) # Value in KBs
        except subprocess.CalledProcessError as e:
            logging.error('Error getting disk size using du: ' + e.output)

    def _log_measure_comparison(self, info_measure, du_measure):
        logging.info('Additional disk that Docker demanded (measured with docker.info()): ' + format_size(info_measure) + '.')
        logging.info('Additional disk that Docker demanded (measured with du): ' + format_size(du_measure) + '.')
        difference = du_measure - info_measure
        if difference>1024:  # More than 1KB of difference
            logging.warning('du measures %s more than docker.info().' % format_size(difference))
        elif difference<-1024:  # Less than 1MB of difference
            logging.warning('du measures %s less than docker.info().' % format_size(difference*-1))

    def record_init_disk_size(self):
        self.init_size = self._get_disk_size()
        self.init_size_du = self._get_disk_size_du()

    def get_disk_size_increase(self):
        folder_size_increase = self._get_disk_size() - self.init_size
        post_size_du = self._get_disk_size_du()
        if self.init_size_du and post_size_du:
            folder_size_increase_du = post_size_du - self.init_size_du
            self._log_measure_comparison(folder_size_increase, folder_size_increase_du * 1024)
        else:
            logging.warning('At least one of the du measures could not be get and compared to the folder size reported by Docker.')
        return folder_size_increase

    def get_container_meter(self, container_id):
        return DockerContainerMeter(container_id, self.allocate)


class DockerContainerMeter(object):
    
    def __init__(self, container_id, allocate_docker):
        self.container_id = container_id
        self.allocate = allocate_docker
        self._pre_measure = None
        self._measure = None

    def _get_measure(self):
        with self.allocate() as docker:
            return next(docker.stats(self.container_id, decode=True))

    def initial_measure(self):
        self._pre_measure = self._get_measure()        
    
    def final_measure(self):
        self._measure = self._get_measure()

    def get_cpu_total(self):
        return self._measure['cpu_stats']['cpu_usage']['total_usage']

    def get_cpu_percent(self):
        # translating it from calculateCPUPercent in https://github.com/docker/docker/blob/master/api/client/stats.go
        cpu_percent = 0.0
        previous_cpu = self._pre_measure['cpu_stats']['cpu_usage']['total_usage']
        previous_system = self._pre_measure['cpu_stats']['system_cpu_usage']
        post_cpu = self._measure['cpu_stats']['cpu_usage']['total_usage']
        post_system = self._measure['cpu_stats']['system_cpu_usage']
        # Otherwise, if both are numbers are integer, the division will return an integer.
        # Alternatively, we could use: from __future__ import division
        cpu_delta = post_cpu - previous_cpu
        system_delta = float(post_system - previous_system)
        if system_delta > 0.0 and cpu_delta > 0.0:
            cpu_percent = (cpu_delta / system_delta) * len(self._measure['cpu_stats']['cpu_usage']['percpu_usage']) * 100.0
        return cpu_percent

    def get_memory_usage(self):
        return self._measure['memory_stats']['usage']

    def get_memory_percent(self):
        return self._measure['memory_stats']['usage'] / float(self._measure['memory_stats']['limit']) * 100.0

    def get_memory_maximum(self):
        return self._measure['memory_stats']['max_usage']
