#!/usr/bin/env python3

"""aiobfd: Asynchronous BFD Daemon"""

import argparse
import socket
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
    return parser.parse_args()


def run():
    """Run aiobfd"""
    args = parse_arguments()
    app = aiobfd.Daemon(args.local, args.remote, args.family)
    app.run()

if __name__ == '__main__':
    run()
