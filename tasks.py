import time
import numpy as np
from scipy.fft import rfft
from scipy.signal import blackman

from dtcom import DTSerialCom
from exception import DTInternalError, DTComError
from dt_c_api import get_peak, get_inl
from dtglobals import kHz, MHz
import dtglobals as dtg  # for dtg.LANG

dtTaskTypes = None


class DTTask:
    """ Base class for a task with DMR TEST device. It defines some common data and methods for
        task parameter and status handling.
    """
    adcSampleFrequency: int = 120000  # Hz

    # dict for parameter decription and limits. All parameters are integers. Defaults are set in the subclass constructors.
    parameterData = {
        'ATT': {'ru': 'Затухание', 'en': 'Attenuation', 'lowlim': 0.5, 'uplim': 31.5},
        'AVENUM': {'ru': 'Точек усреднения', 'en': 'Averaging points', 'lowlim': 1, 'uplim': 4096},
        'DATANUM': {'ru': 'Точек АЦП', 'en': 'ADC points', 'lowlim': 16, 'uplim': 16384},
        'FREQUENCY': {'ru': 'Несущая частота', 'en': 'Carrier frequency',
                      'lowlim': 137*MHz, 'uplim': 800*MHz, 'dunit': ('MHz', MHz)},
        'MODFREQUENCY': {'ru': 'Частота модуляции', 'en': 'Modulating frequency',
                         'lowlim': 1, 'uplim': 100*kHz, 'dunit': ('kHz', kHz)},
        'MODAMP': {'ru': 'Амлитуда модуляции', 'en': 'Modulating amplitude', 'lowlim': 0, 'uplim': 0xFFFF},
        'BITNUM': {'ru': 'Количество бит', 'en': 'Number of bits', 'lowlim': 100, 'uplim': 2000},
        # 'LFRANGE': {'ru': 'Диапазон НЧ АЦП', 'en': 'Range of LF ADC', 'lowlim': 0, 'uplim': 4},
        'REFTHDR': {'ru': 'Порог КНИ', 'en': 'Threshold THDR', 'lowlim': 1, 'uplim': 100},
    }

    # dict for results desciption
    resultDesc = {
        'CARRIER FREQUENCY': {'ru': 'Несущая частота', 'en': 'Carrier frequency'},
        'INPUT FREQUENCY': {'ru': 'Вх. частота модуляции', 'en': 'Input mod. frequency'},
        'INPUT POWER': {'ru': 'Входная мощность', 'en': 'Input power'},
        'OUTPUT POWER': {'ru': 'Выходная мощность', 'en': 'Output power'},
        'THDR': {'ru': 'КНИ', 'en': 'THDR'},
        'MODINDEX': {'ru': 'Индекс модуляции', 'en': 'Modulation index'},
    }

    # Descirption of the read status bits
    statusBitDescription = dict(ru=("Переполнение I-канала ЦАП", "Переполнение Q-канала ЦАП",
                                    "Установлен PLL модулятора", "Установлен PLL демодулятора",
                                    "Загружены данные в модулятор", "Ошибка загрузки данных в модулятор"),
                                en=("DAC I-channel overflow", "DAC Q-channel overflow",
                                    "Modulator PLL lock", "Demodulator PLL lock",
                                    "Data loaded to PLL", "Error of loading data to PLL")
                                )

    # name of the task
    name = dict(ru='Базовая задача', en='Base task')

    def __init__(self):
        """Constructor"""
        self.com = DTSerialCom()  # used serial interface instance (initialised only once as it's singleton)

        self.parameters = dict()  # parameter values of the task
        self.results = dict()  # results of the task
        self.message = ''  # message to be shown after execution
        self.failed = False  # if last task call is failed
        self.completed = False  # if task is successfully completed

    def init_meas(self):
        """ This method should be implemented to initialise the device for the task.
        """
        return self

    def measure(self):
        """ This method should be implemented to perform one measurement. Should return self.
        """
        return self

    def check_parameter(self, par: str):
        if par not in self.parameters:
            raise DTInternalError(self.__class__.__name__+'.check_parameter', f'Unknown parameter "{par}"')

        pardata = DTTask.parameterData[par]
        if not isinstance(self.parameters[par], int) and par != 'ATT' and par != 'REFTHDR':
            raise DTInternalError(self.__class__.__name__+'.check_parameter', f'Parameter "{par}" must be integer')
        elif self.parameters[par] > pardata['uplim'] or self.parameters[par] < pardata['lowlim']:
            if self.message:
                self.message += '\n'
            self.message += pardata[dtg.LANG] + (' вне диапазона' if dtg.LANG == 'ru' else ' out of range')
            return False

        return True

    def check_all_parameters(self):
        self.message = ''
        ok = True
        for par in self.parameters:
            ok = ok and self.check_parameter(par)

        return ok

    @classmethod
    def _decodeStatus(cls, status_word: int):
        desc = ''
        for i in range(len(cls.statusBitDescription[dtg.LANG])):
            if status_word & (1 << i) != 0:
                desc += ('\n' if i > 0 else '') + cls.statusBitDescription[dtg.LANG][i]
        return desc

    def _set_success(self):
        self.failed = False
        self.completed = True
        self.message = 'Успешно' if dtg.LANG == 'ru' else 'Success'

    def _set_error(self, message: str, prependmsg=True):
        self.failed = True
        self.completed = False
        if prependmsg:
            self.message = message + ':\n' + self.message
        elif message != '':
            self.message = message

    def _set_eval_error(self):
        self.failed = True
        self.completed = False
        self.message = 'Ошибка вычисления' if dtg.LANG == 'ru' else 'Evaluation error'

    def _set_com_error(self, exc: DTComError):
        self.failed = True
        self.completed = False
        self.message = ('Ошибка связи с устройством:\n' if dtg.LANG == 'ru' else 'Communication error:\n') + exc

    def _set_status_error(self, status: int):
        self.failed = True
        self.completed = False
        self.message = ('Ошибка статуса:\n' if dtg.LANG == 'ru' else 'Status error:\n') + self._decodeStatus(status & 0x23)

    def _set_pll_error(self):
        self.failed = True
        self.completed = False
        self.message = 'Ошибка PLL демодулятора' if dtg.LANG == 'ru' else 'Demodulator PLL error'

    def __repr__(self):
        return self.__class__.__name__ + '()'


