from numbers import Integral
from os import access, R_OK, getpid, getenv, pread, setpriority, PRIO_PROCESS
from time import asctime
from traceback import print_exc, format_exception_only
from io import FileIO
import numpy as np
from numpy.core.function_base import linspace
from numpy.lib.twodim_base import _trilu_indices_form_dispatcher
from scipy.fft import rfftfreq
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
import tkinter.messagebox as tkmsg
from multiprocessing import Pipe

from process import DTProcess
from config import DTConfiguration
from tasks import DTScenario, DTTask, dtTaskInit, dtResultDesc
from singleton import Singleton
from dtexcept import DTUIError
import tasks
import dtglobals as dtg
from dtglobals import __appname__, __version__

_rootWindowWidth = 1024
_rootWindowHeight = 700

DARK_BG_COLOR = '#0F0F0F'
DEFAULT_BG_COLOR = '#1F1F1F'
LIGHT_BG_COLOR = '#2E2E2E'
LIGHTER_BG_COLOR = '#4E4E4E'
HIGHLIGHT_COLOR = '#3C449D'
SELECT_BG_COLOR = '#274F77'
BUTTON_BG_COLOR = '#505050'
DEFAULT_FG_COLOR = '#F0F0F0'
DIMMED_FG_COLOR = '#CCCCCC'

DEFAULT_FONT_FAMILY = "Helvetica"
MONOSPACE_FONT_FAMILY = "lucidasanstypewriter"
BIG_FONT_SIZE = '14'
DEFAULT_FONT_SIZE = '12'
SMALL_FONT_SIZE = '10'
LITTLE_FONT_SIZE = '9'


def _scrollEntry(event: tk.Event):
    if event.num == 4 or event.keysym == 'Up':  # up
        event.widget.invoke('buttonup')
    elif event.num == 5 or event.keysym == 'Down':  # down
        event.widget.invoke('buttondown')


