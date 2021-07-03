from numbers import Integral
from os import access, R_OK, getpid, getenv
from io import FileIO
import numpy as np
from scipy.fft import rfftfreq
import matplotlib as mpl
import matplotlib.pyplot as plt
import tkinter as tk
# import tkinter.messagebox as tkmsg
from multiprocessing import Pipe

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from process import DTProcess
from config import DTConfiguration, __appname__, __version__
from tasks import DTScenario, DTTask, dtTaskInit, dtParameterDesc, dtResultDesc
import tasks
from singleton import Singleton
import dtglobals as dtg


mpl.rcParams["figure.dpi"] = 100
mpl.rcParams["lines.linewidth"] = 2.0
mpl.rcParams["grid.linewidth"] = 0.5
mpl.rcParams["axes.linewidth"] = 1.0
mpl.rcParams["axes.xmargin"] = 0.0
mpl.rcParams["font.size"] = 10
mpl.rcParams["figure.constrained_layout.use"] = True
mpl.rcParams["figure.constrained_layout.h_pad"] = 0.06
mpl.rcParams["figure.constrained_layout.w_pad"] = 0.1
mpl.rcParams["figure.constrained_layout.hspace"] = 0.02
mpl.rcParams["axes.autolimit_mode"] = 'round_numbers'

_rootWindowWidth = 1024
_rootWindowHeight = 700

DARK_BG_COLOR = '#0F0F0F'
DEFAULT_BG_COLOR = '#1F1F1F'
LIGHT_BG_COLOR = '#2E2E2E'
LIGHTER_BG_COLOR = '#4E4E4E'
HIGHLIGHT_COLOR = '#3C449D'
SELECT_BG_COLOR = '#274F77'
BUTTON_BG_COLOR = '#505050'
DEFAULT_FG_COLOR = '#EEEEEE'

DEFAULT_FONT_FAMILY = "Helvetica"
MONOSPACE_FONT_FAMILY = "lucidasanstypewriter"
BIG_FONT_SIZE = '14'
DEFAULT_FONT_SIZE = '12'
SMALL_FONT_SIZE = '10'


class DTApplication(tk.Tk, metaclass=Singleton):
    """ DMR TEST Application built with Tkinter
    """
    DEBUG = False

    __dtTkOptionFilename = '~/.dtstyle'

    def __init__(self):
        if self.DEBUG:
            print(f'DTApplication created in the procees PID {getpid()}')

        super().__init__()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        if sw/sh > 2:
            sw //= 2
        geometry = f'{_rootWindowWidth}x{_rootWindowHeight}{(sw-_rootWindowWidth)//2:+d}{(sh-_rootWindowHeight)//2:+d}'
        self.geometry(geometry)
        self.title(__appname__ + ' ' + __version__)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.imgdir = getenv('HOME')+'/dmr/img'

        if access(self.imgdir + '/logo.gif', R_OK):
            self.logo = tk.PhotoImage(file=self.imgdir + '/logo.gif')
        else:
            self.logo = None

        self.wm_iconphoto(True, self.logo)

        # init task handlers
        dtTaskInit()

        # start task process
        self.taskConn, child_conn = Pipe()
        self.taskProcess = DTProcess(child_conn)
        self.taskProcess.start()

        # set styles
        # plt.style.use('fivethirtyeight')
        if access(DTApplication.__dtTkOptionFilename, R_OK):
            self.readStyle(DTApplication.__dtTkOptionFilename)
        else:
            self.defaultStyle()
            plt.style.use('dark_background')
        mpl.rcParams['axes.facecolor'] = self.option_get('activeBackground', 'DTApplication')
        mpl.rcParams['figure.facecolor'] = self.option_get('activeBackground', 'DTApplication')

        self.mainMenuFrame = DTMainMenuFrame(self)
        self.mainMenuFrame.grid(sticky=tk.W+tk.E+tk.N+tk.S)

    def readStyle(self, filename: str):
        self.option_clear()
        try:
            self.option_readfile(filename)
        except tk.TclError:
            print(f'DTApplication.readStyle(): Can not read Tk option file {filename}')

    def defaultStyle(self):
        self.option_clear()
        self.option_add('*background', DEFAULT_BG_COLOR)
        self.option_add('*highlightBackground', DEFAULT_BG_COLOR)
        self.option_add('*activeBackground', LIGHT_BG_COLOR)
        self.option_add('*activeForeground', DEFAULT_FG_COLOR)
        self.option_add('*selectColor', LIGHT_BG_COLOR)
        self.option_add('*highlightThickness', '0')
        self.option_add('*Button.highlightThickness', '2')
        self.option_add('*Menubutton.highlightThickness', '2')
        self.option_add('*Entry.highlightThickness', '2')
        self.option_add('*Spinbox.highlightThickness', '2')
        self.option_add('*Listbox.highlightThickness', '2')
        self.option_add('*Entry.background', DARK_BG_COLOR)
        self.option_add('*Spinbox.background', DARK_BG_COLOR)
        self.option_add('*Listbox.background', DARK_BG_COLOR)
        self.option_add('*Button.background', BUTTON_BG_COLOR)
        self.option_add('*Menubutton.background', BUTTON_BG_COLOR)
        self.option_add('*foreground', DEFAULT_FG_COLOR)
        self.option_add('*highlightColor', HIGHLIGHT_COLOR)
        self.option_add('*font', f'{DEFAULT_FONT_FAMILY} {DEFAULT_FONT_SIZE}')
        self.option_add('*Entry.font', f'{MONOSPACE_FONT_FAMILY} {DEFAULT_FONT_SIZE}')
        self.option_add('*Spinbox.font', f'{MONOSPACE_FONT_FAMILY} {DEFAULT_FONT_SIZE}')

    def run(self):
        self.mainloop()

        if self.DEBUG:
            print('DTApplication.run(): exit event loop')
        if self.taskProcess.is_alive():
            self.taskConn.send('terminate')
            self.taskProcess.join()
        self.taskConn.close()

    def showMessage(self, message: str, master=None, delay=0, status='default'):
        w = tk.Toplevel(padx=20, pady=10)
        w.grab_set()
        if master is None:
            master = self
        w.transient(master)
        x0, y0 = master.winfo_rootx(), master.winfo_rooty()
        w.geometry(f'{x0+100:+d}{y0:+d}')
        if status in ('info', 'error', 'warning'):
            tk.Label(w, bitmap=status).grid(column=0, row=0, sticky=tk.W, padx=10)
        tk.Message(w, text=message, justify=tk.LEFT, width=250).grid(row=0, column=1, sticky=tk.W+tk.E)
        if delay == 0:
            tk.Button(w, text='ОК', command=lambda: (w.grab_release(), w.destroy()), padx=20, pady=5)\
                .grid(row=1, column=0, columnspan=2, sticky=tk.S, pady=10)
            w.wait_window(w)
        else:
            self.after(int(delay*1000), lambda: (w.grab_release(), w.destroy()))


