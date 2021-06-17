from dtexcept import DTInternalError
import os
import numpy as np
from math import pi
import matplotlib as mpl
import tkinter as tk
import tkinter.messagebox as tkmsg

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from config import DTConfiguration, __appname__, __version__
from tasks import DTScenario, DTTask, dtTaskInit
import tasks
from singleton import Singleton
import dtglobals as dtg
from dtglobals import kHz, MHz
#import dialogs as dlg


mpl.rcParams["figure.facecolor"] = '#1F1F1F'
mpl.rcParams["figure.dpi"] = 100
mpl.rcParams["lines.linewidth"] = 2.0
mpl.rcParams["grid.linewidth"] = 0.5
mpl.rcParams["axes.linewidth"] = 1.0
mpl.rcParams["font.size"] = 12

_rootWindowGeometry = "1024x600+400+320"

DEFAULT_BG_COLOR = '#1F1F1F'
LIGHT_BG_COLOR = '#2E2E2E'
HIGHLIGHTED_BG_COLOR = '#4F4F4F'
SELECT_BG_COLOR = '#274F77'
BUTTON_BG_COLOR = '#505050'
DEFAULT_FG_COLOR = 'white'

DEFAULT_FONT_FAMILY = "Helvetica"
MONOSPACE_FONT_FAMILY = "lucidasanstypewriter"
BIG_FONT_SIZE = 14
DEFAULT_FONT_SIZE = 12
SMALL_FONT_SIZE = 10


class DTApplication(tk.Tk, metaclass=Singleton):
    __dtTkOptionFilename = '~/.dtstyle'

    def __init__(self):
        super().__init__()
        self.geometry(_rootWindowGeometry)
        self.title(__appname__ + ' ' + __version__)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        if os.access('img/logo.gif', os.R_OK):
            self.logo = tk.PhotoImage(file='img/logo.gif')
        else:
            self.logo = None

        self.wm_iconphoto(True, self.logo)

        # init task handlers
        dtTaskInit()

        # set styles
        self.defaultStyle()
        if os.access(DTApplication.__dtTkOptionFilename, os.R_OK):
            self.readStyle(DTApplication.__dtTkOptionFilename)

        self.mainMenuFrame = DTMainMenuFrame(self)

        self.render(self.mainMenuFrame)

    def render(self, frame: tk.Frame):
        if frame.winfo_ismapped() or frame.master is not self:
            return
        for child in self.winfo_children():
            child.forget()
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
        self.option_add('*Text.background', LIGHT_BG_COLOR)
        self.option_add('*Entry.background', LIGHT_BG_COLOR)
        self.option_add('*Listbox.background', LIGHT_BG_COLOR)
        self.option_add('*Button.background', BUTTON_BG_COLOR)
        self.option_add('*Menubutton.background', BUTTON_BG_COLOR)
        self.option_add('*foreground', DEFAULT_FG_COLOR)
        self.option_add('*font', f'{DEFAULT_FONT_FAMILY} {DEFAULT_FONT_SIZE}')

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


class DTChooseObjectMenu(tk.Menu):

    def __init__(self, menubutton, command, objectList):
        super().__init__(menubutton, tearoff=0)

        self.command = command
        self.objectList = objectList
        self.indexVar = tk.IntVar()
        locName = False
        if hasattr(objectList, '__len__') and len(objectList) > 0:
            obj = objectList[0]
            if hasattr(obj, 'name') and isinstance(obj.name, dict) and dtg.LANG in obj.name:
                locName = True
            elif hasattr(obj, 'name') and isinstance(obj.name, str):
                locName = False
            else:
                raise DTInternalError(self.__class__.__name__, f'No name defined for the object of type {type(obj)}')
            for index, obj in enumerate(objectList):
                self.add_radiobutton(label=obj.name[dtg.LANG] if locName else obj.name, indicatoron=False,
                                     value=index, variable=self.indexVar, command=self.select)

    def select(self):
        index = self.indexVar.get()
        if 0 <= index < len(self.objectList):
            self.forget()
            self.command(self.objectList[index])