class DTApplication(tk.Tk, metaclass=Singleton):
    """ DMR TEST Application with Tkinter
    """
    DEBUG = False

    __tkOptionFilename = getenv('HOME') + '/dmr/dmrtest.tkstyle'
    __tkPidFilename = getenv('HOME') + '/dmr/dmrtest.pid'

    def __init__(self):
        global _scrollEntry
        super().__init__()

        print(f'DTApplication created in the procees PID {getpid()}')

        # write pid of the main process to file
        with open(self.__tkPidFilename, 'w') as f:
            f.write(str(getpid()) + '\n')

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        if sw/sh > 2:
            sw //= 2
        geometry = f'{_rootWindowWidth}x{_rootWindowHeight}{(sw-_rootWindowWidth)//2:+d}{(sh-_rootWindowHeight)//2:+d}'
        self.geometry(geometry)
        self.title(__appname__ + ' ' + __version__)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # directory with icons and images
        self.imgdir = getenv('HOME')+'/dmr/img'

        # load app icon
        if access(self.imgdir + '/logo.gif', R_OK):
            self.logo = tk.PhotoImage(file=self.imgdir + '/logo.gif')
            # set window icon for the window manager
            self.wm_iconphoto(True, self.logo)
        else:
            self.logo = None

        # init task handlers
        dtTaskInit()

        # load app configuration
        DTConfiguration()

        # start task process and its checking
        self.__startTaskProcessWithChecking()

        # set styles
        if access(DTApplication.__tkOptionFilename, R_OK):
            self.readStyle(DTApplication.__tkOptionFilename)
        else:
            self.defaultStyle()

        self.mainMenuFrame = DTMainMenuFrame(self)
        self.mainMenuFrame.grid(sticky=tk.W+tk.E+tk.N+tk.S)

        self.bind_class('Spinbox', '<Button-4>', _scrollEntry)
        self.bind_class('Spinbox', '<Button-5>', _scrollEntry)
        self.bind_class('Spinbox', '<Key-Up>', _scrollEntry)
        self.bind_class('Spinbox', '<Key-Down>', _scrollEntry)

    def readStyle(self, filename: str):
        self.option_clear()
        try:
            self.option_readfile(filename)
        except tk.TclError:
            print(f'DTApplication.readStyle(): Can not read Tk option file {filename}')

    def defaultStyle(self):
        self.option_clear()
        self.option_add('*background', DEFAULT_BG_COLOR)
        self.option_add('*Canvas.background', LIGHT_BG_COLOR)
        self.option_add('*highlightBackground', DEFAULT_BG_COLOR)
        self.option_add('*activeBackground', LIGHT_BG_COLOR)
        self.option_add('*activeForeground', DEFAULT_FG_COLOR)
        self.option_add('*disabledBackground', LIGHT_BG_COLOR)
        self.option_add('*disabledForeground', DIMMED_FG_COLOR)
        self.option_add('*selectColor', LIGHT_BG_COLOR)
        self.option_add('*highlightThickness', '0')
        self.option_add('*Button.highlightThickness', '2')
        self.option_add('*Menubutton.highlightThickness', '2')
        self.option_add('*Optionmenu.highlightThickness', '2')
        self.option_add('*Checkbutton.highlightThickness', '2')
        self.option_add('*Radiobutton.highlightThickness', '2')
        self.option_add('*Entry.highlightThickness', '2')
        self.option_add('*Spinbox.highlightThickness', '2')
        self.option_add('*Listbox.highlightThickness', '2')
        self.option_add('*Entry.background', DARK_BG_COLOR)
        self.option_add('*Spinbox.background', DARK_BG_COLOR)
        self.option_add('*Listbox.background', DARK_BG_COLOR)
        self.option_add('*Button.background', BUTTON_BG_COLOR)
        self.option_add('*Menubutton.background', BUTTON_BG_COLOR)
        self.option_add('*Spinbox.readonlyBackground', LIGHT_BG_COLOR)
        self.option_add('*foreground', DEFAULT_FG_COLOR)
        self.option_add('*highlightColor', HIGHLIGHT_COLOR)
        self.option_add('*font', f'{DEFAULT_FONT_FAMILY} {DEFAULT_FONT_SIZE}')
        self.option_add('*Entry.font', f'{MONOSPACE_FONT_FAMILY} {BIG_FONT_SIZE}')
        self.option_add('*Spinbox.font', f'{MONOSPACE_FONT_FAMILY} {BIG_FONT_SIZE}')

        # take some Tkinter colors for Matplotlib canvas
        plt.style.use('dark_background')
        mpl.rcParams['font.size'] = int(SMALL_FONT_SIZE)
        mpl.rcParams['axes.titlesize'] = int(SMALL_FONT_SIZE)
        mpl.rcParams['axes.labelsize'] = int(SMALL_FONT_SIZE)
        mpl.rcParams['xtick.labelsize'] = mpl.rcParams['ytick.labelsize'] = int(LITTLE_FONT_SIZE)
        mpl.rcParams['axes.facecolor'] = self.option_get('activeBackground', 'DTApplication')
        mpl.rcParams['figure.facecolor'] = self.option_get('activeBackground', 'DTApplication')
        mpl.rcParams['figure.edgecolor'] = self.option_get('background', 'DTApplication')
        mpl.rcParams['lines.markersize'] = 4
        mpl.rcParams["lines.linewidth"] = 1.5
        mpl.rcParams["grid.linewidth"] = 0.5
        mpl.rcParams["axes.linewidth"] = 1.0
        mpl.rcParams["axes.xmargin"] = 0.0
        mpl.rcParams["figure.constrained_layout.use"] = True
        mpl.rcParams["figure.constrained_layout.h_pad"] = 0.06
        mpl.rcParams["figure.constrained_layout.w_pad"] = 0.1
        mpl.rcParams["figure.constrained_layout.hspace"] = 0.02
        #mpl.rcParams["axes.autolimit_mode"] = 'round_numbers'

    def run(self):
        """Start GUI event loop
        """
        print(f'DTApplication started at {asctime()}')

        self.mainloop()

        print('Exiting DTApplication')
        if self.taskProcess.is_alive():
            self.taskConn.send('terminate')
            # self.taskProcess.join()
        self.taskConn.close()

    def startTaskProcess(self):
        """Method for starting a separate process for measurements
        """
        if not hasattr(self, 'taskConn') and not hasattr(self, 'childTaskConn'):
            self.taskConn, self.childTaskConn = Pipe()
        if hasattr(self, 'taskProcess'):
            del self.taskProcess
        self.taskProcess = DTProcess(self.childTaskConn)
        self.taskProcess.start()
        print(f'DTProcess spawned with pid {self.taskProcess.pid}')
        # write pid of the task process to file
        with open(self.__tkPidFilename, 'a') as f:
            f.write(str(self.taskProcess.pid) + '\n')
        # setpriority(PRIO_PROCESS, self.taskProcess.pid, -20)

    def __startTaskProcessWithChecking(self):
        if not hasattr(self, 'taskProcess') or not self.taskProcess.is_alive():
            self.startTaskProcess()
        self.after(10000, self.__startTaskProcessWithChecking)  # check every 10 sec that DTProcess is running

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
        tk.Message(w, text=message, justify=tk.LEFT, aspect=200).grid(row=0, column=1, sticky=tk.W+tk.E)
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
    def __init__(self, master):
        super().__init__(master)
        self.figure = None
        self.gridOn = True  # flag for adding grid to exes
        self.configure(padx=3, pady=3)
        self.columnconfigure(0, minsize=int(0.6*_rootWindowWidth))
        self.rowconfigure(0, pad=5)
        self.rowconfigure(1, weight=1)

        self.ncolors = len(mpl.rcParams["axes.prop_cycle"])

        self.__createControls()
        self.__createCanvas()

    def __createControls(self):
        frame = tk.Frame(self, padx=10)
        frame.grid(row=0, sticky=tk.N+tk.E+tk.W)

        styles = ('  - ', '   .', '  -.', '   o', '  -o', '   ,')
        self.styleVars = [None] * self.ncolors
        self.styleFrames = [None] * self.ncolors
        mplcolors = mpl.rcParams["axes.prop_cycle"]
        for ic, c in enumerate(mplcolors):
            frame.columnconfigure(ic, weight=1)
            self.styleFrames[ic] = sframe = tk.Frame(frame, padx=5, pady=3)
            tk.Label(sframe, text=('Стиль %d' if dtg.LANG == 'ru' else f'Style %d') % (ic+1), fg=c['color'])\
                .grid(row=0, column=0, sticky=tk.E, padx=5)
            self.styleVars[ic] = tk.StringVar()
            self.styleVars[ic].set(styles[0])
            menu = tk.OptionMenu(sframe, self.styleVars[ic], *styles)
            menu.configure(takefocus=True, font={MONOSPACE_FONT_FAMILY, DEFAULT_FONT_SIZE},fg=c['color'])
            menu.grid(row=0, column=1, sticky=tk.W)
        self.styleFrames[0].grid()  # for right canvas size

    def __createCanvas(self):
        self.canvasFrame = frame = tk.Frame(self, padx=0, pady=0)
        frame.grid(row=1, sticky=tk.N+tk.S+tk.E+tk.W)
        self.figure = Figure(figsize=(6.4, 6))  # make it big first
        canvas = FigureCanvasTkAgg(self.figure, master=frame)
        canvas.draw()
        canvas.mpl_connect('scroll_event', self.__scrollAxesHandler)
        canvas.mpl_connect('button_press_event', self.__buttonPressHandler)
        canvas.mpl_connect('motion_notify_event', self.__mouseMoveHandler)
        canvas.mpl_connect('button_release_event', self.__buttonReleaseHandler)
        canvasWidget = canvas.get_tk_widget()
        canvasWidget.configure(bg=LIGHT_BG_COLOR, takefocus=False)  # not styled previously, why?
        canvasWidget.grid()
        self.updateFigSize = True
        self.updateScheduled = False
        self.canvasUpdateScheduled = False

    def __scrollAxesHandler(self, event):
        ax = event.inaxes
        if ax is None or len(ax.lines) == 0:
            return
        line = ax.lines[0]
        xdata = line.get_xdata()
        if len(xdata) <= 1:
            return
        mleft, mright = ax.margins()
        xleft, xright = xdata[0]-mleft*(xdata[-1]-xdata[0]), xdata[-1]+mright*(xdata[-1]-xdata[0])
        x0 = event.xdata
        xmin, xmax = ax.get_xlim()
        if event.step == -1 and (xmin <= xdata[0] and xmax >= xdata[-1]) or\
           event.step == 1 and (xmax-xmin) <= xdata[1] - xdata[0] or\
           event.step == 0:
            return
        xlstep = 0.05*(x0-xmin)
        xrstep = 0.05*(xmax-x0)
        xmin += event.step * xlstep
        xmax -= event.step * xrstep
        xmin = max(xmin, xleft)
        xmax = min(xmax, xright)
        if xmin == xleft and xmax == xright:
            ax.set_autoscalex_on(True)
        else:
            ax.set_xlim(xmin, xmax)
        ax.autoscale_view(tight=True)
        if not self.canvasUpdateScheduled:
            self.canvasUpdateScheduled = True
            self.after(100, self.__canvasUpdate)

    def __buttonPressHandler(self, event):
        self.pressData = [None]*2
        if event.button != 1 or event.inaxes is None or len(event.inaxes.lines) == 0:
            return
        ax = event.inaxes
        x1 = event.xdata
        ymin, ymax = ax.get_ylim()
        zoomBox = plt.Rectangle((x1, ymin), 0, (ymax-ymin), ls='--', ec="c", fc="c", alpha=0.3)
        ax.add_patch(zoomBox)
        self.pressData = [ax, zoomBox]
        ax.set_autoscaley_on(False)
        ax.autoscale_view(tight=True)
        self.__canvasUpdate()

    def __mouseMoveHandler(self, event):
        if event.button != 1 or event.inaxes is None or len(event.inaxes.lines) == 0 or\
           self.pressData[0] is None or self.pressData[0] != event.inaxes:
            return

        zoomBox = self.pressData[1]
        x1 = zoomBox.get_x()
        x2 = event.xdata
        zoomBox.set_width(x2-x1)
        if not self.canvasUpdateScheduled:
            self.canvasUpdateScheduled = True
            self.after(100, self.__canvasUpdate)

    def __buttonReleaseHandler(self, event):
        if self.pressData[1] is not None:
            ax = self.pressData[0]
            zoomBox = self.pressData[1]
            x1 = zoomBox.get_x()
            x2 = event.xdata if event.xdata else x1+zoomBox.get_width()
            x1, x2 = sorted([x1, x2])
            for p in ax.patches:
                del p
            ax.patches = []
            self.pressData = [None]*2
            ax.set_autoscaley_on(True)
            if len(ax.lines) > 0:
                x = ax.lines[0].get_xdata()
                if len(x) > 1 and x2-x1 > x[1]-x[0]:
                    ax.set_xlim(x1, x2)
                    ax.relim(True)
            ax.autoscale_view(tight=False)
            self.__canvasUpdate()

        ax = event.inaxes
        if event.button == 3 and ax is not None:
            ax.set_autoscalex_on(True)
            ax.relim(True)
            ax.autoscale_view(tight=False)
            self.__canvasUpdate()

    def __canvasUpdate(self):
        self.figure.canvas.draw()
        self.figure.canvas.flush_events()
        self.canvasUpdateScheduled = False

    def plotGraphs(self, results: dict):
        """Plot all marked results. Create new subplots for the first time and
           updating them if marked results are the same as in previous call.
           results structure:
             {reskey: {'draw': bool, 'type': ('time'|'freq'), 'n': size, 'x': array, 'y': array},...}
        """
        if not hasattr(self, 'pkeys'):
            self.pkeys = None
        ckeys = dict([(k, r['type']) for k, r in results.items() if r['draw'] and r['n'] > 0])
        nres = len(ckeys)
        if nres == 0:
            if self.pkeys != ckeys:
                self.pkeys = ckeys
                self.clearCanvas()
            return

        if self.updateFigSize:
            h, w = self.canvasFrame.winfo_height(), self.canvasFrame.winfo_width()
            # print(w, h)
            dpi = self.figure.dpi
            self.figure.set_size_inches(w/dpi, h/dpi)  # real dpi differs?
            self.updateFigSize = False

        if self.pkeys != ckeys or len(self.figure.axes) == 0:
            # plot new
            self.pkeys = ckeys
            self.figure.clf()
            types = list(set([typ for k, typ in ckeys.items()]))  # unique type list
            ntypes = len(types)
            self.figure.subplots(nres, 1, sharex=(ntypes == 1), subplot_kw=dict(autoscale_on=True))
            axes = self.figure.axes
            for i, (ax, key, typ) in enumerate(zip(axes, ckeys.keys(), ckeys.values())):
                self.styleFrames[i].grid(row=0, column=i)
                result = results[key]
                n = result['n']
                color = f'C{i%self.ncolors}'  # cycle colors
                xlabel = ''
                if typ == 'time':
                    x = result['x'][:n]
                    y = result['y'][:n]
                    if ntypes == 1 and i == nres-1 or ntypes > 1:
                        xlabel = 'Время [с]' if dtg.LANG == 'ru' else 'Time [s]'
                    yunit = dtg.units[dtResultDesc[key]['dunit']][dtg.LANG]
                    title = f'{dtResultDesc[key][dtg.LANG]} [{yunit}]'
                elif typ == 'freq':
                    x = result['x']
                    y = result['y']
                    if ntypes == 1 and i == nres-1 or ntypes > 1:
                        xlabel = 'Частота [Гц]' if dtg.LANG == 'ru' else 'Frequency [Hz]'
                    title = f'Амплитуда [В/Гц]' if dtg.LANG == 'ru' else 'Amplitude {key}'
                    ax.semilogy()
                elif typ == 'adc':
                    x = result['x']
                    y = result['y']
                    if ntypes == 1 and i == nres-1 or ntypes > 1:
                        xlabel = 'Время [мс]' if dtg.LANG == 'ru' else 'Time [ms]'
                    title = f'Амплитуда [В]' if dtg.LANG == 'ru' else 'Amplitude [V]'
                else:
                    continue

                ax.plot(x, y, color=color)
                ax.set_xlabel(xlabel)
                ls, m = [('' if c == ' ' else c) for c in self.styleVars[i].get()[2:]]
                ax.lines[0].set_ls(ls)
                ax.lines[0].set_marker(m)
                ax.set_title(title)
                ax.grid(self.gridOn, 'major')
        else:
            # update plots
            axes = self.figure.axes
            assert(len(axes) == nres)
            for i, (ax, key, typ) in enumerate(zip(axes, ckeys.keys(), ckeys.values())):
                result = results[key]
                n = result['n']
                if typ == 'time':
                    x = result['x'][:n]
                    y = result['y'][:n]
                else:
                    x = result['x']
                    y = result['y']
                line2d = ax.lines[0]
                xprev = line2d.get_xdata()
                line2d.set_data(x, y)
                ls, m = [('' if c == ' ' else c) for c in self.styleVars[i].get()[2:]]
                line2d.set_ls(ls)
                line2d.set_marker(m)
                if typ == 'time' and not ax.get_autoscalex_on():
                    xmin, xmax = ax.get_xlim()
                    dx = x[-1]-xprev[-1]
                    ax.set_xlim(xmin+dx, xmax+dx)
                ax.relim(True)
                ax.autoscale_view(tight=True)

        self.__updateAxes()

    def __updateAxes(self):
        self.updateScheduled = False
        if self.figure is None:
            return
        axes = self.figure.axes
        if len(axes) == 0:
            return
        for (i, ax) in enumerate(axes):
            ls, m = [('' if c == ' ' else c) for c in self.styleVars[i].get()[2:]]
            if len(ax.lines) == 0:
                continue
            line2d = ax.lines[0]
            line2d.set_ls(ls)
            line2d.set_marker(m)

        for i in range(max(1, len(axes)), len(self.styleFrames)):
            if self.styleFrames[i].winfo_ismapped():
                self.styleFrames[i].grid_forget()

        self.__canvasUpdate()
        self.after(1000, self.__updateAxes)

    def clearCanvas(self):
        if DTApplication.DEBUG:
            print('DTPlotFrame.clearCanvas(): clearing canvas')
        self.figure.clf()
        for sframe in self.styleFrames[1:]:
            if sframe.winfo_ismapped():
                sframe.grid_forget()
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
            self.delScenarioMB['state'] = self.runScenarioMB['state'] = tk.NORMAL
            self.scenariosText.set(f'{nscenarios} сценариев определено')

    def __deleteScenario(self, scenario: DTScenario):
        resp = tkmsg.askyesno('Удаление сценария', 'Удалить сценарий '+scenario.name+'?', icon=tkmsg.QUESTION)
        if not resp:
            return
        del tasks.dtAllScenarios[scenario.name]
        nscenarios = len(tasks.dtAllScenarios)
        self.scenariosText.set(f'{nscenarios} сценариев определено')
        if nscenarios == 0:
            self.delScenarioMB['state'] = self.runScenarioMB['state'] = tk.DISABLED

    def __chooseTask(self, taskType: DTTask):
        task: DTTask = taskType()
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

        label = tk.Label(self.logoFrame)
        label.grid(row=0, sticky=tk.N, padx=10, pady=5)
        if self.master.logo is not None:
            label.configure(image=self.master.logo)

        text = dtg.appInfo[dtg.LANG]

        # add a text Frame
        textbox = tk.Text(self.logoFrame, padx="2m", pady="1m", wrap=tk.WORD,
                          font={DEFAULT_FONT_FAMILY, BIG_FONT_SIZE})

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

        for i in range(1, 6):
            self.menuFrame.rowconfigure(i, pad=20)
        self.menuFrame.rowconfigure(6, pad=10, weight=1)
        self.menuFrame.rowconfigure(7, weight=1)

        self.scenariosText = tk.StringVar()
        self.scenariosText.set(f'{len(tasks.dtAllScenarios)} сценариев определено')
        tk.Label(self.menuFrame, textvariable=self.scenariosText).grid(row=0)

        csmb = self.runScenarioMB = tk.Menubutton(self.menuFrame, text='Запустить сценарий')
        csmb.configure(relief=tk.RAISED, height=2, highlightthickness=2, takefocus=True)
        csmb['menu'] = csmb.menu = DTChooseObjectMenu(csmb, command=self.__runScenario,
                                                      objects=tasks.dtAllScenarios)
        csmb.grid(row=1, sticky=tk.W+tk.E)

        cmmb = tk.Menubutton(self.menuFrame, text='Выбрать измерение')
        cmmb.configure(relief=tk.RAISED, height=2, highlightthickness=2, takefocus=True)
        cmmb['menu'] = cmmb.menu = DTChooseObjectMenu(cmmb, command=self.__chooseTask,
                                                      objects=tasks.dtTaskTypes)
        cmmb.grid(row=2, sticky=tk.W+tk.E)

        csb = tk.Button(self.menuFrame, text='Создать сценарий')
        csb.configure(command=self.__newScenario, height=2, highlightthickness=2)
        csb.grid(row=3, sticky=tk.W+tk.E)
        csb.focus()

        cdsb = self.delScenarioMB = tk.Menubutton(self.menuFrame, text='Удалить сценарий')
        cdsb.configure(relief=tk.RAISED, height=2, highlightthickness=2, takefocus=True)
        cdsb['menu'] = cdsb.menu = DTChooseObjectMenu(cdsb, command=self.__deleteScenario,
                                                      objects=tasks.dtAllScenarios)
        cdsb.grid(row=4, sticky=tk.W+tk.E)

        self.debugVar = tk.IntVar()
        cdb = tk.Checkbutton(self.menuFrame, text='Отладка')
        cdb.configure(variable=self.debugVar, padx=3, command=self.__setDebug)
        cdb.grid(row=5, sticky=tk.W)

        saveb = tk.Button(self.menuFrame, text='Сохранить\nконфигурацию')
        saveb.configure(height=2, command=DTConfiguration().save)
        saveb.grid(row=6, sticky=tk.W+tk.E+tk.S)

        quitb = tk.Button(self.menuFrame, text='Выход', command=self.quit, height=2)
        quitb.grid(row=7, sticky=tk.W+tk.E+tk.S)

        if len(tasks.dtAllScenarios) == 0:
            cdsb['state'] = tk.DISABLED
            csmb['state'] = tk.DISABLED


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
            DTApplication().showMessage('Нет введенных задач!', master=self, status='error')
            # tkmsg.showinfo('', 'Нет введенных задач!')
            return

        name = self.nameVar.get()
        if name in tasks.dtAllScenarios:
            tkmsg.showerror('Ошибка', f'Сценарий с именем "{name}" уже существует!')
            # DTApplication().showMessage(f'Сценарий с именем "{name}" уже существует!', master=self, status='error')
            return
        if name == '':
            tkmsg.showerror('Ошибка', 'Пустое имя сценария!')
            # DTApplication().showMessage('Пустое имя сценария!', master=self, status='error')
            return

        seltasks = self.taskListVar.get().strip('(,)')
        tnameslist = [s.strip("' ") for s in seltasks.split(',')]
        DTScenario(name, tnameslist)
        self.destroy()
        tkmsg.showinfo('', f'{name} создан')
        # DTApplication().showMessage(f'"{name}" создан')

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
    def __init__(self, master=None, task: DTTask = None, state=None):
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
        self.resHistSize = 20000  # maximum number of points in history
        self.maxResPerCol = 2  # maximum number of results per column

        # set when finished dealing with the current task
        self.frameFinished = tk.IntVar()

        self.tostop = tk.IntVar()
        self.restart = tk.IntVar()

        self.__createWidgets()

        # self.after(100, self.__runTask)  # start running immediately

    def __createWidgets(self):
        """Build all widgets"""
        self.configure(padx=10, pady=5)
        self.rowconfigure(0, pad=10)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=6)
        self.columnconfigure(1, weight=4)

        tk.Label(self, text=self.task.name[dtg.LANG], height=2, relief=tk.GROOVE,
                 borderwidth=3, font=(DEFAULT_FONT_FAMILY, BIG_FONT_SIZE))\
            .grid(row=0, column=0, columnspan=2, sticky=tk.W+tk.E+tk.N)

        self.leftFrame = tk.Frame(self)
        self.leftFrame.rowconfigure(1, weight=1)
        self.leftFrame.grid(row=1, column=0, sticky=tk.N+tk.S+tk.W)

        self.rightFrame = tk.Frame(self)
        self.rightFrame.rowconfigure(2, weight=1)
        self.rightFrame.grid(row=1, column=1, sticky=tk.N+tk.S+tk.E)

        self.__createStatusFrame()
        self.__createMenu()
        self.__createParameters()
        self.__createResults()

    def __validatePar(self, wname, after):
        widget = self.nametowidget(wname)
        for par, parentry in self.parentries.items():
            if parentry is widget:
                break
        if not DTTask.check_parameter(par, after):
            widget.configure(bg='red')
        else:
            widget.configure(bg=widget.option_get('background', 'Spinbox'))
            prevpar = self.task.parameters[par]
            self.task.set_conv_par(par, after)
            if prevpar != self.task.parameters[par] and par.split(' ')[0] not in self.task.results:
                self.__flushPipe()
                self.restart.set(1)
        return True

    def __createParameters(self):
        """Create frame with parameters of the task"""
        paramFrame = tk.LabelFrame(self.rightFrame, text="ПАРАМЕТРЫ")
        paramFrame.configure(labelanchor='n', padx=10, pady=5, relief=tk.GROOVE, borderwidth=3)
        paramFrame.grid(row=0, sticky=tk.W+tk.E+tk.N)

        self.parvars = dict()
        self.parentries = dict()

        validateCall = self.register(self.__validatePar)

        irow = 0
        for par in self.task.parameters:
            partuple = self.task.get_conv_par_all(par)
            if partuple is None:
                continue

            paramFrame.rowconfigure(irow, pad=5)

            # distribute tuple to named variables
            pname, ptype, pvalue, plowlim, puplim, pincr, pavalues, pformat, punit, preadonly = partuple

            tk.Label(paramFrame, text=pname+':').grid(row=irow, column=0, sticky=tk.E)

            parvar = tk.StringVar()
            if ptype is Integral and isinstance(pvalue, Integral):
                dvalue = str(int(pvalue))
            else:
                dvalue = ('%'+pformat) % pvalue
            parvar.set(dvalue)

            self.parvars[par] = parvar

            entry = tk.Spinbox(paramFrame, textvariable=parvar, width=10,
                               justify=tk.RIGHT, format='%'+pformat)
            if preadonly:
                entry.configure(state='readonly')
            else:
                self.parentries[par] = entry
                entry.configure(from_=plowlim, to=puplim,
                                validate='key', validatecommand=(validateCall, '%W', '%P'))
                if pavalues is not None:
                    entry.configure(values=pavalues)
                else:  # use increment
                    entry.configure(increment=pincr)

            entry.grid(row=irow, column=1, sticky=tk.W, padx=3)

            tk.Label(paramFrame, text=punit).grid(row=irow, column=2, sticky=tk.W)

            irow += 1

    def __createResults(self):
        """Create frame to show results of the task"""
        resultFrame = tk.LabelFrame(self.leftFrame, text='ИЗМЕРЕНИЕ')
        resultFrame.configure(labelanchor='n', padx=10, pady=5, relief=tk.GROOVE, borderwidth=3)
        resultFrame.grid(row=0, sticky=tk.W+tk.E+tk.N)

        if not self.task.single:
            self.plotFrame = DTPlotFrame(self.leftFrame)
            self.plotFrame.grid(row=1, sticky=tk.W+tk.E+tk.S)
        else:
            self.plotFrame = None

        try:
            mplcolors = mpl.rcParams["axes.prop_cycle"]
            self.actplotimgs = [None]*len(mplcolors)
            # self.actplotimg = tk.PhotoImage(file=DTApplication().imgdir + '/plot.gif')
            # self.inactplotimg = tk.PhotoImage(file=DTApplication().imgdir + '/grayplot.gif')
            self.actplotimg = tk.BitmapImage(file=DTApplication().imgdir + '/plot.xbm',
                                             background='white')
            for i, c in enumerate(mplcolors):
                self.actplotimgs[i] = tk.BitmapImage(file=DTApplication().imgdir + '/plot.xbm',
                                                     background=c['color'])
                self.inactplotimg = tk.BitmapImage(file=DTApplication().imgdir + '/plot.xbm',
                                                   background=self.option_get('activeBackground', 'Checkbutton'))
        except tk.TclError:
            print_exc()
            self.actplotimg = self.inactplotimg = None

        self.reslabels = dict()  # labels with results
        self.plotvars = dict()  # states of checkboxes controlling what vars to plot
        self.plotcbs = dict()  # plot Checkbuttons

        for i in range(self.maxResPerCol):
            resultFrame.rowconfigure(i, pad=10)

        resultFrame.columnconfigure(0, weight=1)
        resultFrame.columnconfigure(4, weight=1)

        i = 0
        for res in self.task.results:
            if res not in dtResultDesc:
                continue

            irow = i % self.maxResPerCol
            icol = 4 * (i // self.maxResPerCol)
            i += 1

            resdata = dtResultDesc[res]
            name = resdata[dtg.LANG]

            if resdata['format'] != '':
                unitname = dtg.units[resdata['dunit']][dtg.LANG]

                valframe = tk.Frame(resultFrame, relief=tk.SUNKEN, bd=2,
                                    bg=self.option_get('background', 'Entry'), padx=4, pady=2)
                valframe.columnconfigure(0, minsize=135)
                valframe.grid(row=irow, column=icol+1, sticky=tk.W+tk.E, padx=3)
                self.reslabels[res] = reslabel = tk.Label(valframe, text='----',
                                                          font=(MONOSPACE_FONT_FAMILY, BIG_FONT_SIZE))
                reslabel.grid(sticky=tk.E)

                tk.Label(resultFrame, text=unitname, justify=tk.LEFT).grid(row=irow, column=icol+2, sticky=tk.W)

            tk.Label(resultFrame, text=name+':', justify=tk.RIGHT).grid(row=irow, column=icol, sticky=tk.E)

            if self.plotFrame is None:
                continue

            self.plotvars[res] = tk.IntVar()

            cb = self.plotcbs[res] = tk.Checkbutton(resultFrame, command=self.__checkPlots)
            cb.configure(indicatoron=0, variable=self.plotvars[res], padx=3, pady=3)
            if self.actplotimg:
                cb.configure(image=self.inactplotimg, selectimage=self.actplotimg)
            else:
                cb.configure(text='Рисовать')
            cb.grid(row=irow, column=icol+3, padx=5, sticky=tk.W)

        self.__resetResHist()

    def __createStatusFrame(self):
        statusFrame = tk.Frame(self.rightFrame, relief=tk.SUNKEN, bd=2, padx=5, pady=3)
        statusFrame.grid(row=2, sticky=tk.W+tk.E+tk.N, pady=5)

        self.messagebox = tk.Message(statusFrame, justify=tk.LEFT, width=300)
        self.messagebox.grid(sticky=tk.W+tk.E)
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
            self.messagebox.configure(text=lastResult.message, foreground='red')
            self.bell()
            return
        elif self.task.single and lastResult.completed:
            self.messagebox.configure(text='ЗАВЕРШЕНО', foreground='green')
            return
        elif lastResult.completed:
            self.progress += len(self.resultBuffer)
            if lastResult.message:
                self.messagebox.configure(text=lastResult.message, foreground='yellow')
            else:
                self.messagebox.configure(text=f'ИЗМЕРЕНО: {self.progress}', foreground='green')
        elif lastResult.inited:
            self.messagebox.configure(text='ИЗМЕРЕНИЕ...', foreground='green')
            return
        else:
            print(lastResult)
            self.messagebox.configure(text='Неизвестное состояние', foreground='red')
            return

        self.task.results_from(lastResult)

        if hasattr(self.task, 'save_cal'):
            self.task.save_cal()

        allbadpars = []
        for res in self.reslabels:
            reslabel: tk.Label = self.reslabels[res]
            value = lastResult.get_conv_res(res)
            if value is not None:
                fmt = f'%{dtResultDesc[res]["format"]}'
                ok, show, badpars = self.task.check_result(res)
                if not ok:
                    reslabel.configure(fg='red')
                    self.bell()
                else:
                    reslabel.configure(fg=self.option_get('foreground', 'Label'))
                reslabel['text'] = (show if show else '') + fmt % value
                if badpars:
                    allbadpars.extend(badpars)
            else:
                reslabel.configure(fg=self.option_get('foreground', 'Label'))
                reslabel['text'] = '----'

            for par in self.parentries:
                if par in allbadpars:
                    self.parentries[par].configure(fg='red')
                elif self.parentries[par]['fg'] == 'red':
                    self.parentries[par].configure(fg=self.option_get('foreground', 'Spinbox'))

        self.__updateAndPlotGraphs()

    def __updateAndPlotGraphs(self):
        if self.plotFrame is None:
            return
        for res in self.plotvars:
            presult = self.presults[res]
            if presult['type'] == 'time':
                # update time data for plotting
                n = presult['n']
                nadd = len(self.resultBuffer)
                if n + nadd > self.resHistSize:
                    # avoid overflow, copy previously gathered data but no more than 0.5 of resHistSize
                    #  or data that plotted
                    startTime = self.resultBuffer[-1].time - 60
                    startCopyIndex = max(np.searchsorted(presult['x'], startTime, side='left'),
                                         self.resHistSize//2)
                    copySize = self.resHistSize - startCopyIndex
                    presult['x'][:copySize] = presult['x'][startCopyIndex:]
                    presult['y'][:copySize] = presult['y'][startCopyIndex:]
                    n = copySize
                for rtask in self.resultBuffer:
                    value = rtask.get_conv_res(res)
                    if value is not None:
                        presult['x'][n] = rtask.time
                        presult['y'][n] = value
                        n += 1
                    presult['n'] = n
            elif presult['type'] == 'freq':
                # prepare FFT data for plotting
                presult['y'] = y = self.resultBuffer[-1].results[res]
                if presult['n'] != y.size:
                    presult['x'] = rfftfreq((y.size-1)*2, 1./dtg.adcSampleFrequency)
                    presult['n'] = y.size
            elif presult['type'] == 'adc':
                # prepare ADC data for plotting
                presult['y'] = y = self.task.results[res]
                if presult['n'] != y.size:
                    presult['x'] = linspace(0, 1000*y.size/dtg.adcSampleFrequency, y.size, endpoint=False)
                    presult['n'] = y.size

        self.plotFrame.plotGraphs(self.presults)

    def __checkPlots(self):
        if self.plotFrame is None:
            return
        actImgIter = iter(self.actplotimgs)
        colorIter = iter(mpl.rcParams["axes.prop_cycle"])
        for res in self.plotcbs:
            cb: tk.Checkbutton = self.plotcbs[res]
            # Prepare for plotting results
            presult = self.presults[res]
            presult['draw'] = draw = self.plotvars[res].get() != 0
            if draw:
                cb.configure(selectimage=next(actImgIter), foreground=next(colorIter)['color'])
        self.plotFrame.plotGraphs(self.presults)

    def __resetResHist(self):
        if DTApplication.DEBUG:
            print('DTTaskFrame.__resetResHist(): creating/resetting data storage for plotting')
        if not hasattr(self, 'presults'):
            self.presults = dict()
        for res in self.plotvars:
            if res in self.presults:
                self.presults[res]['n'] = 0
            else:
                if res == 'ADC':
                    # stub for ADC data
                    self.presults[res] = dict(draw=False, type='adc', n=0, x=None, y=None)
                elif res == 'FFT':
                    # stub for FFT data
                    self.presults[res] = dict(draw=False, type='freq', n=0, x=None, y=None)
                else:
                    # init time data storage
                    self.presults[res] = dict(draw=False,
                                              type='time',
                                              n=0,  # number of points
                                              x=np.zeros(self.resHistSize, dtype='float32'),
                                              y=np.zeros(self.resHistSize, dtype='float32'))

    def __checkRun(self):
        try:
            taskConn = DTApplication().taskConn
            if not DTApplication().taskProcess.is_alive():  # unexpected stop of DTProcess
                tkmsg.showerror('DTProcess got stopped. Restarting.')
                DTApplication().startTaskProcess()
                raise DTUIError('run stopped')

            if self.tostop.get() == 1:  # stop from the user
                if DTApplication.DEBUG:
                    print('DTTaskFrame.__checkRun(): User requested stop. Sending stop to DTProcess.')
                raise DTUIError('stop run')

            if self.restart.get() == 1:
                if DTApplication.DEBUG:
                    print(f'DTTaskFrame.__checkRun(): Parameters are changed. Restart run.')
                raise DTUIError('restart run')

            self.resultBuffer = list()  # list of last DTTask-s with results
            while taskConn.poll():  # new task data are available for retrieving
                msg = taskConn.recv()  # retrieve task object
                if isinstance(msg, DTTask) and msg.id == self.task.id:
                    self.resultBuffer.append(msg)
                elif msg == self.stoppedMsg:  # task run finished
                    if DTApplication.DEBUG:
                        print('DTTaskFrame.__checkRun(): Task run finished')
                    raise DTUIError('run stopped')
                elif isinstance(msg, Exception):
                    raise msg

            if len(self.resultBuffer) > 0:
                if DTApplication.DEBUG:
                    print(f'DTTaskFrame.__checkRun(): Updating frame with task results')
                self.__update()

        except Exception as exc:
            if isinstance(exc, DTUIError):
                if exc.source == 'stop run':
                    taskConn.send('stop')
                elif exc.source == 'restart run':
                    taskConn.send('stop')
                    self.after(100, self.__runTask)
                    self.__configPauseButton()
                    return
                elif exc.source == 'run stopped':
                    if len(self.resultBuffer) > 0:
                        if DTApplication.DEBUG:
                            print(f'DTTaskFrame.__checkRun(): Last updating frame with task results')
                        self.__update()
            else:
                print('DTTaskFrame.__checkRun(): Exception caught. Stopping task run.')
                print_exc()
                tkmsg.showerror('Application error', format_exception_only(type(exc), exc))
            self.__flushPipe()
            self.__configStartButton()
        else:
            self.after(100, self.__checkRun)  # check for measurements every 0.1 sec

    def __runTask(self):
        if DTApplication.DEBUG:
            print('DTTaskFrame.__runTask() entered')
        self.tostop.set(0)
        self.restart.set(0)
        self.messagebox.configure(text='')
        self.progress = 0
        # clear leftovers in the pipe
        self.__flushPipe()

        self.__resetResHist()

        self.plotFrame.clearCanvas()

        for par in self.parvars:
            self.task.set_conv_par(par, self.parvars[par].get())

        self.task.load_cal()

        if not DTApplication().taskProcess.is_alive():  # unexpected stop of DTProcess
            tkmsg.showerror('DTProcess is dead. Restarting.')
            DTApplication().startTaskProcess()

        self.task.set_id(self.task.id+1)  # increment id for the next run
        self.stoppedMsg = f'stopped {self.task.id}'
        self.task.clear_results()
        DTApplication().taskConn.send(self.task)

        self.__configStopButton()

        if DTApplication.DEBUG:
            print('DTTaskFrame.__runTask(): Schedule __checkRun()')
        self.after(10, self.__checkRun())

    def __flushPipe(self):
        if DTApplication.DEBUG:
            print(f'DTTaskFrame.__flushPipe(): flushing pipe reading')
        conn = DTApplication().taskConn
        while conn.poll():
            conn.recv()

    def __configStartButton(self):
        self.startButton.configure(text='Запуск', command=self.__runTask, bg='#21903A', activebackground='#3CA54D',
                                   state=tk.NORMAL)

    def __configStopButton(self):
        self.startButton.configure(text='Остановить', command=self.__stopRun, bg='#A50D00', activebackground='#C63519',
                                   state=tk.NORMAL)

    def __configPauseButton(self):
        self.startButton.configure(state=tk.DISABLED)

    def __stopRun(self):
        if DTApplication.DEBUG:
            print('DTTaskFrame.__stopRun(): Stop button is pressed')
        self.tostop.set(1)

    def __goPrev(self):
        if DTApplication.DEBUG:
            print('DTTaskFrame.__goPrev(): Signalling task stop')
        self.direction = -1
        self.__flushPipe()  # flush pipe input and discard delayed measurements & probably 'stopped' message
        DTApplication().taskConn.send('stop')  # sending 'stop' to DTProcess
        self.frameFinished.set(1)

    def __goNext(self):
        if DTApplication.DEBUG:
            print('DTTaskFrame.__goNext(): Signalling task stop')
        self.direction = 1
        self.__flushPipe()  # flush pipe input and discard delayed measurements & probably 'stopped' message
        DTApplication().taskConn.send('stop')  # sending 'stop' to DTProcess
        self.frameFinished.set(1)

    def __goMainMenu(self):
        if DTApplication.DEBUG:
            print('DTTaskFrame.__goMainMenu(): Signalling task stop')
        self.direction = 0
        self.__flushPipe()  # flush pipe input and discard delayed measurements & probably 'stopped' message
        DTApplication().taskConn.send('stop')  # sending 'stop' to DTProcess
        self.frameFinished.set(1)

    def destroy(self):
        if DTApplication.DEBUG:
            print('DTTaskFrame.destroy(): called')
        super().destroy()
