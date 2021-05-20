"""
A modified copy of easygui, to serve as a driver for the programs in 
Thinking In Tkinter.

"""


"""===============================================================
REVISION HISTORY
2 2002-10-08 re-cloned from easygui.py version 24, to pick up font fixes.
1 2002-09-21 Steve Ferg cloned it from easygui.py version 23.
=================================================================="""
"""
EasyGui provides an easy-to-use interface for simple GUI interaction
with a user.  It does not require the programmer to know anything about
tkinter, frames, widgets, callbacks or lambda.  All GUI interactions are
invoked by simple function calls that return results.

Note that EasyGui requires Tk release 8.0 or greater.
Documentation is in an accompanying file, easygui_doc.txt.

"""

EasyGuiRevisionInfo = "version 0.3, revision 24, 2002-10-06"
"""===============================================================
REVISION HISTORY
24 2002-10-06 improved control over font family and font size
    Added note that EasyGui requires Tk release 8.0 or greater.
    Added check to verify that we're running Tk 8.0 or greater.

23 2002-09-06 more improvements in appearance, added items to testing choices
    changed order of parameters for textbox and codebox.
    Now ALL widgets have message and title as the first two arguments.
    Note that the fileopenbox, filesavebox, and diropenbox but ignore, the msg argument.
        To specify a title, you must pass arguments of (None, title)

23 2002-09-06 revised enterbox so it returns None if it was cancelled
22 2002-09-02 major improvements in formattting, sorting of choiceboxes, keyboard listeners

22 2002-07-22 fixed some problems cause in revision 21
21 2002-07-19 converted all indentation to tabs
20 2002-07-15 bugfix: textbox not displaying title
19 2002-06-03 added enterbox to the test suite
18 2002-05-16 added AutoListBox
17 2002-05-16 added DEFAULT_FONT_SIZE constants & reduced their size
16 2002-03-29 changed choicebox() so it shows as few lines a possible
15 2002-03-09 started work on an improved demo
14 2002-02-03 removed obsolete import of pmw
13 2002-02-02 added NW spec for choice box
12 2002-01-31 created buttonbox as basis for msgbox, etc.
11 2002-01-30 specified a minsize for msgbox()
10 2002-01-30 withdrew root on diropenbox(), fileopenbox(), filesavebox(), etc.
9 2002-01-26 pulled out winrexx routines into winrexxgui.py
    renamed listbox to choicebox
8 2002-01-25 added diropenbox(), fileopenbox(), filesavebox(), and codebox()
7 2002-01-24 disabled the textbox, so text cannot be edited
6 2002-01-22 added case-insensitive sort for choicebox choices
5 2002-01-21 reworked ynbox() and ccbox() as boolboxes. Ready for version 0.1.
4 2002-01-20 added boolbox(), ynbox(), ccbox(); got choicebox working!
3 2002-01-18 got choicebox to display... not working yet
2 2002-01-17 got the messagebox and entry functions to working OK!
1 2002-01-16 Steve Ferg wrote it.
=================================================================="""

import sys
import tkinter as tk


rootWindowPosition = "400x200+300+200"
import string

DEFAULT_FONT_FAMILY   = ("MS", "Sans", "Serif")
MONOSPACE_FONT_FAMILY = ("Courier")
DEFAULT_FONT_SIZE     = 10
BIG_FONT_SIZE         = 12
SMALL_FONT_SIZE       =  9
CODEBOX_FONT_SIZE     =  9
TEXTBOX_FONT_SIZE     = DEFAULT_FONT_SIZE

import tkinter.filedialog as tkFileDialog

#-------------------------------------------------------------------
# various boxes built on top of the basic buttonbox
#-------------------------------------------------------------------

def ynbox(message="Shall I continue?", title=""):
    """Display a message box with choices of Yes and No.
    Return 1 if Yes was chosen, otherwise return 0

    If invoked without a message parameter, displays a generic request for a confirmation
    that the user wishes to continue.  So it can be used this way:

        if ynbox(): pass # continue
        else: sys.exit(0)  # exit the program
    """

    choices = ["Yes", "No"]
    if title == None: title = ""
    return boolbox(message, title, choices)

def ccbox(message="Shall I continue?", title=""):
    """Display a message box with choices of Continue and Cancel.
    Return 1 if Continue was chosen, otherwise return 0.

    If invoked without a message parameter, displays a generic request for a confirmation
    that the user wishes to continue.  So it can be used this way:

        if ccbox(): pass # continue
        else: sys.exit(0)  # exit the program
    """
    choices = ["Continue", "Cancel"]
    if title == None: title = ""
    return boolbox(message, title, choices)


