Travian 4 bot for *nix systems. (Doesn't work on Windows)
Working as a Unix daemon.
Default log file: debug.log

Log-, config- and pid-files should have write and read permissions.

How to run it:
$ python bot.py example.json start

To stop:
$ python bot.py example.json stop

Example of config-file (example.json):

{ 
    "login": {
        "username": "username", 
        "password": "password", 
        "proxy": {}, 
        "server": "http://tx3.travian.ru"
    }, 
    "adventures": {
        "enable": 1
    }, 
    "build": {
        "delay": 20, 
        "enable": 1, 
        "buildingList": [
            {
                "village": 1,
                "fieldId": "res",
                "to": 10,
                "wood": 1, 
                "clay": 1, 
                "iron": 1,
                "crop": 1,
                "skip": 1
            }, 
            {
                "village": 1,
                "fieldId": 36,
                "to": 5,
                "skip": 1
            }
        ]
    }
}

village: number of village in list on the right side of screen.
skip: if 0 - bot would try to upgrade this building until it could. If 1 - if couldn't upgrade - would try to upgrade next building.
to: upgrade to n-th level.
fieldId: id of field, lol. If fieldId == "res": would upgrade resource fields. In this case, you should also give such keys as: wood, clay, iron, crop.

Good luck!
