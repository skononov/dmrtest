from ctypes import cdll, c_double, c_uint, c_int, byref

_libdmr = cdll.LoadLibrary("./libdmr.so")


def get_pll_regs(freq: int):
    """ Return PLL register values for a given frequency setting
    """
    # init ctypes uint array with nulls
    regs = (c_uint*6)(*[0]*6)
    _libdmr.getpllreg(c_uint(freq),
                      c_int(1), c_int(1), c_int(0), c_int(0), c_int(0),
                      regs)
    regs = list(regs)
    return regs


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
