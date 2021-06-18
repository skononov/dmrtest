
Hz: int = 1
kHz: int = 1000
MHz: int = 1000000
GHz: int = 1000000000

LANG = 'ru'  # or 'en'

adcSampleFrequency: int = 120000  # Hz
symbolDevFrequency: int = 648  # Hz

units = {
    'Hz': dict(multiple=Hz, quantity='frequency', title=dict(ru='Гц', en='Hz')),
    'kHz': dict(multiple=kHz, quantity='frequency', title=dict(ru='кГц', en='kHz')),
    'MHz': dict(multiple=MHz, quantity='frequency', title=dict(ru='МГц', en='MHz')),
    'GHz': dict(multiple=GHz, quantity='frequency', title=dict(ru='ГГц', en='GHz')),
    'mV': dict(multiple=0.001, quantity='voltage', title=dict(ru='мВ', en='mV')),
    'V': dict(multiple=1, quantity='voltage', title=dict(ru='В', en='V')),
    'mW': dict(multiple=1, quantity='power', title=dict(ru='мВт', en='mW')),
    'W': dict(multiple=1000, quantity='power', title=dict(ru='мВт', en='mW')),
    'dBm': dict(multiple=1, quantity='logpower', title=dict(ru='дБм', en='dBm')),
    '1': dict(multiple=1, quantity='dimensionless', title=dict(ru='', en=''))
    }
