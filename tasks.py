import sys, time
import numpy as np, scipy

from dtcom import DTSerialCom
from singleton import Singleton
from exception import DTInternalError, DTComError
from dtglobals import *
#from dtpll import encodePLL

dtTaskHandlers = dict()

class DTTask:
    """ Base class for a task with DMR TEST device
    """
    statusBitDescription = ("Переполнение I-канала ЦАП", "Переполнение Q-канала ЦАП",
                            "Установлен PLL модулятора", "Установлен PLL демодулятора",
                            "Загружены данные в модулятор", "Ошибка загрузки данных в модулятор")

    def __init__(self):
        self.com = DTSerialCom() # used serial instance

        self.parameters = dict() # parameters of the task
        self.results = dict() # results of the measurement
        self.message = '' # message to be shown
        self.failed = False # if last task call is failed
        self.completed = False # if task is successfully completed

    def __call__(self):
        """ This method should be implemented in children classes so that task is performed when obj() is called.
            Should return boolean: True - success, False - failure.
        """
        pass

    @classmethod
    def decodeStatus(cls, status_word: int):
        desc = []
        for i in range(len(cls.statusBitDescription)):
            if status_word&(1<<i) != 0:
                desc.append(cls.statusBitDescription[i])
        return desc


class DTCalibrate(DTTask):
    """
    Calibration.
    """
    def __init__(self):
        super().__init__()

    def __call__(self):
        self.completed = self.failed = False

        try:
            self.com.command(b'SET MEASST', 1)
            self.com.command(b'SET DCCOMP', 1)
            time.sleep(1) #Ожидание интервала cal_waite_offs?
            self.com.command(b'SET DCCOMP', 0)

            status = self.com.command(b'STATUS', nreply=1)[0]
            self.results['STATUS'] = status
        except DTComError as exc:
            self.message = 'Ошибка связи с устройством:\n' + exc
            self.failed = True
            return False

        if status&0x3 > 0:
            self.message = '\n'.join(self.decodeStatus(status)[:2])
            self.failed = True
            return False

        self.message = 'Калибровка проведена успешно.'
        self.completed = True
        return True


class DTMeasurePower(DTTask):
    """
    Measuring input&output power.
    """
    def __init__(self, avenum: int = 1, att: int = 0):
        super().__init__()
        self.parameters['AVENUM'] = int(min(avenum, 2**32-1))
        self.parameters['ATT'] = att

    def __call__(self):
        try:
            self.com.command(b'SET RF_PATH', 0)
            self.com.command(b'SET ATT', self.parameters['ATT'])
        except DTComError as exc:
            self.message = 'Ошибка связи с устройством:\n' + exc
            self.failed = True
            return False

        pwrs = self.com.command(b'GET PWR', self.parameters['AVENUM'], nreply=2)

        self.results['OUTPUT POWER'] = pwrs[0]
        self.results['INPUT POWER'] = pwrs[1]
        self.completed = True

        return True

class DTMeasureInputFrequency(DTTask):
    """
    Measuring input frequency.
    """
    def __init__(self, frequency: int = 100*kHz, foffset: int = 1*kHz):
        super().__init__()
        self.parameters['FREQUENCY'] = frequency
        self.parameters['FREQUENCY OFFSET'] = foffset
        self.bufsize = 1000 # buffer size for frequency measurement

    def __call__(self):
        try:
            self.com.command(b'SET MEASST', 1)
            isset = False
            for fshift in (0, -5, 5):
                setfreq += fshift
                
                #regs = encodePLL(setfreq)
                regs = [0]*6 # temporary
                
                self.com.command(b'LOAD PLL', [2, *regs])
                
                isset, _status = self.com.wait_status(1<<3, timeout=2)
                if isset:
                    break
        except DTComError as exc:
            self.message = 'Ошибка связи с устройством:\n' + exc
            self.failed = True
            return False

        if not isset:
            self.message = 'Частота не измерена: ошибка PLL демодулятора.'
            self.failed = True
            return False

        try:
            self.buffer = self.com.command(b'GET ADC DAT', [1, self.bufsize])
        except DTComError as exc:
            self.message = 'Ошибка связи с устройством:\n' + exc
            self.failed = True
            return False

        # TODO: FFT of the buffer and evaluation of power-weighted frequency

        self.results['FREQUENCY'] = 100*kHz # temporary
        self.completed = True
        return True


def dtTaskInit():
    global dtTaskHandlers
    dtTaskHandlers['Калибровка'] = DTCalibrate()
    dtTaskHandlers['Измерение входной/выходной мощности'] = DTMeasurePower()
    dtTaskHandlers['Измерение входной частоты'] = DTMeasureInputFrequency()

