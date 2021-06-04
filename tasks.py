import sys, time
import numpy as np
from scipy import fft

from dtcom import DTSerialCom
from singleton import Singleton
from exception import DTInternalError, DTComError
from dtglobals import *

dtTaskTypes = None

class DTTask:
    """ Base class for a task with DMR TEST device. It defines some common data and methods for 
    task parameter and status handling.
    """
    adcSampleFrequency: int = 120000 # Hz

    # dict for parameter decription and limits. All parameters are integers. Defaults are set in the subclass constructors.
    parameterData = {
        'ATT': {'ru': 'Затухание', 'en': 'Attenuation', 'lowlim': 0, 'uplim': 63, 'dunit': ('dB', 1)},
        'AVENUM': {'ru': 'Точек усреднения мощности', 'en': 'Power averaging points', 'lowlim': 1, 'uplim': 4096},
        'DATANUM': {'ru': 'Точек АЦП', 'en': 'ADC points', 'lowlim': 16, 'uplim': 16384},
        'FREQUENCY': {'ru': 'Несущая частота', 'en': 'Carrier frequency', 'lowlim': 137*MHz, 'uplim': 800*MHz, 'dunit': ('MHz', MHz)},
        'FREQUENCY OFFSET': {'ru': 'Сдвиг частоты', 'en': 'Frequency offset', 'lowlim': -10*kHz, 'uplim': 10*kHz, 'dunit': ('kHz', kHz)},
        'MODFREQUENCY': {'ru': 'Частота модуляции', 'en': 'Modulating frequency', 'lowlim': 1, 'uplim': 100*kHz, 'dunit': ('kHz', kHz)},
        'MODAMP': {'ru': 'Амлитуда модуляции', 'en': 'Modulating amplitude', 'lowlim': 0, 'uplim': 0xFFFF},
        'BNUM': {'ru': 'Количество бит', 'en': 'Number of bits', 'lowlim': 100, 'uplim': 2000},
        'RANGE': {'ru': 'Диапазон НЧ АЦП', 'en': 'Range of LF ADC', 'lowlim': 0, 'uplim': 15}
    }

    # dict for results desciption
    resultDesc = {
        'INPUT FREQUENCY': {'ru': 'Вх. частота модуляции', 'en': 'Input mod. frequency'},
        'INPUT POWER': {'ru': 'Входная мощность', 'en': 'Input power'},
        'OUTPUT POWER': {'ru': 'Выходная мощность', 'en': 'Output power'},
        'THDR': {'ru': 'КНИ', 'en': 'THDR'},
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
        self.com = DTSerialCom() # used serial interface instance (initialised only once as it's singleton)

        self.parameters = dict() # parameter values of the task
        self.results = dict() # results of the task
        self.message = '' # message to be shown after execution
        self.failed = False # if last task call is failed
        self.completed = False # if task is successfully completed

    def __call__(self):
        """ This method should be implemented in children classes so that task is performed when obj() is called.
            Should return the task object.
        """
        return self

    def check_parameter(self, par: str):
        if par not in self.parameters:
            raise DTInternalError(self.__class__.__name__+'.check_parameter', f'Unknown parameter "{par}"')
        
        pardata = DTTask.parameterData[par]
        if self.parameters[par] > pardata['uplim'] or self.parameters[par] < pardata['lowlim']:
            # TODO: should the message be set?
            if self.message:
                self.message += '\n'
            self.message += pardata[LANG] + (' вне диапазона' if LANG == 'ru' else ' out of range')
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
        for i in range(len(cls.statusBitDescription[LANG])):
            if status_word&(1<<i) != 0:
                desc += ('\n' if i>0 else '') + cls.statusBitDescription[LANG][i]
        return desc

    def _set_success(self):
        self.failed = False
        self.completed = True
        self.message = 'Успешно' if LANG == 'ru' else 'Success'

    def _set_error(self, message: str, prependmsg = True):
        self.failed = True
        self.completed = False
        if prependmsg:
            self.message = message + ':\n' + self.message
        elif message != '':
            self.message = message

    def _set_eval_error(self):
        self.failed = True
        self.completed = False
        self.message = 'Ошибка вычисления' if LANG == 'ru' else 'Evaluation error'

    def _set_com_error(self, exc: DTComError):
        self.failed = True
        self.completed = False
        self.message = ('Ошибка связи с устройством:\n' if LANG == 'ru' else 'Communication error:\n') + exc

    def _set_status_error(self, status: int):
        self.failed = True
        self.completed = False
        self.message = ('Ошибка статуса:\n' if LANG == 'ru' else 'Status error:\n') + self._decodeStatus(status&0x23)

    def _set_pll_error(self):
        self.failed = True
        self.completed = False
        self.message = 'Ошибка PLL демодулятора' if LANG=='ru' else 'Demodulator PLL error'

    def __repr__(self):
        return self.__class__.__name__ + '()'


class DTCalibrate(DTTask):
    """
    Calibration.
    """
    name = dict(ru='Калибровка', en='Calibration')

    def __init__(self):
        super().__init__()

    def __call__(self):
        self.failed = self.completed = False
        if not self.check_all_parameters():
            self._set_error('')
            return self

        try:
            self.com.command(b'SET MEASST', 1)
            self.com.command(b'SET DCCOMP', 1)
            time.sleep(1) #Ожидание интервала cal_waite_offs?
            self.com.command(b'SET DCCOMP', 0)

            status = self.com.command(b'STATUS', nreply=1)[0]
            self.results['STATUS'] = status
        except DTComError as exc:
            self._set_com_error(exc)
            return self

        if status&0x23 > 0:
            self._set_status_error(status)
            return self

        self._set_success()
        return self


class DTMeasurePower(DTTask):
    """
    Measuring input&output power.
    """
    name = dict(ru='Измерение входной/выходной мощности', en='Measuring input&output power')

    def __init__(self, avenum: int = 1, att: int = 0):
        super().__init__()
        self.parameters['AVENUM'] = int(min(avenum, 2**32-1))
        self.parameters['ATT'] = att

    def __call__(self):
        self.failed = self.completed = False
        if not self.check_all_parameters():
            self._set_error('')
            return self

        try:
            self.com.command(b'SET RF_PATH', 0)
            self.com.command(b'SET ATT', self.parameters['ATT'])
        except DTComError as exc:
            self._set_com_error(exc)
            return self

        pwrs = self.com.command(b'GET PWR', self.parameters['AVENUM'], nreply=2)

        self.results['OUTPUT POWER'] = pwrs[0]
        self.results['INPUT POWER'] = pwrs[1]

        self._set_success()
        return self

class DTMeasureInputFrequency(DTTask):
    """
    Measuring input frequency.
    """
    name = dict(ru='Измерение входной частоты', en='Measuring input frequency')

    def __init__(self, frequency: int = 200*MHz, foffset: int = 1*kHz, bufsize: int=16384):
        super().__init__()
        self.parameters['FREQUENCY'] = frequency
        self.parameters['FREQUENCY OFFSET'] = foffset
        self.parameters['DATANUM'] = bufsize
        self.buffer = None

    def __call__(self):
        self.failed = self.completed = False
        if not self.check_all_parameters():
            self._set_error('')
            return self

        foffset = 0
        try:
            self.com.command(b'SET MEASST', 1)
            frequency = self.parameters['FREQUENCY'] + self.parameters['FREQUENCY OFFSET']
            isset, foffset = self.com.set_pll_freq(frequency)
            if not isset:
                self._set_pll_error()
                return self
        except DTComError as exc:
            self._set_com_error(exc)
            return self

        try:
            # reading ADC data
            self.buffer = self.com.command(b'GET ADC DAT', [1, self.parameters['DATANUM']])
        except DTComError as exc:
            self._set_com_error(exc)
            return self

        evalfreq = self._eval_freq()
        if evalfreq is None:
            self._set_error('Ошибка вычисления' if LANG=='ru' else 'Evaluation error')    
            return self

        self.results['FREQUENCY'] = evalfreq - self.parameters['FREQUENCY OFFSET'] - foffset
        self._set_success()

        return self

    def _eval_freq(self):
        if self.buffer is None:
            return None

        df = self.results['FFT'] = np.abs(fft(np.array(self.buffer, dtype=np.float64)))

        # TODO: FFT of the buffer and evaluation of power-weighted frequency

        return 10*kHz # dummy value


class DTMeasureNonlinearity(DTTask):
    """
    Measuring nonlinearity.
    """
    name = dict(ru='Измерение КНИ', en='THD measurement')

    def __init__(self, frequency: int = 200*MHz, modamp = 0xFF, modfreq: int = 10*kHz, bufsize: int=16384):
        super().__init__()
        self.parameters['FREQUENCY'] = frequency
        self.parameters['MODAMP'] = modamp
        self.parameters['MODFREQUENCY'] = modfreq
        self.parameters['DATANUM'] = bufsize

    def __call__(self):
        self.failed = self.completed = False
        if not self.check_all_parameters():
            self._set_error('')
            return self
        
        foffset = 0
        try:
            self.com.command(b'SET MEASST', 2)
            isset, foffset = self.com.set_pll_freq(self.parameters['FREQUENCY'])
            if not isset:
                self._set_pll_error()
                return self
        except DTComError as exc:
            self._set_com_error(exc)
            return self

        try:
            self.com.command(b'SET LFDAC', [], owordsize=[2, 4])
            # reading ADC data
            self.buffer = self.com.command(b'GET ADC DAT', [1, self.parameters['DATANUM']])
        except DTComError as exc:
            self._set_com_error(exc)
            return self

        res = self._eval_freq_thdr()
        if res is None:
            self._set_eval_error()
            return self

        freq, thdr = res
        self.results['FREQUENCY'] = freq - foffset
        self.results['THDR'] = thdr
        self._set_success()

        return self

    def _eval_freq_thdr(self):
        if self.buffer is None:
            return None

        df = self.results['FFT'] = np.abs(fft(np.array(self.buffer, dtype=np.float64)))

        # TODO: FFT of the buffer and evaluation of power-weighted frequency and THDR

        return 10*kHz, 50 # dummy values


class DTDMRInput(DTTask):
    """
    DMR analysis
    """
    name = dict(ru='Вход ЦР', en='DMR Input')

    def __init__(self, frequency: int = 200*MHz):
        super().__init__()
        self.parameters['FREQUENCY'] = frequency

    def __call__(self):
        self.failed = self.completed = False
        if not self.check_all_parameters():
            self._set_error('')
            return self
        
        foffset = 0
        try:
            self.com.command(b'SET MEASST', 6)
            isset, foffset = self.com.set_pll_freq(self.parameters['FREQUENCY'])
            if not isset:
                self._set_pll_error()
                return self
        except DTComError as exc:
            self._set_com_error(exc)
            return self

        try:
            self.com.command(b'SET LFDAC', [], owordsize=[2, 4])
            # reading ADC data
            self.buffer = self.com.command(b'GET ADC DAT', [1, self.parameters['DATANUM']])
        except DTComError as exc:
            self._set_com_error(exc)
            return self

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
    DMR output power measurement
    """
    name = dict(ru='Выход ЦР', en='DMR Output')

    def __init__(self):
        super().__init__()
        # TODO

    def __call__(self):
        # TODO
        pass


class DTMeasureSensitivity(DTTask):
    """
    Measuring sensitivity.
    """
    name = dict(ru='Измерение чувствительности', en='Measuring sensitivity')

    def __init__(self):
        super().__init__()
        # TODO

    def __call__(self):
        # TODO
        pass

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
    for taskClass in (DTCalibrate, DTMeasurePower, DTMeasureInputFrequency, DTMeasureNonlinearity, DTDMRInput, DTDMROutput, DTMeasureSensitivity):
        dtTaskTypes.append(taskClass)

