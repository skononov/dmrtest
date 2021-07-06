from os import getenv
from time import time, sleep, perf_counter
import numpy as np
from scipy.fft import rfft
from scipy.signal import blackman
from numbers import Integral, Real

from dtcom import DTSerialCom
from dtexcept import DTInternalError, DTComError
from dt_c_api import get_peak, get_inl, get_ber
from dtglobals import Hz, kHz, MHz, adcSampleFrequency, symbolDevFrequency
import dtglobals as dtg  # for dtg.LANG

dtTaskTypes = None
dtTaskTypeDict = None
dtAllScenarios = None

DEBUG = False

# dict for parameter decription and limits. All parameters are integers. Defaults are set in the subclass constructors.
dtParameterDesc = {
    'att': {'ru': 'Затухание', 'en': 'Attenuation', 'type': Real, 'default': 31.5,
            'lowlim': 0.5, 'uplim': 31.5, 'increment': 0.5, 'dunit': 'dB', 'format': '4.1f'},
    'avenum': {'ru': 'N точек уср.', 'en': 'N av. pnts', 'type': Integral, 'default': 64,
               'lowlim': 1, 'uplim': 4096, 'increment': 1, 'dunit': '1', 'format': '4.0f'},
    'datanum': {'ru': 'N точек АЦП', 'en': 'N ADC pnts', 'type': Integral, 'default': 16384,
                'lowlim': 4, 'uplim': 16384, 'increment': 2, 'dunit': '1', 'format': '5.0f'},
    'frequency': {'ru': 'Несущая част.', 'en': 'Carrier freq.', 'type': Integral, 'default': 200*MHz,
                  'lowlim': 138*MHz, 'uplim': 800*MHz, 'increment': 1*MHz, 'dunit': 'MHz', 'format': '10.6f'},
    'modfrequency': {'ru': 'Частота мод.', 'en': 'Mod. frequency', 'type': Integral, 'default': 10*kHz,
                     'lowlim': 1*Hz, 'uplim': 100*kHz, 'increment': 100*Hz, 'dunit': 'kHz', 'format': '7.3f'},
    'modamp': {'ru': 'Ампл. мод.', 'en': 'Mod. ampl.', 'type': Real, 'default': 0.5,
               'lowlim': 0, 'uplim': 1, 'increment': 0.01, 'dunit': '%', 'format': '5.1f'},
    # 'bitnum': {'ru': 'Количество бит', 'en': 'Number of bits', 'type': Integral,
    #            'lowlim': 100, 'uplim': 2000, 'increment': 100, 'dunit': '1', 'format': '4.0f'},
    'refinl': {'ru': 'Порог КНИ', 'en': 'Thr. INL', 'type': Real, 'default': 0.05,
               'lowlim': 0.01, 'uplim': 1, 'increment': 0.01, 'dunit': '%', 'format': '5.1f'},
    'refatt': {'ru': 'Опор. осл.', 'en': 'Ref. att.', 'type': Real, 'default': 31.5,
               'dunit': 'dB', 'format': '4.1f', 'readonly': True},
    'refoutpower': {'ru': 'Опор. мощн.', 'en': 'Ref. power', 'type': Real, 'default': 1,
                    'dunit': 'dBm', 'format': '5.1f', 'readonly': True},
    'noise': {'ru': 'Шум', 'en': 'Noise', 'type': Real, 'default': 0.1,
              'lowlim': 0, 'uplim': 3, 'increment': 0.01, 'dunit': '%', 'format': '5.1f'},
    # result target values and tolerances by default
    'CARRIER FREQUENCY': {'target_value': 'frequency', 'abs_tolerance': kHz, 'rel_tolerance': 1e-4},
    'INPOWER': {'target_value': 1, 'abs_tolerance': 0.01, 'rel_tolerance': 1e-2},
    'OUTPOWER': {'target_value': 1, 'abs_tolerance': 0.01, 'rel_tolerance': 1e-2},
    'INL': {'upper_value': 1},
    'MODINDEX': {'target_value': 2, 'abs_tolerance': 0.1, 'rel_tolerance': 0.1},
    'BITERR': {'upper_value': 1},
    'BITPOWERDIF': {'target_value': 0, 'abs_tolerance': 0.1},
    'BITFREQDEV': {'target_value': 0, 'abs_tolerance': 1},
    'THRESHOLD POWER': {'upper_value': -10},
}

