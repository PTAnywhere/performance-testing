from contextlib import contextmanager
from threading import BoundedSemaphore
from docker import Client



class DockerClientFactory(object):

    def __init__(self, base_url, max_simultaneous_requests=5):
        self._base_url = base_url
        self._semaphore = BoundedSemaphore(max_simultaneous_requests)

    def create(self):
        return DockerBoundedClient(self._base_url, self._semaphore).get


"""
I have experienced that Docker gets stuck with many simultaneous requests.

Used together the 'with' clause, this class ensures that the docker client will
only be used when the (bounded) semaphore is opened.
"""
class DockerBoundedClient(object):

    def __init__(self, base_url, semaphore):
        self._semaphore = semaphore
        # FIXME we can reuse the client once we know for sure that it is Thread safe...
        self._client = Client(base_url)

    @contextmanager
    def get(self):
        try:
            self._semaphore.acquire()
            yield self._client
        finally:
            self._semaphore.release()