class DTCalibrate(DTTask):
    """
    Calibration.
    """
    name = dict(ru='Калибровка', en='Calibration')

    def __init__(self):
        super().__init__()

    def init_meas(self):
        self.failed = self.completed = False
        try:
            self.com.command(b'SET MEASST', 1)
            self.com.command(b'SET DCCOMP', 1)
            time.sleep(1)  # Wait for calibration by the device
            self.com.command(b'SET DCCOMP', 0)

            status = self.com.command(b'STATUS', nreply=1)[0]
            self.results['STATUS'] = status
        except DTComError as exc:
            self._set_com_error(exc)
            return self

        if status & 0x3 > 0:
            self._set_status_error(status)
            return self

        self._set_success()
        return self


class DTMeasurePower(DTTask):
    """
    Measuring input&output power.
    """
    name = dict(ru='Измерение входной/выходной мощности', en='Measuring input&output power')

    def __init__(self, avenum: int = 64, att: float = 31.5):
        super().__init__()
        self.parameters['AVENUM'] = avenum
        self.parameters['ATT'] = att

    def init_meas(self):
        self.failed = self.completed = False
        if not self.check_all_parameters():
            self._set_error('')
            return self

        try:
            self.com.command(b'SET RF_PATH', 0)
            attcode = int(self.parameters['ATT']/0.5+0.5)
            self.com.command(b'SET ATT', attcode)
        except DTComError as exc:
            self._set_com_error(exc)
            return self

        return self

    def measure(self):
        self.completed = False
        if self.failed:
            return self

        try:
            pwrs = self.com.command(b'GET PWR', self.parameters['AVENUM'], nreply=2)
        except DTComError as exc:
            self._set_com_error(exc)
            return self

        self.results['OUTPUT POWER'] = pwrs[0]
        self.results['INPUT POWER'] = pwrs[1]

        self._set_success()
        return self


