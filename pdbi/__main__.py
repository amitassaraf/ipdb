# Copyright (c) 2011, 2012 Godefroid Chapelle
#
# This file is part of pdbi.
# GNU package is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 2 of the License, or (at your option)
# any later version.
#
# GNU package is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
# for more details.

from __future__ import print_function
import sys
import os
import traceback
from IPython.utils.coloransi import TermColors

from contextlib import contextmanager

try:
    from pdb import Restart
except ImportError:
    class Restart(Exception):
        pass

import IPython


def import_module(possible_modules, needed_module):
    """Make it more resilient to different versions of IPython and try to
    find a module."""
    count = len(possible_modules)
    for module in possible_modules:
        try:
            return __import__(module, fromlist=[needed_module])
        except ImportError:
            count -= 1
            if count == 0:
                raise


if IPython.__version__ > '0.10.2':
    from IPython.core.debugger import Pdb, BdbQuit_excepthook

    possible_modules = ['IPython.terminal.ipapp',  # Newer IPython
                        'IPython.frontend.terminal.ipapp']  # Older IPython

    app = import_module(possible_modules, "TerminalIPythonApp")
    TerminalIPythonApp = app.TerminalIPythonApp

    possible_modules = ['IPython.terminal.embed',  # Newer IPython
                        'IPython.frontend.terminal.embed']  # Older IPython
    embed = import_module(possible_modules, "InteractiveShellEmbed")
    InteractiveShellEmbed = embed.InteractiveShellEmbed
    try:
        get_ipython
    except NameError:
        # Build a terminal app in order to force ipython to load the
        # configuration
        ipapp = TerminalIPythonApp()
        # Avoid output (banner, prints)
        ipapp.interact = False
        ipapp.initialize()
        def_colors = ipapp.shell.colors
    else:
        # If an instance of IPython is already running try to get an instance
        # of the application. If there is no TerminalIPythonApp instanciated
        # the instance method will create a new one without loading the config.
        # i.e: if we are in an embed instance we do not want to load the config.
        ipapp = TerminalIPythonApp.instance()
        shell = get_ipython()
        def_colors = shell.colors

        # Detect if embed shell or not and display a message
        if isinstance(shell, InteractiveShellEmbed):
            shell.write_err(
                "\nYou are currently into an embedded ipython shell,\n"
                "the configuration will not be loaded.\n\n"
            )

    def_exec_lines = [line + '\n' for line in ipapp.exec_lines]

    from IPython.utils import io

    if 'nose' in sys.modules.keys():
        def update_stdout():
            # setup stdout to ensure output is available with nose
            io.stdout = sys.stdout = sys.__stdout__
    else:
        def update_stdout():
            pass
else:
    from IPython.Debugger import Pdb, BdbQuit_excepthook
    from IPython.Shell import IPShell
    from IPython import ipapi

    ip = ipapi.get()
    if ip is None:
        IPShell(argv=[''])
        ip = ipapi.get()
    def_colors = ip.options.colors
    def_exec_lines = []

    from IPython.Shell import Term

    if 'nose' in sys.modules.keys():
        def update_stdout():
            # setup stdout to ensure output is available with nose
            Term.cout = sys.stdout = sys.__stdout__
    else:
        def update_stdout():
            pass


def _init_pdb():
    p = Pdbi(def_colors)
    p.rcLines += def_exec_lines
    return p


