from numbers import Number, Real, Integral
from os import access, R_OK
import numpy as np
from math import pi
from numpy.core.defchararray import _just_dispatcher
from numpy.lib.arraysetops import isin
from scipy.fft import rfftfreq
import matplotlib as mpl
import matplotlib.pyplot as plt
import tkinter as tk
import tkinter.messagebox as tkmsg

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

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
_rootWindowHeight = 800

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
        if frame.winfo_ismapped() or frame.master is not self:
            return
        for child in self.winfo_children():
            if not isinstance(child, tk.Toplevel):
                child.grid_forget()
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
        self.option_add('*Text.background', DEFAULT_BG_COLOR)
        self.option_add('*Entry.background', DARK_BG_COLOR)
        self.option_add('*Listbox.background', LIGHT_BG_COLOR)
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
                                     value=name, variable=self.optVar, command=self.select)
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
                                     value=index, variable=self.optVar, command=self.select)

    def select(self):
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
        ax = self.figure.axes
        if new or ax is None:
            self.figure.clf()
            ax = self.figure.add_subplot(111)
        ax.plot(x, y, 'w')
        if labelx:
            ax.set_xlabel(labelx)
        if labely:
            ax.set_ylabel(labely)
        ax.grid(self.gridOn, 'major')

    def clearCanvas(self):
        self.figure.clf()


class DTMainMenuFrame(tk.Frame, metaclass=Singleton):

    def __init__(self, master):
        super().__init__(master, class_='DTMainMenuWindow')
        self.configure(padx=10, pady=10)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=1)

        self.createLogoFrame()
        self.logoFrame.grid(column=0, row=0, sticky=tk.W+tk.E+tk.N+tk.S)

        self.createMenuFrame()
        self.menuFrame.grid(column=1, row=0, sticky=tk.N+tk.S)

    def runScenario(self, scenario: DTScenario):
        for task in scenario:
            taskFrame = DTTaskFrame(self.master, task, inscenario=True)
            self.master.render(taskFrame)
            self.wait_window(taskFrame)
            if taskFrame.gotoMainMenu:
                del taskFrame
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

    def createLogoFrame(self):
        self.logoFrame = tk.Frame(self, padx=10, pady=10, relief=tk.GROOVE)
        self.logoFrame.columnconfigure(0, weight=1)
        self.logoFrame.rowconfigure(0, weight=1)
        self.logoFrame.rowconfigure(1, weight=1)

        tk.Label(self.logoFrame, image=self.master.logo, padx=5, pady=5).grid(row=0, sticky=tk.N)

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

    def createMenuFrame(self):
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


