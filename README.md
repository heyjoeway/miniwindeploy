# miniwindeploy
Stupid simple task runner, intended for deploying/debloating/customizing Windows

**WARNING: STILL IN EARLY TESTING**

## Usage

```
$ python -m minideploywin
usage: __main__.py [-h] [-e] [-l LOG] [-m MODEL] [-u]

optional arguments:
  -h, --help            show this help message and exit
  -e, --execute         Execute actions (default behavior is to do a dry run)
  -l LOG, --log LOG     File to log to (will also output to stdout)
  -m MODEL, --model MODEL
                        Act as if device is different model
  -u, --usermode        Skip requesting elevation
```