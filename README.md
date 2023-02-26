# miniwindeploy

## Usage

```
> python -m miniwindeploy -h
usage: miniwindeploy [-h] [-e] [-l LOG] [-m MODEL] [-u] [-r]

Stupid simple task runner, intended for deploying/debloating/customizing Windows

optional arguments:
  -h, --help            show this help message and exit
  -e, --execute         Execute actions (default behavior is to do a dry run)
  -l LOG, --log LOG     File to log to (will also output to stdout)
  -m MODEL, --model MODEL
                        Act as if device is different model
  -u, --usermode        Skip requesting elevation
  -r, --realonly        Only execute on physical machines, exit if in VM

The following filetypes are recognized:

bat:  Runs batch script and waits until exit.

exe:  Runs executable and waits until exit.

lnk:  Executes shortcut and waits for process to exit.

msi:  Executes MSI installer silently and waits until finished. Cancels restarts.

ps1:  Runs Powershell script and waits until exit.

reg:  Applies registry patch.

xml:  For XML files beginning with "Wi-Fi-", registers the wireless profiles.
      Ignores other XML files.
```

## Explanation

Assume we have the following directory structure in the current working directory and that the current PC model name (as specified in System Information) is `modelname`:

```
- All
|-- 1
  |-- hello.bat
|-- 9
  |-- world.bat
- Models
|-- modelname
  |-- 5
    |-- model.bat
```

The following tasks will be executed, in order:
```
All/1/hello.bat
Models/modelname/5/model.bat
All/9/world.bat
```

All folder in `All` and `Models/modelname` are added to a pool, [sorted naturally](https://en.wikipedia.org/wiki/Natural_sort_order), and then the contents of each directory are executed (after also being naturally sorted). If the `modelname` directory isn't present, the script will proceed with a warning.