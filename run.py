#!/usr/bin/env python3

"""aiobfd: Asynchronous BFD Daemon"""

import argparse
import socket
import logging
import sys
import aiobfd


def parse_arguments():
    """Parse the user arguments"""
    parser = argparse.ArgumentParser(
        description='Maintain a BFD session with a remote system')
    parser.add_argument('local', help='Local IP address or hostname')
    parser.add_argument('remote', help='Remote IP address or hostname')
    family_group = parser.add_mutually_exclusive_group()
    family_group.add_argument('-4', '--ipv4', action='store_const',
                              dest='family', default=socket.AF_UNSPEC,
                              const=socket.AF_INET,
                              help='Force IPv4 connectivity')
    family_group.add_argument('-6', '--ipv6', action='store_const',
                              dest='family', default=socket.AF_UNSPEC,
                              const=socket.AF_INET6,
                              help='Force IPv6 connectivity')
    parser.add_argument('-r', '--rx-interval', default=1000, type=int,
                        help='Required minimum Rx interval (ms)')
    parser.add_argument('-t', '--tx-interval', default=1000, type=int,
                        help='Desired minimum Tx interval (ms)')
    parser.add_argument('-m', '--detect-mult', default=1, type=int,
                        help='Detection multiplier')
    parser.add_argument('-p', '--passive', action='store_true',
                        help='Take a passive role in session initialization')
    log_group = parser.add_mutually_exclusive_group()
    log_group.add_argument('-v', '--verbose', action='store_const',
                           dest='loglevel', default=logging.WARNING,
                           const=logging.INFO)
    log_group.add_argument('-d', '--debug', action='store_const',
                           dest='loglevel', default=logging.WARNING,
                           const=logging.DEBUG)
    return parser.parse_args()


def run():
    """Run aiobfd"""
    args = parse_arguments()
    logging.basicConfig(stream=sys.stdout, level=args.loglevel,
                        format='%(asctime)s %(name)-12s '
                               '%(levelname)-8s %(message)s')
    control = aiobfd.Control(args.local, [args.remote], family=args.family,
                             passive=args.passive,
                             rx_interval=args.rx_interval*1000,
                             tx_interval=args.tx_interval*1000,
                             detect_mult=args.detect_mult)
    control.run()

if __name__ == '__main__':
    run()
