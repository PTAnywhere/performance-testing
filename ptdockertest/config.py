"""
Created on 5/10/2015

@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
"""

import ConfigParser


class ConfigFileReader(object):

    def __init__(self):
        self.config = ConfigParser.RawConfigParser()

    def set_file_path(self, file_path):
        self.config.read(file_path)

    def get_log(self):
        return self.config.get('benchmark', 'log')

    def get_db(self):
        return self.config.get('benchmark', 'db')

    def get_exposed_port(self):
        return self.config.get('benchmark', 'exposed_pt_port')

    def get_docker_url(self):
        return self.config.get('docker', 'url')

    def get_jar_path(self):
        return self.config.get('pt_checker', 'jar_path')


configuration = ConfigFileReader()