class DTChooseObjectMenu(tk.Menu):
    """ Univeral menu for choosing one object from a list. Uses Radiobutton widget as a menu item.
    """
    def __init__(self, menubutton, command, objects):
        super().__init__(menubutton, tearoff=0, postcommand=self.composeMenu)
        self.command = command
        self.objects = objects
        self.locName = False
        self.isDict = False
        self.isSubscriptable = False

        if hasattr(self.objects, '__iter__'):
            if isinstance(self.objects, dict):
                self.isDict = True
            if hasattr(self.objects, '__getitem__'):
                self.isSubscriptable = True
        else:
            DTApplication().showMessage('Ошибка приложения. Требуется перезапуск.\n' +
                                        self.__class__.__name__ + f': Called for invalid type {type(self.objects)}',
                                        status='error')
            DTApplication().quit()

    def composeMenu(self):
        self.delete(0, tk.END)
        if len(self.objects) == 0:
            return
        if self.isDict:
            self.optVar = tk.StringVar()
            for name, obj in self.objects.items():
                self.add_radiobutton(label=name, indicatoron=False,
                                     value=name, variable=self.optVar, command=self.__select)
        else:
            obj = next(iter(self.objects))
            if hasattr(obj, 'name') and isinstance(obj.name, dict) and dtg.LANG in obj.name:
                locName = True
            elif hasattr(obj, 'name') and isinstance(obj.name, str):
                locName = False
            else:
                DTApplication().showMessage('Ошибка приложения. Требуется перезапуск.\n' +
                                            self.__class__.__name__ + f': No name defined for the object of type {type(obj)}',
                                            status='error')
                DTApplication().quit()
                return
            self.optVar = tk.IntVar()
            for index, obj in enumerate(self.objects):
                self.add_radiobutton(label=obj.name[dtg.LANG] if locName else obj.name, indicatoron=False,
                                     value=index, variable=self.optVar, command=self.__select)

    def __select(self):
        opt = self.optVar.get()
        self.forget()
        if self.isSubscriptable:
            self.command(self.objects[opt])
        else:
            self.command(list(self.objects)[opt])


