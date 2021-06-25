from tasks import DTTask
from multiprocessing import Process
from multiprocessing.connection import Connection
from copy import copy


class DTProcess(Process):

    DEBUG = True

    """ Process for running DTTask-s in parallel to GUI """
    def __init__(self, conn: Connection):
        super().__init__()
        self.conn = conn

    def run(self):
        """ Run loop and waiting for submitted tasks """
        if self.DEBUG:
            print(f'DTProcess: Process {self.pid} started')

        while True:  # event loop
            obj = self.conn.recv()
            if isinstance(obj, DTTask):
                self.__runTask(obj)
            elif obj == 'terminate':
                if self.DEBUG:
                    print('DTProcess: Terminate command received')
                break

        if self.DEBUG:
            print(f'DTProcess: Process {self.pid} is finishing')

    def __runTask(self, task: DTTask):
        if self.DEBUG:
            print(f'DTProcess: Task {task.name["en"]} started')
        msg = None
        task.init_meas()
        self.__sendResults(task)
        if self.conn.poll():
            msg = self.conn.recv()
        if task.failed or task.completed or msg == 'stop':
            if self.DEBUG:
                print(f'DTProcess: Task {task.name["en"]} finished after init')
            if msg == 'stop':
                print(f'DTProcess: by user request')
            self.conn.send('stopped')
            return

        while msg != 'stop':
            task.measure()
            self.__sendResults(task)
            if task.failed:
                break
            if self.conn.poll():
                msg = self.conn.recv()

        self.conn.send('stopped')
        if self.DEBUG:
            print(f'DTProcess: Task {task.name["en"]} finished')

    def __sendResults(self, task: DTTask):
        if self.DEBUG:
            print('DTProcess: Sending task results')
        rtask = copy(task)  # shallow copying the task object before sending
        rtask.com = None  # avoid using or deleting DTSerialCom instance in the main process
        self.conn.send(rtask)
