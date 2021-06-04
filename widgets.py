import os
import numpy as np
import scipy
from math import pi
import matplotlib as mpl
import tkinter as tk
import tkinter.messagebox as tkmsg

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from config import DTConfiguration
from tasks import dtTaskTypes, dtTaskInit
from singleton import Singleton
from dtglobals import DEBUG, LANG
#import dialogs as dlg


mpl.rcParams["figure.facecolor"] = '#1F1F1F'
mpl.rcParams["figure.dpi"] = 100
mpl.rcParams["lines.linewidth"] = 2.0
mpl.rcParams["grid.linewidth"] = 0.5
mpl.rcParams["axes.linewidth"] = 1.0
mpl.rcParams["font.size"] = 12

_rootWindowGeometry = "800x600+400+320"
_dialogWindowGeometry = "+400+320"
LEFT_PANEL_WIDTH = 400

DEFAULT_BG_COLOR = '#1F1F1F'
LIGHT_BG_COLOR = '#2E2E2E'
BUTTON_BG_COLOR = '#505050'
HIGHLIGHTED_BG_COLOR = '#6F6F6F'
DEFAULT_FG_COLOR = 'white'

DEFAULT_FONT_FAMILY   = "Helvetica"
MONOSPACE_FONT_FAMILY = "lucidasanstypewriter"
DEFAULT_FONT_SIZE     = 10
BIG_FONT_SIZE         = 12
SMALL_FONT_SIZE       =  9


class DTApplication(tk.Tk, metaclass=Singleton):
    __dtTkOptionFilename = '~/.dtstyle'

    def __init__(self):
        super().__init__()
        self.geometry(_rootWindowGeometry)
        self.title(DTConfiguration.__appname__+' '+ DTConfiguration.__version__)

        # init task handlers
        dtTaskInit()

        # set styles
        self.defaultStyle()
        if os.access(DTApplication.__dtTkOptionFilename, os.R_OK):
            self.readStyle(DTApplication.__dtTkOptionFilename)

        self.mainMenuFrame = DTMainMenuFrame(self)

        self.render(self.mainMenuFrame)

    def render(self, frame: tk.Frame):
        if frame.winfo_ismapped():
            return
        for child in self.winfo_children():
            child.forget()
        frame.pack(fill=tk.BOTH)

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
        self.option_add('*Button.background', BUTTON_BG_COLOR)
        self.option_add('*Menubutton.background', BUTTON_BG_COLOR)
        self.option_add('*foreground', DEFAULT_FG_COLOR)
        self.option_add('*font', f'{DEFAULT_FONT_FAMILY} {DEFAULT_FONT_SIZE}')
        self.option_add('*Button.font', f'{DEFAULT_FONT_FAMILY} {BIG_FONT_SIZE}')
        self.option_add('*Menubutton.font', f'{DEFAULT_FONT_FAMILY} {BIG_FONT_SIZE}')

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


class DTPlotFrame(tk.Frame, metaclass=Singleton):
    def __init__(self, master):
        super().__init__(master, bg='#3E3E3E', class_='DTPlotFrame')
        self.figure = None
        self.createCanvas()
        self.gridOn = True
    
    def createCanvas(self):
        if self.figure is not None:
            del self.figure
        self.figure = Figure(figsize=(3.5, 3.5))
        self.figure.add_subplot(111)

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

        self.makeLogoFrame()
        self.logoFrame.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)

        self.menuFrame = tk.Frame(self, padx=5)
        self.menuFrame.pack(side=tk.RIGHT, fill=tk.Y)

        for i in range(3):
            self.menuFrame.rowconfigure(i, minsize=50, pad=10)

        csmb = self.chooseScenarioMB = tk.Menubutton(self.menuFrame, text='Запустить сценарий')
        csmb.configure(relief=tk.RAISED, width=23, height=2, padx=5, pady=0, takefocus=tk.YES)
        csmb.grid(row=0)
        csmb.menu = DTChooseScenarioMenu(self.chooseScenarioMB)
        csmb['menu'] = csmb.menu
        csmb.focus()

        cmmb = self.chooseTaskMB = tk.Menubutton(self.menuFrame, text='Выбрать измерение')
        cmmb.configure(relief=tk.RAISED, width=23, height=2, padx=5, pady=0, takefocus=tk.YES)
        cmmb.menu = DTChooseTaskMenu(cmmb, self.runTask)
        cmmb['menu'] = cmmb.menu
        cmmb.grid(row=1)

        csb = self.newScenarioMB = tk.Button(self.menuFrame, text='Создать сценарий', command=self.newScenario)
        csb.configure(relief=tk.RAISED, width=23, height=2, padx=5, pady=0)
        csb.grid(row=2)

    def newScenario(self):
        pass

    def runTask(self):
        pass

    def makeLogoFrame(self):
        lf = self.logoFrame = tk.Frame(self)
        lf.configure(padx=10, pady=10, relief=tk.GROOVE)
        
        text = f"""
            Информация о приложении {DTConfiguration.__appname__} {DTConfiguration.__version__}.
            Информация о приложении {DTConfiguration.__appname__} {DTConfiguration.__version__}.
            Информация о приложении {DTConfiguration.__appname__} {DTConfiguration.__version__}.
            """
        if os.access('img/logo.gif', os.R_OK):
            logofilename = 'img/logo.gif'
        lf.image = tk.PhotoImage(file=logofilename)

        tk.Label(lf, image=self.image, padx=5, pady=5).pack(side=tk.TOP)

        # add a text Frame
        textboxFrame = tk.Frame(lf, borderwidth=10)
        textboxFrame.pack(side=tk.BOTTOM, fill=tk.BOTH)
        textbox = tk.Text(textboxFrame, padx="2m", pady="1m", wrap=tk.WORD)

        # add a vertical scrollbar to the frame
        ##rightScrollbar = tk.Scrollbar(textboxFrame, orient=tk.VERTICAL, command=textbox.yview)
        ##textbox.configure(yscrollcommand = rightScrollbar.set)
        ##rightScrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        textbox.pack(side=tk.TOP, fill=tk.BOTH)
        textbox.insert(tk.END, text, "normal")
        textbox.configure(state=tk.DISABLED)


