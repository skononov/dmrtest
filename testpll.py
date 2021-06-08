#!/usr/bin/python3

import sys
from dt_c_api import get_pll_regs

if __name__ == "__main__":
    flow = 137000000
    fup = 800000000

    if len(sys.argv) == 1:
        print("Usage: %s frequency_hz\n\tfrequency_hz - integer between %d and %d" % (sys.argv[0], flow, fup))
        exit(0)

    for arg in sys.argv[1:]:
        freq = abs(int(arg))
        if freq < flow or freq > fup:
            print("%d: frequency must be integer between %d and %d" % (freq, flow, fup))
            continue

        regs = get_pll_regs(freq)
        print('Frequency: %d\nRegisters: %s' % (freq, ' '.join([f'{r:d}' for r in regs])))
