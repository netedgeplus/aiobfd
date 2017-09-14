aiobfd: Asynchronous BFD Daemon
=================
Bidirectional Forwarding Detection Daemon written in Python, using [asyncio](https://www.python.org/dev/peps/pep-3156/).

Installation
-----------------
You can obtain a copy of aiofd from GitHub.

Running the service
-------------------
Run aiobfd as following:
```
./run.py 192.168.0.2 192.168.0.5
```
For a full list of options, check:
```
./run.py --help
```

Questions & Answers
-------------------
**Q**: Which Python versions do you support?

**A**: aiobfd will run on Python 3.5+.
***
**Q**: Do you support IPv6?

**A**: Of course!
