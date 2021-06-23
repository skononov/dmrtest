from numbers import Integral
from os import access, R_OK
import numpy as np
from scipy.fft import rfftfreq
import matplotlib as mpl
import matplotlib.pyplot as plt
from time import perf_counter
import tkinter as tk
# import tkinter.messagebox as tkmsg

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from threading import Thread, Event

from dtexcept import DTInternalError
from config import DTConfiguration, __appname__, __version__
from tasks import DTScenario, DTTask, dtTaskInit, dtResultDesc
import tasks
from singleton import Singleton
import dtglobals as dtg


mpl.rcParams["figure.dpi"] = 100
mpl.rcParams["lines.linewidth"] = 2.0
mpl.rcParams["grid.linewidth"] = 0.5
mpl.rcParams["axes.linewidth"] = 1.0
mpl.rcParams["axes.xmargin"] = 0.0
mpl.rcParams["font.size"] = 10
mpl.rcParams["figure.autolayout"] = True

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
        # plt.style.use('fivethirtyeight')
        plt.style.use('dark_background')
        self.defaultStyle()
        if access(DTApplication.__dtTkOptionFilename, R_OK):
            self.readStyle(DTApplication.__dtTkOptionFilename)

        self.mainMenuFrame = DTMainMenuFrame(self)
        self.mainMenuFrame.grid(sticky=tk.W+tk.E+tk.N+tk.S)

    def render(self, frame: tk.Frame):
        try:
            if frame.winfo_ismapped() or frame.master is not self:
                return
            for child in self.winfo_children():
                if not isinstance(child, tk.Toplevel):
                    child.grid_forget()
            frame.grid(sticky=tk.W+tk.E+tk.N+tk.S)
        except tk.TclError:
            pass

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

        # self.option_add('*DTLogoFrame.background', DEFAULT_BG_COLOR)
        # self.option_add('*DTMainMenuFrame.background', DEFAULT_BG_COLOR)
        # self.option_add('*DTLogoFrame.background', DEFAULT_BG_COLOR)
        # self.option_add('*DTMainMenuFrame.background', DEFAULT_BG_COLOR)
        # self.option_add('*DTPlotFrame.background', DEFAULT_BG_COLOR)
        # self.option_add('*Label.background', DEFAULT_BG_COLOR)
        # self.option_add('*Menubutton.background', BUTTON_BG_COLOR)
        # self.option_add('*Menu.background', _lightBG)
        # self.option_add('*Button.activebackground', HIGHLIGHTED_BG_COLOR)
        # self.option_add('*Menubutton.activebackground', HIGHLIGHTED_BG_COLOR)
        # self.option_add('*Menu.activebackground', HIGHLIGHTED_BG_COLOR)
        # self.option_add('*Label.foreground', DEFAULT_FG_COLOR)
        # self.option_add('*Button.foreground', DEFAULT_FG_COLOR)
        # self.option_add('*Menubutton.foreground', DEFAULT_FG_COLOR)

    def run(self):
        self.mainloop()

    def stop(self):
        self.destroy()

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
    """ Widget for plotting results data with Matplotlib/TkAgg.
    """
    def __init__(self, master, figsize=None):
        super().__init__(master)
        self.figure = None
        self.gridOn = True
        self.createCanvas(figsize)

    def createCanvas(self, figsize=None):
        if self.figure is not None:
            del self.figure
        if figsize is None:
            figsize = (5, 5)
        self.figure = Figure(figsize=figsize)
        self.resaxes = dict()
        canvas = FigureCanvasTkAgg(self.figure, master=self)
        canvas.draw()
        canvas.get_tk_widget().grid()

        # example plot
        # x = np.arange(-4*pi, 4*pi, 0.1)
        # y = np.sin(x)/x
        # self.plotGraph(x, y)

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
        if self.pkeys != ckeys:
            # plot new
            self.pkeys = ckeys
            self.figure.clf()
            if nres == 0:
                return

            ntypes = len(set([r['type'] for r in results.values() if r['draw']]))
            self.figure.subplots(nres, 1, sharex=(ntypes == 1), subplot_kw=dict(autoscale_on=True))
            axes = self.figure.axes
            for i, (ax, key) in enumerate(zip(axes, ckeys)):
                result = results[key]
                if result['type'] == 'time':
                    n = result['n']
                    ax.plot(result['x'][:n], result['y'][:n])
                    if ntypes == 1 and i == nres-1 or ntypes > 1:
                        ax.set_xlabel('Время [с]' if dtg.LANG == 'ru' else 'Time [s]')
                    yunit = dtg.units[dtResultDesc[key]['dunit']][dtg.LANG]
                    ax.set_ylabel(f'{dtResultDesc[key][dtg.LANG]} [{yunit}]')
                    ax.set_xlim(0, max(result['x'][n-1]+1, 10))
                else:
                    ax.plot(result['x'], result['y'])
                    if ntypes == 1 and i == nres-1 or ntypes > 1:
                        ax.set_xlabel('Частота [Гц]' if dtg.LANG == 'ru' else 'Frequency [Hz]')
                    ax.set_ylabel(f'Амплитуда {key}' if dtg.LANG == 'ru' else 'Amplitude {key}')
                ax.grid(self.gridOn, 'major')
        else:
            # update plots
            if nres == 0:
                return
            axes = self.figure.axes
            assert(len(axes) == nres)
            for ax, key in zip(axes, ckeys):
                result = results[key]
                n = result['n']
                ax.lines[0].set_data(result['x'][:n], result['y'][:n])
                if result['type'] == 'time':
                    ax.set_xlim(0, max(result['x'][n-1]+1, 10))
                ax.relim(True)
                ax.autoscale_view()
        self.figure.canvas.draw()
        self.figure.canvas.flush_events()

    def clearCanvas(self):
        self.figure.clf()


