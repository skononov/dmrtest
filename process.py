import tasks
from tasks import DTTask
from dtcom import DTSerialCom
from multiprocessing import Process
from multiprocessing.connection import Connection


class DTProcess(Process):

    DEBUG = False

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

        task.init_meas()

        if self.conn.poll():
            msg = self.conn.recv()

        if task.failed or task.completed or msg == 'stop':
            self.__sendResults(task)
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

        self.conn.send(f'stopped {task.id}')
        if self.DEBUG:
            print(f'DTProcess: Task "{task.name["en"]}" finished')

    def __sendResults(self, task: DTTask):
        if self.DEBUG:
            print('DTProcess: Sending task results')
        rtask = DTTask().results_from(task)  # copying the results to a new task object before sending
        self.conn.send(rtask)
