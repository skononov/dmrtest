
__appname__ = 'DMR TEST'
__version__ = '0.1'


Hz: int = 1
kHz: int = 1000
MHz: int = 1000000
GHz: int = 1000000000

LANG = 'ru'  # or 'en'

adcSampleFrequency: int = 120000  # Hz
symbolDevFrequency: int = 648  # Hz

# Input range of MAX11198 ADC in volts (assumed bipolar)
hfAdcRange = 2.5

# Input ranges of ADS868x ADC in volts (assumed bipolar) in the order of code
lfAdcVoltRanges = (12.288, 10.24, 6.144, 5.12, 2.56)

adcCountRange = (1 << 16)  # full count range both for LF and HF ADCs (max. value is adcCountRange-1)

units = {
    'Hz': dict(multiple=Hz, quantity='frequency', ru='Гц', en='Hz'),
    'kHz': dict(multiple=kHz, quantity='frequency', ru='кГц', en='kHz'),
    'MHz': dict(multiple=MHz, quantity='frequency', ru='МГц', en='MHz'),
    'GHz': dict(multiple=GHz, quantity='frequency', ru='ГГц', en='GHz'),
    'mV': dict(multiple=0.001, quantity='voltage', ru='мВ', en='mV'),
    'V': dict(multiple=1, quantity='voltage', ru='В', en='V'),
    'mW': dict(multiple=1, quantity='power', ru='мВт', en='mW'),
    'W': dict(multiple=1000, quantity='power', ru='мВт', en='mW'),
    'dB': dict(multiple=1, quantity='attenuation', ru='дБ', en='dB'),
    'dBm': dict(multiple=1, quantity='logpower', ru='дБм', en='dBm'),
    '%': dict(multiple=0.01, quantity='fraction', ru='%', en='%'),
    'ppm': dict(multiple=1e-6, quantity='fraction', ru='ppm', en='ppm'),
    '1': dict(multiple=1, quantity='dimensionless', ru='', en=''),
    'none': dict(multiple=1, quantity='none', ru='', en='')
    }

appInfo = dict(
    ru=f"""
        {__appname__} {__version__}
        Тест цифрового передвижного радио от "ИТЦ Контур"

        Для управления используйте манипулятор мышь или клавиатуру.
        Управляющие клавиши:
            Tab, Shift-Tab - передвижение между элементами
            \u2191 \u2193 - передвижение по меню, прокрутка значений параметров
            Space - нажатие кнопки, открытие меню, выбор пункта меню
            Esc - выход из текущего окна или меню
            Колесо мыши - прокрутка значений параметров
        """,
    en=f"""
        {__appname__} {__version__}
        Test of Digital Mobile Radio by "ITC Kontur"

        Use mouse or keyboard for control.
        Controlling keys:
            Tab, Shift-Tab - move between elements
            \u2191 \u2193 - scroll menu, scrolling parameter values
            Space - press a button, open a menu, choose a menu item
            Esc - exit the current window or menu
            Mouse wheel - scrolling parameter values
        """
)
