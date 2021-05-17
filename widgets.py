import os
import numpy as np
import scipy
from math import pi
import tkinter as tk

import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)

from config import DTConfiguration
from tasks import dtTaskHandlers

mpl.rcParams["figure.facecolor"] = '#1F1F1F'
mpl.rcParams["figure.dpi"] = 100
mpl.rcParams["lines.linewidth"] = 2.0
mpl.rcParams["grid.linewidth"] = 0.5
mpl.rcParams["axes.linewidth"] = 1.0
mpl.rcParams["font.size"] = 12

class DTLogoFrame(tk.Frame):

    def __init__(self, master=None, text=None, filename=None):
        super().__init__(self, master, bg='#1F1F1F')
        self.grid(column=0, columnspan=3, padx=10, pady=10)

        font = ('Helvetica', 14)
        
        if text is None:
            text = """
            Информация о приложении и копирайте.
            """
        if filename is None and os.access('img/logo.gif', os.R_OK):
            filename = 'img/logo.gif'
        self.image = tk.PhotoImage(file=filename)

        label = tk.Label(self, 
                         text=text,
                         font=font,
                         fg='white', bg='#3E3E3E', 
                         compound=tk.TOP,
                         image=self.image,
                         anchor=tk.NW,
#                         width=60, height=45,
                         padx=3, pady=3)
        label.grid()

class DTPlotFrame(tk.Frame):

    def __init__(self, master=None):
        super().__init__(self, master, bg='#3E3E3E')
        self.grid(columns=0, columnspan=3, padx=10, pady=10)
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
        super().__init__(self, master)
        self.configure(bg='#1F1F1F', relief=tk.FLAT)
        self.grid(column=3, padx=10, pady=10)

        csmb = self.chooseScenarioMB = tk.Menubutton(master=self, text='Запустить сценарий')
        csmb.configure(padx=10, pady=5)
        csmb.grid(row=0)
        csmb.menu = DTChooseScenarioMenu(self.chooseScenarioMB)

        cmmb = self.chooseMeasurementMB = tk.Menubutton(master=self, text='Запустить измерение')
        cmmb.configure(padx=10, pady=5)
        cmmb.grid(row=1)
        cmmb.menu = DTChooseMeasurementMenu(self.chooseMeasurementMB)

        csb = self.newScenarioMB = tk.Button(master=self, text='Создать сценарий', 
                command=self.newScenario)
        csb.configure(padx=10, pady=5)
        csb.grid(row=2)


    def newScenario(self):
        pass
        

class DTChooseScenarioMenu(tk.Menu):

    def __init__(self, menubutton):
        super().__init__(self, tearoff = 0)

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
        super().__init__(self, tearoff = 0)

        for task, handler in dtTaskHandlers.items():
            self.add_command(label=task, command=handler)

