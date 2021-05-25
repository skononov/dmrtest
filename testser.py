#!/usr/bin/python3

from dtcom import DTSerialCom
from dtglobals import DEBUG

DEBUG = True

com = DTSerialCom(device='/dev/ttyACM0', timeout=2)

print('Sending STATUS command')

reply = com.command('STATUS', nreply=1)

print('Received:', reply)
