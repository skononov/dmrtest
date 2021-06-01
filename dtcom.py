import serial, time
from numbers import Integral

from singleton import Singleton
from exception import DTInternalError, DTComError
from dtglobals import DEBUG

class DTSerialCom(metaclass=Singleton):
    """
    Class implementing communication between PC and DMR TEST device via [emulated] serial port
    """

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

    def command(self, command: bytes, odata=None, owordsize: int=2, nreply: int=0):
        """
        Send a binary packet to the device, receive a binary packet from the device and return data as list of integers if any.
        Command format: b'[COMMAND]\0[LEN][DATA]END\0', where [COMMAND] - command name, [LEN] - [LEN] - length of [DATA], 
                             [DATA] - sequence of little-endian 2-byte words.
        Acknowledgement response: b'ACK\0'
        Reply with results: b'[LEN][DATA]END\0'

        Parameters:
            command   - command name (ASCII)
            odata     - a bytes object or bytearray (transmitted as is) OR an integer OR a sequence of integers.
                        In the latter 2 cases the word data length is calculated and prepended by the method, 
                        the caller must not include it.
            owordsize - output word size in bytes.
            nreply    - number of data words in the reply. 0 - if no reply besides 'ACK' is expected. 
                        If nreply<0, then read all data available.
        """
        global DEBUG

        raisesource = 'DTSerialCom.command()'

        if owordsize != 2 and owordsize != 4:
            raise DTInternalError(raisesource, 'Output word size must be between 2 or 4')

        imask = (1<<owordsize*8)-1 # mask output data integers to fit to the requested byte-size
        # COMMAND null-terminated 
        packet = b'\0' + command + b'\0'
        
        if isinstance(odata, bytes) or isinstance(odata, bytearray):
            packet += bytes(odata)
        elif isinstance(odata, Integral):
            # LEN in words
            packet += (owordsize//2).to_bytes(2, byteorder='little')
            # DATA as LE-bytes
            packet += int(odata&imask).to_bytes(owordsize, byteorder='little', signed=False)
        elif hasattr(odata, '__getitem__') and hasattr(odata, '__len__') and len(odata)>0 and isinstance(odata[0], Integral):
            # LEN in words
            packet += (owordsize//2*len(odata)).to_bytes(2, byteorder='little')
            # DATA as LE-bytes
            for n in odata:
                packet += int(n&imask).to_bytes(owordsize, byteorder='little', signed=False)
        elif odata is None or hasattr(odata, '__len__') and len(odata)==0:
            packet += b'\0\0'
        else:
            raise DTInternalError(raisesource, 'Sending data type is expected to be bytes, integer or iterable of integers')
        
        # END null-terminated
        packet += b'END\0'

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

        # Read ACK
        try:
            if DEBUG:
                print(f'{raisesource}: reading 4 bytes with timeout {self.port.timeout}s')
            ack = self.port.read(4)
        except serial.SerialException as exc:
            raise DTComError(raisesource, 'Read from serial port failed') from exc

        if DEBUG:
            print(f'{raisesource}: {ack} is read')

        if ack == b'':
            raise DTComError(raisesource, f'Empty answer or timeout {self.port.timeout}s expired.')
        elif ack != b'ACK\0':
            raise DTComError(raisesource, f'b"ACK\\0" is expected while "{ack}" was received')
        
        if nreply == 0:
            return list()

        # Read reply from the device
        try:
            if nreply > 0:
                # await 2*nreply bytes plus number of transmitted words (2 bytes) and 'END\0' directive (4 bytes)
                nbexpect = 2*nreply+6
                if DEBUG:
                    print(f'{raisesource}: reading {nbexpect} bytes')
                response: bytes = self.port.read(nbexpect)
            else:
                if DEBUG:
                    print(f'{raisesource}: reading until b"END\\0" arrives')
                response: bytes = self.port.read_until(b'END\0')
        except serial.SerialException as exc:
            raise DTComError(raisesource, 'Read from serial port failed') from exc

        if DEBUG:
            print(f'{raisesource}: received: {response}')

        rdata = list()

        if len(response) == 0:
            raise DTComError(raisesource, 'No response from the device')
        elif response[-4:] != b'END\0':
            print('{raisesource}: b"END\\0" was not received from the device.')
        elif nreply > 0 and len(response) != 2*nreply+6:
            raise DTComError(raisesource, f'Byte-length of the reply ({len(response)}) differs from expected one ({2*nreply+6})')
        else:
            response = response[:-4] # omit 'END'
            length = int.from_bytes(response[:2], byteorder='little', signed=False)
            if length != (len(response)-2)/2:
                raise DTComError(raisesource, f'Length of the reply ({(len(response)-2)/2}) in words differs from length read ({length})')

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