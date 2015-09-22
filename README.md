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

Go to the top package (```cd ptdockertest```) and follow these steps:

1. __Prepare__ benchmark.
```
    python prepare_benchmark.py [-db /tmp/benchmark.db]
```
1. __Run__ benchmark.
```
python run_benchmark.py [-db /tmp/benchmark.db] [-log /tmp/benchmark.log] testId
```
1. Generate __plots__
```
python generate_plots.py [-db /tmp/benchmark.db] [-output /tmp/plots] testId
```


Acknowledgements
----------------

These performance tests were developed as part of the [FORGE project](http://ict-forge.eu/).
