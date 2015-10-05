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

    def get_log(self, priotity_value=None):
        if priotity_value: return priority_value
        return self.config.get('benchmark', 'log')

    def get_db(self, priotity_value=None):
        if priotity_value: return priority_value
        return self.config.get('benchmark', 'db')

    def get_docker_url(self, priotity_value=None):
        if priotity_value: return priority_value
        return self.config.get('docker', 'url')

    def get_jar_path(self, priotity_value=None):
        if priotity_value: return priority_value
        return self.config.get('pt_checker', 'jar_path')


configuration = ConfigFileReader()