# dict for results desciption
dtResultDesc = {
    'CARRIER FREQUENCY': {'ru': 'Несущая f', 'en': 'Carrier f', 'dunit': 'MHz', 'format': '10.6f'},
    'INPOWER': {'ru': 'Вх. P', 'en': 'In P', 'dunit': 'dBm', 'format': '5.1f'},
    'OUTPOWER': {'ru': 'Вых. P', 'en': 'Out P', 'dunit': 'dBm', 'format': '5.1f'},
    'INL': {'ru': 'КНИ', 'en': 'INL', 'dunit': '%', 'format': '5.1f'},
    'MODINDEX': {'ru': 'Индекс мод.', 'en': 'Mod/ index', 'dunit': '1', 'format': '4.2f'},
    'BITERR': {'ru': 'BER', 'en': 'BER', 'dunit': '%', 'format': '5.1f'},
    'BITPOWERDIF': {'ru': '\u2206 P', 'en': '\u2206 P', 'dunit': '%', 'format': '5.1f'},
    'BITFREQDEV': {'ru': '\u2206 f', 'en': '\u2206 f', 'dunit': 'Hz', 'format': '5.1f'},
    'THRESHOLD POWER': {'ru': 'Порог P', 'en': 'Thr. P', 'dunit': 'dBm', 'format': '5.1f'},
}


class DTTask:
    """ Base class for a task, usually measurement. It defines some common data and methods for
        task parameter and status handling.
    """

    # Descirption of the read status bits
    __statusBitDescription = dict(ru=("Переполнение I-канала ЦАП", "Переполнение Q-канала ЦАП",
                                      "Установлен PLL модулятора", "Установлен PLL демодулятора",
                                      "Загружены данные в модулятор", "Ошибка загрузки данных в модулятор"),
                                  en=("DAC I-channel overflow", "DAC Q-channel overflow",
                                      "Modulator PLL lock", "Demodulator PLL lock",
                                      "Data loaded to PLL", "Error of loading data to PLL")
                                  )

    # name of the task
    name = dict(ru='Базовая задача', en='Base task')

    def __init__(self, parameters=None, results=None):
        """Constructor"""
        global dtParameterDesc
        # parameter values of the task
        if parameters is None:
            self.parameters = dict()
        else:
            self.parameters = dict.fromkeys(parameters)
            for par in parameters:
                if par in dtParameterDesc:
                    self.parameters[par] = dtParameterDesc[par]['default']

        # results of the task
        if results is None:
            self.results = dict()
        else:
            self.results = dict.fromkeys(results, None)

        self.message = ''  # message to be shown after execution
        self.failed = False  # if last task call is failed
        self.inited = False  # init_meas successfully completed
        self.completed = False  # if measure successfully completed
        self.single = False  # if task is single (only init_meas(), no measure() methon defined)
        self.com = None  # reference to DTSerialCom instance
        self.start = self.time = 0  # time of measurements
        self.id = None  # ID of the task (set once in the main process)

    def load_cal(self):
        """ This method can be implemented to load calibration from some storage or from dtParameterDesc
        """
        pass

    def init_meas(self, **kwargs):
        """ This method should be implemented to initialise the device just before the task run
        """
        self.failed = self.completed = self.inited = False
        self.message = ''
        self.start = self.time = 0
        if 'autotest' not in kwargs:  # do not establish communication with the device for autotest tasks
            try:
                self.com = DTSerialCom()  # serial communication instance (initialised only once as DTSerialCom is singleton)
            except DTComError as exc:
                self.set_com_error(exc)
                return self
        for par in kwargs:
            if par in self.parameters:
                self.parameters[par] = kwargs[par]
        if not self.check_all_parameters():
            self.set_error('Ошибка ввода параметров' if dtg.LANG == 'ru' else 'Parameter enter error')
        for res in self.results:
            self.results[res] = None
        return self

    def measure(self):
        """ This method should be implemented to perform one measurement
        """
        return self

    @classmethod
    def check_parameter(cls, par: str, value):
        """ Check parameter value and return True if it's valid or False otherwise.
            All values considered to be float.
            If expected parameter type is Integral, check float value has no fractions.
        """

        global dtParameterDesc
        if par not in dtParameterDesc:
            # raise DTInternalError(cls.__name__+'.check_parameter', f'Unknown parameter "{par}"')
            return False

        pardata = dtParameterDesc[par]
        if pardata['type'] is Integral and value != int(value):
            return False
        if 'uplim' in pardata and (value > pardata['uplim'] or value < pardata['lowlim']):
            return False
        return True

    def check_all_parameters(self):
        """ Check all defined parameters and return True in case of success, False otherwise.
        """
        global dtParameterDesc
        self.message = ''
        ok = True
        for par in self.parameters:
            if par in dtParameterDesc:
                pardata = dtParameterDesc[par]
                check = self.check_parameter(par, self.parameters[par])
                ok = ok and check
                if not check:
                    self.message += ('\n' if self.message != '' else '') + pardata[dtg.LANG] +\
                        (' вне диапазона' if dtg.LANG == 'ru' else ' out of range')

        return ok

    def get_conv_par_value(self, par):
        try:
            return self.parameters[par] / dtg.units[dtParameterDesc[par]['dunit']]['multiple']
        except (KeyError, TypeError):
            return None

    def get_conv_par_all(self, par):
        global dtParameterDesc
        try:
            pardesc = dtParameterDesc[par]
            value = self.parameters[par]
        except KeyError:
            return None
        mult = dtg.units[pardesc['dunit']]['multiple']
        dvalue = int(value) if mult == 1 and pardesc['type'] is Integral else value / mult
        lowlim = pardesc['lowlim']/mult if 'lowlim' in pardesc else None
        uplim = pardesc['uplim']/mult if 'uplim' in pardesc else None
        increment = pardesc['increment']/mult if 'increment' in pardesc else None
        avalues = [val/mult for val in pardesc['values']] if 'values' in pardesc else None
        return (pardesc[dtg.LANG], pardesc['type'], dvalue, 
                lowlim, uplim, increment, avalues,
                pardesc['format'], dtg.units[pardesc['dunit']][dtg.LANG],
                'readonly' in pardesc)

    def set_conv_par(self, par, value):
        global dtParameterDesc
        if isinstance(value, str) and ',' in value:
            value = value.replace(',', '.')
        if dtParameterDesc[par]['type'] is Real:
            value = float(value) * dtg.units[dtParameterDesc[par]['dunit']]['multiple']
        elif dtParameterDesc[par]['type'] is Integral:
            value = int(float(value) * dtg.units[dtParameterDesc[par]['dunit']]['multiple'])
        self.parameters[par] = value
        if par in dtParameterDesc and 'readonly' not in dtParameterDesc[par]:
            dtParameterDesc[par]['default'] = value

    def get_conv_res(self, res):
        global dtResultDesc
        try:
            return self.results[res] / dtg.units[dtResultDesc[res]['dunit']]['multiple']
        except (KeyError, TypeError):
            return None

    def results_from(self, src):
        """ Copy (by ref) results to this instance from a given one
        """
        if isinstance(src, DTTask):
            self.id = src.id
            self.results = src.results
            self.message = src.message
            self.time = src.time
            self.failed = src.failed
            self.inited = src.inited
            self.completed = src.completed
        return self

    def set_id(self, id_=None):
        """ Set ID of the task. Should be called from the main process.
        """
        if id_ is None:
            self.id = id(self)
        else:
            self.id = id_

    @classmethod
    def __decode_status(cls, status_word: int):
        desc = ''
        for i in range(len(cls.__statusBitDescription[dtg.LANG])):
            if status_word & (1 << i) != 0:
                desc += ('\n' if i > 0 else '') + cls.__statusBitDescription[dtg.LANG][i]
        return desc

    def set_success(self):
        self.failed = False
        self.completed = True
        if self.start == 0.:
            self.start = perf_counter()
        self.time = perf_counter() - self.start

    def set_error(self, message: str, prependmsg=True):
        self.failed = True
        self.completed = False
        if prependmsg:
            self.message = message + ':\n' + self.message
        elif message:
            self.message = message

    def set_eval_error(self, message: str = None):
        self.failed = True
        self.completed = False
        self.message = 'Ошибка измерения' if dtg.LANG == 'ru' else 'Measurement error'
        if message:
            self.message += ':\n' + message

    def set_message(self, message: str):
        self.message = message

    def set_com_error(self, exc: DTComError):
        self.failed = True
        self.completed = False
        strexc = str(exc)
        self.message = ('Ошибка связи с устройством:\n' if dtg.LANG == 'ru' else 'Communication error:\n') + strexc
        if 'MCU BUSY' in strexc:
            self.message += '\nПерезагрузите устройство.'
        if hasattr(self, 'com'):
            del self.com  # delete failed instance to try opening port next time

    def set_status_error(self, status: int):
        self.failed = True
        self.completed = False
        self.message = ('Ошибка статуса:\n' if dtg.LANG == 'ru' else 'Status error:\n') +\
                        self.__decode_status(status & 0x23)

    def set_pll_error(self):
        self.failed = True
        self.completed = False
        self.message = 'Ошибка PLL демодулятора' if dtg.LANG == 'ru' else 'Demodulator PLL error'


