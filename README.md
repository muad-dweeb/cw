# Remote Deploy

* Use `ops/remote_sync.sh` to sync the full repo to the remote server
* For a bare-bones Ubuntu 16.04 server (EC2 tested), use `ops/fresh_machine.sh` to configure the server as a graphical desktop with VNC connectivity

# Setup

* Use `install.sh` to install the system requirements and prep the server for running the repo code

# Spreadsheet Scrape

Reads a spreadsheet containing first/last names, State and city values, then scrapes the configured (if supported) website for contact info matching those values as search arguments.

Supports distributed processing by defining what hostname is assigned which rows in a `hostname` column in the spreadsheet.

### Warning

Unable to automatically clear Captchas! As such, babysitting is required and remote machines can not be run headless for sites with Captchas.

### Usage

Recommend to sort the input sheet by owner last-name/first-name to prevent duplicate scrapes beforehand. 

#### View Options
`~/.virtualenvs/cw/bin/python3 /home/ubuntu/muad-dweeb/cw/scrape/spreadsheet_scrape.py -h`

#### Scrape the specified config for 5 Hours using IC
`~/.virtualenvs/cw/bin/python3 /home/ubuntu/muad-dweeb/cw/scrape/spreadsheet_scrape.py --config whatcom_duplexes_350_plus --limit-minutes 300 --email-report --site ic --environment ec2`

# Sheet Manager

Utility for joining spreadsheets based on a configured primary key.

### Run with included test data

`python ~/muad-dweeb/cw/manage_sheets.py --master-config master_test --child-config child_test --operation merge`
