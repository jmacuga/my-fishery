## MY Fishery

### Requirements

python 3.13.2

### Set up
sudo apt install prosody

sudo prosodyctl start

sudo cat /var/log/prosody/prosody.log

sudo mkdir -p /run/prosody
sudo chown prosody:prosody /run/prosody

sudo prosodyctl adduser owner@localhost
sudo prosodyctl adduser fisher@localhost
...

### Run

sudo mkdir -p /run/prosody
sudo chown prosody:prosody /run/prosody

sudo prosodyctl start
sudo prosodyctl status
