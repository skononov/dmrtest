from numbers import Number, Real, Integral
from os import access, R_OK
import numpy as np
from math import pi
from numpy.core.fromnumeric import var
from scipy.fft import rfftfreq
import matplotlib as mpl
import matplotlib.pyplot as plt
from time import perf_counter
import tkinter as tk
from tkinter import TclError, ttk
# import tkinter.messagebox as tkmsg

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from threading import Thread, Event

from dtexcept import DTInternalError
from config import DTConfiguration, __appname__, __version__
from tasks import DTScenario, DTTask, dtTaskInit, dtResultDesc, dtParameterDesc
import tasks
from singleton import Singleton
import dtglobals as dtg


mpl.rcParams["figure.facecolor"] = '#1F1F1F'
mpl.rcParams["figure.dpi"] = 100
mpl.rcParams["lines.linewidth"] = 2.0
mpl.rcParams["grid.linewidth"] = 0.5
mpl.rcParams["axes.linewidth"] = 1.0
mpl.rcParams["font.size"] = 12

_rootWindowWidth = 1024
_rootWindowHeight = 700

DARK_BG_COLOR = '#0F0F0F'
DEFAULT_BG_COLOR = '#1F1F1F'
LIGHT_BG_COLOR = '#2E2E2E'
HIGHLIGHTED_BG_COLOR = '#4F4F4F'
SELECT_BG_COLOR = '#274F77'
BUTTON_BG_COLOR = '#505050'
DEFAULT_FG_COLOR = 'white'

DEFAULT_FONT_FAMILY = "Helvetica"
MONOSPACE_FONT_FAMILY = "lucidasanstypewriter"
BIG_FONT_SIZE = '14'
DEFAULT_FONT_SIZE = '12'
SMALL_FONT_SIZE = '10'