class DTMeasureCarrierFrequency(DTTask):
    """
    Measuring carrier frequency.
    """
    nominalCarrierOffset = 10*kHz  # auxillary offset of PLL frequency

    name = dict(ru='Измерение несущей', en='Measuring carrier')

    def __init__(self, frequency: int = 200*MHz, bufsize: int = 16384):
        super().__init__()
        self.parameters['FREQUENCY'] = frequency
        self.parameters['DATANUM'] = bufsize
        self.buffer = None

    def init_meas(self):
        self.failed = self.completed = False
        if not self.check_all_parameters():
            self._set_error('')
            return self

        try:
            self.com.command(b'SET MEASST', 1)
        except DTComError as exc:
            self._set_com_error(exc)
            return self

        return self

    def measure(self):
        self.completed = False
        if self.failed:
            return self

        self.foffset0 = self.foffset = 0
        try:
            isset, self.foffset0 = self.com.set_pll_freq(self.parameters['FREQUENCY'])
            if not isset:
                self._set_pll_error()
                return self

            bsize = self.parameters['DATANUM']
            # reading ADC data 1st time
            self.buffer0 = self.com.command(b'GET ADC DAT', [1, bsize], nreply=bsize)

            isset, self.foffset = self.com.set_pll_freq(self.parameters['FREQUENCY'] + self.nominalCarrierOffset)
            if not isset:
                self._set_pll_error()
                return self

            # reading ADC data 2nd time
            self.buffer = self.com.command(b'GET ADC DAT', [1, bsize], nreply=bsize)
        except DTComError as exc:
            self._set_com_error(exc)
            return self

        try:
            self.results['CARRIER FREQUENCY'] = self._eval_carrier_freq()
        except Exception:
            self._set_eval_error()
            return self

        if self.results['CARRIER FREQUENCY'] is None:
            self._set_eval_error()
            return self

        self._set_success()

        return self

    def _eval_carrier_freq(self):
        if self.buffer is None or len(self.buffer0) != len(self.buffer) != self.parameters['DATANUM']:
            return None

        N = self.parameters['DATANUM']
        a0 = 2/N*np.abs(rfft(np.array(blackman(N)*self.buffer0, dtype=np.float64)))
        aoff = 2/N*np.abs(rfft(np.array(blackman(N)*self.buffer, dtype=np.float64)))
        p0, f0 = get_peak(a0, 0, len(a0)-1)
        poff, foff = get_peak(aoff, 0, len(aoff)-1)

        if p0 == 0 or poff == 0:  # could not find peaks
            return None

        f0 = f0/N*self.adcSampleFrequency - self.foffset0  # Hz
        foff = foff/N*self.adcSampleFrequency - self.foffset  # Hz
        F = self.parameters['FREQUENCY']
        dF = self.nominalCarrierOffset

        if f0 < foff >= dF:
            return F - 0.5*(f0+foff-dF)
        elif f0 <= dF > foff:
            return F + 0.5*(f0+dF-foff)
        elif dF < f0 > foff:
            return F + 0.5*(f0+dF+foff)
        else:  # non-consistent measurements
            return None


