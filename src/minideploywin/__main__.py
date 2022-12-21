import argparse
parser = argparse.ArgumentParser()
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

args = parser.parse_args()

DIR_ROOT = "./"

# =============================================================================

import os
import shutil
import re
import ctypes
import sys
from typing import Optional
import logging
import subprocess
import functools

import win32comext.shell.shell as shell
import win32event

# =============================================================================

# https://stackoverflow.com/a/41930586
def IsAdmin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def ForceAdmin() -> bool:
    if not IsAdmin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        return True
    return False

# =============================================================================

def execute(cmd, capture=True, errors_ok=True) -> Optional[str]:
    try:
        if capture:
            return subprocess.check_output(cmd).strip().decode("utf-8")
        subprocess.call(cmd)
    except Exception as e:
        if not errors_ok:
            raise e
    return None

@functools.cache
def getSystemModelReal() -> Optional[str]:
    cmd = [
        'powershell.exe',
        "(Get-CimInstance -ClassName Win32_ComputerSystem).Model"
    ]

    return execute(cmd)

def getSystemModel() -> Optional[str]:
    if args.model is not None:
        return args.model

    return getSystemModelReal()

@functools.cache
def IsVirtualMachine() -> bool:
    return getSystemModel() == "Virtual Machine"

# =============================================================================

class TaskExtensionHandlers:
    @staticmethod
    def msi(path: str) -> bool:
        return execute(
            ["msiexec", "/i", path, "/passive", "/qr", "/norestart"],
            capture=False,
            errors_ok=True
        )

    @staticmethod
    def reg(path: str) -> bool:
        return execute(
            ["reg", "import", path],
            capture=False,
            errors_ok=True
        )

    @staticmethod
    def lnk(path: str) -> int:
        se_ret = shell.ShellExecuteEx(fMask=0x140, lpFile=path, nShow=1)
        win32event.WaitForSingleObject(se_ret['hProcess'], -1)
        return se_ret

    @staticmethod
    def xml(path: str) -> Optional[bool]:
        if not os.path.basename(path).startswith("Wi-Fi-"):
            return None

        return execute(
            ["netsh", "wlan", "add", "profile", f'filename="{path}"'],
            capture=False,
            errors_ok=True
        )

    @staticmethod
    def bat(path: str) -> bool:
        return execute(
            [path],
            capture=False,
            errors_ok=True
        )

    @staticmethod
    def ps1(path: str) -> bool:
        return execute(
            ["powershell", "-File", path],
            capture=False,
            errors_ok=True
        )

# =============================================================================

# https://stackoverflow.com/a/16090640/2605226
def natural_sort_key(s, _nsre=re.compile('([0-9]+)')):
    return [
        int(text) if text.isdigit()
        else text.lower()
        for text in _nsre.split(str(s))
    ]

def ProcessTaskDir(path: str) -> None:
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

def getSubdirs(path: str):
    return filter(
        lambda x: x.is_dir(),
        os.scandir(path)
    )

def GetModelPath():
    systemModel = getSystemModel()

    systemModelsPath = os.path.join(DIR_ROOT, "Models")

    # Get names of only subdirectories
    try:
        systemModels = list(map(
            lambda x: x.name,
            getSubdirs(systemModelsPath)
        ))
    except:
        logging.warning("Could not find model deployments")
        return None

    if systemModel in systemModels:
        return os.path.join(systemModelsPath, systemModel)

    logging.warning(f"No deployment information found for device: {systemModel}")
    return None

def ExecuteOrderedTasks():
    pool = []
    
    try:
        pool = list(getSubdirs(os.path.join(DIR_ROOT, "All")))
    except:
        logging.warning("Could not find global deployments")

    modelPath = GetModelPath()
    if modelPath is not None:
        pool += list(getSubdirs(modelPath))

    pool.sort(key=lambda x: natural_sort_key(x.name))

    for dirEntry in pool:
        ProcessTaskDir(dirEntry.path)

def tryRemove(path):
    try:
        os.remove(path)
    except:
        pass

def tryRmtree(path):
    try:
        shutil.rmtree(path)
    except:
        pass

def pause():
    input("Press the <ENTER> key to continue...")

def main():
    if IsVirtualMachine():
        logging.info("Virtual machine detected, skipping deployment")
        pause()
        tryRemove(args.log)
        return

    if not args.usermode and ForceAdmin():
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

    ExecuteOrderedTasks()
    
    pause()

if __name__=="__main__":
    main()