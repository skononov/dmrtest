from ctypes import cdll, c_double, c_uint, c_int, byref
from numpy import pi, linspace, sin, abs, sqrt
from numpy.random import default_rng
from scipy.special import jn
from scipy.signal import blackman
from scipy.fft import rfft, fftfreq
from time import time
import matplotlib.pyplot as plt
import timeit

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
    rmsnoise = 0.001 # rms of noise added
    t = linspace(0, T*N, N, endpoint=False)
    at = sum([jn(n, d)/jn(1, d) * sin(2*pi*(n*fm*t + rng.random()))
              for n in range(1, 10)]) + rng.normal(0, rmsnoise, N)

    at2 = blackman(N)*sum([jn(n, d)/jn(1, d) * sin(2*pi*(n*fm*t + rng.random()))
                           for n in range(1, 10)]) + rng.normal(0, rmsnoise, N)

    f = fftfreq(N, T)[:N//2]
    af = 2/N*abs(rfft(at))[:-1]
    af2 = 2/N*abs(rfft(at2))[:-1]

    dt = timeit.timeit('2/N*abs(rfft(at))[:-1]',
                        number=100, globals=globals())/100
    print(f'fft execution time: {dt:3g} sec')

    dt = timeit.timeit('get_peak(af, int(fm*N*T*0.9), int(fm*N*T*1.1))', 
                        number=100, globals=globals())/100
    print(f'get_peak execution time: {dt:3f} sec')

    pwr, fpeak = get_peak(af, int(fm*N*T*0.9), int(fm*N*T*1.1))
    pwr2, fpeak2 = get_peak(af2, int(fm*N*T*0.9), int(fm*N*T*1.1))
    fpeak /= N*T  # transform to Hz
    fpeak2 /= N*T  # transform to Hz
    pwr2 /= sum(blackman(N)**2)/N
    print(f"Raw signal: Power={pwr:4g}, Fpeak={fpeak:.1f}Hz")
    print(f"Signal w. Blackman: Power={pwr2:4g}, Fpeak={fpeak2:.1f}Hz")

    dt = timeit.timeit('get_inl(af, fm*N*T)',
                        number=100, globals=globals())/100
    print(f'get_inl execution time: {dt:3g} sec')

    inl, mi = get_inl(af, fm*N*T)
    inl2, mi2 = get_inl(af2, fm*N*T)
    print(f"Raw signal: INL={inl:5g}, MI={mi:.2f}")
    print(f"Signal w. Blackman: INL={inl2:5g}, MI={mi2:.2f}")

    plt.figure(figsize=(12, 10))
    plt.subplot(211)
    plt.plot(t, at, '-', label='Raw signal')
    plt.plot(t, at2, '-', label='Signal w. Blackman window')
    plt.xlabel('Time, s')
    plt.ylabel('Amplitude')
    plt.legend()
    plt.title(r'$f_{mod}$=%.1f kHz, MI=%.1f, $RMS_{noise}=%2g$' % (fm/1000, d, rmsnoise))

    plt.subplot(212)
    plt.plot(f, af, 'k-', label='Raw signal FFT')
    plt.plot(f, af2, 'b-', label='FFT of Singal w. Blackman window')
    plt.plot(fpeak, sqrt(pwr), 'ro')
    plt.xlabel('Frequency, Hz')
    plt.ylabel('Fourier amplitude')
    plt.semilogy()
    ymin, ymax = plt.ylim()
    plt.ylim(ymin, 10*ymax)
    plt.legend()
    plt.text(0.2*0.5/T, ymax*5, 
             'Eval. Raw: PWR=%4g $f_{peak}$=%.1f INL=%4g MI=%.2f' % (pwr, fpeak, inl, mi) + 
             '\nEval. Blackman: PWR=%4g $f_{peak}$=%.1f INL=%4g MI=%.2f' % (pwr2, fpeak2, inl2, mi2), 
             va='top', ha='left')

    plt.tight_layout()
    plt.savefig('../pics/fft_analysis.png')
    plt.show()
