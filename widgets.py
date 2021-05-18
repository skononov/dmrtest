import os
import numpy as np
import scipy
from math import pi
import matplotlib as mpl
import tkinter as tk

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from config import DTConfiguration
from tasks import dtTaskHandlers

mpl.rcParams["figure.facecolor"] = '#1F1F1F'
mpl.rcParams["figure.dpi"] = 100
mpl.rcParams["lines.linewidth"] = 2.0
mpl.rcParams["grid.linewidth"] = 0.5
mpl.rcParams["axes.linewidth"] = 1.0
mpl.rcParams["font.size"] = 12

_darkBG = '#1F1F1F'
_lightBG = '#2E2E2E'
_btnBG = '#505050'
_hlBG = '#6F6F6F'
_fg = 'white'
_font = ('Helvetica', 14)


class DTApplication(tk.Tk):
    __dtTkOptionFilename = '~/.dtstyle'
    __appname: str = 'DMR TEST'
    __version__: str = ''

    def __init__(self):
        super().__init__()
        self.geometry("640x480+400+320")
        self.title(DTApplication.__appname+' '+ DTApplication.__version__)
        
        self.defaultStyle()
        if os.access(DTApplication.__dtTkOptionFilename, os.R_OK):
            self.readStyle(DTApplication.__dtTkOptionFilename)
#        self.columnconfigure(0, minsize=460, pad=0)
#        self.columnconfigure(1, minsize=120, pad=0)
#        self.rowconfigure(0, minsize=460, pad=0)

        logo = DTLogoFrame(self)
        logo.grid(row=0, column=0)
        logo.configure(width=460, height=460)
        logo.grid_propagate(0)

        mainMenu = DTMainMenuFrame(self)
        mainMenu.grid(row=0, column=1)
        mainMenu.configure(width=120, height=460)
        mainMenu.grid_propagate(0)

    def readStyle(self, filename: str):
        try:
            self.option_readfile(filename)
        except tk.TclError:
            print(f'DTApplication.readStyle(): Can not read Tk option file {filename}')

    def defaultStyle(self):
        self.configure(bg=_lightBG)
        self.option_add('*DTLogoFrame.background', _darkBG)
        self.option_add('*DTMainMenuFrame.background', _darkBG)
        self.option_add('*DTPlotFrame.background', _darkBG)
        self.option_add('*Label.background', _darkBG)
        self.option_add('*Button.background', _btnBG)
        self.option_add('*Menubutton.background', _btnBG)
        self.option_add('*Menu.background', _lightBG)
        self.option_add('*Button.activebackground', _hlBG)
        self.option_add('*Menubutton.activebackground', _hlBG)
        self.option_add('*Menu.activebackground', _hlBG)
        self.option_add('*Label.foreground', _fg)
        self.option_add('*Button.foreground', _fg)
        self.option_add('*Menubutton.foreground', _fg)
        self.option_add('*font', _font)

    def run(self):
        self.mainloop()

    def stop(self):
        self.destroy()

class DTLogoFrame(tk.Frame):

    def __init__(self, master=None, text=None, logofilename=None):
        super().__init__(master, class_='DTLogoFrame')
        self.configure(padx=10, pady=10, relief=tk.GROOVE)
        
        if text is None:
            text = """
            Информация о приложении\n и копирайте.
            """
        if logofilename is None and os.access('img/logo.gif', os.R_OK):
            logofilename = 'img/logo.gif'
        self.image = tk.PhotoImage(file=logofilename)

        label = tk.Label(self,
                         text=text,
                         compound=tk.TOP,
                         image=self.image,
#                         anchor=tk.NW,
#                         width=60, height=45,
                         padx=3, pady=3)
        label.grid()

class DTPlotFrame(tk.Frame):

    def __init__(self, master=None):
        super().__init__(master, bg='#3E3E3E', class_='DTPlotFrame')
        self.configure(padx=20, pady=20)
        self.grid(columns=0, columnspan=3, row=0)
        self.createCanvas()
        self.gridOn = True
    
    def createCanvas(self):
        self.figure = Figure(figsize=(5, 5))
        self.figure.add_subplot(111)

        # example plot
        x = np.arange(-4*pi, 4*pi, 0.1)
        y = np.sin(x)/x
        self.plotGraph(x, y)

    def plotGraph(self, x, y):
        ax = self.figure.add_subplot(111)
        ax.plot(x, y, 'w')
        ax.grid(self.gridOn, 'major')

    def clearCanvas(self):
        self.figure.clf()

class DTMainMenuFrame(tk.Frame):
    
    def __init__(self, master=None):
        super().__init__(master, class_='DTMainMenuFrame')
        self.configure(padx=10, pady=10, relief=tk.GROOVE)
        
        self.rowconfigure(0, minsize=30, pad=20)
        self.rowconfigure(1, minsize=30, pad=20)
        self.rowconfigure(2, minsize=30, pad=20)

        csmb = self.chooseScenarioMB = tk.Menubutton(master=self, text='Запустить сценарий', relief=tk.RAISED)
        csmb.grid(row=0)
        csmb.menu = DTChooseScenarioMenu(self.chooseScenarioMB)

        cmmb = self.chooseMeasurementMB = tk.Menubutton(master=self, text='Запустить измерение', relief=tk.RAISED)
        cmmb.grid(row=1)
        cmmb.menu = DTChooseMeasurementMenu(self.chooseMeasurementMB)

        csb = self.newScenarioMB = tk.Button(master=self, text='Создать сценарий', 
                command=self.newScenario, relief=tk.RAISED)
        csb.grid(row=2)


    def newScenario(self):
        pass
        

class DTChooseScenarioMenu(tk.Menu):

    def __init__(self, menubutton):
        super().__init__(tearoff = 0)

        config = DTConfiguration()
        self.scenarios = config.scenarios
        
        for name, tasks in self.scenarios.items():
            scenarioTasksMenu = tk.Menu(self)
            for task in tasks:
                scenarioTasksMenu.add_command(label=task, command=dtTaskHandlers[task])
            self.add_cascade(label=name, menu=scenarioTasksMenu)

    def update(self):
        pass


class DTChooseMeasurementMenu(tk.Menu):

    def __init__(self, menubutton):
        super().__init__(tearoff = 0)

        for task, handler in dtTaskHandlers.items():
            self.add_command(label=task, command=handler)

