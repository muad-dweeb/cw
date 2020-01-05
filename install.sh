#/bin/bash


##################
#  Python setup  #
##################

if [[ -z "${command -v pip}" ]]; then
    echo 'Installing PIP...'

    if [[ "$OSTYPE" == "linux-gnu" ]]; then
        echo 'Linux OS detected'
        apt install -y python-pip

    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo 'Mac OS detected'
        curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
        python get-pip.py
        rm get-pip.py

    else
        echo "Unsupported OS detected: $OSTYPE"
    
    fi
fi

echo 'Upgrading PIP...'
pip install --upgrade pip

echo 'Building Python virtual environment...'
pip install virtualenv virtualenvwrapper
mkvirtualenv --python=`which python3` cw
pip install -r requirements.txt


##################
#  Chrome Setup  #
##################

# TODO: write runner for ChromeInstaller
# TODO: switch Scraper driver to use new in-repo path