class DTPlotFrame(tk.Frame):
    """ Widget for plotting results data with Matplotlib/TkAgg
    """
    def __init__(self, master, figsize=None):
        super().__init__(master)
        self.figure = None
        self.gridOn = True  # flag for adding grid to exes
        self.createCanvas(figsize)

    def createCanvas(self, figsize=None):
        if self.figure is not None:
            del self.figure
        if figsize is None:
            figsize = (5, 5)
        self.figure = Figure(figsize=figsize)
        self.resaxes = dict()
        self.ncolors = len(mpl.rcParams["axes.prop_cycle"])
        canvas = FigureCanvasTkAgg(self.figure, master=self)
        canvas.draw()
        canvas.get_tk_widget().grid()

    def plotGraph(self, x, y, labelx=None, labely=None):
        self.figure.clf()
        axes = self.figure.add_subplot(111, autoscale_on=True)
        axes.plot(x, y)
        if labelx:
            axes.set_xlabel(labelx)
        if labely:
            axes.set_ylabel(labely)
        axes.grid(self.gridOn, 'major')
        self.figure.canvas.draw()
        self.figure.canvas.flush_events()

    def updateGraph(self, x, y):
        if len(self.figure.axes) == 1 and len(self.figure.axes[0].lines) == 1:
            axes = self.figure.axes[0]
            axes.lines[0].set_data(x, y)
            axes.relim(True)
            axes.autoscale_view()
            self.figure.canvas.draw()
            self.figure.canvas.flush_events()

    def plotGraphs(self, results: dict):
        """Plot all marked results. Create new subplots for the first time and
           updating them if marked results are the same as in previous call.
           results structure:
             {reskey: {'draw': bool, 'type': ('time'|'freq'), 'n': size, 'x': array, 'y': array},...}
        """
        if not hasattr(self, 'pkeys'):
            self.pkeys = None
        ckeys = tuple([k for k, r in results.items() if r['draw']])
        nres = len(ckeys)
        if nres == 0:
            self.clearCanvas()
            return
        if self.pkeys != ckeys or len(self.figure.axes) == 0:
            # plot new
            self.pkeys = ckeys
            self.figure.clf()

            ntypes = len(set([r['type'] for r in results.values() if r['draw']]))
            self.figure.subplots(nres, 1, sharex=(ntypes == 1), subplot_kw=dict(autoscale_on=True))
            axes = self.figure.axes
            for i, (ax, key) in enumerate(zip(axes, ckeys)):
                result = results[key]
                color = f'C{i%self.ncolors}'  # cycle colors
                if result['type'] == 'time':
                    n = result['n']
                    x = result['x']
                    ax.plot(x[:n], result['y'][:n], '.', ls=('-' if n < 100 else ''), color=color)
                    if ntypes == 1 and i == nres-1 or ntypes > 1:
                        ax.set_xlabel('Время [с]' if dtg.LANG == 'ru' else 'Time [s]')
                    yunit = dtg.units[dtResultDesc[key]['dunit']][dtg.LANG]
                    ax.set_title(f'{dtResultDesc[key][dtg.LANG]} [{yunit}]')
                    ax.set_xlim(x[0], max(int(x[n-1]+1), x[0]+10))
                else:
                    ax.plot(result['x'], result['y'], '.', ls=('-' if result['n'] < 100 else ''), color=color)
                    if ntypes == 1 and i == nres-1 or ntypes > 1:
                        ax.set_xlabel('Частота [Гц]' if dtg.LANG == 'ru' else 'Frequency [Hz]')
                    ax.set_title(f'Амплитуда {key}' if dtg.LANG == 'ru' else 'Amplitude {key}')
                ax.relim(True)
                ax.autoscale_view(tight=False)
                ax.grid(self.gridOn, 'major')
        else:
            # update plots
            axes = self.figure.axes
            assert(len(axes) == nres)
            for ax, key in zip(axes, ckeys):
                result = results[key]
                n = result['n']
                x = result['x'][:n] if result['x'].size > n else result['x']
                y = result['y'][:n] if result['y'].size > n else result['y']
                ax.lines[0].set_ls('-' if n < 100 else '')
                ax.lines[0].set_data(x, y)
                if result['type'] == 'time':
                    ax.set_xlim(x[0], max(int(x[n-1]+1), x[0]+10))
                ax.relim(True)
                ax.autoscale_view(tight=False)
        self.figure.canvas.draw()
        self.figure.canvas.flush_events()

    def clearCanvas(self):
        self.figure.clf()
        self.figure.canvas.draw()
        self.figure.canvas.flush_events()