class Pdbi(Pdb):
    # Used for editing files :D
    NOTEPAD_PLUS_PLUS_PATH = r'C:\Program Files (x86)\Notepad++\notepad++.exe'
    VIM = r'vim'
    VI = r'vi'
    TMP_EDIT_PATH = 'pdb_edt.tmp'
    NO_DIFF_FLAG = '--no-diff'
    NO_RESTART_FLAG = '--no-restart'
    PROMPT = 'pdbi> '
    WINDOWS_IDENTIFIER = 'wind'

    # Used to repeat commands
    command_repeat = 1
    command_repeat_callback = None
    command_repeat_deep = False

    def __init__(self, *args, **kwargs):
        self.skip = kwargs.get('skip', None)
        Pdb.__init__(self, *args, **kwargs)
        self.prompt = Pdbi.PROMPT

    def set_command_repeat(self, arg, frame, callback, command_repeat_deep=False):
        try:
            Pdbi.command_repeat = int(arg)
        except:
            try:
                Pdbi.command_repeat = eval(arg, frame.f_globals, frame.f_locals) or 1
            except:
                Pdbi.command_repeat = 1

        Pdbi.command_repeat_callback = callback
        Pdbi.command_repeat_deep = command_repeat_deep

    def check_command_repeat(self, frame):
        Pdbi.command_repeat -= 1
        if Pdbi.command_repeat == 0:
            return True
        if Pdbi.command_repeat_callback:
            try:
                Pdbi.command_repeat_callback(frame)
            except TypeError:
                Pdbi.command_repeat_callback()
        return False

    def stop_here(self, frame):
        # (CT) stopframe may now also be None, see dispatch_call.
        # (CT) the former test for None is therefore removed from here.
        if self.skip and \
                self.is_skipped_module(frame.f_globals.get('__name__')):
            return False

        if frame is self.stopframe:
            if self.stoplineno == -1:
                return False

            if frame.f_lineno >= self.stoplineno:
                return self.check_command_repeat(frame)
            return False

        while frame is not None and frame is not self.stopframe:
            if frame is self.botframe:
                if self.command_repeat_deep:
                    return self.check_command_repeat(frame)

                return True

            frame = frame.f_back

        return False

    def precmd(self, line):
        line = Pdb.precmd(self, line)
        if line:
            if line.endswith('??'):
                line = 'pinfo2 {0}'.format(line[:-2])
            elif line.endswith('?!'):
                line = 'psource {0}'.format(line[:-2])
            elif line.endswith('?@'):
                line = 'pdef {0}'.format(line[:-2])
            elif line.endswith('?'):
                line = 'pinfo {0}'.format(line[:-1])
            elif line.startswith('!'):
                line = 'forcecommandmagic {0}'.format(line[1:])
        return line

    """
    New commands
    """

    def do_forcecommandmagic(self, arg):
        run_cmd = getattr(self, 'do_{0}'.format(arg[:arg.find(' ')]), None)
        if run_cmd:
            return run_cmd(arg[arg.find(' ') + 1:])
        return 0

    def do_restartp(self, arg):
        from sys import platform as _platform

        print('\n{0} Restarting debugger...\n'.format(TermColors.LightBlue), file=io.stdout)

        os.system(Pdbi._get_original_python_run_command())

        # Kill previous debugger.
        if Pdbi.WINDOWS_IDENTIFIER in _platform:  # Windows
            os.system('taskkill /F /PID {0} > nul 2>&1'.format(os.getpid()))
        else:  # Unix
            os.system('kill -9 {0} > /dev/null 2>&1'.format(os.getpid()))
        return self.do_quit('')

    # Preserve original restart
    do_restarto = Pdb.do_restart
    help_restarto = Pdb.help_restart

    do_reset = do_restart = do_restartp

    def do_cls(self, arg):
        from sys import platform as _platform

        if Pdbi.WINDOWS_IDENTIFIER in _platform:  # Windows
            os.system('cls')
        else:
            os.system('clear')

        return 0

    do_clear = do_cls

    def do_list_relative(self, arg):
        try:
            relative_amount = int(arg)
        except:
            try:
                relative_amount = eval(arg, self.curframe.f_globals, self.curframe.f_locals) or 5
                if isinstance(relative_amount, tuple):
                    return Pdb.do_list(self, arg)
            except:
                relative_amount = 5

        top = max(1, self.curframe.f_lineno - relative_amount)
        bottom = min(len(open(self.curframe.f_code.co_filename, 'rb').readlines()),
                     self.curframe.f_lineno + relative_amount)
        return Pdb.do_list(self, '{0},{1}'.format(top, bottom))

    do_la = Pdb.do_list
    help_la = Pdb.help_l
    do_l = do_lr = do_list_relative

    def do_edit(self, arg):
        from sys import platform as _platform
        import shutil
        import subprocess
        import linecache

        return_val = 0
        filename = self.curframe.f_code.co_filename

        shutil.copyfile(filename, Pdbi.TMP_EDIT_PATH)

        if Pdbi.WINDOWS_IDENTIFIER in _platform and os.path.exists(Pdbi.NOTEPAD_PLUS_PLUS_PATH):  # Windows
            proc_args = [Pdbi.NOTEPAD_PLUS_PLUS_PATH, filename, '-n{0}'.format(self.curframe.f_lineno)]
        elif Pdbi.WINDOWS_IDENTIFIER in _platform:
            print('{0} Notepad++ not installed (I am sad now). Ignoring command. {1}'.format(TermColors.LightRed,
                                                                                             TermColors.Normal),
                  file=io.stdout)
            return 0
        else:  # Unix
            result = subprocess.check_output('which vim', shell=True)
            if len(result) != 0:
                proc_args = [Pdbi.VIM, '+{0}'.format(self.curframe.f_lineno), filename]
            else:
                proc_args = [Pdbi.VI, '+{0}'.format(self.curframe.f_lineno), filename]

        process = subprocess.Popen(proc_args)
        process.wait()

        if filename.endswith('.py'):
            Pdbi._safe(os.remove, '{0}c'.format(filename))

        linecache.clearcache()

        if Pdbi.NO_DIFF_FLAG not in arg:

            # Calculate difference between files
            difference = Pdbi._difference_between_files(Pdbi.TMP_EDIT_PATH, filename)

            if difference:

                for diff in difference:
                    line = diff[2]
                    scheme = self.color_scheme_table.active_scheme_name
                    new_line, err = self.parser.format2(line, 'str', scheme)
                    if not err: line = new_line
                    print('{0}+++{1}-> {2}{3}'.format(TermColors.LightRed,
                                                      TermColors.LightGreen, diff[0], line), file=io.stdout, end='')

                if Pdbi.NO_RESTART_FLAG not in arg:
                    return_val = self.do_restartp('')

        Pdbi._safe(os.remove, Pdbi.TMP_EDIT_PATH)

        return return_val

    do_e = do_ed = do_edit

    do_eer = lambda self, arg: self.do_edit(self, self.NO_RESTART_FLAG + self.NO_DIFF_FLAG)

    do_er = lambda self, arg: self.do_edit(self, self.NO_RESTART_FLAG)

    do_ee = lambda self, arg: self.do_edit(self, self.NO_DIFF_FLAG)

    do_ll = lambda self, arg: self.do_list_relative('0')

    def help_restartp(self):
        print("""restartp(rogram)
Restarts the current program/script using sys.argv. """, file=self.stdout)

    help_reset = help_restart = help_restartp

    def help_cls(self):
        print("""cls [clear screen])
Used to clear the screen from text. """, file=self.stdout)

    help_clear = help_cls

    def help_e(self):
        print("""e(d(it))
Edit the source code of the current line. (Opens Notepad++ in Windows,
in Unix opens VIM or VI). Detects when the notepad has closed and
restarts the program if any changes were made.""", file=self.stdout)

    def help_ee(self):
        print("""e(dit)e(xclude_diff)
Same as the e(dit) command but does not display the diff afterwards. See "help e".""", file=self.stdout)

    def help_er(self):
        print("""e(dit)r(estart)
Same as the e(dit) command but does not restart the debugger afterwards. See "help e".""", file=self.stdout)

    def help_eer(self):
        print("""e(dit)e(xclude_diff)r(estart)
See "help e" & "help er" & "help ee" """, file=self.stdout)

    help_edit = help_ed = help_e

    def help_ll(self):
        print("""ll
List source code for the current line.""", file=self.stdout)

    def help_l(self):
        print("""l(ist (r)elative) [line_counnt]
List source code for the current file.
Without arguments, list 5 lines around the current line
or continue the previous listing.
With one argument, list <argument> lines around the current line.""", file=self.stdout)

    help_list_relative = help_lr = help_l

    """
    Updated commands
    """

    def do_until(self, arg):
        self.set_until(self.curframe)
        return 1

    def do_continue(self, arg):
        self.set_command_repeat(arg, self.curframe, self.set_continue, command_repeat_deep=True)
        self.set_continue()
        return 1

    do_cf = lambda self, arg: self.do_continue('0')

    do_c = do_cont = do_continue

    def do_next(self, arg):
        self.set_command_repeat(arg, self.curframe, self.set_next)
        self.set_next(self.curframe)
        return 1

    do_n = do_next

    def help_n(self):
        print("""n(ext) [repeat_count <0 = Until next return>]
Continue execution until the next line in the current function
is reached or it returns.""", file=self.stdout)

    def help_c(self):
        print("""c(ont(inue)) [repeat_count <0 = Until end of execution>]
Continue execution, only stop when a breakpoint is encountered.""", file=self.stdout)

    def help_cf(self):
        print("""c(ontinue)f(orever)
Continue execution until the end of the program.""", file=self.stdout)

    @staticmethod
    def _get_original_python_run_command():
        if len(sys.argv) == 1 and sys.argv[0].endswith('py'):
            sys.argv = ['python'] + sys.argv

        for index, arg in enumerate(sys.argv, 0):
            if 'ipython' in arg:
                sys.argv[index] = 'ipython'
            elif not arg.startswith('-') and not Pdbi._check_number(arg) and index != 0:
                # Wrap all arguments with quotation marks
                sys.argv[index] = '\"{0}\"'.format(arg.replace('\"', '\''))

        return ' '.join(sys.argv)

    @staticmethod
    def _difference_between_files(file_path_a, file_path_b):
        """
        Method to calculate the difference between two files
        :param file_path_a: The path of the first file
        :param file_path_b: The path of the second file
        :return: a list of 3 element types showing the difference & line number (4, 'x = 2', 'x = 1')
        """
        import difflib

        difference = difflib.unified_diff(open(file_path_a, 'rb').readlines(), open(file_path_b, 'rb').readlines())
        difference = [dif[1:] for dif in difference if dif.startswith('-') or dif.startswith('+')][2:]
        difference = difference[::2] + difference[1::2]
        itr = iter(difference)
        difference = zip(itr, itr)

        for lineno, line in enumerate(open(file_path_a, 'rb'), 1):
            for index in xrange(len(difference)):
                diff = difference[index]
                if len(diff) < 3 and diff[0] in line:
                    difference[index] = (lineno,) + diff

        return difference

    @staticmethod
    def _check_number(s):
        """
        Function to check if a string is a number
        :param s: The string to check
        :return: True if its a number, False otherwise
        """
        try:
            float(s)
            return True
        except ValueError:
            try:
                int(s)
                return True
            except ValueError:
                pass

        return False

    @staticmethod
    def _safe(func, *args, **kwargs):
        """
        Method to run a function safely.
        :param func: The function to run
        :param args: The arguments to pass
        :param kwargs: The key arguments to pass
        :return: The function return value or None if it failed.
        """
        assert hasattr(func, '__call__')

        try:
            return func(*args, **kwargs)
        except:
            pass