class DTNewScenarioDialog(tk.Tk):

    def __init__(self):
        super().__init__()
        self.geometry(_dialogWindowGeometry)
        self.title('Создать новый сценарий')

        frame = tk.Frame(self, padx=5, pady=5)
        frame.pack(side=tk.TOP)

        tk.Label(frame, text='Название сценария:').grid(column=0, row=0, sticky=tk.E)

        self.namevar = tk.StringVar()
        self.namevar.set('Новый сценарий')
        nameentry = tk.Entry(frame, textvariable=self.namevar, width=40)
        nameentry.grid(column=1, row=0, sticky=tk.W)
        nameentry.focus()

        tk.Label(frame, text='Задачи:').grid(column=0, row=1, sticky=tk.NE)

        self.tasklist = tk.Listbox(frame, height=7, width=40)
        self.tasklist.grid(column=1, row=1, sticky=tk.NW)

        addbtn = tk.Menubutton(frame, text='Добавить задачу')
        addbtn.menu = DTChooseTaskMenu(addbtn, command=self.addTask)
        addbtn['menu'] = addbtn.menu
        addbtn.grid(column=2, row=2, sticky=tk.N)

        tk.Button(frame, text='Создать', command=self.create).grid(column=1, row=2, sticky=tk.S)
    
    def create(self):
        pass

    def addTask(self):
        self.tasklist.insert(i, task.name[LANG])


        

class DTTaskFrame(tk.Frame):
    def __init__(self, master, task: DTTask):
        super().__init__(master, class_='DTTaskFrame')
        self.configure(padx=10, pady=10)

        self.leftFrame = tk.Frame(self)
        self.rightFrame = tk.Frame(self)

        self.paramFrame = tk.Frame(self)
        self.paramFrame.pack(row=0, column=0, sticky=tk.NW)

        self.resultFrame = tk.Frame(self, padx=4, pady=3)
        self.resultFrame.grid(row=0, column=1, sticky=tk.NE)

        self.menuFrame = tk.Frame(self, padx=4, pady=3)
        self.menuFrame.grid(row=1, column=1, sticky=tk.N+tk.S+tk.W+tk.E)

        self.plotFrame = DTPlotFrame(self)
        self.plotFrame.grid(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH)

        for i in range(3):
            self.menuFrame.rowconfigure(i, minsize=100, pad=20)

        csmb = self.chooseScenarioMB = tk.Menubutton(master=menuFrame, text='Запустить сценарий')
        csmb.configure(relief=tk.RAISED, width=23, height=2, padx=5, pady=0, takefocus=tk.YES)
        csmb.grid(row=0)
        csmb.menu = DTChooseScenarioMenu(self.chooseScenarioMB)
        csmb['menu'] = csmb.menu
        csmb.focus_set()

        cmmb = self.chooseMeasurementMB = tk.Menubutton(master=menuFrame, text='Запустить измерение')
        cmmb.configure(relief=tk.RAISED, width=23, height=2, padx=5, pady=0, takefocus=tk.YES)
        cmmb.grid(row=1)
        cmmb.menu = DTChooseMeasurementMenu(self.chooseMeasurementMB)
        cmmb['menu'] = cmmb.menu

        csb = self.newScenarioMB = tk.Button(master=menuFrame, text='Создать сценарий', command=self.newScenario)
        csb.configure(relief=tk.RAISED, width=23, height=2, padx=5, pady=0)
        csb.grid(row=2)

    def update(self):
        pass

class DTChooseScenarioMenu(tk.Menu):

    def __init__(self, menubutton):
        super().__init__(menubutton, tearoff = 0)

        config = DTConfiguration()
        self.scenarios = config.scenarios
        
        for name, tasks in self.scenarios.items():
            scenarioTasksMenu = tk.Menu(self)
            for task in tasks:
                scenarioTasksMenu.add_command(label=task, command=dtTaskTypes[task])
            self.add_cascade(label=name, menu=scenarioTasksMenu)

    def update(self):
        pass


class DTChooseTaskMenu(tk.Menu):
    def __init__(self, menubutton, command):
        super().__init__(menubutton, tearoff = 0)

        for tasktype in dtTaskTypes:
            self.add_command(label=tasktype.name[LANG], command=command)

