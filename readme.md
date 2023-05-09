<p align="center">
  <img height=256 width=256 src='https://user-images.githubusercontent.com/70798458/194714777-167bb130-d9af-47ee-8967-2f6fea2364b4.png'>
</p>
<br/>
<p align="center">
  <em>The backend system that controls and manages Senarc's Discord Guilds.</em>
</p>

---

<p align="center">
  <a href='https://discord.gg/5YY3W83YWg'><img alt="Discord" height=45 src='https://pbs.twimg.com/media/FM7jr5BXIAkke5D?format=png&name=4096x4096'/></a>
</p>

# Quickstart Guide
### Installing Packages
```sh
# Windows
pip install -U -r requirements.txt
# Other OS
python3 -m pip install -U -r requirements.txt
```
### Constants File
1. Rename the file in `assets/json/constants-template.json` into `constants.json`
2. Replace all the constants with valid values from application and Discord Guild.

### Running Bot Client
```sh
# Windows
python ./bot.py
# Other OS
python3 ./bot.py
```

### Running API Client
```sh
# Windows
python -m uvicorn main:app --reload --host 127.0.0.1 --workers 2 --port 2000
# Other OS
./start.sh
```
