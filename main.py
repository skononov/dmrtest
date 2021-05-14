import os, sys
import tkinter as tk

from widgets import *

__appname: str = 'DMR TEST'
__version__: str = ''

def main():
    root = tk.Tk()
    root.geometry("800x640+400+320")
    root.title(__appname+' '+ __version__)
    
    logo = DTLogoFrame(root)
    mainMenu = DTMainMenuFrame(root)

    tk.mainloop()

if __name__ == "__main__":
    main()