class DTMainMenuFrame(tk.Frame, metaclass=Singleton):

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
            raise DTInternalError('DTMainMenuFrame.__runScenario()', f'Empty scenario {scenario.name}.')

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

    def __newScenario(self):
        dialog = DTNewScenarioDialog(self.master)
        dialog.grab_set()
        self.wait_window(dialog)
        nscenarios = len(tasks.dtAllScenarios)
        if nscenarios > 0:
            self.runScenarioMB['state'] = tk.NORMAL
            self.scenariosText.set(f'{nscenarios} сценариев определено')

    def __chooseTask(self, taskType: type):
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
        # rightScrollbar = tk.Scrollbar(textboxFrame, orient=tk.VERTICAL, command=textbox.yview)
        # textbox.configure(yscrollcommand = rightScrollbar.set)
        # rightScrollbar.pack(side=tk.RIGHT, fill=tk.Y)

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

        quitb = tk.Button(self.menuFrame, text='Выход', command=self.quit, height=2)
        quitb.grid(row=4, sticky=tk.W+tk.E+tk.S)


class DTNewScenarioDialog(tk.Toplevel):

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
    def __init__(self, task: DTTask):
        super().__init__()
        self.task = task
        self.__updated = Event()
        self.__tostop = Event()

    def run(self):
        print('DTThread.run(): Thread started')
        self.__updated.clear()
        self.__tostop.clear()

        self.task.init_meas()
        self.__updated.set()
        if self.task.failed or self.task.completed or self.__tostop.is_set():
            print('DTThread.run(): Thread is about to stop after init')
            return

        while not self.__tostop.is_set():
            self.task.measure()
            self.__updated.set()
            if self.task.failed:
                break

        print('DTThread.run(): Thread is about to stop')

    def is_updated(self):
        return self.__updated.is_set()

    def clear_updated(self):
        return self.__updated.clear()

    def signal_stop(self):
        print('DTThread.signal_stop(): Thread stop signalled')
        self.__tostop.set()


