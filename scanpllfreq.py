#!/usr/bin/python3

from threading import Thread, Event
from dtcom import DTSerialCom

freqset = Event()
refmode = None


def setfreq(pllnum, f):
    global refmode
    isset, refmode = com.set_pll_freq(pllnum, f)
    if isset:
        freqset.set()


if __name__ == "__main__":
    pllnum = 2
    flow = 138000000
    fup = 800000000
    df = 21200

    DTSerialCom.DEBUG = False
    com = DTSerialCom()

    print(f'Scanning frequency range for pllnum={pllnum} from {flow} Hz to {fup} Hz with step {df} Hz')
    for f in range(flow, fup, df):
        print(f, end=': ')
        freqset.clear()
        thread = Thread(target=setfreq, args=(pllnum, f))
        thread.start()
        thread.join(5)
        if thread.is_alive():
            print('looped', flush=True)
        elif not freqset.is_set():
            print('failed', flush=True)
        else:
            print(f'success {refmode}', flush=True)
