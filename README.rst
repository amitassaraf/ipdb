Python Debugger Improved
========================

pdbi is an improvment on ipdb which is a Python Debugger that exports IPython functionality.
The improvements are aimed at more powerful debugging as well as fixing useless commands.

Features
--------

* 'cf' command (continue forever) will continue execution until the end of the program.
* 'c' command argument that allows to decide the number of breakpoints to continue over. 'c 2'
* 'n' command argument that allows to decide the number of lines to execute. 'n 2' [Stops when a frame returns]
* New 'e' command that will open an editor (Notepad++ on Windows, VIM or VI on Unix) on the current debugger line, then when the editor is closed, the debugger shows the difference and restarts the program (Based on sys.argv).
* Allow the usage of ipython magics like 'func?' or 'func?@' etc.
* All updated commands allow pythonic arguments for example 'c len(cmd_list)' or 'n abc'.
* 'l' command updated to allow giving only one argument that shows that argument amount of lines around the current line.
* 'll' command that is a shortcut to show the current line the debugger is on.
* 'restart' command that is used to restart the program based on sys.argv.
* 'cls/clear' command that clears the screen.
* Added ability to force ignore commands by prefixing the command with an '!'. For example '!cls' or '!e'.


Installation
------------

Install from pip:
::

        pip install pdbi

or clone from Github and run:
::

        python setup.py install


Use
---

Example usage:
::

        import pdbi; pdbi.set_trace()


Contact me
----------

Email: amit@helpi.me

Linkedin: Amit Assaraf

I'd love to get feedback and suggestions on what I should add/change! Thanks!
