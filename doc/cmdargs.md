## rssforward.py --help
```
usage: rssforward.py [-h] [-c CONFIG] [--trayicon {True,False}]
                     [--startserver {True,False}] [--genloop {True,False}]

RSS Forward

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Path to TOML config file (default: None)
  --trayicon {True,False}
                        Use system tray icon (overrides config 'trayicon'
                        option) (default: None)
  --startserver {True,False}
                        Enable RSS server at startup (overrides config
                        'startserver' option) (default: None)
  --genloop {True,False}
                        Use RSS generator loop or scrap RSS data only once at
                        startup (overrides config 'genloop' option) (default:
                        None)
```
