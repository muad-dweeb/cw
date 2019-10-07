# Setup

```mkvirtualenv --python=`which python3` cw```

`pip install -r requirements.txt`

# SheetManager

### Run with test data

`python ~/muad-dweeb/cw/manage_sheets.py --master-config master_test --child-config child_test --operation merge`

# spreadsheet_IC_scrape.py

### Setup

1. Download chromedriver and move to /usr/bin/ or /usr/local/bin

### Usage

Recommend to sort the input sheet by owner last name to prevent duplicate scrapes beforehand. 