class DTMeasureNonlinearity(DTTask):
    """
    Measuring nonlinearity.
    """
    name = dict(ru='Измерение КНИ', en='THD measurement')

    def __init__(self, frequency: int = 200*MHz, modamp: int = 0xFF, modfreq: int = 10*kHz, bufsize: int = 16384):
        super().__init__()
        self.parameters['FREQUENCY'] = frequency
        self.parameters['MODAMP'] = modamp
        self.parameters['MODFREQUENCY'] = modfreq
        self.parameters['DATANUM'] = bufsize

    def init_meas(self):
        self.failed = self.completed = False
        if not self.check_all_parameters():
            self._set_error('')
            return self

        mfcode = int(self.parameters['MODFREQUENCY']*120*kHz/(1 << 16)+0.5)

        self.foffset = 0
        try:
            self.com.command(b'SET MEASST', 2)
            isset, self.foffset = self.com.set_pll_freq(self.parameters['FREQUENCY'])
            if not isset:
                self._set_pll_error()
                return self

            self.com.command(b'SET LFDAC', [self.parameters['MODAMP'], mfcode], owordsize=[2, 4])
        except DTComError as exc:
            self._set_com_error(exc)
            return self

        return self

    def measure(self):
        self.completed = False

        try:
            # reading ADC data
            bsize = self.parameters['DATANUM']
            self.buffer = self.com.command(b'GET ADC DAT', [2, bsize], nreply=2*bsize)
        except DTComError as exc:
            self._set_com_error(exc)
            return self

        res = self._eval_inl()
        if res is None:
            self._set_eval_error()
            return self

        self.results['THDR'] = res[0]
        self.results['MODINDEX'] = res[1]
        self._set_success()

        return self

    def _eval_inl(self):
        if self.buffer is None:
            return None

        N = self.parameters['DATANUM']
        if 2*N != len(self.buffer):
            return None

        It = self.buffer[:N]  # take first half of the buffer as the I input
        Qt = self.buffer[N:]  # take first half of the buffer as the Q input
        # Compute FFT (non-negative frequencies only)
        If = self.results['IFFT'] = 2/N*np.abs(rfft(np.array(blackman(N)*It, dtype=np.float64)))
        Qf = self.results['QFFT'] = 2/N*np.abs(rfft(np.array(blackman(N)*Qt, dtype=np.float64)))

        fm = self.parameters['MODFREQUENCY']/self.adcSampleFrequency * N
        inl, mi = get_inl(np.sqrt(If**2+Qf**2), fm)

        return inl, mi


class DTDMRInput(DTTask):
    """
    DMR input analysis
    """
    name = dict(ru='Вход ЦР', en='DMR Input')

    def __init__(self, frequency: int = 200*MHz, bitnum: int = 1000):
        super().__init__()
        self.parameters['FREQUENCY'] = frequency
        self.parameters['BITNUM'] = bitnum

    def init(self):
        self.failed = self.completed = False
        if not self.check_all_parameters():
            self._set_error('')
            return self

        self.foffset = 0
        try:
            self.com.command(b'SET MEASST', 6)
            isset, self.foffset = self.com.set_pll_freq(self.parameters['FREQUENCY'])
            if not isset:
                self._set_pll_error()
                return self
        except DTComError as exc:
            self._set_com_error(exc)
            return self

        return self

    def measure(self):
        self.completed = False
        if self.failed:
            return self

        try:
            nerrbits = self.com.command(b'GET BITERR', self.parameters['BITNUM'], nreply=1)[0]

            self.buffers = list()
            for dibit in range(4):
                self.buffers.append(self.com.command(b'GET DMRDIBIT', dibit, nreply=128))
        except DTComError as exc:
            self._set_com_error(exc)
            return self

        self.results['BITERR'] = 100*nerrbits/self.parameters['BITNUM']  # percent of bit errors

        res = self._eval_dmr_errors()
        if res is None:
            self._set_eval_error()
            return self

        # TODO getting results
        self._set_success()

        return self

    def _eval_dmr_errors(self):
        # TODO
        return None