class DTApplication(tk.Tk, metaclass=Singleton):
    __dtTkOptionFilename = '~/.dtstyle'

    def __init__(self):
        super().__init__()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        if sw/sh > 2:
            sw //= 2
        geometry = f'{_rootWindowWidth}x{_rootWindowHeight}{(sw-_rootWindowWidth)//2:+d}{(sh-_rootWindowHeight)//2:+d}'
        self.geometry(geometry)
        self.title(__appname__ + ' ' + __version__)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        if access('img/logo.gif', R_OK):
            self.logo = tk.PhotoImage(file='img/logo.gif')
        else:
            self.logo = None

        self.wm_iconphoto(True, self.logo)

        # init task handlers
        dtTaskInit()

        # set styles
        self.defaultStyle()
        if access(DTApplication.__dtTkOptionFilename, R_OK):
            self.readStyle(DTApplication.__dtTkOptionFilename)

        plt.style.use('dark_background')

        self.mainMenuFrame = DTMainMenuFrame(self)
        self.mainMenuFrame.grid(sticky=tk.W+tk.E+tk.N+tk.S)

    def render(self, frame: tk.Frame):
        try:
            if frame.winfo_ismapped() or frame.master is not self:
                return
            for child in self.winfo_children():
                if not isinstance(child, tk.Toplevel):
                    child.grid_forget()
        except tk.TclError:
            pass
        frame.grid(sticky=tk.W+tk.E+tk.N+tk.S)

    def readStyle(self, filename: str):
        self.option_clear()
        try:
            self.option_readfile(filename)
        except tk.TclError:
            print(f'DTApplication.readStyle(): Can not read Tk option file {filename}')

    def defaultStyle(self):
        self.option_clear()
        self.option_add('*DTApplication.background', LIGHT_BG_COLOR)
        self.option_add('*background', DEFAULT_BG_COLOR)
        self.option_add('*Entry.background', DARK_BG_COLOR)
        self.option_add('*Listbox.background', DARK_BG_COLOR)
        self.option_add('*Button.background', BUTTON_BG_COLOR)
        self.option_add('*Menubutton.background', BUTTON_BG_COLOR)
        self.option_add('*foreground', DEFAULT_FG_COLOR)
        self.option_add('*font', f'{DEFAULT_FONT_FAMILY} {DEFAULT_FONT_SIZE}')
        self.option_add('*Entry.font', f'{MONOSPACE_FONT_FAMILY} {DEFAULT_FONT_SIZE}')

        #self.option_add('*DTLogoFrame.background', DEFAULT_BG_COLOR)
        #self.option_add('*DTMainMenuFrame.background', DEFAULT_BG_COLOR)
        #self.option_add('*DTLogoFrame.background', DEFAULT_BG_COLOR)
        #self.option_add('*DTMainMenuFrame.background', DEFAULT_BG_COLOR)
        #self.option_add('*DTPlotFrame.background', DEFAULT_BG_COLOR)
        #self.option_add('*Label.background', DEFAULT_BG_COLOR)
        #self.option_add('*Menubutton.background', BUTTON_BG_COLOR)
        #self.option_add('*Menu.background', _lightBG)
        #self.option_add('*Button.activebackground', HIGHLIGHTED_BG_COLOR)
        #self.option_add('*Menubutton.activebackground', HIGHLIGHTED_BG_COLOR)
        #self.option_add('*Menu.activebackground', HIGHLIGHTED_BG_COLOR)
        #self.option_add('*Label.foreground', DEFAULT_FG_COLOR)
        #self.option_add('*Button.foreground', DEFAULT_FG_COLOR)
        #self.option_add('*Menubutton.foreground', DEFAULT_FG_COLOR)

    def run(self):
        self.mainloop()

    def stop(self):
        self.destroy()

    def showMessage(self, message: str, master=None, delay=0, status='default'):
        w = tk.Toplevel(padx=20, pady=10)
        if master is None:
            master = self
        w.transient(master)
        x0, y0 = master.winfo_rootx(), master.winfo_rooty()
        w.geometry(f'{x0+100:+d}{y0:+d}')
        if status in ('info', 'error', 'warning'):
            tk.Label(w, bitmap=status).grid(column=0, row=0, sticky=tk.W, padx=10)
        tk.Message(w, text=message, justify=tk.LEFT, width=250).grid(row=0, column=1, sticky=tk.W+tk.E)
        if delay == 0:
            tk.Button(w, text='ОК', command=w.destroy, padx=20, pady=5)\
                .grid(row=1, column=0, columnspan=2, sticky=tk.S, pady=10)
        else:
            self.after(int(delay*1000), w.destroy)


class DTChooseObjectMenu(tk.Menu):

    def __init__(self, menubutton, command, objects):
        super().__init__(menubutton, tearoff=0, postcommand=self.composeMenu)
        self.command = command
        if objects is None:
            raise DTInternalError(self.__class__.__name__, 'objects must not be None')
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
            raise DTInternalError(self.__class__.__name__, f'Called for invalid type {type(self.objects)}')

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
                raise DTInternalError(self.__class__.__name__, f'No name defined for the object of type {type(obj)}')
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
    def __init__(self, master):
        super().__init__(master, class_='DTPlotFrame')
        self.figure = None
        self.gridOn = True
        self.createCanvas()

    def createCanvas(self):
        if self.figure is not None:
            del self.figure
        self.figure = Figure(figsize=(5, 5))
        self.figure.add_subplot(111)
        canvas = FigureCanvasTkAgg(self.figure, master=self)
        canvas.draw()
        canvas.get_tk_widget().grid()

        # example plot
        x = np.arange(-4*pi, 4*pi, 0.1)
        y = np.sin(x)/x
        self.plotGraph(x, y)

    def plotGraph(self, x, y, new=True, labelx=None, labely=None):
        self.axes = self.figure.axes
        if new or self.axes is None:
            self.figure.clf()
            self.axes = self.figure.add_subplot(111)
        self.hlines, = self.axes.plot(x, y, 'w')
        if labelx:
            self.axes.set_xlabel(labelx)
        if labely:
            self.axes.set_ylabel(labely)
        self.axes.grid(self.gridOn, 'major')

    def updateGraph(self, x, y):
        if hasattr(self, 'hlines'):
            self.hlines.set_xdata(x)
            self.hlines.set_ydata(y)
            self.axes.redraw_in_frame()

    def clearCanvas(self):
        self.figure.clf()


