import serial, time
from numbers import Integral

from singleton import Singleton
from exception import DTInternalError, DTComError
from dtglobals import DEBUG

class DTSerialCom(metaclass=Singleton):
    """
    Class implementing communication between PC and DMR TEST device via [emulated] serial port
    """

    def __init__(self, device='/dev/ttyACM0', timeout=1):
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

    def command(self, command: bytes, data=None, wordsize: int=2, nreply: int=0):
        """
        Send a binary packet to the device, receive a binary packet from the device and return data as list of integers if any.
        Command format: b'[COMMAND][LEN][DATA]END', where [COMMAND] - command name, [LEN] - [LEN] - length of [DATA], 
                                                    [DATA] - sequence of little-endian 2-byte words.
        Acknowledgement response: b'ACK'
        Reply with results: b'[LEN][DATA]END'

        Parameters:
            command - bytes object sent as a command
            data    - a bytes object, 2-byte integer or a sequence of 2-byte integers (in the latter case the data length must not be included) to be sent.
            nreply  - number of data words in the reply. 0 if no reply besides 'ACK' is expected. If nreply<0, then read all data available.
        """
        global DEBUG

        raisesource = 'DTSerialCom.command()'

        imask = (1<<wordsize*8)-1
        packet = b'\0' + command
        if isinstance(data, bytes) or isinstance(data, bytearray):
            packet += bytes(data)
        elif isinstance(data, Integral):
            packet += b'\x01\0'
            packet += int(data&imask).to_bytes(wordsize, byteorder='little', signed=False)
        elif hasattr(data, '__getitem__') and isinstance(data[0], Integral):
            for n in data:
                packet += int(n&imask).to_bytes(wordsize, byteorder='little', signed=False)
        elif data is None:
            packet += b'\0\0'
        else:
            raise DTInternalError(raisesource, 'Sending data type is expected to be bytes, integer or iterable of integers')
        packet += b'END'

        if DEBUG:
            print(f'DTSerialCom.command(): sending: {packet}')

        # Flush all buffers before communication
        self.port.reset_input_buffer()
        self.port.reset_output_buffer()

        try:
            nw = self.port.write(packet)
        except serial.SerialException as exc:
            raise DTComError(raisesource, 'Write to serial port failed') from exc

        if DEBUG:
            print(f'DTSerialCom.command(): {nw} bytes written to port')

        # Read acknowledgement
        try:
            ack = self.port.read(3)
        except serial.SerialException as exc:
            raise DTComError(raisesource, 'Read from serial port failed') from exc

        if ack != b'ACK':
            raise DTComError(raisesource, f'"ACK" was not received before timeout ({self.port.timeout}s) expired.')
        
        if nreply == 0:
            return list()

        # Read reply from the device
        try:
            if nreply > 0:
                response: bytes = self.port.read(nreply+5)
            else:
                response: bytes = self.port.read_until(b'END')
        except serial.SerialException as exc:
            raise DTComError(raisesource, 'Read from serial port failed') from exc

        if DEBUG:
            print(f'DTSerialCom.command(): received: {response}')

        rdata = list()

        if len(response) == 0:
            raise DTComError(raisesource, 'No response from the device')
        elif response[-3:] != b'END':
            print('DTSerialCom.command(): "END" was not received from the device.')
        elif nreply > 0 and len(response) != 2*nreply+5:
            raise DTComError(raisesource, f'Byte-length of the reply ({len(response)}) differs from expected one ({2*nreply+5})')
        else:
            response = response[:-3] # omit 'END'
            length = int.from_bytes(response[:2], byteorder='little', signed=False)
            if length != (len(response)-2)/2:
                raise DTComError(raisesource, f'Word-length of the reply ({(len(response)-2)/2}) differs from length read ({length})')

            for pos in range(2, min(2+2*length, len(response)), 2):
                rdata.append(int.from_bytes(response[pos:pos+2], byteorder='little', signed=False))

        return rdata

    def wait_status(self, mask: int, timeout=10):
        start = time.time()
        while 1:
            resp = self.command(b'STATUS', nreply=1)
            if len(resp) > 0 and resp[0]&mask > 0:
                return (True, resp[0])
            if timeout!=0 and time.time()-start > timeout:
                return (False, resp[0] if len(resp)>0 else None)
            time.sleep(0.2)

    def __del__(self):
        if hasattr(self, 'port'):
            self.port.close()