# 6200-tools
GIOS 6200 tools

# Python test clients for Getfile client wire protocol:

## Installing python
```apt-get install python```

## Testing Server

After running your server, you can run
```python ./gftestclient.py 5```
If you don't pass command line argument, default option tested would be 2


## Testing Client

```python ./gftestserver.py 3```
If you don't pass command line argument, default option tested would be 1


# Java test client for Multithreaded Getfile threading:

This test only sends invalid paths and does not validate the filename. The server should just return File Not Found.

## Installing Java
```apt-get install java-8-openjdk```

## Building
```make```

## Running
```java -classpath ./classes/ edu.gatech.gios.MtgfTestClient number-of-workers min-delay max-delay```

Delays in milliseconds.

Example: A slow test for single-threaded operation:
```java -classpath ./classes/ edu.gatech.gios.MtgfTestClient 1 1000 1000```

Example: Stress test:
```java -classpath ./classes/ edu.gatech.gios.MtgfTestClient 1000 10 10```