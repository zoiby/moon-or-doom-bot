# moon-or-doom-bot

This is a CLI bot intended for use with the YoloGames.io Moon or Doom game. 

It will allow a user to quickly enter positions, claim rewards, and track stats for their existing session. Session stats are written to a file when the application is exited.

#### NOTE: This bot does not provide realtime price or round timer data at this time.

## Setup and Use Instructions:

Step 1) Open the `moon-or-doom-bot` directory in VS Code

Step 2) Open a new terminal in VS Code, you should be in the `moon-or-doom-bot` directory

Step 3) Attempt to install all dependencies by typing: `pip install -r ./requirements.txt`

Step 4) Create a copy of the `.env.example` file and name it `.env`

Step 5) Add your wallets private key to the appropriate field in the `.env` file and save it

Step 6) In the VS Code terminal, from the `moon-or-doom-bot` directory, type `cd src/bot` to move into the bot directory

Step 7) Type `py moon_or_doom.py` or `python3 moon_or_doom.py` -- it depends on your local environments Python configuration, if one does not work try the other

Step 8) Enter the wager amount in Ether -- !! If you enter 1, it will attempt to wager 1 ETH !! If you enter .01, it will wager .01 ETH

Step 9) Ensure you have the YOLOGames.io moon or doom page open so you can watch the timer and chart to enter

Step 10) You may now enter positions by typing either 'm' or 'd' and pressing enter