def wrap_sys_excepthook():
    # make sure we wrap it only once or we would end up with a cycle
    #  BdbQuit_excepthook.excepthook_ori == BdbQuit_excepthook
    if sys.excepthook != BdbQuit_excepthook:
        BdbQuit_excepthook.excepthook_ori = sys.excepthook
        sys.excepthook = BdbQuit_excepthook


def set_trace(frame=None):
    update_stdout()
    wrap_sys_excepthook()
    if frame is None:
        frame = sys._getframe().f_back
    _init_pdb().set_trace(frame)


def post_mortem(tb):
    update_stdout()
    wrap_sys_excepthook()
    p = _init_pdb()
    p.reset()
    if tb is None:
        return
    p.interaction(None, tb)


def pm():
    post_mortem(sys.last_traceback)


def run(statement, globals=None, locals=None):
    _init_pdb().run(statement, globals, locals)


def runcall(*args, **kwargs):
    return _init_pdb().runcall(*args, **kwargs)


def runeval(expression, globals=None, locals=None):
    return _init_pdb().runeval(expression, globals, locals)


@contextmanager
def launch_ipdb_on_exception():
    try:
        yield
    except Exception:
        e, m, tb = sys.exc_info()
        print(m.__repr__(), file=sys.stderr)
        post_mortem(tb)
    finally:
        pass