class DTTaskFrame(tk.Frame):
    def __init__(self, master, task: DTTask, state=None):
        """ Constructor for a task front-end.
            state - can have values: None, 'first' (first in scenario), 'last' (last in scenario), 'midthrough'.
        """
        super().__init__(master)
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

        tk.Label(self, text=self.task.name[dtg.LANG], height=2, relief=tk.GROOVE, borderwidth=3)\
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

        self.__createStatusFrame()
        self.__createMenu()
        self.__createParameters()
        self.__createResults()

    def __createParameters(self):
        self.paramFrame = tk.LabelFrame(self.rightFrame, text="ПАРАМЕТРЫ")
        self.paramFrame.configure(labelanchor='n', padx=10, pady=5, relief=tk.GROOVE, borderwidth=3, )
        self.paramFrame.grid(row=0, sticky=tk.W+tk.E+tk.N)

        self.parvars = dict()
        self.wpars = dict()

        irow = 0
        for par in self.task.parameters:
            partuple = self.task.get_conv_par_all(par)
            if partuple is None:
                continue

            self.paramFrame.rowconfigure(irow, pad=10)

            pname, ptype, pvalue, plowlim, puplim, pincr, pavalues, pformat, punit = partuple

            tk.Label(self.paramFrame, text=pname+':').grid(row=irow, column=0, sticky=tk.E)

            parvar = tk.StringVar()
            if ptype is Integral:
                dvalue = str(int(pvalue))
            else:
                dvalue = str(pvalue).replace('.', ',')
            parvar.set(dvalue)

            self.parvars[par] = parvar

            # entry = tk.Entry(self.paramFrame, width=12, textvariable=parvar,
            #                 justify=tk.RIGHT)

            entry = tk.Spinbox(self.paramFrame, textvariable=parvar)
            entry.configure(width=12, from_=plowlim, to=puplim,
                            justify=tk.RIGHT, format='%'+pformat)
            self.wpars[str(entry)] = par
            entry.bind('<Button>', self.__scrollPar)
            entry.bind('<Key>', self.__scrollPar)
            if pavalues is not None:
                entry.configure(values=pavalues)
            else:  # use increment
                entry.configure(increment=pincr)

            entry.grid(row=irow, column=1, sticky=tk.W, padx=5)

            tk.Label(self.paramFrame, text=punit).grid(row=irow, column=2, sticky=tk.W)

            irow += 1

    def __scrollPar(self, event: tk.Event):
        if event.num == 4 or event.keycode == 98:  # up
            event.widget.invoke('buttonup')
        elif event.num == 5 or event.keycode == 104:  # down
            event.widget.invoke('buttondown')

    def __createResults(self):
        self.resultFrame = tk.LabelFrame(self.leftFrame, text='ИЗМЕРЕНИЕ')
        self.resultFrame.configure(labelanchor='n', padx=10, pady=5, relief=tk.GROOVE, borderwidth=3)
        self.resultFrame.grid(row=0, sticky=tk.W+tk.E+tk.N, pady=5)

        if not self.task.single:
            self.plotFrame = DTPlotFrame(self.leftFrame, figsize=(6, 5))
            self.plotFrame.grid(row=1, sticky=tk.W+tk.E+tk.S)

        self.resvars = dict()
        self.plotvars = dict()

        irow = 0
        for res in self.task.results:
            self.resultFrame.rowconfigure(irow, pad=10)
            if res in dtResultDesc:
                name = dtResultDesc[res][dtg.LANG]
                unitname = dtg.units[dtResultDesc[res]['dunit']][dtg.LANG]

                self.resvars[res] = resvar = tk.StringVar()
                resvar.set('----')
                reslabel = tk.Label(self.resultFrame, textvariable=resvar)
                reslabel.configure(relief=tk.SUNKEN, padx=5, width=10, justify=tk.RIGHT,
                                   font=(MONOSPACE_FONT_FAMILY, DEFAULT_FONT_SIZE))
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

            self.plotvars[res] = tk.IntVar()

            cb = tk.Checkbutton(self.resultFrame, text='Рисовать')
            cb.configure(indicatoron=0, variable=self.plotvars[res],
                         padx=3, pady=3)
            cb.grid(row=irow, column=3, padx=5)

            irow += 1

        self.__resetResHist()

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

        self.startButton = tk.Button(self.menuFrame, width=20, height=2)
        self.__configStartButton()
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

        tk.Button(self.menuFrame, text='Главное меню', height=2, command=self.__goMainMenu).\
            grid(row=2, columnspan=2, sticky=tk.W+tk.E, pady=10)

    def __update(self):
        if self.task.failed:
            self.message.configure(text=self.task.message, foreground='red')
            return
        elif self.task.single and self.task.completed:
            self.message.configure(text='ЗАВЕРШЕНО', justify=tk.CENTER, foreground='green')
            return
        else:
            self.message.configure(foreground='green')
            self.__stepProgress()

        if self.startTime == 0.:
            self.startTime = perf_counter()

        elapsedtime = perf_counter() - self.startTime
        for res in self.resvars:
            value = self.task.get_conv_res(res)
            presult = self.presults[res]
            if value is not None:
                self.resvars[res].set(f'%{dtResultDesc[res]["format"]}' % value)
                if presult['type'] == 'time':
                    n = presult['n']
                    presult['x'][n] = elapsedtime
                    presult['y'][n] = value
                    presult['n'] += 1
            else:
                self.resvars[res].set('----')

        self.___plotResult()

    def __resetResHist(self):
        self.startTime = 0.
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

    def ___plotResult(self):
        """ Call to DTPlotFrame for plotting/updating plots """
        print('DTTaskFrame.___plotResult()')
        for res, presult in self.presults.items():
            presult['draw'] = self.plotvars[res].get() != 0
            # only FFT data need preparation for plotting, time data are always up-to-date
            if presult['type'] == 'freq':
                presult['y'] = y = self.task.results[res]
                presult['x'] = rfftfreq(y.size, 1./dtg.adcSampleFrequency)
                presult['n'] = y.size

        self.plotFrame.plotGraphs(self.presults)

    def __stepProgress(self):
        self.progress = (self.progress+1) % self.maxProgressLen
        self.message['text'] = '\u2588' * self.progress

    def __check_thread(self):
        if self.tostop.get() == 1:
            print('DTTaskFrame.__check_thread(): Signalling thread stop')
            self.thread.signal_stop()
            return
        elif not self.thread.is_alive():
            print('DTTaskFrame.__check_thread(): Thread is dead. Updating frame to stop state.')
            self.__update()
            self.__stopTask()
            return
        elif self.thread.is_updated():
            print('DTTaskFrame.__check_thread(): Updating frame')
            try:
                self.__update()
                self.thread.clear_updated()
            except Exception as exc:
                print('DTTaskFrame.__check_thread(): Exception caught in __update(). Signal thread stop.')
                self.thread.signal_stop()
                raise exc
        print('DTTaskFrame.__check_thread(): Schedule thread check in 100ms')
        self.after(100, self.__check_thread)

    def __scheduleTask(self):
        print('DTTaskFrame.__scheduleTask()')
        self.startButton.configure(text='Остановить', command=self.__stopTask, bg='#A50D00', activebackground='#C63519')
        self.tostop.set(0)
        self.message.configure(text='')
        self.after(5, self.__runTask)

    def __runTask(self):
        print('DTTaskFrame.__runTask()')
        if self.tostop.get() == 1:
            return
        self.progress = 0

        if self.startTime > 0:
            self.__resetResHist()

        for par in self.parvars:
            pvalue = float(self.parvars[par].get().replace(',', '.'))
            self.task.set_conv_par(par, pvalue)

        self.thread = DTThread(self.task)

        self.thread.start()

        self.__check_thread()

    def __configStartButton(self):
        self.startButton.configure(text='Запуск', command=self.__scheduleTask, bg='#21903A', activebackground='#3CA54D')

    def __stopTask(self):
        self.tostop.set(1)
        print('DTTaskFrame.__stopTask()')
        self.__configStartButton()

    def __goPrev(self):
        self.direction = -1
        if hasattr(self, 'thread'):
            self.thread.signal_stop()
        self.destroy()

    def __goNext(self):
        self.direction = 1
        if hasattr(self, 'thread'):
            self.thread.signal_stop()
        self.destroy()

    def __goMainMenu(self):
        self.direction = 0
        if hasattr(self, 'thread'):
            self.thread.signal_stop()
        self.destroy()