def boolbox(message="Shall I continue?", title="", choices=["Yes","No"]):
    """Display a boolean message box.
    Return 1 if the first choice was selected, otherwise return 0.
    """
    if title == None:
        if message == "Shall I continue?": title = "Confirmation"
        else: title = ""


    reply = buttonbox(message, title, choices)
    if reply == choices[0]: return 1
    else: return 0


def indexbox(message="Shall I continue?", title="", choices=["Yes","No"]):
    """Display a buttonbox with the specified choices.
    Return the index of the choice selected.
    """
    reply = buttonbox(message, title, choices)
    index = -1
    for choice in choices:
        index = index + 1
        if reply == choice: return index



#-------------------------------------------------------------------
# msgbox
#-------------------------------------------------------------------

def msgbox(message="Shall I continue?", title=""):
    """Display a messagebox
    """
    choices = ["OK"]
    reply = buttonbox(message, title, choices)
    return reply

#-------------------------------------------------------------------
# errorbox
#-------------------------------------------------------------------

def errorbox(message="Text of error", level="error"):
    """Display an errorbox
    """
    levels = {"error": ("Error!", "error"),
              "warning": ("Warning!", "warining"),
              "info": ("Information", "info")
             }

    try:
        title, iconname = levels[level]
    except KeyError:
        title, iconname = "", None

    choices = ["Continue"]
    buttonbox(message, title, choices, iconname)


#-------------------------------------------------------------------
# buttonbox
#-------------------------------------------------------------------
def buttonbox(message="Shall I continue?", title="", choices = ["Button1", "Button2", "Button3"], iconname=None):
    """Display a message, a title, and a set of buttons.
    The buttons are defined by the members of the choices list.
    Return the text of the button that the user selected.
    """

    global root, __replyButtonText, __a_button_was_clicked, __widgetTexts, buttonsFrame

    if title == None: title = ""
    if message == None: message = "This is an example of a buttonbox."

    # __a_button_was_clicked will remain 0 if window is closed using the close button.
    # It will be changed to 1 if the event loop is exited by a click of one of the buttons.
    __a_button_was_clicked = 0

    # Initialize __replyButtonText to the first choice.
    # This is what will be used if the window is closed by the close button.
    __replyButtonText = choices[0]

    root = tk.Tk()
    root.title(title)
    if iconname is not None:
        root.iconname(iconname)
    root.geometry(rootWindowPosition)
    root.minsize(400, 100)

    # ------------- define the frames --------------------------------------------
    messageFrame = tk.Frame(root)
    messageFrame.pack(side=tk.TOP, fill=tk.BOTH)

    buttonsFrame = tk.Frame(root)
    buttonsFrame.pack(side=tk.BOTTOM, fill=tk.BOTH)

    # -------------------- place the widgets in the frames -----------------------
    messageWidget = tk.Message(messageFrame, text=message, width=400)
    messageWidget.configure(font=(DEFAULT_FONT_FAMILY,DEFAULT_FONT_SIZE))
    messageWidget.pack(side=tk.TOP, expand=tk.YES, fill=tk.X, padx='3m', pady='3m')

    __put_buttons_in_buttonframe(choices)

    # -------------- the action begins -----------
    # put the focus on the first button
    __firstWidget.focus_force()
    root.mainloop()
    if __a_button_was_clicked: root.destroy()
    return __replyButtonText