class DTTaskFrame(tk.Frame):
    def __init__(self, master, task: DTTask, inscenario=False):
        super().__init__(master, class_='DTTaskFrame')
        self.task = task
        self.inscenario = inscenario
        self.gotoMainMenu = False

        self.createWidgets()

    def createWidgets(self):
        self.configure(padx=20, pady=20)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1, minsize=550)
        self.columnconfigure(0, weight=1, minsize=550)
        self.columnconfigure(1, weight=1, minsize=300)

        self.titleLabel = tk.Label(self, text=self.task.name[dtg.LANG])
        self.titleLabel.configure(relief=tk.GROOVE, bd=3, height=2)
        self.titleLabel.grid(row=0, columnspan=2, sticky=tk.W+tk.E+tk.N)

        self.__createParameters()
        self.__createResults()
        self.__createMenu()

    def __validateParameter(self, where, what):
        print('Validating:', where, what)
        if where in self.wpars:
            return tasks.DTTask.check_parameter(self.wpars[where], what)
        return False

    def __createMenu(self):
        self.menuFrame = tk.Frame(self)
        self.menuFrame.grid(row=2, column=1, sticky=tk.SE)

        self.startButton = tk.Button(self.menuFrame, text='Начать', command=self.runTask)
        self.startButton.configure(bg='#21903A', width=20)
        self.startButton.grid(row=0, column=0, sticky=tk.E, pady=10)

        if self.inscenario:
            tk.Button(self.menuFrame, text='Следующее измерение', command=self.destroy, width=20).\
                grid(row=1, column=0, sticky=tk.E, pady=10)

        tk.Button(self.menuFrame, text='Главное меню', command=self.mainMenu, width=20).\
            grid(row=2, column=0, sticky=tk.E, pady=10)

    def __createParameters(self):
        self.paramFrame = tk.LabelFrame(self, text="ПАРАМЕТРЫ")
        self.paramFrame.configure(labelanchor='n', padx=10, pady=5, relief=tk.GROOVE)
        self.paramFrame.grid(row=1, column=1, sticky=tk.NE)

        self.parvars = dict()
        self.wpars = dict()
        valProc = self.register(self.__validateParameter)

        irow = 0
        for par, value in self.task.parameters.items():
            if par not in dtParameterDesc:
                continue
            self.paramFrame.rowconfigure(irow, pad=10)
            partype = dtParameterDesc[par]['type']
            tk.Label(self.paramFrame, text=dtParameterDesc[par][dtg.LANG]+':')\
                .grid(row=irow, column=0, sticky=tk.E)

            if partype is Real:
                self.parvars[par] = tk.DoubleVar()
            elif dtParameterDesc[par]['type'] is Integral:
                self.parvars[par] = tk.IntVar()
            else:
                self.parvars[par] = tk.StringVar()
            self.parvars[par].set(value)

            entry = tk.Entry(self.paramFrame, textvariable=self.parvars[par], width=10,
                             validate='all', validatecommand=(valProc, '%W', '%P'), justify=tk.RIGHT)
            self.wpars[str(entry)] = par
            entry.grid(row=irow, column=1, sticky=tk.W, padx=5)

            unit = dtg.units[dtParameterDesc[par]['dunit']][dtg.LANG]
            tk.Label(self.paramFrame, text=unit).grid(row=irow, column=2, sticky=tk.W)

            irow += 1

    def __createResults(self):
        self.resultFrame = tk.LabelFrame(self, text="РЕЗУЛЬТАТЫ")
        self.resultFrame.configure(labelanchor='n', padx=10, pady=5, relief=tk.GROOVE)
        self.resultFrame.grid(row=1, column=0, sticky=tk.W+tk.E+tk.N)

        if isinstance(self.task, tasks.DTMeasureCarrierFrequency) or\
           isinstance(self.task, tasks.DTMeasureNonlinearity) or\
           isinstance(self.task, tasks.DTMeasureSensitivity):
            self.plotFrame = DTPlotFrame(self)
            self.plotFrame.grid(row=2, column=0, sticky=tk.W+tk.E+tk.S)

        self.resvars = dict()

        irow = 0
        for res, value in self.task.results.items():
            self.resultFrame.rowconfigure(irow, pad=10)
            if res not in dtResultDesc or not (isinstance(value, Number) or value is None):
                continue
            name = dtResultDesc[res][dtg.LANG]
            unit = dtg.units[dtResultDesc[res]['dunit']]
            unitname = unit[dtg.LANG]

            tk.Label(self.resultFrame, text=name+':', justify=tk.RIGHT).grid(row=irow, column=0, sticky=tk.E)

            self.resvars[res] = tk.StringVar()
            reslabel = tk.Label(self.resultFrame, textvariable=self.resvars[res])
            reslabel.configure(relief=tk.SUNKEN, font=(MONOSPACE_FONT_FAMILY, DEFAULT_FONT_SIZE),
                               padx=5, width=10, justify=tk.RIGHT)
            reslabel.grid(row=irow, column=1, sticky=tk.W, padx=5)

            if unitname != '':
                tk.Label(self.resultFrame, text=unitname, justify=tk.LEFT).grid(row=irow, column=2, sticky=tk.W)

            irow += 1

        self.resultRows = irow
        self.message = tk.Message(self.resultFrame, justify=tk.LEFT, width=400)
        self.stopped = tk.IntVar()

        self.update()

    def update(self):
        if self.task.failed and self.task.message != '':
            self.message['text'] = self.task.message
            self.message.grid(row=self.resultRows, columnspan=3)
            return
        else:
            self.message.grid_forget()

        for res, value in self.task.results.items():
            if res not in self.resvars:
                continue

            if value is not None:
                value /= dtg.units[dtResultDesc[res]['dunit']]['multiple']
                self.resvars[res].set(f'%{dtResultDesc[res]["format"]}' % value)
            else:
                self.resvars[res].set('----')

        if 'IFFT' in self.task.results and self.task.results['IFFT'] is not None and self.plotFrame is not None:
            y = self.task.results['IFFT']
            x = rfftfreq(y.size, 1/dtg.adcSampleFrequency)
            self.plotFrame.plotGraph(x, y,
                                     labelx=('Частота, Гц' if dtg.LANG == 'ru' else 'Frequency, Hz'),
                                     labely=('Амплитуда' if dtg.LANG == 'ru' else 'Amplitude'))

    def measure(self):
        self.task.measure()
        self.update()
        if self.task.completed:
            self.stopped.set(0)
        else:
            self.stopTask()

    def runTask(self):
        self.startButton.configure(text='Остановить', command=self.stopTask, bg='#A10D0D')

        for par in self.parvars:
            self.task.parameters[par] = self.parvars[par].get()

        self.after(100)
        self.task.init_meas()
        if self.task.failed or self.task.single:
            self.update()
            self.stopTask()
            return

        self.stopped.set(0)
        while self.stopped.get() == 0:
            self.after(10, self.measure)
            self.wait_variable(self.stopped)

    def stopTask(self):
        self.stopped.set(1)
        self.startButton.configure(text='Начать', command=self.runTask, bg='#21903A')

    def mainMenu(self):
        self.stopTask()
        self.gotoMainMenu = True
        self.destroy()