class DTCalibrate(DTTask):
    """Calibration.
    """
    name = dict(ru='Калибровка', en='Calibration')

    def __init__(self):
        super().__init__()
        self.single = True

    def init_meas(self):
        super().init_meas()
        if self.failed:
            return self

        try:
            self.com.command('SET MEASST', 1)
            self.com.command('SET DCCOMP', 1)
            sleep(1)  # Wait for calibration by the device
            self.com.command('SET DCCOMP', 0)

            status = self.com.command('STATUS', nreply=1)[0]
            self.results['STATUS'] = status
        except DTComError as exc:
            self.set_com_error(exc)
            return self

        if status & 0x3 > 0:
            self.set_status_error(status)
            return self

        self.inited = True
        self.set_success()
        return self


class DTMeasurePower(DTTask):
    """
    Measuring input&output power.
    """
    name = dict(ru='Измерение входной/выходной мощности', en='Measuring input&output power')

    adcCountToPower = 3/34  # [dBm/ADC_LSB]
    minPowerRange = -70  # dBm
    # Power[dBm] = ADC_counts*adcCountToPower + minPowerRange

    def __init__(self):
        super().__init__(('avenum', 'att'), ('OUTPOWER', 'INPOWER'))

    def init_meas(self, **kwargs):
        super().init_meas(**kwargs)
        if self.failed:
            return self

        try:
            self.com.command('SET RF_PATH', 0)
            attcode = int(2*self.parameters['att']+0.5)
            self.com.command('SET ATT', attcode)
        except DTComError as exc:
            self.set_com_error(exc)
            return self

        self.inited = True
        return self

    def __evalPower(self, counts):
        return [c * self.adcCountToPower + self.minPowerRange for c in counts]

    def measure(self):
        self.completed = False
        self.message = ''
        for res in self.results:
            self.results[res] = None
        if self.failed:
            return self

        try:
            counts = self.com.command('GET PWR', int(self.parameters['avenum']), nreply=2)
        except DTComError as exc:
            self.set_com_error(exc)
            return self

        pwrs = self.__evalPower(counts)
        self.results['OUTPOWER'] = pwrs[0]
        self.results['INPOWER'] = pwrs[1]

        self.set_success()
        return self