#-------------------------------------------------------------------
# enterbox
#-------------------------------------------------------------------
def enterbox(message="Enter something.", title="", argDefaultText=None):
    """Show a box in which a user can enter some text.
    You may optionally specify some default text, which will appear in the
    enterbox when it is displayed.
    Returns the text that the user entered, or None if he cancels the operation.
    """

    global root, __enterboxText, __enterboxDefaultText, __a_button_was_clicked, cancelButton, entryWidget, okButton

    if title == None: title == ""
    #choices = ["OK", "Cancel"]
    if argDefaultText == None:
        __enterboxDefaultText = ""
    else:
        __enterboxDefaultText = argDefaultText

    __enterboxText = __enterboxDefaultText


    # __a_button_was_clicked will remain 0 if window is closed using the close button]
    # will be changed to 1 if event-loop is quit by a click of one of the buttons.
    __a_button_was_clicked = 0

    root = tk.Tk()
    root.title(title)
    root.iconname('Dialog')
    root.geometry(rootWindowPosition)
    root.bind("Escape", __enterboxCancel)

    # -------------------- put subframes in the root --------------------
    messageFrame = tk.Frame(root)
    messageFrame.pack(side=tk.TOP, fill=tk.BOTH)

    entryFrame = tk.Frame(root)
    entryFrame.pack(side=tk.TOP, fill=tk.BOTH)

    buttonsFrame = tk.Frame(root)
    buttonsFrame.pack(side=tk.BOTTOM, fill=tk.BOTH)

    #-------------------- the message widget ----------------------------
    messageWidget = tk.Message(messageFrame, width="4.5i", text=message)
    messageWidget.pack(side=tk.RIGHT, expand=1, fill=tk.BOTH, padx='3m', pady='3m')

    # --------- entryWidget ----------------------------------------------
    entryWidget = tk.Entry(entryFrame, width=40)
    entryWidget.configure(font=(DEFAULT_FONT_FAMILY,BIG_FONT_SIZE))
    entryWidget.pack(side=tk.LEFT, padx="3m")
    entryWidget.bind("<Return>", __enterboxGetText)
    entryWidget.bind("<Escape>", __enterboxCancel)
    # put text into the entryWidget
    entryWidget.insert(0,__enterboxDefaultText)

    # ------------------ ok button -------------------------------
    okButton = tk.Button(buttonsFrame, takefocus=1, text="OK")
    okButton.pack(expand=1, side=tk.LEFT, padx='3m', pady='3m', ipadx='2m', ipady='1m')
    okButton.bind("<Return>", __enterboxGetText)
    okButton.bind("<Button-1>", __enterboxGetText)

    # ------------------ (possible) restore button -------------------------------
    if argDefaultText != None:
        # make a button to restore the default text
        restoreButton = tk.Button(buttonsFrame, takefocus=1, text="Restore default")
        restoreButton.pack(expand=1, side=tk.LEFT, padx='3m', pady='3m', ipadx='2m', ipady='1m')
        restoreButton.bind("<Return>", __enterboxRestore)
        restoreButton.bind("<Button-1>", __enterboxRestore)

    # ------------------ cancel button -------------------------------
    cancelButton = tk.Button(buttonsFrame, takefocus=1, text="Cancel")
    cancelButton.pack(expand=1, side=tk.RIGHT, padx='3m', pady='3m', ipadx='2m', ipady='1m')
    cancelButton.bind("<Return>", __enterboxCancel)
    cancelButton.bind("<Button-1>", __enterboxCancel)

    # ------------------- time for action! -----------------
    entryWidget.focus_force()    # put the focus on the entryWidget
    root.mainloop()  # run it!

    # -------- after the run has completed ----------------------------------
    if __a_button_was_clicked:
        root.destroy()  # button_click didn't destroy root, so we do it now
        return __enterboxText
    else:
        # No button was clicked, so we know the OK button was not clicked
        __enterboxText = None
        return __enterboxText


def __enterboxGetText(event):
    global root, __enterboxText, entryWidget, __a_button_was_clicked
    __enterboxText = entryWidget.get()
    __a_button_was_clicked = 1
    root.quit()

def __enterboxRestore(event):
    global root, __enterboxText, entryWidget
    entryWidget.delete(0,len(entryWidget.get()))
    entryWidget.insert(0, __enterboxDefaultText)

def __enterboxCancel(event):
    global root,  __enterboxDefaultText, __enterboxText, __a_button_was_clicked
    __enterboxText = None
    __a_button_was_clicked = 1
    root.quit()


