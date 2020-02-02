# Remote Deploy

* For a bare-bones Ubuntu 16.04 server (EC2 tested), use `ops/fresh_machine.sh` to configure the server as a graphical desktop with VNC connectivity
* Use `ops/remote_sync.sh` to sync the full repo to the remote server

# Setup

* Use `install.sh` to install the system requirements and prep the server for running the repo code

# Sheet Manager

### Run with test data

`python ~/muad-dweeb/cw/manage_sheets.py --master-config master_test --child-config child_test --operation merge`

# Spreadsheet Scrape

### Usage

Recommend to sort the input sheet by owner last name to prevent duplicate scrapes beforehand. 

`cd ~/muad-dweeb/cw`

`./python scrape/spreadsheet_scrape.py -h`