class DTDMROutput(DTTask):
    """
    DMR output set
    """
    name = dict(ru='Выход ЦР', en='DMR Output')

    def __init__(self, frequency: int = 200*MHz, att: int = 1):
        super().__init__()
        self.parameters['FREQUENCY'] = frequency
        self.parameters['ATT'] = att

    def init_meas(self):
        self.failed = self.completed = False
        if not self.check_all_parameters():
            self._set_error('')
            return self

        try:
            self.com.command(b'SET MEASST', 5)
            isset, foffset = self.com.set_pll_freq(self.parameters['FREQUENCY'])
            if not isset:
                self._set_pll_error()
                return self

            self.com.command(b'SET ATT', self.parameters['ATT'])
        except DTComError as exc:
            self._set_com_error(exc)
            return self

        self._set_success()
        return self


class DTMeasureSensitivity(DTTask):
    """
    Measuring sensitivity.
    """
    name = dict(ru='Измерение чувствительности', en='Measuring sensitivity')

    def __init__(self, frequency: int = 200*MHz, modfreq: int = 10*kHz, refthdr: float = 1):
        super().__init__()
        self.parameters['FREQUENCY'] = frequency
        self.parameters['MODFREQUENCY'] = modfreq
        self.parameters['REFTHDR'] = refthdr
        self.buffer = None

    def init_meas(self):
        self.failed = self.completed = False
        if not self.check_all_parameters():
            self._set_error('')
            return self

        try:
            self.com.command(b'SET MEASST', 4)
            
            isset, foffset = self.com.set_pll_freq(self.parameters['FREQUENCY'] + self.parameters['MODFREQUENCY'])
            if not isset:
                self._set_pll_error()
                return self
        except DTComError as exc:
            self._set_com_error(exc)
            return self

        return self

    def measure(self):
        self.completed = False

        try:
            for att in range(63, 0, -1):
                self.com.command("SET ATT", att)
                self.com.command("SET LF RANGE", 0)
                bsize = self.parameters['DATANUM']
                # reading ADC data
                self.buffer = self.com.command(b'GET ADC DAT', [3, bsize], nreply=bsize)
        except DTComError as exc:
            self._set_com_error(exc)
            return self

        res = self._eval_inl()
        if res is None:
            self._set_eval_error()
            return self

        self.results['THDR'] = res[0]
        self.results['MODINDEX'] = res[1]
        self._set_success()

        return self

    def _eval_inl(self):
        if self.buffer is None:
            return None

        N = self.parameters['DATANUM']
        if N != len(self.buffer):
            return None

        # Compute FFT (non-negative frequencies only)
        af = self.results['IFFT'] = 2/N*np.abs(rfft(np.array(blackman(N)*self.buffer, dtype=np.float64)))

        fm = self.parameters['MODFREQUENCY']/self.adcSampleFrequency * N
        inl, mi = get_inl(af, fm)

        return inl, mi



class DTScenario:
    def __init__(self, name: str, tasktypes = None):
        self.name = name
        self.tasks = list()
        for tasktype in tasktypes:
            self.addTask(tasktype)
        self.taskIter = iter(self.tasks)

    def addTask(self, tasktype: DTTask):
        if tasktype not in dtTaskTypes:
            raise DTInternalError('DTScenario.addTask()', f'Unknown task type given')

        self.tasks.append(tasktype())

    def runNextTask(self):
        if self.taskIter is None:
            self.taskIter = iter(self.tasks)
        task = next(self.taskIter)

        # run the task
        return task()

    def __repr__(self):
        return '%s("%s")' % (DTScenario.__name__, self.name)

    def __del__(self):
        for instance in self.tasks:
            del instance


def dtTaskInit():
    global dtTaskTypes
    dtTaskTypes = list()
    for taskClass in (DTCalibrate, DTMeasurePower, DTMeasureCarrierFrequency, DTMeasureNonlinearity, DTDMRInput, DTDMROutput, DTMeasureSensitivity):
        dtTaskTypes.append(taskClass)

