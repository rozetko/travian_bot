Travian 4 bot for *nix systems. (Doesn't work on Windows)
Working as a Unix daemon.
Default log file: debug.log

Log-, config- and pid-files should have write and read permissions.

How to run it:
$ python bot.py example.json start

To stop:
$ python bot.py example.json stop

Example of config-file (example.json):

http://pastebin.com/tLMPkhWf

village: number of village in list on the right side of screen.
skip: if 0 - bot would try to upgrade this building until it could. If 1 - if couldn't upgrade - would try to upgrade next building.
to: upgrade to n-th level.
fieldId: id of field, lol. If fieldId == "res": would upgrade resource fields. In this case, you should also give such keys as: wood, clay, iron, crop.

Good luck!
