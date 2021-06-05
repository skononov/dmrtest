from ctypes import cdll, c_double, c_uint, c_int, byref
from numpy import pi, linspace, sin, abs, sqrt
from numpy.random import default_rng
from scipy.special import jn
from scipy.fft import rfft, fftfreq
from time import time
import matplotlib.pyplot as plt

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


if __name__ == "__main__":
    print("\nTesting pll calc code")
    rng = default_rng(int(time()*100))
    rndfreqs = rng.integers(137000000, 800000000, 20)
    print('Frequency\tRegisters')
    for freq in rndfreqs:
        regs = get_pll_regs(freq)
        print(freq, '\t', ' '.join([f'{r:d}' for r in regs]), sep='')

    print("\nTesting spectrum peak search & INL")
    N = 16384  # number of ADC points
    T = 1/120000.  # sampling period in s
    fm = 10000  # modulating frequency
    d = 2  # modulation index
    t = linspace(0, T*N, N, endpoint=False)
    at = sum([jn(n, d)/jn(1, d) * sin(2*pi*(n*fm*t + rng.random()))
              for n in range(1, 8)]) + rng.normal(0, 0.01, N)

    f = fftfreq(N, T)[:N//2]
    af = 2/N*abs(rfft(at))[:-1]

    pwr, fpeak = get_peak(af, int(fm*N*T*0.9), int(fm*N*T*1.1))
    fpeak /= N*T  # transform to Hz
    print(f"Power={pwr:4g}, Fpeak={fpeak:.1f}Hz")

    inl, mi = get_inl(af, fm*N*T)
    print(f"INL={inl:5g}, MI={mi:.2f}")

    plt.figure(figsize=(10, 8))
    plt.subplot(211)
    plt.plot(t[:500], at[:500], '-')
    plt.xlabel('Time, s')
    plt.ylabel('Amplitude')
    plt.title(r'$f_{mod}$=%.1f kHz, MI=%.1f' % (fm/1000, d))

    plt.subplot(212)
    plt.plot(f, af, '-')
    plt.plot(fpeak, sqrt(pwr), 'ro')
    plt.xlabel('Frequency, Hz')
    plt.ylabel('Fourier amplitude')
    plt.text(0.7*0.5/T, 0.5, 'Evaluated:\nPWR=%4g $f_{peak}$=%.1f\nINL=%4g MI=%.2f' % (pwr, fpeak, inl, mi), va='top')
    plt.semilogy()
    plt.savefig('../pics/fft_analysis.png')
    plt.show()
