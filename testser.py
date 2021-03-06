#!/usr/bin/python3

from dtcom import DTSerialCom
import argparse

parser = argparse.ArgumentParser(description='Communicate with a DMR TEST device.')
parser.add_argument('command', type=str,
                    help='command to send')
parser.add_argument('data', metavar='dataword', type=int, nargs='*',
                    help='integer data words to send', default=[])
parser.add_argument('-v', '--verbose', action='store_true',
                    help='verbose print-out')
parser.add_argument('-e', '--expect', metavar='N', type=int,
                    help='expected number of 2-byte words in reply', default=-1)
parser.add_argument('-s', metavar='2|4', type=int, nargs='+',
                    help='integer or whitespace separated list of output word sizes; place it after data words', default=2)

args = parser.parse_args()
# print(args)

DTSerialCom.DEBUG = args.verbose

com = DTSerialCom()

if args.command == 'LOAD PLL':
    if len(args.data) != 7:
        print(f'"LOAD PLL" should be supplied with 7 integers')
        exit(1)
    owordsize = [2] + 6*[4]
elif args.command == 'SET PLLFREQ':
    if len(args.data) != 2:
        print(f'"SET PLLFREQ" should be supplied with 2 integers')
        exit(1)
    print(f"Setting frequency {args.data[1]} Hz to PLL {args.data[0]} and wait locking...")
    isset = com.set_pll_freq(args.data[0], args.data[1])
    print(f'Frequency is{"" if isset else " not"} set.')
    exit(0)
elif args.command == 'SET LFDAC':
    if len(args.data) != 2:
        print(f'"SET LFDAC" should be supplied with 2 integers')
        exit(1)
    owordsize = [2, 4]
else:
    owordsize = args.s

print(f"Call:", args.command, *args.data)
reply = com.command(args.command.encode(), odata=args.data, owordsize=owordsize, nreply=args.expect)
if reply is not None:
    print(f"Reply with {reply.size} words:", reply)
else:
    print(f"Empty reply")