#-------------------------------------------------------------------
# choicebox
#-------------------------------------------------------------------
def choicebox(message="Pick something.", title="", choices=["program logic error - no choices specified"]):
    """Present the user with a list of choices.
    Return the choice that he selected, or return None if he cancelled selection.
    """
    global root, __choiceboxText, choiceboxWidget
    global __a_button_was_clicked # cancelButton, okButton
    global choiceboxWidget, choiceboxChoices, choiceboxChoices

    #choiceboxButtons = ["OK", "Cancel"]

    lines_to_show = min(len(choices), 20)
    #lines_to_show = 20

    if title == None: title = ""

    # Initialize __choiceboxText
    # This is the value that will be returned if the user clicks the close icon
    __choiceboxText = None

    # __a_button_was_clicked will remain 0 if window is closed using the close button]
    # will be changed to 1 if event-loop is quit by a click of one of the buttons.
    __a_button_was_clicked = 0

    root = tk.Tk()

    root.title(title)
    root.iconname('Dialog')
    root_width = 800
    root_height = 400
    rootWindowPosition = f'{root_width}x{root_height}+400+200'
    root.geometry(rootWindowPosition)
    root.expand=tk.YES


    # ---------------- put the frames in the window -----------------------------------------
    message_and_buttonsFrame = tk.Frame(root)
    message_and_buttonsFrame.pack(side=tk.TOP, fill=tk.X, expand=tk.YES, pady=0, ipady=0)

    messageFrame = tk.Frame(message_and_buttonsFrame)
    messageFrame.pack(side=tk.LEFT, fill=tk.X, expand=tk.YES)

    buttonsFrame = tk.Frame(message_and_buttonsFrame)
    buttonsFrame.pack(side=tk.RIGHT, expand=tk.NO, pady=0)

    choiceboxFrame = tk.Frame(root)
    choiceboxFrame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=tk.YES)

    # -------------------------- put the widgets in the frames ------------------------------

    # ---------- put a message widget in the message frame-------------------
    messageWidget = tk.Message(messageFrame, anchor=tk.NW, text=message, width=0.8*root_width)
    messageWidget.configure(font=(DEFAULT_FONT_FAMILY,DEFAULT_FONT_SIZE))
    messageWidget.pack(side=tk.LEFT, expand=tk.YES, fill=tk.BOTH, padx='1m', pady='1m')

    # --------  put the choiceboxWidget in the choiceboxFrame ---------------------------
    choiceboxWidget = tk.Listbox(choiceboxFrame
        , height=lines_to_show
        , borderwidth="1m"
        , relief="flat"
        , bg="white"
        )
    choiceboxWidget.configure(font=(DEFAULT_FONT_FAMILY,DEFAULT_FONT_SIZE))

        # add a vertical scrollbar to the frame
    rightScrollbar = tk.Scrollbar(choiceboxFrame, orient=tk.VERTICAL, command=choiceboxWidget.yview)
    choiceboxWidget.configure(yscrollcommand = rightScrollbar.set)

    # add a horizontal scrollbar to the frame
    bottomScrollbar = tk.Scrollbar(choiceboxFrame, orient=tk.HORIZONTAL, command=choiceboxWidget.xview)
    choiceboxWidget.configure(xscrollcommand = bottomScrollbar.set)

    # pack the Listbox and the scrollbars.  Note that although we must define
    # the textbox first, we must pack it last, so that the bottomScrollbar will
    # be located properly.

    bottomScrollbar.pack(side=tk.BOTTOM, fill = tk.X)
    rightScrollbar.pack(side=tk.RIGHT, fill = tk.Y)

    choiceboxWidget.pack(side=tk.LEFT, padx="1m", pady="1m", expand=tk.YES, fill=tk.BOTH)

    # sort the choices, eliminate duplicates, and put the choices into the choiceboxWidget
    #choices.sort(key=str.lower) # case-insensitive sort
    lastInserted = None
    choiceboxChoices = []
    for choice in choices:
        if choice == lastInserted: pass
        else:
            choiceboxWidget.insert(tk.END, choice)
            choiceboxChoices.append(choice)
            lastInserted = choice

    root.bind('<Any-Key>', KeyboardListener)

    # put the buttons in the buttonsFrame
    if len(choices) > 0:
        okButton = tk.Button(buttonsFrame, takefocus=tk.YES, text="OK", height=1, width=6)
        okButton.pack(expand=tk.NO, side=tk.TOP,  padx='2m', pady='1m', ipady="1m", ipadx="2m")
        okButton.bind("<Return>", __choiceboxChoice)
        okButton.bind("<Button-1>",__choiceboxChoice)

        # now bind the keyboard events
        choiceboxWidget.bind("<Return>", __choiceboxChoice)
        choiceboxWidget.bind("<Double-Button-1>", __choiceboxChoice)
    else:
        # now bind the keyboard events
        choiceboxWidget.bind("<Return>", __choiceboxCancel)
        choiceboxWidget.bind("<Double-Button-1>", __choiceboxCancel)

    cancelButton = tk.Button(buttonsFrame, takefocus=tk.YES, text="Cancel", height=1, width=6)
    cancelButton.pack(expand=tk.NO, side=tk.BOTTOM, padx='2m', pady='1m', ipady="1m", ipadx="2m")
    cancelButton.bind("<Return>", __choiceboxCancel)
    cancelButton.bind("<Button-1>", __choiceboxCancel)

    # -------------------- bind some keyboard events ----------------------------


    root.bind("<Escape>", __choiceboxCancel)

    # --------------------- the action begins -----------------------------------
    # put the focus on the choiceboxWidget, and the select highlight on the first item
    choiceboxWidget.select_set(0)
    choiceboxWidget.focus_force()

    # --- run it! -----
    root.mainloop()
    if __a_button_was_clicked: root.destroy()
    return __choiceboxText


