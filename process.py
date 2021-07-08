from time import time
from multiprocessing import Process
from multiprocessing.connection import Connection
from io import FileIO
from traceback import print_exc

import tasks
from tasks import DTTask, DTCalibrate
from dtcom import DTSerialCom


class DTProcess(Process):

    DEBUG = False

    """ Process for running DTTask-s in parallel to GUI """
    def __init__(self, conn: Connection):
        super().__init__()
        self.conn = conn
        self.caltask = DTCalibrate()
        self.calibPeriod = 600  # 10 min

    def calibrate(self):
        if self.DEBUG:
            print(f'DTProcess: Calibration')

        self.caltask.init_meas()
        if self.caltask.failed:
            print('Calibration error:', self.caltask.message)
        self.prevCalTime = time()

    def run(self):
        """ Run loop and waiting for submitted tasks """

        # Calibration after the start
        self.calibrate()

        while True:  # event loop
            # periodic calibration
            if time() - self.prevCalTime >= self.calibPeriod:
                self.calibrate()
            if not self.conn.poll(self.calibPeriod/10):
                continue
            obj = self.conn.recv()
            if isinstance(obj, DTTask):
                self.__runTask(obj)
            elif obj == 'terminate':
                if self.DEBUG:
                    print('DTProcess: Terminate command received')
                break
            elif obj == 'debugon':
                tasks.DEBUG = DTSerialCom.DEBUG = self.DEBUG = True
                print('DTProcess: DEBUG on')
            elif obj == 'debugoff':
                DTSerialCom.DEBUG = self.DEBUG = False
                print('DTProcess: DEBUG off')

        if self.DEBUG:
            print(f'DTProcess: Process {self.pid} is finishing')

    def __runTask(self, task: DTTask):
        if self.DEBUG:
            print(f'DTProcess: Task {task.name["en"]} started')

        msg = None

        try:
            task.init_meas()
            self.__sendResults(task)

            if self.conn.poll():
                msg = self.conn.recv()

            if task.failed or task.completed or msg == 'stop':
                if self.DEBUG:
                    print('DTProcess: task stopped after init')
            else:  # continue with the measurements
                while msg != 'stop':
                    task.measure()
                    self.__sendResults(task)
                    if task.failed:
                        break
                    if self.conn.poll():
                        msg = self.conn.recv()

        except Exception as exc:
            print_exc()
            self.conn.send(exc)
        finally:
            self.conn.send(f'stopped {task.id}')
            FileIO(self.conn.fileno(), 'r', closefd=False).flush()  # flush input messages
            if self.DEBUG:
                print(f'DTProcess: Task "{task.name["en"]}" finished')

    def __sendResults(self, task: DTTask):
        if self.DEBUG:
            print('DTProcess: Sending task results')
        rtask = DTTask().results_from(task)  # copying the results to a new task object before sending
        self.conn.send(rtask)
