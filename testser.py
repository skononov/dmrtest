#!/usr/bin/python3

import sys
from dtcom import DTSerialCom

if __name__ == "__main__":
    if '-v' in sys.argv:
        DTSerialCom.DEBUG = True
        sys.argv.remove('-v')

    if len(sys.argv) > 1:
        command = sys.argv[1].encode('utf-8')
        data = [int(arg) for arg in sys.argv[2:]]
    else:
        print(f"Usage: {sys.argv[0]} [-v] command [data...]")
        exit(0)

    com = DTSerialCom()

    if command == b'LOAD PLL':
        assert(len(data)==7)
        owordsize = [2] + 6*[4]
    elif command == b'SET PLLFREQ':
        assert(len(data)==1)
        print(f"Setting frequency to PLL and wait for lock...")
        isset, foffset = com.set_pll_freq(data[0])
        print(f'Frequency is{"" if isset else " not"} set.' + (f'FOFFSET={foffset}' if isset else ''))
        exit(0)
    else:
        owordsize = 2

    print(f"Call:", command.decode(), *data)
    reply = com.command(command, odata=data, owordsize=owordsize, nreply=-1)
    if reply != []:
        print(f"Reply:", *reply)
    else:
        print(f"Empty reply")