def __choiceboxChoice(event):
    global root, __choiceboxText, __a_button_was_clicked, choiceboxWidget
    choice_index = choiceboxWidget.curselection()
    __choiceboxText = choiceboxWidget.get(choice_index)
    __a_button_was_clicked = 1
    # print("Debugging> mouse-event=", event, " event.type=", event.type)
    # print("Debugging> choice =", choice_index, __choiceboxText)
    root.quit()


def __choiceboxCancel(event):
    global root, __choiceboxText, __a_button_was_clicked
    __a_button_was_clicked = 1
    __choiceboxText = None
    root.quit()


def KeyboardListener(event):
    global choiceboxChoices, choiceboxWidget
    key = event.keysym
    if len(key) <= 1:
        if key in string.printable:
            ## print(key)
            # now find it in list.....

            ## before we clear the list, remember the selected member
            try:
                start_n = int(choiceboxWidget.curselection()[0])
            except IndexError:
                start_n = -1

            ## clear the selection.
            choiceboxWidget.selection_clear(0, 'end')

            ## start from previous selection +1
            for n in range(start_n+1, len(choiceboxChoices)):
                item = choiceboxChoices[n]
                if item[0].lower() == key.lower():
                    choiceboxWidget.selection_set(first=n)
                    return
            else:
                # has not found it so loop from top
                for n in range(len(choiceboxChoices)):
                    item = choiceboxChoices[n]
                    if item[0].lower() == key.lower():
                        choiceboxWidget.selection_set(first = n)
                        ## should call see method but don't have
                        ## scrollbars in this demo!
                        return

                # nothing matched -- we'll look for the next logical choice
                for n in range(len(choiceboxChoices)):
                    item = choiceboxChoices[n]
                    if item[0].lower() > key.lower():
                        if n > 0:
                            choiceboxWidget.selection_set(first = (n-1))
                        else:
                            choiceboxWidget.selection_set(first = 0)
                        ## should call see method but don't have
                        ## scrollbars in this demo!
                        return

                # still no match (nothing was greater than the key)
                # we set the selection to the first item in the list
                choiceboxWidget.selection_set(first = (len(choiceboxChoices)-1))
                ## should call see method but don't have
                ## scrollbars in this demo!
                return

#-------------------------------------------------------------------
# diropenbox
#-------------------------------------------------------------------
def diropenbox(msg=None, title=None, startpos=None):
    """A dialog to get a directory name.
    Returns the name of a directory, or None if user chose to cancel.
    """
    root = tk.Tk()
    root.withdraw()
    f = tkFileDialog.askdirectory(parent=root, title=title)
    if f == "": return None
    return f

#-------------------------------------------------------------------
# fileopenbox
#-------------------------------------------------------------------
def fileopenbox(msg=None, title=None, startpos=None):
    """A dialog to get a file name.
    Returns the name of a file, or None if user chose to cancel.
    """
    root = tk.Tk()
    root.withdraw()
    f = tkFileDialog.askopenfilename(parent=root,title=title)
    if f == "": return None
    return f


#-------------------------------------------------------------------
# filesavebox
#-------------------------------------------------------------------
def filesavebox(msg=None, title=None, startpos=None):
    """A file to get the name of a file to save.
    Returns the name of a file, or None if user chose to cancel.
    """
    root = tk.Tk()
    root.withdraw()
    f = tkFileDialog.asksaveasfilename(parent=root, title=title)
    if f == "": return None
    return f


#-------------------------------------------------------------------
# utility routines
#-------------------------------------------------------------------
# These routines are used by several other functions in the EasyGui module.

def __buttonEvent(event):
    """Handle an event that is generated by a person clicking a button.
    """
    global  root, __a_button_was_clicked, __widgetTexts, __replyButtonText
    __replyButtonText = __widgetTexts[event.widget]
    __a_button_was_clicked = 1
    root.quit() # quit the main loop


def __put_buttons_in_buttonframe(choices):
    """Put the buttons in the buttons frame
    """
    global __widgetTexts, __firstWidget, buttonsFrame

    __widgetTexts = {}
    i = 0

    for buttonText in choices:
        tempButton = tk.Button(buttonsFrame, takefocus=1, text=buttonText)
        tempButton.pack(expand=tk.YES, side=tk.LEFT, padx='1m', pady='1m', ipadx='2m', ipady='1m')

        # remember the text associated with this widget
        __widgetTexts[tempButton] = buttonText

        # remember the first widget, so we can put the focus there
        if i == 0:
            __firstWidget = tempButton
            i = 1

        # bind the keyboard events to the widget
        tempButton.bind("<Return>", __buttonEvent)
        tempButton.bind("<Button-1>", __buttonEvent)



