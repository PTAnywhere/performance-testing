# PTChecker

This folder contains a class which allows you to check when a Packet Tracer session is up and able to answer IPC requests.

It can alson be used to measure the average response time of the instance for a predefine request.

Note that this class depends on the ptipc library.
I cannot provide a version of it as its intellectual property belongs to Cisco.


## Usage

You need to first compile the class using:
```
javac -cp "[ptipc-library-path]" PTChecker.java 
```

Then, you can execute it using:
```
java -cp ".:[ptipc-library-path]" PTChecker [hostname] [port]
```