class DTMainMenuFrame(tk.Frame, metaclass=Singleton):

    def __init__(self, master):
        super().__init__(master, class_='DTMainMenuWindow')
        self.configure(padx=10, pady=10)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=1)

        self.__createLogoFrame()
        self.logoFrame.grid(column=0, row=0, sticky=tk.W+tk.E+tk.N+tk.S)

        self.__createMenuFrame()
        self.menuFrame.grid(column=1, row=0, sticky=tk.N+tk.S)

    def runScenario(self, scenario: DTScenario):
        if len(scenario) == 0:
            raise DTInternalError('DTMainMenuFrame.runScenario()', f'Empty scenario {scenario.name}.')

        index = 0
        while True:
            state = 'midthrough'
            if index == 0:
                state = 'first'
            elif index == len(scenario)-1:
                state = 'last'
            taskFrame = DTTaskFrame(self.master, scenario[index], state=state)
            self.master.render(taskFrame)
            self.wait_window(taskFrame)
            if taskFrame.direction == 0:
                break
            elif taskFrame.direction == -1 and index > 0:
                index -= 1
                continue
            index += 1
            if index == len(scenario):
                break
        del taskFrame
        self.master.render(self)

    def newScenario(self):
        dialog = DTNewScenarioDialog(self.master)
        self.wait_window(dialog)
        nscenarios = len(tasks.dtAllScenarios)
        if nscenarios > 0:
            self.runScenarioMB['state'] = tk.NORMAL
            self.scenariosText.set(f'{nscenarios} сценариев определено')

    def chooseTask(self, taskType: type):
        task = taskType()
        taskFrame = DTTaskFrame(self.master, task)
        self.master.render(taskFrame)
        self.wait_window(taskFrame)
        del taskFrame
        self.master.render(self)

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
        ##rightScrollbar = tk.Scrollbar(textboxFrame, orient=tk.VERTICAL, command=textbox.yview)
        ##textbox.configure(yscrollcommand = rightScrollbar.set)
        ##rightScrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        textbox.grid(row=1, sticky=tk.W+tk.E+tk.N+tk.S)
        textbox.insert(tk.END, text, "normal")
        textbox.configure(state=tk.DISABLED)

    def __createMenuFrame(self):
        self.menuFrame = tk.Frame(self, padx=10, pady=10)

        for i in range(1, 5):
            self.menuFrame.rowconfigure(i, pad=20)
        self.menuFrame.rowconfigure(4, weight=1)

        self.scenariosText = tk.StringVar()
        self.scenariosText.set(f'{len(tasks.dtAllScenarios)} сценариев определено')
        self.scenariosText.set(f'{len(tasks.dtAllScenarios)} сценариев определено')
        tk.Label(self.menuFrame, textvariable=self.scenariosText).grid(row=0)

        csmb = self.runScenarioMB = tk.Menubutton(self.menuFrame, text='Запустить сценарий', takefocus=True)
        csmb.configure(relief=tk.RAISED, height=2)
        if len(tasks.dtAllScenarios) == 0:
            csmb['state'] = tk.DISABLED
        csmb.grid(row=1, sticky=tk.W+tk.E)
        csmb['menu'] = csmb.menu = DTChooseObjectMenu(csmb, command=self.runScenario,
                                                      objects=tasks.dtAllScenarios)

        cmmb = tk.Menubutton(self.menuFrame, text='Выбрать измерение', takefocus=True)
        cmmb.configure(relief=tk.RAISED, height=2)
        cmmb['menu'] = cmmb.menu = DTChooseObjectMenu(cmmb, command=self.chooseTask,
                                                      objects=tasks.dtTaskTypes)
        cmmb.grid(row=2, sticky=tk.W+tk.E)

        csb = tk.Button(self.menuFrame, text='Создать сценарий', command=self.newScenario, height=2)
        csb.grid(row=3, sticky=tk.W+tk.E)
        csb.focus()

        quitb = tk.Button(self.menuFrame, text='Выход', command=self.quit, height=2)
        quitb.grid(row=4, sticky=tk.W+tk.E+tk.S)


