import sys
import os
import logging
import errno
import shlex
import subprocess

log = logging.getLogger(__name__)

class CommandFailed(Exception):
    def __init__(self, cmd, retcode, output):
        if not isinstance(cmd, str):
            cmd = " ".join(map(shlex.quote, cmd))
        self.cmd = cmd
        self.retcode = retcode
        self.output = output

def run_command(command, raise_on_fail=True, wait_for_output=True):
    """Run command in a subprocess.

    Return `process` return code and output once it completes.
    """
    log.info("Running %s", " ".join(command))

    if command[0] == "python": process = python_process(command[1:])
    else:process = create_process(command)

    if wait_for_output:
        output = []
        while process.poll() is None:
            try:
                line = process.stdout.readline()
            except IOError as ex:
                if ex.errno != errno.EINTR:
                    raise
            else:
                output.append(line)
                print(line, end="")
        # Read remaining output if any
        line = process.stdout.read()
        if line:
            output.append(line)
            print(line, end="")

        if process.returncode != 0:
            log.info("Command %s failed with %s",
                     " ".join(command), process.returncode)
            log.debug("Output:\n%s", "\n".join(output))
            if raise_on_fail:
                raise CommandFailed(command, process.returncode, output)

        return process.returncode, output


def python_process(args, script_name=None, **kwargs):
    """
    Run a `sys.executable` in a subprocess with `args`.
    """
    executable = sys.executable
    if os.name == "nt" and os.path.basename(executable) == "pythonw.exe":
        # Don't run the script with a 'gui' (detached) process.
        dirname = os.path.dirname(executable)
        executable = os.path.join(dirname, "python.exe")

    if script_name is not None:
        script = script_name
    else:
        script = executable

    return create_process(
        [script] + args,
        executable=executable
    )


def create_process(cmd, executable=None, **kwargs):
    if hasattr(subprocess, "STARTUPINFO"):
        # do not open a new console window for command on windows
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        kwargs["startupinfo"] = startupinfo

    return subprocess.Popen(
        cmd,
        executable=executable,
        cwd=None,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
        bufsize=-1,
        universal_newlines=True,
        **kwargs
    )