class DTMainMenuFrame(tk.Frame, metaclass=Singleton):
    """ Main menu frame drawn in the root window
    """
    def __init__(self, master):
        super().__init__(master)
        self.configure(padx=10, pady=10)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=1)

        self.__createLogoFrame()
        self.logoFrame.grid(column=0, row=0, sticky=tk.W+tk.E+tk.N+tk.S)

        self.__createMenuFrame()
        self.menuFrame.grid(column=1, row=0, sticky=tk.N+tk.S)

    def __runScenario(self, scenario: DTScenario):
        if len(scenario) == 0:
            DTApplication().showMessage('Сценарий без задач!', status='error')
            return

        self.grid_forget()
        index = 0
        while True:
            state = 'midthrough'
            if index == 0:
                state = 'first'
            elif index == len(scenario)-1:
                state = 'last'
            task: DTTask = scenario[index]
            taskFrame = DTTaskFrame(self.master, task, state)
            task.load_cal()
            scenario[index] = taskFrame.task  # update scenario task
            taskFrame.grid(sticky=tk.W+tk.E+tk.N+tk.S)
            taskFrame.wait_variable(taskFrame.frameFinished)
            taskFrame.grid_forget()
            if taskFrame.direction == 0:
                break
            elif taskFrame.direction == -1 and index > 0:
                index -= 1
                continue
            index += 1
            if index == len(scenario):
                break
        self.grid(sticky=tk.W+tk.E+tk.N+tk.S)

    def __newScenario(self):
        dialog = DTNewScenarioDialog(self.master)
        dialog.grab_set()
        self.wait_window(dialog)
        dialog.grab_release()
        nscenarios = len(tasks.dtAllScenarios)
        if nscenarios > 0:
            self.runScenarioMB['state'] = tk.NORMAL
            self.scenariosText.set(f'{nscenarios} сценариев определено')

    def __chooseTask(self, taskType: DTTask):
        task: DTTask = taskType()
        task.load_cal()
        task.set_id()  # set task ID in the main process
        taskFrame = DTTaskFrame(self.master, task)
        self.grid_forget()
        taskFrame.grid(sticky=tk.W+tk.E+tk.N+tk.S)
        taskFrame.wait_variable(taskFrame.frameFinished)
        taskFrame.destroy()
        self.grid(sticky=tk.W+tk.E+tk.N+tk.S)
        del taskFrame
        del task

    def __createLogoFrame(self):
        self.logoFrame = tk.Frame(self, padx=10, pady=10, relief=tk.GROOVE)
        self.logoFrame.columnconfigure(0, weight=1)
        self.logoFrame.rowconfigure(0, weight=1)
        self.logoFrame.rowconfigure(1, weight=1)

        tk.Label(self.logoFrame, image=self.master.logo).grid(row=0, sticky=tk.N, padx=10, pady=5)

        text = f"""
            Информация о приложении {__appname__} {__version__}.
            Информация о приложении {__appname__} {__version__}.
            Информация о приложении {__appname__} {__version__}.
            """

        # add a text Frame
        textbox = tk.Text(self.logoFrame, padx="2m", pady="1m", wrap=tk.WORD)

        # add a vertical scrollbar to the frame
        # rightScrollbar = tk.Scrollbar(textboxFrame, orient=tk.VERTICAL, command=textbox.yview)
        # textbox.configure(yscrollcommand = rightScrollbar.set)
        # rightScrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        textbox.grid(row=1, sticky=tk.W+tk.E+tk.N+tk.S)
        textbox.insert(tk.END, text, "normal")
        textbox.configure(state=tk.DISABLED)

    def __setDebug(self):
        DTApplication.DEBUG = (self.debugVar.get() != 0)
        self.master.taskConn.send('debugon' if DTApplication.DEBUG else 'debugoff')

    def __createMenuFrame(self):
        self.menuFrame = tk.Frame(self, padx=10, pady=10)

        for i in range(1, 5):
            self.menuFrame.rowconfigure(i, pad=20)
        self.menuFrame.rowconfigure(5, weight=1)

        self.scenariosText = tk.StringVar()
        self.scenariosText.set(f'{len(tasks.dtAllScenarios)} сценариев определено')
        self.scenariosText.set(f'{len(tasks.dtAllScenarios)} сценариев определено')
        tk.Label(self.menuFrame, textvariable=self.scenariosText).grid(row=0)

        csmb = self.runScenarioMB = tk.Menubutton(self.menuFrame, text='Запустить сценарий')
        csmb.configure(relief=tk.RAISED, height=2, highlightthickness=2, takefocus=True)
        if len(tasks.dtAllScenarios) == 0:
            csmb['state'] = tk.DISABLED
        csmb.grid(row=1, sticky=tk.W+tk.E)
        csmb['menu'] = csmb.menu = DTChooseObjectMenu(csmb, command=self.__runScenario,
                                                      objects=tasks.dtAllScenarios)

        cmmb = tk.Menubutton(self.menuFrame, text='Выбрать измерение')
        cmmb.configure(relief=tk.RAISED, height=2, highlightthickness=2, takefocus=True)
        cmmb['menu'] = cmmb.menu = DTChooseObjectMenu(cmmb, command=self.__chooseTask,
                                                      objects=tasks.dtTaskTypes)
        cmmb.grid(row=2, sticky=tk.W+tk.E)

        csb = tk.Button(self.menuFrame, text='Создать сценарий')
        csb.configure(command=self.__newScenario, height=2, highlightthickness=2)
        csb.grid(row=3, sticky=tk.W+tk.E)
        csb.focus()

        self.debugVar = tk.IntVar()
        cdb = tk.Checkbutton(self.menuFrame, text='Отладка')
        cdb.configure(variable=self.debugVar, padx=3, command=self.__setDebug)
        cdb.grid(row=4, sticky=tk.W)

        quitb = tk.Button(self.menuFrame, text='Выход', command=self.master.quit, height=2)
        quitb.grid(row=5, sticky=tk.W+tk.E+tk.S)


