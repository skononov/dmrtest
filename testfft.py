from dtglobals import hfAdcRange
from dt_c_api import get_peak, get_inl_fm
from numpy import pi, linspace, sin, abs, sqrt, floor, floor
from numpy.fft import rfft as np_rfft
try:
    import pyfftw
except ImportError:
    pyfftw = None
from numpy.random import default_rng
from scipy.special import jn
from scipy.signal import blackman
from scipy.fft import rfft, rfftfreq
from time import time
import matplotlib.pyplot as plt
import timeit
import os

if __name__ == "__main__":
    plt.style.use('dark_background')
    rng = default_rng(int(time()))

    print("\nTesting spectrum peak search & INL")
    A0 = 1  # amplitude of the main harmonic in Volts
    A0c = A0/hfAdcRange*(2**31)  # amplitude of main harmonics in ADC LSB
    N = 16384  # number of ADC counts
    T = 1/120000.  # sampling period in s
    fm = 1000  # modulating frequency
    h = 0.6  # modulation index
    nh = 20  # number of harmonics counted
    rmsnoise = 0.001  # rms of noise added in Volts
    rmsnoise_c = rmsnoise/hfAdcRange*(2**31)  # rms of noise added in ADC LSB
    t = linspace(0, T*N, N, endpoint=False)

    print(f"Number of harmonics counted is {nh}")

    at = floor(sum([A0c * jn(n, h)/jn(1, h) * sin(2*pi*(n*fm*t + rng.random())) for n in range(1, nh+1)]) +
               rng.normal(0, rmsnoise_c, N)) / (2**31) * hfAdcRange

    bwin = blackman(N)
    bwin /= sqrt(sum(bwin**2)/N)

    atw = bwin*at

    f = rfftfreq(N, T)
    af = 2/N*abs(rfft(at))
    afw = 2/N*abs(rfft(atw))

    dt = timeit.timeit('rfft(atw)',
                       number=100, globals=globals())/100
    print(f'scipy.fft.rfft execution time: {dt:3g} sec')

    dt = timeit.timeit('np_rfft(atw)',
                       number=100, globals=globals())/100
    print(f'numpy.fft.rfft execution time: {dt:3g} sec')

    if pyfftw is not None:
        pyfftw.interfaces.cache.enable()
        pyfftw.interfaces.numpy_fft.rfft(atw)  # first run for optimization
        dt = timeit.timeit('pyfftw.interfaces.numpy_fft.rfft(atw)',
                           number=100, globals=globals())/100
        print(f'pyfftw.interfaces.numpy_fft.rfft execution time: {dt:3g} sec')

    dt = timeit.timeit('get_peak(af, int(fm*N*T*0.9), int(fm*N*T*1.1))',
                       number=100, globals=globals())/100
    print(f'get_peak execution time: {dt:3f} sec')

    pwr, fpeak = get_peak(af, int(fm*N*T*0.9), int(fm*N*T*1.1))
    pwrw, fpeakw = get_peak(afw, int(fm*N*T*0.9), int(fm*N*T*1.1))
    fpeak /= N*T  # transform to Hz
    fpeakw /= N*T  # transform to Hz
    print(f"Raw signal: Power={pwr:4g}, Fpeak={fpeak:.1f}Hz")
    print(f"Signal w. Blackman: Power={pwrw:4g}, Fpeak={fpeakw:.1f}Hz")

    dt = timeit.timeit('get_inl_fm(af, fm*N*T)',
                       number=100, globals=globals())/100
    print(f'get_inl_fm execution time: {dt:3g} sec')

    inl, mi = get_inl_fm(af, fm*N*T)
    inlw, miw = get_inl_fm(afw, fm*N*T)
    print(f"Raw signal: INL={inl:5g}, MI={mi:.2f}")
    print(f"Signal w. Blackman: INL={inlw:5g}, MI={miw:.2f}")

    plt.figure(figsize=(12, 10))
    plt.subplot(211)
    plt.plot(t, at, '-', label='Raw signal')
    plt.plot(t, atw, '-', label='Signal w. Blackman window')
    plt.xlabel('Time, s')
    plt.ylabel('Amplitude')
    plt.legend()
    plt.title(r'$f_{mod}$=%.1f kHz, MI=%.1f, $RMS_{noise}=%2g$' % (fm/1000, h, rmsnoise))

    plt.subplot(212)
    plt.plot(f, af, label='Raw signal FFT')
    plt.plot(f, afw, label='FFT of Singal w. Blackman window')
    plt.plot(fpeak, sqrt(pwr), 'ro')
    plt.xlabel('Frequency, Hz')
    plt.ylabel('Fourier amplitude')
    plt.semilogy()
    ymin, ymax = plt.ylim()
    plt.ylim(ymin, 10*ymax)
    plt.legend()
    plt.text(0.2*0.5/T, ymax*5,
             'Eval. Raw: PWR=%4g $f_{peak}$=%.1f INL=%4g MI=%.2f' % (pwr, fpeak, inl, mi) +
             '\nEval. Blackman: PWR=%4g $f_{peak}$=%.1f INL=%4g MI=%.2f' % (pwrw, fpeakw, inlw, miw),
             va='top', ha='left')

    plt.tight_layout()

    try:
        os.mkdir('../pics')
    except FileExistsError:
        pass

    plt.savefig('../pics/fft_analysis.png')
    plt.show()
