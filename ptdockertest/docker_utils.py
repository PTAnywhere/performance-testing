from itertools import cycle
from contextlib import contextmanager
from threading import BoundedSemaphore
from docker import Client



class DockerClientFactory(object):

    def __init__(self, base_url, max_simultaneous_requests=5, max_clients=100):
        self._base_url = base_url
        self._semaphore = BoundedSemaphore(max_simultaneous_requests)
        self._pool = []
        self._max_clients = max_clients
        self._pool_cycle = None

    def create(self):
        if len(self._pool) < self._max_clients:
            client = DockerBoundedClient(self._base_url, self._semaphore)
            self._pool.append(client)
            return client.get
        else:
            if len(self._pool) == self._max_clients:
                self._pool_cycle = cycle(self._pool)
            return next(self._pool_cycle).get


"""
I have experienced that Docker gets stuck with many simultaneous requests.

Used together the 'with' clause, this class ensures that the docker client will
only be used when the (bounded) semaphore is opened.

NOTE: the simultaneous request don't affect Docker getting blocked.
It was the amount of CPU consumed by the many containers created.
"""
class DockerBoundedClient(object):

    def __init__(self, base_url, semaphore):
        self._semaphore = semaphore
        # FIXME we can reuse the client once we know for sure that it is Thread safe...
        self._client = Client(base_url, version='1.19')

    @contextmanager
    def get(self):
        try:
            self._semaphore.acquire()
            yield self._client
        finally:
            self._semaphore.release()
