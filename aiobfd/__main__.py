"""aiobfd: Asynchronous BFD Daemon"""

import argparse
import socket
import logging
import logging.handlers
import sys
import aiobfd

_LOG_LEVELS = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']


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
    parser.add_argument('-l', '--log-level', default='WARNING',
                        help='Logging level', choices=_LOG_LEVELS)
    parser.add_argument('-o', '--no-log-to-stdout', action='store_true',
                        help='Disable logging to stdout; will be ignored if no'
                             ' other logging is selected.')
    parser.add_argument('-f', '--log-to-file', action='store_true',
                        help='Enable logging to a file on the filesystem')
    parser.add_argument('-n', '--log-file', default='/var/log/aiobfd.log',
                        help='Path on filesystem to log to, if enabled')
    parser.add_argument('-s', '--log-to-syslog', action='store_true',
                        help='Enable logging to a syslog handler')
    parser.add_argument('-y', '--log-sock', default='/dev/log',
                        help='Syslog socket to log to, if enabled')
    return parser.parse_args()


def main():
    """Run aiobfd"""
    args = parse_arguments()
    handlers = []

    if (args.log_to_file or args.log_to_syslog) and not args.no_log_to_stdout:
        handlers.append(logging.StreamHandler(sys.stdout))
    if args.log_to_file:
        handlers.append(logging.handlers.WatchedFileHandler(args.log_file))
    if args.log_to_syslog:
        handlers.append(logging.handlers.SysLogHandler(args.log_sock))

    log_format = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
    logging.basicConfig(handlers=handlers, format=log_format,
                        level=logging.getLevelName(args.log_level))
    control = aiobfd.Control(args.local, [args.remote], family=args.family,
                             passive=args.passive,
                             rx_interval=args.rx_interval*1000,
                             tx_interval=args.tx_interval*1000,
                             detect_mult=args.detect_mult)
    control.run()

if __name__ == '__main__':
    main()