class DTMeasureCarrierFrequency(DTTask):
    """
    Measuring carrier frequency.
    """
    nominalCarrierOffset = 10*kHz  # auxillary offset of PLL frequency

    name = dict(ru='Измерение несущей', en='Measuring carrier')

    def __init__(self):
        super().__init__(('frequency', 'datanum'), ('CARRIER FREQUENCY', 'FFT'))
        self.buffer = None

    def init_meas(self, **kwargs):
        super().init_meas(**kwargs)
        if self.failed:
            return self

        try:
            self.com.command('SET MEASST', 1)
        except DTComError as exc:
            self.set_com_error(exc)
            return self

        self.inited = True
        return self

    def measure(self):
        self.completed = False
        self.message = ''
        for res in self.results:
            self.results[res] = None
        if self.failed:
            return self

        self.foffset0 = self.foffset = 0
        try:
            isset, self.foffset0 = self.com.set_pll_freq(2, int(self.parameters['frequency']))
            if not isset:
                self.set_pll_error()
                return self

            bsize = int(self.parameters['datanum'])
            # reading ADC data 1st time
            self.buffer0 = self.com.command('GET ADC DAT', [1, bsize], nreply=bsize)

            isset, self.foffset = self.com.set_pll_freq(2, int(self.parameters['frequency'] + self.nominalCarrierOffset))
            if not isset:
                self.set_pll_error()
                return self

            # reading ADC data 2nd time
            self.buffer = self.com.command('GET ADC DAT', [1, bsize], nreply=bsize)
        except DTComError as exc:
            self.set_com_error(exc)
            return self

        cfreq = self.__eval_carrier_freq()
        if self.failed:
            return self

        self.results['CARRIER FREQUENCY'] = cfreq

        self.set_success()

        return self

    def __eval_carrier_freq(self):
        if self.buffer is None or self.buffer0.size != self.buffer.size != self.parameters['datanum']:
            self.set_eval_error('Inconsistent data buffer size')
            return None

        N = self.parameters['datanum']
        # preparing Blackman window
        bwin = blackman(N)
        bwin /= np.sqrt(sum(bwin**2)/N)

        # convert data to float64 and subtract DC component
        It0 = self.buffer0.astype('float64')
        It0 -= np.mean(It0)
        # FFT for nominal PLL frequency
        a0 = self.results['FFT'] = 2/N*np.abs(rfft(bwin*It0))

        # convert data to float64 and subtract DC component
        It = self.buffer.astype('float64')
        It -= np.mean(It)
        # FFT for PLL frequency with offset
        aoff = 2/N*np.abs(rfft(bwin*It))

        p0, f0 = get_peak(a0, 0, len(a0)-1)
        poff, foff = get_peak(aoff, 0, len(aoff)-1)

        if p0 == 0 or poff == 0:  # could not find peaks
            self.set_message('Сигнал несущей не обнаружен' if dtg.LANG == 'ru' else 'No carrier signal')
            return None

        f0 = f0/N*adcSampleFrequency - self.foffset0  # Hz
        foff = foff/N*adcSampleFrequency - self.foffset  # Hz
        F = self.parameters['frequency']
        dF = self.nominalCarrierOffset

        if f0 < foff >= dF:
            return F - 0.5*(f0+foff-dF)
        elif f0 <= dF > foff:
            return F + 0.5*(f0+dF-foff)
        elif dF < f0 > foff:
            return F + 0.5*(f0+dF+foff)
        else:  # inconsistent measurements
            self.set_message('Ошибка в вычислении несущей частоты' if dtg.LANG == 'ru'
                             else 'Error in evaluating carrier frequency')
            return None


