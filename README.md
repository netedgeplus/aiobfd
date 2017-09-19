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
***
**Q**: Does aiobfd support BFD Demand mode?

**A**: aiobfd will currently not request to switch to Demand mode. But we will honor a request to go into Demand mode by a remote BFD speaker.
***
**Q**: Does aiobfd support the BFD Echo Function?

**A**: No, aiobfd does not implement the Echo Function. As this is a pure software implemenation we see Echo support as a low priority. if you have a good use case for this, feel free to open up a GitHub issue.
***
**Q**: Does aiobfd support Authentication?

**A**: No, aiobfd does not support authentication at present. This is actively being worked on.
