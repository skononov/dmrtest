from ctypes import cdll, c_uint, c_int
from numpy.random import default_rng
from time import time

_libdmr = cdll.LoadLibrary("./libdmr.so")

def _init_ctypes_array(ctype, size: int, value: int = 0):
    array_ctype = ctype*size
    return array_ctype(*[value]*size)

def get_pll_regs(freq: int):
    # init ctypes uint array with nulls
    regs = (c_uint*6)(*[0]*6)
    _libdmr.getpllreg(c_uint(freq), c_int(1), c_int(1), c_int(0), c_int(0), c_int(0), regs)
    regs = list(regs)
    return regs

if __name__ == "__main__":
    rng = default_rng(int(time()*100))
    rndfreqs = rng.integers(100000, 500000, 10)
    for freq in rndfreqs:
        regs = get_pll_regs(freq)
        print(f'Registers for input frequency {freq}: {regs}')
    