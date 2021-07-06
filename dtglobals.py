
Hz: int = 1
kHz: int = 1000
MHz: int = 1000000
GHz: int = 1000000000

LANG = 'ru'  # or 'en'

adcSampleFrequency: int = 120000  # Hz
symbolDevFrequency: int = 648  # Hz

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
    '1': dict(multiple=1, quantity='dimensionless', ru='', en='')
    }