class DTPlotFrame(tk.Frame, metaclass=Singleton):
    def __init__(self, master):
        super().__init__(master, bg=LIGHT_BG_COLOR, class_='DTPlotFrame')
        self.figure = None
        self.createCanvas()
        self.gridOn = True

    def createCanvas(self):
        if self.figure is not None:
            del self.figure
        self.figure = Figure(figsize=(4, 4))
        self.figure.add_subplot(111)
        canvas = FigureCanvasTkAgg(self.figure, master=self)
        canvas.draw()
        canvas.get_tk_widget().grid()

        # example plot
        x = np.arange(-4*pi, 4*pi, 0.1)
        y = np.sin(x)/x
        self.plotGraph(x, y)

    def plotGraph(self, x, y, new=True):
        ax = self.figure.axes
        if new or ax is None:
            self.figure.clf()
            ax = self.figure.add_subplot(111)
        ax.plot(x, y, 'w')
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

        self.makeLogoFrame()
        self.logoFrame.grid(column=0, row=0, sticky=tk.W+tk.E+tk.N+tk.S)

        self.makeMenuFrame()
        self.menuFrame.grid(column=1, row=0, sticky=tk.N+tk.S)

    def runScenario(self, scenario: DTScenario):
        for task in scenario:
            taskFrame = DTTaskFrame(self.master, task)
            self.master.render(taskFrame)
            taskFrame.mainloop()

    def newScenario(self):
        DTNewScenarioDialog(self.master)

    def chooseTask(self, taskType: type):
        task = taskType()
        taskFrame = DTTaskFrame(self.master, task)
        self.master.render(taskFrame)

    def makeLogoFrame(self):
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

    def makeMenuFrame(self):
        self.menuFrame = tk.Frame(self, padx=10, pady=10)

        for i in range(4):
            self.menuFrame.rowconfigure(i, pad=20)
        self.menuFrame.rowconfigure(3, weight=1)

        csmb = self.runScenarioMB = tk.Menubutton(self.menuFrame, text='Запустить сценарий', takefocus=True)
        csmb.configure(relief=tk.RAISED, height=2, state=tk.DISABLED)
        csmb.grid(row=0, sticky=tk.W+tk.E)
        csmb['menu'] = csmb.menu = DTChooseObjectMenu(csmb, command=self.runScenario, objectList=tasks.dtAllScenarios)

        cmmb = tk.Menubutton(self.menuFrame, text='Выбрать измерение', takefocus=True)
        cmmb.configure(relief=tk.RAISED, height=2)
        cmmb['menu'] = cmmb.menu = DTChooseObjectMenu(cmmb, command=self.chooseTask, objectList=tasks.dtTaskTypes)
        cmmb.grid(row=1, sticky=tk.W+tk.E)

        csb = tk.Button(self.menuFrame, text='Создать сценарий', command=self.newScenario, height=2)
        csb.grid(row=2, sticky=tk.W+tk.E)
        csb.focus()

        quitb = tk.Button(self.menuFrame, text='Выход', command=self.quit, height=2)
        quitb.grid(row=3, sticky=tk.W+tk.E+tk.S)


class DTNewScenarioDialog(tk.Toplevel):

    def __init__(self, master=None):
        super().__init__()
        self.transient(master)
        x0, y0 = master.winfo_rootx(), master.winfo_rooty()
        self.geometry(f'{x0+300:+d}{y0+200:+d}')
        self.title('Создать сценарий')
        self.configure(padx=10, pady=10)

        for irow in range(4):
            self.rowconfigure(irow, pad=10)
        self.columnconfigure(0, pad=20)
        self.columnconfigure(1, pad=10)
        self.columnconfigure(2, pad=0)

        tk.Label(self, text='Название:').grid(column=0, row=0, sticky=tk.E, padx=10, pady=5)

        self.nameVar = tk.StringVar()
        self.nameVar.set('Новый сценарий')
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
        menubtn['menu'] = menubtn.menu = DTChooseObjectMenu(menubtn, command=self.__addTask, objectList=tasks.dtTaskTypes)
        menubtn.grid(column=1, row=2, sticky=tk.N, pady=5)

        tk.Button(self, text='Создать сценарий', command=self.__create).grid(column=1, row=3, sticky=tk.E)

        tk.Button(self, text='Отмена', command=self.destroy).grid(column=0, row=3, sticky=tk.W)

    def __create(self):
        if self.taskListbox.size() == 0:
            tkmsg.showinfo('', 'Нет введенных задач!')
            return

        name = self.nameVar.get()
        if name in tasks.dtAllScenarios:
            tkmsg.showerror('Ошибка', f'Сценарий с именем {name} уже существует!')
            return

        slist = self.taskListVar.get()
        tnameslist = [s.strip("'") for s in slist[1:-1].split(', ')]
        DTScenario(name, tnameslist)
        self.destroy()
        tkmsg.showinfo('', f'Сценарий {name} создан')

    def __addTask(self, tasktype):
        if self.taskListbox.curselection() == ():
            self.taskListbox.insert(tk.END, tasktype.name[dtg.LANG])
        else:
            self.taskListbox.insert(tk.ACTIVE, tasktype.name[dtg.LANG])

    def __deleteTask(self, event):
        if event.keysym == 'Delete':
            selected = self.taskListbox.curselection()
            if len(selected) == 0:
                return
            self.taskListbox.delete(selected[0])


class DTTaskFrame(tk.Frame):
    def __init__(self, master, task: DTTask):
        super().__init__(master, class_='DTTaskFrame')
        self.configure(padx=10, pady=10)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self.task = task

        self.leftFrame = tk.Frame(self)
        self.leftFrame.columnconfigure(0, weight=1)
        self.leftFrame.rowconfigure(0, weight=1, minsize=150)
        self.leftFrame.rowconfigure(1, minsize=400)
        self.leftFrame.grid(row=0, column=0, sticky=tk.N+tk.S)

        self.rightFrame = tk.Frame(self)
        self.rightFrame.grid(row=0, column=1, sticky=tk.N+tk.S)

        self.paramFrame = tk.Frame(self.rightFrame)
        self.paramFrame.grid(row=0, column=0, sticky=tk.NW)

        self.resultFrame = tk.Frame(self, padx=4, pady=3)
        self.resultFrame.grid(row=0, column=1, sticky=tk.NE)

        self.menuFrame = tk.Frame(self, padx=4, pady=3)
        self.menuFrame.grid(row=1, column=1, sticky=tk.N+tk.S)

        self.plotFrame = DTPlotFrame(self)
        self.plotFrame.grid(row=2, column=0, sticky=tk.N+tk.S+tk.W+tk.E)

        # TODO ...

    def update(self):
        pass

    def runTask(self):
        self.task.init_meas()

        while True:
            self.task.measure()
            self.update()
