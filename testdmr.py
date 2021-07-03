from dtglobals import adcSampleFrequency
from numpy import linspace, genfromtxt, sqrt, abs
from scipy.fft import rfft, rfftfreq
from scipy.signal import blackman

import tasks
import matplotlib.pyplot as plt

if __name__ == "__main__":
    Qt = genfromtxt('Qdmr.txt', dtype='int32')
    print(f'{Qt.size} points read from Idmr.txt')
    It = genfromtxt('Idmr.txt', dtype='int32')
    print(f'{It.size} points read from Qdmr.txt')

    t = linspace(0, It.size/adcSampleFrequency, It.size, endpoint=False)

    tasks.DEBUG = True
    dmrtask = tasks.DTDMRInput()
    fftlen = dmrtask.fftlen

    res = dmrtask.dmr_test_analysis(It, Qt)
    if res is None:
        print('Failed DMR analysis')
        exit(1)

    symintervals = res[3]
    dibits = ['00', '10', '01', '11']

    _, (axi, axq) = plt.subplots(2, 1, sharex=True, figsize=(12, 6))
    axi.plot(t, It, '.')
    axi.set_title('Raw I signal')
    axi.set_ylabel('Amplitude')
    ymin, ymax = axi.get_ylim()
    for i, (istart, iend) in enumerate(symintervals):
        tmin, tmax = t[istart], t[iend]
        axi.add_patch(plt.Rectangle((tmin, ymin), (tmax-tmin), (ymax-ymin), ls='-', ec="k", fc="r", alpha=0.5))
        axi.text((tmin+tmax)/2, ymax*1.06, dibits[i], ha='center')

    axq.plot(t, Qt, '.')
    axq.set_title('Raw Q signal')
    axq.set_xlabel('Time, s')
    axq.set_ylabel('Amplitude')
    ymin, ymax = axq.get_ylim()
    for i, (istart, iend) in enumerate(symintervals):
        tmin, tmax = t[istart], t[iend]
        axq.add_patch(plt.Rectangle((tmin, ymin), (tmax-tmin), (ymax-ymin), ls='-', ec="k", fc="r", alpha=0.5))
        axq.text((tmin+tmax)/2, ymax*1.06, dibits[i], ha='center')

    plt.tight_layout()

    f = rfftfreq(fftlen, 1/adcSampleFrequency)

    _, ax = plt.subplots(3, 4, sharex=True, figsize=(12, 9))
    for i in range(4):
        If = res[4][i]
        Qf = res[5][i]
        Af = res[6][i]
        ax[0][i].plot(f[:10], If[:10], '-o')
        ax[0][i].set_title(f'I FFT, dibit {dibits[i]}')
        ax[0][i].set_ylabel('Amplitude')

        ax[1][i].plot(f[:10], Qf[:10], '-o')
        ax[1][i].set_title(f'Q FFT, dibit {dibits[i]}')
        ax[1][i].set_ylabel('Amplitude')

        ax[2][i].plot(f[:10], Af[:10], '-o')
        ax[2][i].set_title(r'$\sqrt{If^{2}+Qf^{2}}$, dibit ' + f'{dibits[i]}')
        ax[2][i].set_xlabel('Frequency, Hz')
        ax[2][i].set_ylabel('Amplitude')

    plt.tight_layout()

    bwin = blackman(It.size)
    bwin /= sqrt(sum(bwin**2)/It.size)
    If = 2/It.size * abs(rfft(bwin*It))
    Qf = 2/It.size * abs(rfft(bwin*Qt))
    f = rfftfreq(It.size, 1/adcSampleFrequency)

    _, (axi, axq, axiq2) = plt.subplots(3, 1, sharex=True, figsize=(12, 9))
    axi.plot(f, If, '-', color='C0')
    axi.set_title('I FFT')
    axi.set_ylabel('Amplitude')

    axq.plot(f, Qf, '-', color='C1')
    axq.set_title('Q FFT')
    axq.set_ylabel('Amplitude')

    axiq2.plot(f, sqrt(If**2+Qf**2), '-', color='C2')
    axiq2.set_title(r'$\sqrt{I_{f}^2 + Q_{f}^2}$')
    axiq2.set_xlabel('Frequency, Hz')
    axiq2.set_ylabel('Amplitude')

    plt.tight_layout()

    plt.show()
