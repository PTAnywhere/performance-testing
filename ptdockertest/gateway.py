"""
Created on 23/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Docker client.
"""

from docker import Client


class DockerClient(object):
    def __init__(self, base_url):
        self.client = Client(base_url)

    def create_container(self, image_name):
        return self.client.create_container(image=image_name)

    def start_container(self, container):
        return self.client.start(container=container.get('Id'))