class DTNewScenarioDialog(tk.Toplevel):
    """ A dialog window for defining a new scenario.
    """
    def __init__(self, master=None):
        super().__init__(master)
        x0, y0 = master.winfo_rootx(), master.winfo_rooty()
        self.geometry(f'{x0+200:+d}{y0:+d}')
        self.title('Создать сценарий')
        self.configure(padx=20, pady=10)
        self.bind('<Key-Escape>', self.__close)

        for irow in range(4):
            self.rowconfigure(irow, pad=10)
        self.columnconfigure(0, pad=20)
        self.columnconfigure(1, pad=10)
        self.columnconfigure(2, pad=0)

        tk.Label(self, text='Имя:').grid(column=0, row=0, sticky=tk.E, padx=10, pady=5)

        self.nameVar = tk.StringVar()
        self.nameVar.set(self.__newName())
        nameEntry = tk.Entry(self, textvariable=self.nameVar, width=35)
        nameEntry.grid(column=1, row=0, sticky=tk.W+tk.E)
        nameEntry.focus()

        tk.Label(self, text='Задачи:').grid(column=0, row=1, sticky=tk.NE, padx=10, pady=5)

        self.yTaskScroll = tk.Scrollbar(self, orient=tk.VERTICAL)
        self.yTaskScroll.grid(column=2, row=1, sticky=tk.N+tk.S+tk.W)
        self.taskListVar = tk.StringVar()
        self.taskListbox = tk.Listbox(self, height=10, selectmode=tk.SINGLE, listvariable=self.taskListVar)
        self.taskListbox['yscrollcommand'] = self.yTaskScroll.set
        self.yTaskScroll['command'] = self.taskListbox.yview
        self.taskListbox.grid(column=1, row=1, sticky=tk.N+tk.S+tk.W+tk.E, pady=5)
        self.taskListbox.bind('<Key-Delete>', self.__deleteTask)

        menubtn = tk.Menubutton(self, text='Добавить', relief=tk.RAISED, takefocus=True, width=30)
        menubtn['menu'] = menubtn.menu = DTChooseObjectMenu(menubtn, command=self.__addTask, objects=tasks.dtTaskTypes)
        menubtn.grid(column=1, row=2, sticky=tk.NW, pady=5)

        tk.Button(self, text='Создать сценарий', command=self.__create).grid(column=1, row=3, sticky=tk.E)

        tk.Button(self, text='Отмена', command=self.destroy).grid(column=0, row=3, sticky=tk.W)

    def __close(self, event):
        self.destroy()

    def __create(self):
        if self.taskListbox.size() == 0:
            DTApplication().showMessage('Нет введенных задач.', master=self, status='error')
            # tkmsg.showinfo('', 'Нет введенных задач!')
            return

        name = self.nameVar.get()
        if name in tasks.dtAllScenarios:
            # tkmsg.showerror('Ошибка', f'Сценарий с именем {name} уже существует!')
            DTApplication().showMessage(f'Сценарий с именем "{name}" уже существует!', master=self, status='error')
            return
        if name == '':
            # tkmsg.showerror('Ошибка', 'Пустое имя сценария!')
            DTApplication().showMessage('Пустое имя сценария!', master=self, status='error')
            return

        seltasks = self.taskListVar.get().strip('(,)')
        tnameslist = [s.strip("' ") for s in seltasks.split(',')]
        DTScenario(name, tnameslist)
        self.destroy()
        # tkmsg.showinfo('', f'Сценарий {name} создан')
        DTApplication().showMessage(f'"{name}" создан')

    def __addTask(self, tasktype):
        if self.taskListbox.curselection() == ():
            self.taskListbox.insert(tk.END, tasktype.name[dtg.LANG])
        else:
            self.taskListbox.insert(tk.ACTIVE, tasktype.name[dtg.LANG])

    def __newName(self):
        n = 1
        while f'Сценарий {n}' in tasks.dtAllScenarios:
            n += 1
        return f'Сценарий {n}'

    def __deleteTask(self, event):
        if event.keysym == 'Delete':
            selected = self.taskListbox.curselection()
            if len(selected) == 0:
                return
            self.taskListbox.delete(selected[0])


