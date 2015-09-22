# performance-testing

Project created to measure the performance of the Docker-based Packet Tracer.

Installation
------------

Why would you want to install it?

    pip install git+https://github.com/PTAnywhere/performance-testing.git


Requirements
------------

The required packages are automatically installed in the procedure described above.

However, if you are going to contribute to this project, you might want to install __only__ the project's dependencies in your [virtualenv](http://virtualenv.readthedocs.org).

You can install them using the _requirements.txt_ file in the following way:

    pip install -r requirements.txt

Usage
-----

Follow these steps:

1. __Prepare__ benchmark.
    ```cd src/testptdocker; python prepare_database.py```
1. __Run__ benchmark.
    ```cd src/testptdocker; python run_benchmark.py [-test=testId] [-log=/tmp/benchmark.log]```
1. Generate __plots__
    ```cd src/testptdocker; python generate_plots.py [-output=/tmp/plots]```


Acknowledgements
----------------

These performance tests were developed as part of the [FORGE project](http://ict-forge.eu/).
