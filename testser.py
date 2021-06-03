#!/usr/bin/python3

import sys
from dtcom import DTSerialCom
from dtglobals import DEBUG

DEBUG = True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].encode('utf-8')
        data = [int(arg) for arg in sys.argv[2:]]
    else:
        command = b'STATUS'
        data = None

    com = DTSerialCom()

    if command == b'LOAD PLL':
        assert(len(data)==7)
        owordsize = [2] + 6*[4]
    else:
        owordsize = 2

    com.command(command, odata=data, owordsize=owordsize, nreply=-1)