class DTNewScenarioDialog(tk.Toplevel):

    def __init__(self, master=None):
        super().__init__(master)
        x0, y0 = master.winfo_rootx(), master.winfo_rooty()
        self.geometry(f'{x0+200:+d}{y0:+d}')
        self.title('Создать сценарий')
        self.configure(padx=10, pady=10)

        for irow in range(4):
            self.rowconfigure(irow, pad=10)
        self.columnconfigure(0, pad=20)
        self.columnconfigure(1, pad=10)
        self.columnconfigure(2, pad=0)

        tk.Label(self, text='Название:').grid(column=0, row=0, sticky=tk.E, padx=10, pady=5)

        self.nameVar = tk.StringVar()
        self.nameVar.set(self.__newName())
        nameEntry = tk.Entry(self, textvariable=self.nameVar, width=38)
        nameEntry.grid(column=1, row=0, sticky=tk.N+tk.S, pady=5)
        nameEntry.focus()

        tk.Label(self, text='Задачи:').grid(column=0, row=1, sticky=tk.NE, padx=10, pady=5)

        self.yTaskScroll = tk.Scrollbar(self, orient=tk.VERTICAL)
        self.yTaskScroll.grid(column=2, row=1, sticky=tk.N+tk.S+tk.W)
        self.taskListVar = tk.StringVar()
        self.taskListbox = tk.Listbox(self, height=10, width=38, selectmode=tk.SINGLE, listvariable=self.taskListVar)
        self.taskListbox['yscrollcommand'] = self.yTaskScroll.set
        self.yTaskScroll['command'] = self.taskListbox.yview
        self.taskListbox.grid(column=1, row=1, sticky=tk.N+tk.S, pady=5)
        self.taskListbox.bind('<Key-Delete>', self.__deleteTask)

        menubtn = tk.Menubutton(self, text='Добавить', relief=tk.RAISED, takefocus=True, width=30)
        menubtn['menu'] = menubtn.menu = DTChooseObjectMenu(menubtn, command=self.__addTask, objects=tasks.dtTaskTypes)
        menubtn.grid(column=1, row=2, sticky=tk.N, pady=5)

        tk.Button(self, text='Создать сценарий', command=self.__create).grid(column=1, row=3, sticky=tk.E)

        tk.Button(self, text='Отмена', command=self.destroy).grid(column=0, row=3, sticky=tk.W)

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
        DTApplication().showMessage(f'"{name}" создан', delay=2)

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


class DTThread(Thread):
    def __init__(self, task: DTTask, timeout=0.1):
        super().__init__()
        self.task = task
        self.timeout = timeout
        self.__updated = Event()
        self.__tostop = Event()

    def run(self):
        self.__updated.clear()
        self.__tostop.clear()

        self.task.init_meas()
        self.__updated.set()
        if self.task.failed or self.task.completed:
            #print('Thread is about to stop after init')
            return

        while not self.__tostop.is_set():
            self.task.measure()
            self.__updated.set()
            if self.task.failed:
                break

        #print('Thread is about to stop')

    def inc_wait_update(self):
        return self.__updated.wait(self.timeout)

    def is_updated(self):
        return self.__updated.is_set()

    def clear_updated(self):
        return self.__updated.clear()

    def signal_stop(self):
        #print('Thread stop signalled')
        self.__tostop.set()


