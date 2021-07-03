from ctypes import cdll, c_double, c_uint, c_int, byref
# from ctypes.util import find_library # does not work with LD_LIBRARY_PATH
from numpy import array
from os import getenv

_libdmr = cdll.LoadLibrary(getenv("HOME") + "/dmr/lib/libdmr.so")


def get_pll_regs(freq: int):
    """ Return PLL register values for a given frequency setting
    """
    # init ctypes uint array with nulls
    regs = (c_uint*6)(*[0]*6)
    rc = _libdmr.getpllreg(c_uint(freq),
                           c_int(1), c_int(1), c_int(0), c_int(0), c_int(0),
                           regs)
    if rc == 0:
        return None

    return list(regs)


def get_peak(amp, start: int, end: int):
    """ Return peak power and weghted mean frequency for a given FFT spectrum
    """
    c_amp = (c_double*len(amp))(*amp)
    c_pwr = c_double(0)
    c_fpeak = c_double(0)
    rc = _libdmr.peak_search(c_amp, c_int(start), c_int(end),
                             byref(c_pwr), byref(c_fpeak))
    if rc == c_int(0):
        return None, None

    return c_pwr.value, c_fpeak.value


def get_inl(amp, fm):
    """ Return INL and modulation index for a given FFT spectrum
        and nominal modulating frequency
    """
    c_amp = (c_double*len(amp))(*amp)
    c_inl = c_double(0)
    c_h = c_double(0)
    rc = _libdmr.get_inl(c_amp, c_int(len(amp)), c_double(fm),
                         byref(c_inl), byref(c_h))
    if rc == c_int(0):
        return None, None
    return c_inl.value, c_h.value


def get_ber(iamp, qamp, maxlen):
    """ Calculate number of total and erroneously decoded symbols, symbol intervals
    """
    c_size = c_int(len(iamp))
    c_iamp = (c_int*len(iamp))(*iamp)
    c_qamp = (c_int*len(qamp))(*qamp)
    c_iref = (c_int*maxlen)(*[0]*maxlen)
    c_qref = (c_int*maxlen)(*[0]*maxlen)
    c_symlenref = (c_int*4)(*[0]*4)
    c_maxlen = c_int(maxlen)
    c_numerr = c_int(0)
    c_numbit = c_int(0)
    rc = _libdmr.bercalc(c_iamp, c_qamp, c_size, byref(c_numerr), byref(c_numbit), c_iref, c_qref, c_symlenref, c_maxlen)
    if rc == c_int(0):
        return None, None
    return c_numerr.value, c_numbit.value, array(c_iref, dtype=int), array(c_qref, dtype=int), array(c_symlenref, dtype=int)