class DTMeasureNonlinearity(DTTask):
    """
    Measuring nonlinearity.
    """
    name = dict(ru='Измерение КНИ', en='THD measurement')

    def __init__(self):
        super().__init__(('frequency', 'modamp', 'modfrequency', 'datanum'),
                         ('INL', 'MODINDEX', 'FFT'))

    def init_meas(self, **kwargs):
        super().init_meas(**kwargs)
        if self.failed:
            return self

        macode = int(self.parameters['modamp']*0xFFFF)
        mfcode = int(self.parameters['modfrequency']*120*kHz/(1 << 16)+0.5)

        self.foffset = 0
        try:
            self.com.command('SET MEASST', 2)
            isset, self.foffset = self.com.set_pll_freq(2, int(self.parameters['frequency']))
            if not isset:
                self.set_pll_error()
                return self

            self.com.command('SET LFDAC', [macode, mfcode], owordsize=[2, 4])
        except DTComError as exc:
            self.set_com_error(exc)
            return self

        self.inited = True
        return self

    def measure(self):
        self.completed = False
        self.message = ''
        for res in self.results:
            self.results[res] = None
        if self.failed:
            return self

        try:
            # reading ADC data
            datanum = int(self.parameters['datanum'])
            self.buffer = self.com.command('GET ADC DAT', [2, 2*datanum], nreply=2*datanum)
        except DTComError as exc:
            self.set_com_error(exc)
            return self

        res = self.__eval_inl()
        if res is None:
            self.set_eval_error()
            return self

        self.results['INL'] = res[0]
        self.results['MODINDEX'] = res[1]
        self.set_success()

        return self

    def __eval_inl(self):
        if self.buffer is None:
            return None

        # check that buffer length is even
        if len(self.buffer) & 1 == 1:
            return None

        N = len(self.buffer)//2

        # preparing Blackman window
        bwin = blackman(N)
        bwin /= np.sqrt(sum(bwin**2)/N)

        # convert data to float64 and subtract DC component
        It = self.buffer[:N].astype('float64')  # take first half of the buffer as the I input
        It -= np.mean(It)
        Qt = self.buffer[N:].astype('float64')  # take second half of the buffer as the Q input
        Qt -= np.mean(Qt)
        # Compute FFT (non-negative frequencies only)
        If = 2/N*np.abs(rfft(bwin*It))
        Qf = 2/N*np.abs(rfft(bwin*Qt))
        self.results['FFT'] = np.sqrt(If**2 + Qf**2)

        fm = self.parameters['modfrequency']/adcSampleFrequency * N
        inl, mi = get_inl(np.sqrt(If**2+Qf**2), fm)

        return inl, mi