class DTTaskFrame(tk.Frame):
    def __init__(self, master, task: DTTask, state=None):
        """ Constructor for a task front-end.
            state - can have values: None, 'first' (first in scenario), 'last' (last in scenario), 'midthrough'.
        """
        super().__init__(master, class_='DTTaskFrame')
        self.task = task
        self.state = state
        self.direction = None
        self.resHistSize = 10000

        self.__createWidgets()

    def __createWidgets(self):
        self.lw = int(0.6*_rootWindowWidth)
        self.rw = _rootWindowWidth-self.lw
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1, minsize=self.lw)
        self.columnconfigure(1, weight=1, minsize=self.rw)

        tk.Label(self, text=self.task.name[dtg.LANG], height=2, relief=tk.GROOVE, bg=LIGHT_BG_COLOR, borderwidth=3)\
            .grid(row=0, column=0, columnspan=2, pady=5, sticky=tk.W+tk.E+tk.N)

        self.leftFrame = tk.Frame(self, padx=10, pady=20)
        self.leftFrame.columnconfigure(0, weight=1, minsize=self.lw-20)
        self.leftFrame.rowconfigure(1, weight=1)
        self.leftFrame.grid(row=1, column=0, sticky=tk.N+tk.S+tk.W+tk.E)

        self.rightFrame = tk.Frame(self, padx=10, pady=20)
        self.rightFrame.columnconfigure(0, weight=1, minsize=self.rw-20)
        self.rightFrame.rowconfigure(2, weight=1)
        self.rightFrame.grid(row=1, column=1, sticky=tk.N+tk.S+tk.W+tk.E)

        self.tostop = tk.IntVar()
        self.stopped = tk.IntVar()

        self.__createStatusFrame()
        self.__createMenu()
        self.__createParameters()
        self.__createResults()

    def __validateParameter(self, where, what):
        print('Validating:', where, what)
        if where in self.wpars:
            return tasks.DTTask.check_parameter(self.wpars[where], what)
        return False

    def __createParameters(self):
        self.paramFrame = tk.LabelFrame(self.rightFrame, text="ПАРАМЕТРЫ")
        self.paramFrame.configure(labelanchor='n', padx=10, pady=5, relief=tk.GROOVE, borderwidth=3)
        self.paramFrame.grid(row=0, sticky=tk.W+tk.E+tk.N)

        self.parvars = dict()
        self.wpars = dict()
        self.valProc = self.register(self.__validateParameter)

        sbstyle = ttk.Style()
        sbstyle.configure('DT.TSpinbox', background=LIGHT_BG_COLOR, foreground=DEFAULT_FG_COLOR)
        sbstyle.map('DT.TSpinbox', fieldbackground=[('focus', DARK_BG_COLOR), ('!disabled', DEFAULT_BG_COLOR)])

        irow = 0
        for par, value in self.task.parameters.items():
            if par not in dtParameterDesc:
                continue
            self.paramFrame.rowconfigure(irow, pad=10)
            pardesc = dtParameterDesc[par]
            tk.Label(self.paramFrame, text=pardesc[dtg.LANG]+':').grid(row=irow, column=0, sticky=tk.E)

            if pardesc['type'] is Real:
                self.parvars[par] = tk.DoubleVar()
            elif pardesc['type'] is Integral:
                self.parvars[par] = tk.IntVar()
            else:
                self.parvars[par] = tk.StringVar()

            mult = dtg.units[pardesc['dunit']]['multiple']
            dvalue = value / mult
            dlowlim = pardesc['lowlim'] / mult
            duplim = pardesc['uplim'] / mult
            self.parvars[par].set(dvalue)

            # entry = tk.Entry(self.paramFrame, textvariable=self.parvars[par], width=10,
            #                 validate='key', validatecommand=(self.valProc, '%W', '%P'),
            #                 justify=tk.RIGHT)

            entry = ttk.Spinbox(self.paramFrame, textvariable=self.parvars[par])
            entry.set(dvalue)
            entry.configure(width=12, from_=dlowlim, to=duplim,
                            justify=tk.RIGHT, format='%'+pardesc['format'], style='DT.TSpinbox')
            if 'values' in pardesc:
                entry.configure(values=pardesc['values'])
            else:  # use increment
                entry.configure(increment=pardesc['increment'] / mult)

            self.wpars[str(entry)] = par
            entry.grid(row=irow, column=1, sticky=tk.W, padx=5)

            unit = dtg.units[pardesc['dunit']][dtg.LANG]
            tk.Label(self.paramFrame, text=unit).grid(row=irow, column=2, sticky=tk.W)

            irow += 1

    def __createResults(self):
        self.resultFrame = tk.LabelFrame(self.leftFrame, text='ИЗМЕРЕНИЕ')
        self.resultFrame.configure(labelanchor='n', padx=10, pady=5, relief=tk.GROOVE, borderwidth=3)
        self.resultFrame.grid(row=0, sticky=tk.W+tk.E+tk.N, pady=5)

        if not self.task.single:
            self.plotFrame = DTPlotFrame(self.leftFrame)
            self.plotFrame.grid(row=1, sticky=tk.S)

        self.resvars = dict()
        self.resplotvar = tk.StringVar()
        self.resvalues = dict()

        irow = 0
        for res in self.task.results:
            self.resultFrame.rowconfigure(irow, pad=10)
            if res in dtResultDesc:
                name = dtResultDesc[res][dtg.LANG]
                unit = dtg.units[dtResultDesc[res]['dunit']]
                unitname = unit[dtg.LANG]

                self.resvars[res] = tk.StringVar()
                reslabel = tk.Label(self.resultFrame, textvariable=self.resvars[res])
                reslabel.configure(relief=tk.SUNKEN, font=(MONOSPACE_FONT_FAMILY, DEFAULT_FONT_SIZE, 'bold'),
                                   padx=5, width=10, justify=tk.RIGHT)
                reslabel.grid(row=irow, column=1, sticky=tk.W, padx=5)

                if unitname != '':
                    tk.Label(self.resultFrame, text=unitname, justify=tk.LEFT).grid(row=irow, column=2, sticky=tk.W)
                colspan = 1
            elif res == 'IFFT' or res == 'QFFT':
                name = res
                colspan = 3
            else:
                continue

            tk.Label(self.resultFrame, text=name+':', justify=tk.RIGHT).grid(row=irow, column=0, columnspan=colspan, sticky=tk.E)

            rb = tk.Radiobutton(self.resultFrame, text='Рисовать')
            rb.configure(indicatoron=0, value=res, variable=self.resplotvar, command=self.___plotResult,
                         activeforeground=DEFAULT_FG_COLOR, fg=rb['bg'])
            rb.grid(row=irow, column=3, padx=5)

            self.resvalues[res] = None

            irow += 1

        self.__resetResHist()
        self.__update()

    def __createStatusFrame(self):
        self.statusFrame = tk.Frame(self.rightFrame, padx=5, pady=5, relief=tk.GROOVE, borderwidth=3)
        self.statusFrame.grid(row=1, sticky=tk.W+tk.E+tk.N, pady=5)

        # progressStyle = ttk.Style()
        # progressStyle.configure('DT.Horizontal.TProgressbar', background='green')
        # self.progressBar = ttk.Progressbar(self.statusFrame)
        # self.progressBar.configure(length=self.rw-40, mode='indeterminate', orient=tk.HORIZONTAL,
        #                            style='DT.Horizontal.TProgressbar')

        self.message = tk.Message(self.statusFrame, justify=tk.LEFT, width=self.rw-40)
        self.message.grid()
        self.maxProgressLen = int((self.rw-40)/16)
        self.progress = -1

    def __createMenu(self):
        self.menuFrame = tk.Frame(self.rightFrame)
        self.menuFrame.grid(row=2, sticky=tk.SE)

        self.startButton = tk.Button(self.menuFrame, width=20)
        self.__stopTask()  # configures actual text, color and command
        self.startButton.grid(row=0, columnspan=2, sticky=tk.W+tk.E, pady=10)
        self.startButton.focus()

        if self.state is not None:
            navFrame = tk.Frame(self.menuFrame)
            navFrame.grid(row=1, pady=10, sticky=tk.W+tk.E)
            navFrame.columnconfigure(0, weight=1)
            navFrame.columnconfigure(1, weight=1)
            prevBtn = tk.Button(self.menuFrame, text='< Пред.', command=self.__goPrev)
            prevBtn.grid(row=1, column=0, sticky=tk.W+tk.E)
            if self.state == 'first':
                prevBtn.configure(state=tk.DISABLED)
            nextBtn = tk.Button(self.menuFrame, text='След. >', command=self.__goNext)
            nextBtn.grid(row=1, column=1, sticky=tk.W+tk.E)
            if self.state == 'last':
                nextBtn.configure(state=tk.DISABLED)

        tk.Button(self.menuFrame, text='Главное меню', command=self.__goMainMenu).\
            grid(row=2, columnspan=2, sticky=tk.W+tk.E, pady=10)

    def __update(self):
        if self.task.failed and self.task.message != '':
            self.message.configure(text=self.task.message, foreground='red')
            return
        elif self.task.single and self.task.completed:
            self.message.configure(text='ЗАВЕРШЕНО', foreground='green')
        else:
            self.message.configure(foreground='green')
            self.__stepProgress()

        if self.startTime == 0.:
            self.startTime = perf_counter()

        self.times[self.npoints] = perf_counter() - self.startTime
        for res, value in self.task.results.items():
            if res not in self.resvars:
                continue

            if value is not None:
                value /= dtg.units[dtResultDesc[res]['dunit']]['multiple']
                self.resvars[res].set(f'%{dtResultDesc[res]["format"]}' % value)
                self.resvalues[res][self.npoints] = value
            else:
                self.resvars[res].set('----')

        self.___plotResult()

    def __resetResHist(self):
        self.npoints = 0
        self.startTime = 0.
        self.times = np.zeros(self.resHistSize, dtype='float32')
        for res in self.task.results:
            if res not in dtResultDesc:
                continue
            self.resvalues[res] = np.zeros(self.resHistSize, dtype='float32')

    def ___plotResult(self, update=False):
        if self.npoints == 0:
            return
        res = self.resplotvar.get()
        if res[-3:] != 'FFT':
            x = self.times[:self.npoints]
            y = self.resvalues[res][:self.npoints]
            self.plotFrame.plotGraph(x, y, new=True, labelx=('Время, с' if dtg.LANG == 'ru' else 'Time, s'),
                                     labely=dtResultDesc[res][dtg.LANG])
        else:
            y = self.task.results[res]
            x = rfftfreq(y.size, 1/dtg.adcSampleFrequency)
            self.plotFrame.plotGraph(x, y, new=True,
                                     labelx=('Частота, Гц' if dtg.LANG == 'ru' else 'Frequency, Hz'),
                                     labely=('Амплитуда' if dtg.LANG == 'ru' else 'Amplitude'))

    def __stepProgress(self):
        self.progress = (self.progress+1) % self.maxProgressLen
        self.message['text'] = '\u2588' * self.progress

    def __runTask(self):
        self.startButton.configure(text='Остановить', command=self.__stopTask, bg='#A10D0D')

        self.progress = 0
        self.__resetResHist()
        for par in self.parvars:
            value = self.parvars[par].get() * dtg.units[dtParameterDesc[par]['dunit']]['multiple']
            self.task.parameters[par] = value

        self.thread = DTThread(self.task, timeout=0.1)

        self.thread.start()

        self.tostop.set(0)
        while self.tostop.get() == 0 and self.thread.is_alive():
            #print("Update cycle 1")
            while not self.thread.inc_wait_update() and self.thread.is_alive() and self.tostop.get() == 0:
                #print("  Update cycle 2")
                self.update()
            try:
                self.__update()
            except TclError:
                break
            self.thread.clear_updated()

        self.__stopTask()
        self.__finishTask()

    def __finishTask(self):
        if hasattr(self, 'thread') and self.thread.is_alive():
            #print('Await task stop')
            self.thread.signal_stop()
            self.thread.join()

    def __stopTask(self):
        self.tostop.set(1)
        try:
            self.startButton.configure(text='Запуск', command=self.__runTask, bg='#21903A')
        except TclError:
            pass

    def __goPrev(self):
        self.direction = -1
        self.__finishTask()
        self.destroy()

    def __goNext(self):
        self.direction = 1
        self.__finishTask()
        self.destroy()

    def __goMainMenu(self):
        self.direction = 0
        self.__finishTask()
        self.destroy()
