import serial
import time
from numbers import Integral
from numpy import frombuffer, uint16

from singleton import Singleton
from dtexcept import DTInternalError, DTComError
# import dtglobals as dtg
from dt_c_api import get_pll_regs

_END = b'END'
_lenEND = len(_END)
_ACK = b'ACK'
_lenACK = len(_ACK)


class DTSerialCom(metaclass=Singleton):
    """
    Class implementing communication between PC and DMR TEST device via [emulated] serial port
    """

    DEBUG = False

    def __init__(self, device='/dev/ttyACM0', timeout=3):
        try:
            self.port = serial.Serial(device, timeout=timeout)
        except serial.SerialException as exc:
            raise DTComError('DTSerialCom()', f'Opening device {device} failed. Device is offline?') from exc

    @property
    def timeout(self):
        return self.port.timeout

    @timeout.setter
    def timeout(self, to):
        self.port.timeout = to

    def command(self, command, odata=None, owordsize=2, nreply=0):
        """
        Send a binary packet to the device, receive a binary packet from the device and return data as list of integers if any.
        Command format: b'[COMMAND]\0[LEN][DATA]END\0', where [COMMAND] - command name, [LEN] - [LEN] - length of [DATA],
                             [DATA] - sequence of little-endian 2-byte words.
        Acknowledgement response: b'ACK'
        Device must reply: b'[LEN][DATA]END\0'
        Method returns the NumPy array of uint16 with received data if any.

        Parameters:
            command   - command name (ASCII)
            odata     - a bytes object or bytearray (transmitted as is) OR an integer OR a sequence of integers.
                        In the latter 2 cases the word data length is calculated and prepended by the method,
                        the caller must not include it.
            owordsize - integer or list of integers output word size in bytes (2 and 4 only allowed).
            nreply    - number of data words in the reply. 0 - if no reply besides 'ACK' is expected.
                        If nreply<0, then read all data available.
        """
        global _END, _lenEND, _ACK, _lenACK
        DEBUG = DTSerialCom.DEBUG

        raisesource = 'DTSerialCom.command()'

        # COMMAND null-terminated
        if isinstance(command, str):
            packet = b'\0' + bytes(command, encoding='utf-8') + b'\0'
        elif isinstance(command, bytes) or isinstance(command, bytearray):
            packet = b'\0' + bytes(command) + b'\0'
        else:
            raise DTInternalError(raisesource, f'Invalid type of command argument: {type(command)}')

        if isinstance(odata, bytes) or isinstance(odata, bytearray):
            packet += bytes(odata)
        elif isinstance(odata, Integral):
            if not isinstance(owordsize, Integral) or owordsize != 2 and owordsize != 4:
                raise DTInternalError(raisesource, 'Output word size must be 2 or 4')
            imask = (1 << owordsize*8)-1  # mask output data integers to fit to the requested byte-size
            # LEN in words
            packet += (owordsize//2).to_bytes(2, byteorder='little')
            # DATA as LE-bytes
            packet += int(odata & imask).to_bytes(owordsize, byteorder='little', signed=False)
        elif hasattr(odata, '__getitem__') and hasattr(odata, '__len__') and len(odata) > 0:
            if not all([isinstance(oword, Integral) for oword in odata]):
                raise DTInternalError(raisesource, f'Some of output data words is not integer: {odata}.')
            if isinstance(owordsize, Integral):
                if owordsize != 2 and owordsize != 4:
                    raise DTInternalError(raisesource, 'Output word size must be 2 or 4.')
                owordsize = [owordsize]*len(odata)
            elif isinstance(owordsize, list) or isinstance(owordsize, tuple):
                owordsize = list(owordsize)
                lenwsize = len(owordsize)
                lendata = len(odata)
                if lenwsize == 0:
                    raise DTInternalError(raisesource, 'Output word size list must not be empty and contain only 2 or 4.')
                elif set(owordsize+[2, 4]) != {2, 4}:
                    raise DTInternalError(raisesource, 'Output word size list must contain only 2 or 4.')
                elif lenwsize < lendata:
                    owordsize.extend([owordsize[-1]]*(lendata-lenwsize))  # extend word sizes with the last value
                elif lenwsize > lendata:
                    owordsize = owordsize[:lendata]
            elif not isinstance(owordsize, list) and not isinstance(owordsize, tuple) and not isinstance(owordsize, Integral):
                raise DTInternalError(raisesource, 'Output word size must be scalar or list of 2 and 4.')

            # LEN in words
            packet += (sum(owordsize)//2).to_bytes(2, byteorder='little')
            # DATA as LE-bytes
            for oword, osize in zip(odata, owordsize):
                packet += int(oword & ((1 << osize*8)-1)).to_bytes(osize, byteorder='little', signed=False)
        elif odata is None or hasattr(odata, '__len__') and len(odata) == 0:
            packet += b'\0\0'
        else:
            raise DTInternalError(raisesource, 'Sending data type is expected to be bytes, integer or iterable of integers')

        # null-terminated END
        packet += _END + b'\0'

        if DEBUG:
            print(f'{raisesource}: sending {packet}')

        # Flush all buffers before communication
        self.port.reset_input_buffer()
        self.port.reset_output_buffer()

        try:
            nw = self.port.write(packet)
        except serial.SerialException as exc:
            raise DTComError(raisesource, 'Write to serial port failed') from exc

        if DEBUG:
            print(f'{raisesource}: {nw} bytes written to port')

        # Read reply from the device
        try:
            nbexpect = 0
            if nreply >= 0:
                # await 2*nreply bytes plus number of transmitted words (2 bytes) and END directive
                nbexpect = 2*nreply+2+_lenACK+_lenEND
                if DEBUG:
                    print(f'{raisesource}: reading {nbexpect} bytes')
                response: bytes = self.port.read(nbexpect)
            else:
                if DEBUG:
                    print(f'{raisesource}: reading until {_END} arrives')
                response: bytes = self.port.read_until(_END)
        except serial.SerialException as exc:
            raise DTComError(raisesource, 'Read from serial port failed') from exc

        if DEBUG:
            print(f'{raisesource}: received: {response}')

        if response == b'':
            raise DTComError(raisesource, f'Empty answer or timeout {self.port.timeout}s expired.')
        elif response == b'MCU BUSY':
            raise DTComError(raisesource, 'MCU BUSY')

        errmsgs = []
        if response[:_lenACK] != _ACK:
            errmsgs.append('ACK was not received')
        if response[-_lenEND:] != _END:
            errmsgs.append('END was not received')
        if nreply > 0 and len(response) != nbexpect:
            errmsgs.append(f'Number of bytes in the reply ({len(response)}) does not match' +
                           f' expected one ({nbexpect}). Can not read out data.')
        if len(errmsgs) > 0:
            raise DTComError(raisesource, '; '.join(errmsgs))

        if nreply == 0:
            return None

        rdata = None

        response = response[_lenACK:-_lenEND]  # omit ACK & END
        actualLength = (len(response)-2)//2  # actual response data length in 2-byte words
        length = int.from_bytes(response[:2], byteorder='little', signed=False)
        if length != actualLength:
            print(f'{raisesource}: Warning: Length of the reply ({actualLength}) in ' +
                  f'words differs from length read ({length})')
            length = actualLength
        rdata = frombuffer(response[2:], dtype=uint16, count=length)

        if DEBUG:
            print(f'{raisesource}: read data: {rdata}')

        return rdata

    def wait_status(self, mask: int, timeout=10):
        start = time.time()
        while 1:
            resp = self.command('STATUS', nreply=1)
            if len(resp) > 0 and resp[0] & mask > 0:
                return (True, resp[0])
            if timeout != 0 and time.time()-start > timeout:
                return (False, resp[0] if len(resp) > 0 else None)
            time.sleep(0.2)
        raise DTInternalError('DTSerialCom.wait_status()', 'End of function reached that must not happen')

    def set_pll_freq(self, pllnum: int, frequency: int):
        if pllnum not in (1, 2):
            raise DTInternalError('DTSerialCom.set_pll_freq()', f'Illegal PLL_NUM value: {pllnum}')
        for foffset in (0, -5, 5):
            regs = get_pll_regs(frequency+foffset)
            if regs is None:
                continue
            self.command('SET PLL', [1, 1])
            self.command('LOAD PLL', [pllnum, *regs], owordsize=[2]+6*[4])
            isset, _status = self.wait_status(1 << (1+pllnum), timeout=2)
            if isset:
                return isset, foffset
        return False, 0

    def __del__(self):
        if hasattr(self, 'port') and self.port.isOpen:
            self.port.close()
