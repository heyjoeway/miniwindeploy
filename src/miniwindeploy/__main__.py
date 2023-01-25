
DIR_ROOT = "./"

# =============================================================================

import argparse
from argparse import RawTextHelpFormatter
import os
import re
import ctypes
import sys
from typing import Callable, Optional, Type
import logging
import subprocess
import functools

import win32comext.shell.shell as shell
import win32event

# =============================================================================

# https://stackoverflow.com/a/41930586
def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def request_admin() -> bool:
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        return True
    return False

# =============================================================================

# https://stackoverflow.com/a/21978778
def log_subprocess_output(pipe):
    for line in iter(pipe.readline, b''): # b'\n'-separated lines
        logging.info('SUBPROCESS: %r', line)
    
def execute(cmd, capture=True, errors_ok=True, cwd=None) -> Optional[str]:
    try:
        if capture:
            return subprocess.check_output(
                cmd, cwd=cwd
            ).strip().decode("utf-8")
        
        process = subprocess.Popen(
            cmd, cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        with process.stdout:
            log_subprocess_output(process.stdout)
        exitcode = process.wait() # 0 means success
        if (exitcode != 0):
            raise Exception(exitcode)
    except Exception as e:
        if not errors_ok:
            raise e
    return None

@functools.cache
def get_system_model_real() -> Optional[str]:
    cmd = [
        'powershell.exe',
        "(Get-CimInstance -ClassName Win32_ComputerSystem).Model"
    ]

    return execute(cmd)

def get_system_model() -> Optional[str]:
    if args.model is not None:
        return args.model

    return get_system_model_real()

@functools.cache
def IsVirtualMachine() -> bool:
    return get_system_model() == "Virtual Machine"

# =============================================================================

class TaskExtensionHandlers:
    @staticmethod
    def msi(path: str) -> bool:
        """
        Executes MSI installer silently and waits until finished. Cancels restarts.
        """
        return execute(
            ["msiexec", "/i", path, "/passive", "/qr", "/norestart"],
            capture=False,
            errors_ok=True,
            cwd=os.path.dirname(path)
        )

    @staticmethod
    def reg(path: str) -> bool:
        """
        Applies registry patch.
        """
        return execute(
            ["reg", "import", path],
            capture=False,
            errors_ok=True,
            cwd=os.path.dirname(path)
        )

    @staticmethod
    def lnk(path: str) -> int:
        """
        Executes shortcut and waits for process to exit.
        """
        se_ret = shell.ShellExecuteEx(fMask=0x140, lpFile=path, nShow=1)
        win32event.WaitForSingleObject(se_ret['hProcess'], -1)
        return se_ret

    @staticmethod
    def xml(path: str) -> Optional[bool]:
        """
        For XML files beginning with "Wi-Fi-", registers the wireless profiles.
        Ignores other XML files.
        """
        if not os.path.basename(path).startswith("Wi-Fi-"):
            return None

        return execute(
            ["netsh", "wlan", "add", "profile", f'filename="{path}"'],
            capture=False,
            errors_ok=True
        )

    @staticmethod
    def bat(path: str) -> bool:
        """
        Runs batch script and waits until exit.
        """
        return execute(
            [path],
            capture=False,
            errors_ok=True,
            cwd=os.path.dirname(path)
        )

    @staticmethod
    def exe(path: str) -> bool:
        """
        Runs executable and waits until exit.
        """
        return execute(
            [path],
            capture=False,
            errors_ok=True,
            cwd=os.path.dirname(path)
        )

    @staticmethod
    def ps1(path: str) -> bool:
        """
        Runs Powershell script and waits until exit.
        """
        return execute(
            ["powershell", "-File", path],
            capture=False,
            errors_ok=True
        )

def get_class_functions(cls: Type) -> list[str, Callable]:
    for funcName in dir(cls):
        func: Callable = getattr(cls, funcName)
        if callable(func) and not funcName.startswith("__"):
            yield (funcName, func)

# =============================================================================

epilogue = "The following filetypes are recognized:\n\n"

for funcName, func in get_class_functions(TaskExtensionHandlers):
    epilogue += f"{funcName}: {func.__doc__}\n\n"

parser = argparse.ArgumentParser(
    prog="miniwindeploy",
    description="Stupid simple task runner, intended for deploying/debloating/customizing Windows",
    epilog=epilogue,
    formatter_class=RawTextHelpFormatter
)
parser.add_argument(
    "-e", "--execute",
    help="Execute actions (default behavior is to do a dry run)",
    action="store_true"
)
parser.add_argument(
    "-l", "--log",
    help="File to log to (will also output to stdout)",
    type=str
)
parser.add_argument(
    "-m", "--model",
    help="Act as if device is different model",
    type=str
)
parser.add_argument(
    "-u", "--usermode",
    help="Skip requesting elevation",
    action="store_true"
)
parser.add_argument(
    "-r", "--realonly",
    help="Only execute on physical machines, exit if in VM",
    action="store_true"
)


args = parser.parse_args()

# =============================================================================

# https://stackoverflow.com/a/16090640/2605226
def natural_sort_key(s, _nsre=re.compile('([0-9]+)')):
    return [
        int(text) if text.isdigit()
        else text.lower()
        for text in _nsre.split(str(s))
    ]

def process_task_dir(path: str) -> None:
    logging.info(f"Processing task directory: {path}")

    # Only keep files
    dirEntries = list(filter(
        lambda x: x.is_file(),
        os.scandir(path)
    ))
    dirEntries.sort(key=lambda x: natural_sort_key(x.name))

    for dirEntry in dirEntries:
        try:
            fullPath = os.path.abspath(dirEntry.path)
            extension = os.path.splitext(dirEntry.name)[1][1:].lower()
            handler = getattr(TaskExtensionHandlers, extension)

            logging.debug(f"Full Path: {str(fullPath)}")
            logging.debug(f"Extension: {str(extension)}")
            logging.debug(f"Handler: {str(handler)}")

            # Dry run
            if not args.execute:
                continue

            handler(fullPath)
        except:
            pass

def get_subdirs(path: str):
    return filter(
        lambda x: x.is_dir(),
        os.scandir(path)
    )

def get_model_path():
    systemModel = get_system_model()

    systemModelsPath = os.path.join(DIR_ROOT, "Models")

    # Get names of only subdirectories
    try:
        systemModels = list(map(
            lambda x: x.name,
            get_subdirs(systemModelsPath)
        ))
    except:
        logging.warning("Could not find model deployments")
        return None

    if systemModel in systemModels:
        return os.path.join(systemModelsPath, systemModel)

    logging.warning(f"No deployment information found for device: {systemModel}")
    return None

def execute_ordered_tasks():
    pool = []
    
    try:
        pool = list(get_subdirs(os.path.join(DIR_ROOT, "All")))
    except:
        logging.warning("Could not find global deployments")

    modelPath = get_model_path()
    if modelPath is not None:
        pool += list(get_subdirs(modelPath))

    pool.sort(key=lambda x: natural_sort_key(x.name))

    for dirEntry in pool:
        process_task_dir(dirEntry.path)

def main():
    if args.realonly and IsVirtualMachine():
        logging.info("Virtual machine detected, skipping deployment")
        try:
            os.remove(args.log)
        except:
            pass
        return

    if not args.usermode and request_admin():
        return

    logFormat = '%(asctime)s %(levelname)-8s %(message)s'
    dateFormat = '%Y-%m-%d %H:%M:%S'
    logging.basicConfig(
        filename=args.log,
        encoding="utf-8",
        level=logging.DEBUG,
        format=logFormat,
        datefmt=dateFormat
    )

    if args.log is not None:
        streamHandler = logging.StreamHandler(sys.stdout)
        streamHandler.setFormatter(logging.Formatter(
            fmt=logFormat,
            datefmt=dateFormat
        ))
        logging.getLogger().addHandler(streamHandler)

    execute_ordered_tasks()

if __name__=="__main__":
    main()