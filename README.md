aiobfd: Asynchronous BFD Daemon
=================
Bidirectional Forwarding Detection Daemon written in Python, using [AsyncIO](https://www.python.org/dev/peps/pep-3156/). This package enables you to run the BFD protocol between the host and a neighbouring device, often a router.

A common use case for aiobfd would be to pair it with a BGP speaker such as [ExaBGP](https://github.com/Exa-Networks/exabgp) for anycast loadbalancing. By establishing a BFD session alongside the BGP session it's possible to to do subsecond failure detection and fail-over.

This implementation is compliant with:
 * [RFC5880](https://tools.ietf.org/html/rfc5880): Bidirectional Forwarding Detection (BFD)
 * [RFC5881](https://tools.ietf.org/html/rfc5881): Bidirectional Forwarding Detection (BFD) for IPv4 and IPv6 (Single Hop)

Installation
-----------------
aiobfd is available from [PyPI](https://pypi.python.org/pypi/aiobfd) and can be installed with pip.
```
pip install aiobfd
```

Running the service
-------------------
After installation you can run a basic aiobfd as following.
This assumes 192.168.0.2 is a locally configured IP address and 192.168.0.5 is the remote BFD speaker.
```
aiobfd 192.0.2.2 192.0.2.1
```
A more complex example over IPv6 where we agree to transmit & receive packets at 15ms intervals and use a detection multiplier of 3, resulting in a failure detection time of 45ms.
```
aiobfd 2001:db8::2 2001:db8::1 --rx-interval 15 --tx-interval 15 --detect-mult 3
```

Security considerations
-----------------------
To comply with [section 5 of RFC 5881](https://tools.ietf.org/html/rfc5881#section-5) a BFD peer should drop any BFD packets with a TTL/HL of less than the maximum (255) when authentication is not used. aiobfd does not currently check the TTL/HL value on incoming packets. You should make sure that only compliant packets can reach the service. Assuming a default DROP policy an ip(6)tables rule such as these examples should achieve the desired result.
```
iptables -A INPUT -i eth0 -p udp --dport 3784  --ttl-eq 255 -j ACCEPT
ip6tables -A INPUT -i eth0 -p udp --dport 3784 --hl-eq 255 -j ACCEPT
```

Questions & Answers
-------------------
**Q**: Which Python versions do you support?

**A**: aiobfd will run on Python 3.5+.
***
**Q**: Do you support IPv6?

**A**: Of course!
***
**Q**: What sort of fail-over times can I achieve?

**A**: In our testing we have succesfully setup and maintained BFD sessions with remote hardware routers with 10ms intervals and a detection multiplier of 3. Most software routers used in testing etc. had to use use less aggressive timers, up to around 300ms detection times.
***
**Q**: Does aiobfd support BFD Demand mode?

**A**: aiobfd will never request to switch to Demand mode. But it does honor a request to go into Demand mode by a remote BFD speaker.
***
**Q**: Does aiobfd support the BFD Echo Function?

**A**: No, aiobfd does not implement the Echo Function. As this is a pure software implemenation we see Echo support as a low priority. if you have a good use case for this, feel free to open up a GitHub issue.
***
**Q**: Does aiobfd support Authentication?

**A**: No, aiobfd does not support authentication at present.

Other BFD implementations
-------------------

* [FreeBFD](https://github.com/silpertan/FreeBFD) - a C implementation, IPv4 only
* [OpenBFDD](https://github.com/dyninc/OpenBFDD) - a C implemenation using a beacon service which relies on a control utility to be configured
* [GoBFD](https://github.com/jthurman42/go-bfd) - early work on a Go BFD library
