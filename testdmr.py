from dtglobals import adcSampleFrequency
from numpy import linspace, genfromtxt, append, sqrt
import tasks
from dt_c_api import get_ber
import matplotlib.pyplot as plt
from scipy.fft import rfftfreq

if __name__ == "__main__":
    It = genfromtxt('Idmr.txt', dtype='int32')
    print(f'{It.size} points read from Idmr.txt')
    Qt = genfromtxt('Qdmr.txt', dtype='int32')
    print(f'{Qt.size} points read from Qdmr.txt')

    t = linspace(0, It.size/adcSampleFrequency, It.size, endpoint=False)

    tasks.DEBUG = True
    dmrtask = tasks.DTDMRInput()
    dmrtask.buffer = append(It, Qt)
    fftlen = dmrtask.fftlen

    res = dmrtask.dmr_analysis()
    if res is None:
        print('Failed DMR analysis')
        exit(1)

    print('Max. frequency deviation: ', res[0])
    print('Amplitude diff: ', res[1])

    numerr, numbit = get_ber(It, Qt)
    print(f'Total symbols: {numbit}, error symbols: {numerr}')

    bestpos = res[2]
    dibits = ['00', '10', '01', '11']

    fig, (axi, axq) = plt.subplots(2, 1, sharex=True, figsize=(12, 6))
    axi.plot(t, It, '.')
    axi.set_title('Raw I signal')
    axi.set_ylabel('Amplitude')
    ymin, ymax = axi.get_ylim()
    for i, bp in enumerate(bestpos):
        tmin, tmax = t[bp-fftlen//2], t[bp+fftlen//2-1]
        axi.add_patch(plt.Rectangle((tmin, ymin), (tmax-tmin), (ymax-ymin), ls='-', ec="k", fc="r", alpha=0.5))
        axi.text((tmin+tmax)/2, ymax*1.06, dibits[i], ha='center')

    axq.plot(t, Qt, '.')
    axq.set_title('Raw Q signal')
    axq.set_xlabel('Time, s')
    axq.set_ylabel('Amplitude')
    ymin, ymax = axq.get_ylim()
    for i, bp in enumerate(bestpos):
        tmin, tmax = t[bp-fftlen//2], t[bp+fftlen//2-1]
        axq.add_patch(plt.Rectangle((tmin, ymin), (tmax-tmin), (ymax-ymin), ls='-', ec="k", fc="r", alpha=0.5))
        axq.text((tmin+tmax)/2, ymax*1.06, dibits[i], ha='center')

    plt.tight_layout()

    f = rfftfreq(fftlen, 1/adcSampleFrequency)

    fig, ax = plt.subplots(3, 4, sharex=True, figsize=(12, 9))
    for i in range(4):
        If = res[3][i]
        Qf = res[4][i]
        Af = sqrt(If**2 + Qf**2)
        ax[0][i].plot(f[:10], If[:10], '-o')
        ax[0][i].set_title(f'I FFT, dibit {dibits[i]}')
        ax[0][i].set_ylabel('Amplitude')

        ax[1][i].plot(f[:10], Qf[:10], '-o')
        ax[1][i].set_title(f'Q FFT, dibit {dibits[i]}')
        ax[1][i].set_ylabel('Amplitude')

        ax[2][i].plot(f[:10], Af[:10], '-o')
        ax[2][i].set_title(r'$\sqrt{I^{2}+Q^{2}}$ FFT, dibit ' + f'{dibits[i]}')
        ax[2][i].set_xlabel('Frequency, Hz')
        ax[2][i].set_ylabel('Amplitude')

    plt.tight_layout()
    plt.show()