class DTTaskFrame(tk.Frame):
    """ A frame rendered in the root window to manage task execution
    """
    def __init__(self, master=None, task=None, state=None):
        """ Constructor for a task front-end.
            task - DTTask object to be managed
            state - can have values: None, 'first' (first in scenario), 'last' (last in scenario), 'midthrough'.
        """
        if DTApplication.DEBUG:
            print(f'DTTaskFrame created with for task "{task.name["ru"]}"')

        super().__init__(master)
        self.task = task
        self.state = state
        self.direction = None
        self.resHistSize = 1000

        # objects to communicate with task process
        self.taskConn = DTApplication().taskConn
        self.taskProcess = DTApplication().taskProcess

        # set when finished dealing with the current task
        self.frameFinished = tk.IntVar()

        self.__createWidgets()

    def __createWidgets(self):
        self.configure(padx=5, pady=5)
        self.lw = int(0.6*_rootWindowWidth)
        self.rw = _rootWindowWidth-self.lw
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1, minsize=self.lw)
        self.columnconfigure(1, weight=1)

        tk.Label(self, text=self.task.name[dtg.LANG], height=2, relief=tk.GROOVE,
                 borderwidth=3, font=(DEFAULT_FONT_FAMILY, BIG_FONT_SIZE))\
            .grid(row=0, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E+tk.N)

        self.leftFrame = tk.Frame(self, padx=10, pady=20)
        self.leftFrame.columnconfigure(0, weight=1, minsize=self.lw-20)
        self.leftFrame.rowconfigure(1, weight=1)
        self.leftFrame.grid(row=1, column=0, sticky=tk.N+tk.S+tk.W+tk.E)

        self.rightFrame = tk.Frame(self, padx=10, pady=20)
        self.rightFrame.columnconfigure(0, weight=1)
        self.rightFrame.rowconfigure(2, weight=1)
        self.rightFrame.grid(row=1, column=1, sticky=tk.N+tk.S+tk.W+tk.E)

        self.tostop = tk.IntVar()

        self.__createStatusFrame()
        self.__createMenu()
        self.__createParameters()
        self.__createResults()

    def __createParameters(self):
        paramFrame = tk.LabelFrame(self.rightFrame, text="ПАРАМЕТРЫ")
        paramFrame.configure(labelanchor='n', padx=10, pady=5, relief=tk.GROOVE, borderwidth=3)
        paramFrame.grid(row=0, sticky=tk.W+tk.E+tk.N)

        resultTolFrame = tk.LabelFrame(self.rightFrame, text="ДОПУСКИ")
        resultTolFrame.configure(labelanchor='n', padx=10, pady=5, relief=tk.GROOVE, borderwidth=3)
        resultTolFrame.grid(row=1, sticky=tk.W+tk.E+tk.N)

        self.parvars = dict()

        irow = 0
        for par in self.task.parameters:
            partuple = self.task.get_conv_par_all(par)
            if partuple is None:
                continue

            paramFrame.rowconfigure(irow, pad=10)

            pname, ptype, pvalue, plowlim, puplim, pincr, pavalues, pformat, punit, preadonly = partuple

            tk.Label(paramFrame, text=pname+':').grid(row=irow, column=0, sticky=tk.E)

            parvar = tk.StringVar()
            if ptype is Integral and isinstance(pvalue, Integral):
                dvalue = str(int(pvalue))
            else:
                dvalue = str(pvalue)
            parvar.set(dvalue)

            self.parvars[par] = parvar

            if preadonly:
                entry = tk.Label(paramFrame, textvariable=parvar)
                entry.configure(width=12, font=(MONOSPACE_FONT_FAMILY, BIG_FONT_SIZE),
                                justify=tk.RIGHT, relief=tk.SUNKEN)
            else:
                entry = tk.Spinbox(paramFrame, textvariable=parvar)
                entry.configure(width=12, from_=plowlim, to=puplim, font=(MONOSPACE_FONT_FAMILY, BIG_FONT_SIZE),
                                justify=tk.RIGHT, format='%'+pformat)
                entry.bind('<Button>', self.__scrollPar)
                entry.bind('<Key>', self.__scrollPar)
                if pavalues is not None:
                    entry.configure(values=pavalues)
                else:  # use increment
                    entry.configure(increment=pincr)

            entry.grid(row=irow, column=1, sticky=tk.W, padx=5)

            tk.Label(paramFrame, text=punit).grid(row=irow, column=2, sticky=tk.W)

            irow += 1
        """
        irow = 0
        for res in self.task.results:
            if res not in dtParameterDesc:
                continue

            resultTolFrame.rowconfigure(irow, pad=10)

            name = dtResultDesc[res][dtg.LANG]
            unitname = dtg.units[dtResultDesc[res]['dunit']][dtg.LANG]

            tk.Label(paramFrame, text=name+':').grid(row=irow, column=0, sticky=tk.E)

            parvar = tk.StringVar()
            if ptype is Integral:
                dvalue = str(int(pvalue))
            else:
                dvalue = str(pvalue).replace('.', ',')
            parvar.set(dvalue)

            self.parvars[par] = parvar

            entry = tk.Spinbox(paramFrame, textvariable=parvar)
            entry.configure(width=12, from_=plowlim, to=puplim, font=(MONOSPACE_FONT_FAMILY, BIG_FONT_SIZE),
                            justify=tk.RIGHT, format='%'+pformat)
            self.wpars[str(entry)] = par
            entry.bind('<Button>', self.__scrollPar)
            entry.bind('<Key>', self.__scrollPar)
            if pavalues is not None:
                entry.configure(values=pavalues)
            else:  # use increment
                entry.configure(increment=pincr)

            entry.grid(row=irow, column=1, sticky=tk.W, padx=5)

            tk.Label(paramFrame, text=punit).grid(row=irow, column=2, sticky=tk.W)

            irow += 1
            """

    def __scrollPar(self, event: tk.Event):
        if event.num == 4 or event.keycode == 98:  # up
            event.widget.invoke('buttonup')
        elif event.num == 5 or event.keycode == 104:  # down
            event.widget.invoke('buttondown')

    def __createResults(self):
        resultFrame = tk.LabelFrame(self.leftFrame, text='ИЗМЕРЕНИЕ')
        resultFrame.configure(labelanchor='n', padx=10, pady=5, relief=tk.GROOVE, borderwidth=3)
        resultFrame.grid(row=0, sticky=tk.W+tk.E+tk.N, pady=5)

        self.plotFrame = DTPlotFrame(self.leftFrame, figsize=(6, 4.2))
        self.plotFrame.grid(row=1, sticky=tk.W+tk.E+tk.S)

        self.plotimg = tk.PhotoImage(file=DTApplication().imgdir + '/plot.gif')

        self.reslabels = dict()  # labels with results
        self.plotvars = dict()  # states of checkboxes controlling what vars to plot

        irow = 0
        for res in self.task.results:
            resultFrame.rowconfigure(irow, pad=10)
            if res in dtResultDesc:
                name = dtResultDesc[res][dtg.LANG]
                unitname = dtg.units[dtResultDesc[res]['dunit']][dtg.LANG]

                self.reslabels[res] = reslabel = tk.Label(resultFrame, text='----')
                reslabel.configure(relief=tk.SUNKEN, padx=5, width=10, justify=tk.RIGHT,
                                   font=(MONOSPACE_FONT_FAMILY, BIG_FONT_SIZE))
                reslabel.grid(row=irow, column=1, sticky=tk.W, padx=5)

                tk.Label(resultFrame, text=unitname, justify=tk.LEFT).grid(row=irow, column=2, sticky=tk.W)
            elif res == 'IFFT' or res == 'QFFT':
                name = res
            else:
                continue

            tk.Label(resultFrame, text=name+':', justify=tk.RIGHT).grid(row=irow, column=0, sticky=tk.E)

            self.plotvars[res] = tk.IntVar()

            cb = tk.Checkbutton(resultFrame, image=self.plotimg)
            cb.configure(indicatoron=0, variable=self.plotvars[res],
                         padx=3, pady=3)
            cb.grid(row=irow, column=3, padx=5)

            irow += 1

        self.__resetResHist()

    def __createStatusFrame(self):
        statusFrame = tk.Frame(self.rightFrame, relief=tk.SUNKEN, bd=2, padx=5, pady=3)
        statusFrame.grid(row=1, sticky=tk.W+tk.E+tk.N, pady=5)

        self.message = tk.Message(statusFrame, justify=tk.LEFT, width=self.rw-60)
        self.message.grid(sticky=tk.W+tk.E)
        self.progress = -1

    def __createMenu(self):
        menuFrame = tk.Frame(self.rightFrame)
        menuFrame.grid(row=2, sticky=tk.SE)

        self.startButton = tk.Button(menuFrame, width=20, height=2)
        self.__configStartButton()
        self.startButton.grid(row=0, columnspan=2, sticky=tk.W+tk.E, pady=10)
        self.startButton.focus()

        if self.state is not None:
            # widgets for navigation in the scenario
            navFrame = tk.Frame(menuFrame)
            navFrame.grid(row=1, pady=10, sticky=tk.W+tk.E)
            navFrame.columnconfigure(0, weight=1)
            navFrame.columnconfigure(1, weight=1)
            prevBtn = tk.Button(menuFrame, text='< Пред.', command=self.__goPrev)
            prevBtn.grid(row=1, column=0, sticky=tk.W+tk.E)
            if self.state == 'first':
                prevBtn.configure(state=tk.DISABLED)
            nextBtn = tk.Button(menuFrame, text='След. >', command=self.__goNext)
            nextBtn.grid(row=1, column=1, sticky=tk.W+tk.E)
            if self.state == 'last':
                nextBtn.configure(state=tk.DISABLED)

        tk.Button(menuFrame, text='Главное меню', height=2, command=self.__goMainMenu).\
            grid(row=2, columnspan=2, sticky=tk.W+tk.E, pady=10)

    def __update(self):
        lastResult: DTTask = self.resultBuffer[-1]
        if lastResult.failed:
            self.message.configure(text=lastResult.message, foreground='red')
            return
        elif lastResult.single and lastResult.completed:
            self.message.configure(text='ЗАВЕРШЕНО', foreground='green')
            return
        elif lastResult.completed:
            self.progress += len(self.resultBuffer)
            if lastResult.message:
                self.message.configure(text=lastResult.message, foreground='yellow')
            else:
                self.message.configure(text=f'ИЗМЕРЕНО: {self.progress}', foreground='green')
        elif lastResult.inited:
            self.message.configure(text='ГОТОВ', foreground='green')
            return
        else:
            self.message.configure(text='Неизвестное состояние', foreground='red')
            return

        for res in self.plotvars:
            presult = self.presults[res]
            value = lastResult.get_conv_res(res)
            if presult['type'] == 'time':
                n = presult['n']
                nadd = len(self.resultBuffer)
                if n + nadd > self.resHistSize:
                    n = 0
                for rtask in self.resultBuffer:
                    value = rtask.get_conv_res(res)
                    if value is not None:
                        presult['x'][n] = rtask.time
                        presult['y'][n] = value
                        n += 1
                    presult['n'] = n

            # Prepare for plotting results
            presult['draw'] = draw = self.plotvars[res].get() != 0

            # only FFT data need preparation for plotting, time data are always up-to-date
            if draw and presult['type'] == 'freq':
                presult['y'] = y = lastResult.results[res]
                presult['x'] = rfftfreq((y.size-1)*2, 1./dtg.adcSampleFrequency)
                presult['n'] = y.size

            if res in self.reslabels:
                reslabel: tk.Label = self.reslabels[res]
                value = lastResult.get_conv_res(res)
                if value is not None:
                    fmt = f'%{dtResultDesc[res]["format"]}'
                    if isinstance(self.task, tasks.DTMeasureSensitivity) and res == 'THRESHOLD POWER':
                        if lastResult.results['STATUS'] == -1:  # actual thr. power is lower
                            reslabel.configure(fg='red')
                            fmt = '<' + fmt
                        elif lastResult.results['STATUS'] == 1:  # actual thr. power is higher
                            reslabel.configure(fg='red')
                            fmt = '>' + fmt
                        elif lastResult.results['STATUS'] == 2:  # fluctuations
                            reslabel.configure(fg='red')
                            fmt = '~' + fmt
                        else:
                            reslabel.configure(fg='green')

                    if isinstance(self.task, tasks.DTMeasurePower) and res == 'OUTPOWER':
                        # store calibration of output power to global parameters
                        dtParameterDesc['refoutpower']['default'] = value
                        dtParameterDesc['refatt']['default'] = self.task.parameters['att']

                    reslabel['text'] = fmt % value
                else:
                    reslabel['text'] = '----'

        self.plotFrame.plotGraphs(self.presults)

    def __resetResHist(self):
        self.presults = dict()
        for res in self.plotvars:
            if res[-3:] != 'FFT':  # init time data storage
                self.presults[res] = dict(draw=False,
                                          type='time',
                                          n=0,  # number of points
                                          x=np.zeros(self.resHistSize, dtype='float32'),
                                          y=np.zeros(self.resHistSize, dtype='float32'))
            else:  # stub for FFT data
                self.presults[res] = dict(draw=False, type='freq', n=0, x=None, y=None)

    def __check_process(self):
        if not self.taskProcess.is_alive():  # unexpected stop of DTProcess
            DTApplication().showMessage('Ошибка приложения. Требуется перезапуск.\n' +
                                        self.__class__.__name__ +
                                        'DTProcess is dead, that must not happen while application is running.',
                                        status='error')
            DTApplication().quit()
            return

        if self.tostop.get() == 1:  # stop from the user
            if DTApplication.DEBUG:
                print('DTTaskFrame.__check_process(): User requested stop. Sending stop to DTProcess.')
            self.taskConn.send('stop')  # sending 'stop' to DTProcess
            self.__flushPipe()  # flush pipe input and discard delayed measurements & probably 'stopped' message
            self.__configStartButton()
            return

        self.resultBuffer = list()  # list of last DTTask-s with results
        runstopped = False
        while self.taskConn.poll():  # new task data are available for retrieving
            msg = self.taskConn.recv()  # retrieve task object
            if isinstance(msg, DTTask) and msg.id == self.task.id:
                self.resultBuffer.append(msg)
            elif msg == self.stoppedMsg:  # task run finished
                if DTApplication.DEBUG:
                    print('DTTaskFrame.__check_process(): Task run finished')
                self.__configStartButton()  # return start button to initial state
                runstopped = True
                break

        if len(self.resultBuffer) > 0:
            if DTApplication.DEBUG:
                print(f'DTTaskFrame.__check_process(): Updating frame with task results')
            try:
                self.__update()
            except Exception as exc:
                if DTApplication.DEBUG:
                    print('DTTaskFrame.__check_process(): Exception caught during frame update. Stopping task run.')
                self.taskConn.send('stop')
                self.__flushPipe()
                self.__configStartButton()
                raise exc

        if not runstopped:
            self.after(100, self.__check_process)

    def __runTask(self):
        if DTApplication.DEBUG:
            print('DTTaskFrame.__runTask() entered')
        self.tostop.set(0)
        self.message.configure(text='')
        self.progress = 0
        # clear leftovers in the pipe
        self.__flushPipe()

        self.__resetResHist()
        self.plotFrame.clearCanvas()

        for par in self.parvars:
            self.task.set_conv_par(par, self.parvars[par].get())

        self.task.set_id(self.task.id+1)
        self.stoppedMsg = f'stopped {self.task.id}'
        self.taskConn.send(self.task)

        self.__configStopButton()

        if DTApplication.DEBUG:
            print('DTTaskFrame.__runTask(): Schedule __check_process()')
        self.after(100, self.__check_process())

    def __flushPipe(self):
        fd = self.taskConn.fileno()
        if DTApplication.DEBUG:
            print(f'DTTaskFrame.__flushPipe(): flushing read buffer of fd {fd}')
        FileIO(fd, 'r', closefd=False).flush()

    def __configStartButton(self):
        self.startButton.configure(text='Запуск', command=self.__runTask, bg='#21903A', activebackground='#3CA54D')

    def __configStopButton(self):
        self.startButton.configure(text='Остановить', command=self.__stopTask, bg='#A50D00', activebackground='#C63519')

    def __stopTask(self):
        if DTApplication.DEBUG:
            print('DTTaskFrame.__stopTask(): Stop button is pressed')
        self.tostop.set(1)

    def __goPrev(self):
        if DTApplication.DEBUG:
            print('DTTaskFrame.__goPrev(): Signalling task stop')
        self.direction = -1
        self.taskConn.send('stop')  # sending 'stop' to DTProcess
        self.__flushPipe()  # flush pipe input and discard delayed measurements & probably 'stopped' message
        self.frameFinished.set(1)

    def __goNext(self):
        if DTApplication.DEBUG:
            print('DTTaskFrame.__goNext(): Signalling task stop')
        self.direction = 1
        self.taskConn.send('stop')  # sending 'stop' to DTProcess
        self.__flushPipe()  # flush pipe input and discard delayed measurements & probably 'stopped' message
        self.frameFinished.set(1)

    def __goMainMenu(self):
        if DTApplication.DEBUG:
            print('DTTaskFrame.__goMainMenu(): Signalling task stop')
        self.direction = 0
        self.taskConn.send('stop')  # sending 'stop' to DTProcess
        self.__flushPipe()  # flush pipe input and discard delayed measurements & probably 'stopped' message
        self.frameFinished.set(1)

    def destroy(self):
        if DTApplication.DEBUG:
            print('DTTaskFrame.destroy(): called')
        super().destroy()