def main():
    if not sys.argv[1:] or sys.argv[1] in ("--help", "-h"):
        print("usage: pdbi.py scriptfile [arg] ...")
        sys.exit(2)

    mainpyfile = sys.argv[1]  # Get script filename
    if not os.path.exists(mainpyfile):
        print('Error:', mainpyfile, 'does not exist')
        sys.exit(1)

    del sys.argv[0]  # Hide "pdb.py" from argument list

    # Replace pdb's dir with script's dir in front of module search path.
    sys.path[0] = os.path.dirname(mainpyfile)

    # Note on saving/restoring sys.argv: it's a good idea when sys.argv was
    # modified by the script being debugged. It's a bad idea when it was
    # changed by the user from the command line. There is a "restart" command
    # which allows explicit specification of command line arguments.
    pdb = _init_pdb()
    while 1:
        try:
            pdb._runscript(mainpyfile)
            if pdb._user_requested_quit:
                break
            print("The program finished and will be restarted")
        except Restart:
            print("Restarting", mainpyfile, "with arguments:")
            print("\t" + " ".join(sys.argv[1:]))
        except SystemExit:
            # In most cases SystemExit does not warrant a post-mortem session.
            print("The program exited via sys.exit(). Exit status: ", end='')
            print(sys.exc_info()[1])
        except:
            traceback.print_exc()
            print("Uncaught exception. Entering post mortem debugging")
            print("Running 'cont' or 'step' will restart the program")
            t = sys.exc_info()[2]
            pdb.interaction(None, t)
            print("Post mortem debugger finished. The " + mainpyfile +
                  " will be restarted")


if __name__ == '__main__':
    main()