class DTDMRInput(DTTask):
    """
    DMR input analysis
    """
    name = dict(ru='Вход ЦР', en='DMR Input')

    refFreq = np.array([symbolDevFrequency, 3*symbolDevFrequency]*2)

    def __init__(self):
        super().__init__(('frequency',), ('BITERR',))

        # 255 - dibit sequence length, 2 - number of repetitions, 25 - samples per symbol, 2 - I & Q channels
        self.bufsize = 255*2*25*2

    def init_meas(self, **kwargs):
        super().init_meas(**kwargs)
        if self.failed:
            return self

        self.foffset = 0
        try:
            self.com.command('SET MEASST', 6)
            isset, self.foffset = self.com.set_pll_freq(2, int(self.parameters['frequency']))
            if not isset:
                self.set_pll_error()
                return self
        except DTComError as exc:
            self.set_com_error(exc)
            return self

        self.inited = True
        return self

    def measure(self):
        self.completed = False
        self.message = ''
        for res in self.results:
            self.results[res] = None
        if self.failed:
            return self

        # bitnum = int(self.parameters['bitnum'])

        try:
            # read out the number of error bits
            # nerrbits = self.com.command('GET BITERR', bitnum, nreply=1)[0]
            # read out the ADC data for dibit sequence
            self.buffer = self.com.command('GET DMRDIBIT', nreply=self.bufsize)
        except DTComError as exc:
            self.set_com_error(exc)
            return self

        res = self.__dmr_analysis()
        if res is None:
            self.set_eval_error()
            return self

        self.results['BITERR'] = res[0]  # bit errors, %

        self.set_success()

        return self

    # run analysis on generated data
    def dmr_test_analysis(self, It, Qt):
        self.buffer = np.append(It, Qt)
        return self.__dmr_analysis(True)

    def __dmr_analysis(self, debug=False):
        """ Do analysis of a random symbol sequence sent by the device.
            Calculate BER.
        """
        if self.buffer is None or len(self.buffer) != self.bufsize:
            self.set_eval_error(f'Data length ({len(self.buffer)}) differs from expected ({self.bufsize})')
            return None

        It = self.buffer[:self.bufsize//2]
        Qt = self.buffer[self.bufsize//2:]

        # subtract the DC component for real data
        It = np.around(It-np.mean(It)).astype('int32')
        Qt = np.around(Qt-np.mean(Qt)).astype('int32')

        # find the bit error rate and constant symbol intervals
        maxlen = 20*200  # max length of returned Iref, Qref
        numerr, numbit, Iref, Qref, symlenref = get_ber(It, Qt, maxlen)

        if numerr is None or numbit is None:
            self.set_eval_error(f'Too small data length - {len(self.buffer)}')
            return None

        ber = numerr/numbit

        return ber


class DTDMROutput(DTTask):
    """
    DMR output set
    """
    name = dict(ru='Выход ЦР', en='DMR Output')

    def __init__(self):
        super().__init__(('frequency', 'att'))
        self.single = True

    def init_meas(self, **kwargs):
        super().init_meas(**kwargs)
        if self.failed:
            return self

        try:
            self.com.command('SET MEASST', 5)
            isset, foffset = self.com.set_pll_freq(1, int(self.parameters['frequency']))
            if not isset:
                self.set_pll_error()
                return self

            self.com.command('SET ATT', int(self.parameters['att']*2+0.5))
        except DTComError as exc:
            self.set_com_error(exc)
            return self

        self.set_success()
        self.inited = True
        return self


class DTMeasureSensitivity(DTTask):
    """
    Measuring sensitivity.
    """
    name = dict(ru='Измерение чувствительности', en='Measuring sensitivity')

    # Input ranges of ADS868x in volts (assumed bipolar) in the order of code
    __adcVoltRange = (12.288, 10.240, 6.1440, 5.1200, 2.5600)

    def __init__(self):
        super().__init__(('frequency', 'modfrequency', 'refinl', 'datanum', 'refatt', 'refoutpower'),
                         ('THRESHOLD POWER', 'STATUS'))
        self.buffer = None

    def load_cal(self):
        """ Loading calibration of output power. Called from the main process where dtParameterDesc is kept up to date.
        """
        global dtParameterDesc
        for par in ('refatt', 'refoutpower'):
            self.parameters[par] = dtParameterDesc[par]['default']

    def init_meas(self, **kwargs):
        super().init_meas(**kwargs)
        if self.failed:
            return self

        try:
            self.com.command('SET MEASST', 4)

            # set DAC to 80% of maximum amplitude and zero frequency
            self.com.command('SET LFDAC', [52400, 0], owordsize=[2, 4])

            isset, foffset = self.com.set_pll_freq(1, int(self.parameters['frequency'] + self.parameters['modfrequency']))
            if not isset:
                self.set_pll_error()
                return self
        except DTComError as exc:
            self.set_com_error(exc)
            return self

        self.inited = True
        return self

    def measure(self):
        self.completed = False
        self.message = ''
        for res in self.results:
            self.results[res] = None
        if self.failed:
            return self

        self.adcrange = 0
        try:
            attrange = range(1, 64)
            lastinlcomp = True
            while len(attrange) > 1:
                midindex = len(attrange)//2
                attcode = attrange[midindex]
                lastinlcomp = self.__measure_inl_for_att(attcode)
                if self.failed:
                    return self
                if lastinlcomp:  # inl < refinl
                    attrange = attrange[midindex:]
                else:  # inl > refinl
                    if self.failed:  # failed to measure INL
                        return self
                    attrange = attrange[:midindex]
        except DTComError as exc:
            self.set_com_error(exc)
            return self

        if attcode != attrange[0]:
            # do last measurement if INL
            attcode = attrange[0]
            lastinlcomp = self.__measure_inl_for_att(attcode)

        if lastinlcomp and attcode == 63:
            # threshold power is lower than achievable
            status = -1
        elif not lastinlcomp and attcode == 1:
            # threshold power is higher than achievable
            status = 1
        elif attcode < 63 and lastinlcomp == self.__measure_inl_for_att(attcode+1):
            # Could not find the exact threshold. Signal is fluctuating?
            status = 2
        else:
            status = 0

        self.results['THRESHOLD POWER'] = self.parameters['refoutpower'] + self.parameters['refatt'] - 0.5*attcode
        self.results['STATUS'] = status
        self.set_success()

        return self

    def __measure_inl_for_att(self, attcode: int):
        ampuplim = 0xFFFF
        bsize = int(self.parameters['datanum'])
        tsize = 1024

        self.com.command("SET ATT", attcode)
        self.com.command("SET LF RANGE", self.adcrange)

        # find appropriate LF ADC range
        buf = np.array(self.com.command('GET ADC DAT', [3, tsize], nreply=tsize))
        amax = max(abs(buf.max()), abs(buf.min()))
        tryrange = self.adcrange
        if amax/ampuplim < 0.7:
            while tryrange < 4 and amax/ampuplim*self.__adcVoltRange[self.adcrange]/self.__adcVoltRange[tryrange+1] < 0.9:
                tryrange += 1
            if tryrange != self.adcrange:
                self.com.command("SET LF RANGE", tryrange)
        elif amax/ampuplim > 0.9:
            while tryrange > 0:
                # update ADC data in case of saturation
                tryrange -= 1
                self.com.command("SET LF RANGE", tryrange)
                buf = np.array(self.com.command('GET ADC DAT', [3, tsize], nreply=tsize))
                amax = max(abs(buf.max()), abs(buf.min()))
                if amax/ampuplim <= 0.9:
                    break
        self.adcrange = tryrange

        if amax/ampuplim > 0.9:
            self.set_eval_error(f'Перегузка НЧ АЦП для диапазона {self.__adcVoltRange[tryrange]}В'
                                if dtg.LANG == 'ru' else f'LF ADC overload for range {self.__adcVoltRange[tryrange]}V')
            return False

        self.buffer = self.com.command('GET ADC DAT', [3, bsize], nreply=bsize)

        inl = self.__eval_inl()
        if inl is None:
            self.set_eval_error('КНИ не определен' if dtg.LANG == 'ru' else 'INL is not defined')
            return False

        if inl <= self.parameters['refinl']:
            return True

        return False

    def __eval_inl(self):
        if self.buffer is None:
            return None

        N = len(self.buffer)
        bwin = blackman(N)
        bwin /= np.sqrt(sum(bwin**2)/N)

        # convert data to float64 and subtract DC component
        It = self.buffer.astype('float64')
        It -= np.mean(It)

        # Compute FFT (non-negative frequencies only)
        af = self.results['FFT'] = 2/N*np.abs(rfft(bwin*It))

        fm = self.parameters['modfrequency']/adcSampleFrequency * N
        inl, mi = get_inl(af, fm)

        return inl


class DTDMRInputModel(DTTask):
    """
    DMR input analysis with simulated data
    """
    name = dict(ru='Вход ЦР (модель)', en='DMR Input (model)')

    refFreq = DTDMRInput.refFreq
    adcCountRange = 1<<15-1  # unipolar

    def __init__(self):
        super().__init__(('frequency','noise'), ('BITERR', 'BITFREQDEV', 'BITPOWERDIF'))
        homedir = getenv('HOME')
        self.ifilename, self.qfilename = homedir+'/dmr/dev/Idmr_long.txt', homedir+'/dmr/dev/Qdmr_long.txt'
        self.bufsize = 255*2*25*2

    def init_meas(self, **kwargs):
        super().init_meas(**kwargs, autotest=True)
        if self.failed:
            return self

        self.rng = np.random.default_rng(int(time()))

        try:
            self.ibuffer = np.genfromtxt(self.ifilename, dtype='int32', delimiter='\n')
            self.qbuffer = np.genfromtxt(self.qfilename, dtype='int32', delimiter='\n')
            print(f'Data loaded with length of {self.ibuffer.size}')
        except Exception as exc:
            self.set_error('Error loading data files\n' + str(exc))
            return self

        if self.ibuffer.size != self.qbuffer.size or self.ibuffer.size < self.bufsize//2:
            self.set_error(f'Wrong length of I or Q data ({self.ibuffer.size}, {self.qbuffer.size})')

        return self

    def measure(self):
        self.completed = False
        self.message = ''
        for res in self.results:
            self.results[res] = None
        if self.failed:
            return self

        offset = self.rng.integers(0, self.ibuffer.size-self.bufsize//2)
        It = self.ibuffer[offset:offset+self.bufsize//2]
        Qt = self.qbuffer[offset:offset+self.bufsize//2]
        self.buffer = np.append(It, Qt)

        res = self.dmr_analysis()
        if res is None:
            return self

        self.results['BITERR'] = res[0]  # bit errors, %
        self.results['BITFREQDEV'] = res[1]  # bit frequency deviation, Hz
        self.results['BITPOWERDIF'] = res[2]  # bit power difference, %
        self.set_success()

        return self

    def dmr_analysis(self, It=None, Qt=None):
        """ Do analysis of a random symbol sequence sent by the device.
            Calculate BER.
            Extract maximum frequency deviation of a symbol and power difference between symbols.
        """
        global DEBUG

        if It is None or Qt is None:
            if self.buffer is None or len(self.buffer) != self.bufsize:
                self.set_eval_error(f'Data length ({len(self.buffer)}) differs from expected ({self.bufsize})')
                return None
            It = self.buffer[:self.bufsize//2]
            Qt = self.buffer[self.bufsize//2:]

        ampNoise = self.parameters['noise']*self.adcCountRange
        ampMax = self.adcCountRange
        # subtract the DC component for real data
        It = np.clip(np.around(It-np.mean(It)).astype('int32') +\
             (ampNoise*self.rng.normal(size=It.size)).astype('int32'), -ampMax, ampMax)
        Qt = np.clip(np.around(Qt-np.mean(Qt)).astype('int32') +\
             (ampNoise*self.rng.normal(size=Qt.size)).astype('int32'), -ampMax, ampMax)

        # find the bit error rate and constant symbol intervals
        maxlen = 20*200  # max length of returned Iref, Qref
        numerr, numbit, Iref, Qref, symlenref = get_ber(It, Qt, maxlen)

        if numerr is None or numbit is None:
            self.set_eval_error(f'Too small data length - {len(self.buffer)}')
            return None

        ber = numerr/numbit

        if DEBUG:
            print(f'Total bits: {numbit}, error bits: {numerr}, BER: {100*ber:.1f}%')

        pwr = np.zeros(4, float)
        fpeak = np.zeros(4, float)

        If = [None]*4
        Qf = [None]*4
        Af = [None]*4
        istart = iend = 0
        symintervals = []  # for testing

        for i in range(4):
            iend += symlenref[i]
            symintervals.append((istart, iend))
            # preparing Blackman window
            bwin = blackman(symlenref[i])
            bwin /= np.sqrt(sum(bwin**2)/symlenref[i])
            iref, qref = Iref[istart:iend], Qref[istart:iend]
            If[i] = 2/symlenref[i]*np.abs(rfft(iref))
            Qf[i] = 2/symlenref[i]*np.abs(rfft(qref))
            istart = iend

            Af[i] = np.sqrt(If[i]**2 + Qf[i]**2)
            fmin, fmax = 0, 5
            pwr[i], fpeak[i] = get_peak(Af[i], fmin, fmax)
            fpeak[i] *= adcSampleFrequency/symlenref[i]  # convert to Hz

        fdev = np.abs(fpeak-self.refFreq)
        ampf = np.sqrt(pwr)
        min_ampf, max_ampf = min(ampf), max(ampf)

        maxfdev = np.max(fdev)
        ampdiff = 2*(max_ampf-min_ampf)/(min_ampf+max_ampf)

        if DEBUG:
            print('Symbol intervals and lengths:', symintervals, symlenref)
            print('Frequency peaks [Hz]:', fpeak)
            print('Frequency deviations [Hz]:', fdev)
            print('Amplitude of symbols:', ampf)
            print(f'Max frequency deviation: {maxfdev:.1f} Hz')
            print(f'Max difference in symbol amplitudes: {100*ampdiff:.1f}%')
        return ber, maxfdev, ampdiff, symintervals, If, Qf, Af


class DTScenario:
    def __init__(self, name: str, tasknames=None):
        global dtTaskTypeDict, dtAllScenarios
        self.name = name
        self.tasks = list()
        if dtTaskTypeDict is None or dtAllScenarios is None:
            dtTaskInit()

        if name in dtAllScenarios:
            raise DTInternalError(self.__class__.__name__, f'Scenario with name {name} already exists')

        try:
            taskname = ''
            if tasknames is not None:
                for taskname in tasknames:
                    self.addTask(dtTaskTypeDict[dtg.LANG][taskname])
        except KeyError as exc:
            raise DTInternalError(self.__class__.__name__, f'No task {taskname} defined') from exc

        dtAllScenarios[name] = self

    def addTask(self, taskType: DTTask, parameters=None):
        if taskType not in dtTaskTypes:
            raise DTInternalError('DTScenario.addTask()', 'Unknown task type given')

        task = taskType()
        task.set_id()  # scenario is created in the main process, set task ID here
        if isinstance(parameters, dict):
            task.parameters = parameters
        self.tasks.append(task)
        return task

    @classmethod
    def from_dict(cls, d: dict):
        """Define scenario from dict (read from configuration file)
        """
        scen = None
        try:
            scen = DTScenario(d['name'])
            for t in d['tasks']:
                scen.addTask(dtTaskTypeDict['cls'][t['class']], t['parameters'])
        except KeyError:
            del scen
            raise DTInternalError('DTScenario.fromDict()', 'Wrong dict format')
        return scen

    def to_dict(self):
        d = dict(name=self.name, tasks=list())
        for task in self.tasks:
            d['tasks'].append({'class': task.__class__.__name__,
                               'parameters': task.parameters})
        return d

    def __getitem__(self, key):
        return self.tasks[key]

    def __setitem__(self, key, item):
        self.tasks[key] = item

    def __len__(self):
        return len(self.tasks)

    def __iter__(self):
        """Initialize iterator with previous and current tasks
        """
        self.__prevtask = None
        self.__curtask = None
        self.__taskiter = iter(self.tasks)
        return self.__taskiter

    def __next__(self):
        """Iterate returning previous and current tasks as a tuple
        """
        self.__prevtask = self.__curtask
        self.__curtask = next(self.__taskiter)
        return (self.__prevtask, self.__curtask)

    def __repr__(self):
        return '%s("%s")' % (DTScenario.__name__, self.name)

    def __del__(self):
        for instance in self.tasks:
            del instance


def dtTaskInit():
    global dtTaskTypes, dtTaskTypeDict, dtAllScenarios
    dtTaskTypes = list()
    dtTaskTypeDict = dict(cls=dict(), ru=dict(), en=dict())
    dtAllScenarios = dict()
    for taskClass in (DTCalibrate, DTMeasurePower, DTMeasureCarrierFrequency,
                      DTMeasureNonlinearity, DTDMRInput, DTDMROutput, DTMeasureSensitivity, DTDMRInputModel):
        dtTaskTypes.append(taskClass)
        dtTaskTypeDict['cls'][taskClass.__name__] = taskClass
        dtTaskTypeDict['ru'][taskClass.name['ru']] = taskClass
        dtTaskTypeDict['en'][taskClass.name['en']] = taskClass
