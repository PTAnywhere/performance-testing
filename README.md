# performance-testing

Project created to measure the performance of the Docker-based Packet Tracer.

It is developed in Python 3 (to use [Barriers](https://docs.python.org/3/library/threading.html#barrier-objects)).

Installation
------------

Why would you want to install it?

    pip3 install git+https://github.com/PTAnywhere/performance-testing.git


Requirements
------------

The required packages are automatically installed in the procedure described above.

However, if you are going to contribute to this project, you might want to install __only__ the project's dependencies in your [virtualenv](http://virtualenv.readthedocs.org).

You can install them using the _requirements.txt_ file in the following way:

    pip3 install -r requirements.txt

Usage
-----

Go to the top package (```cd ptdockertest```) and follow these steps:

* __Prepare__ benchmark.
```
python3 prepare_benchmark.py [-db /tmp/benchmark.db]
```
* __Run__ benchmark.
```
python3 run_benchmark.py [-db /tmp/benchmark.db] [-log /tmp/benchmark.log] testId
```
* Generate __plots__
```
python3 generate_plots.py [-db /tmp/benchmark.db] [-output /tmp/plots] testId
```


Acknowledgements
----------------

These performance tests were developed as part of the [FORGE project](http://ict-forge.eu/).
