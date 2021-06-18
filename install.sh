#/bin/bash

# The directory this script lives in, regardless of where it is called from.
#   https://stackoverflow.com/a/246128/3900915
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

VENV_ROOT="${HOME}/.virtualenvs/cw"


##################
#  Python setup  #
##################

if [[ -z "$(command -v pip)" ]]; then
    echo 'Installing PIP...'

    if [[ "$OSTYPE" == "linux-gnu" ]]; then
        echo 'Linux OS detected'
        sudo apt install -y python-pip
        "export PYTHONPATH=/home/ubuntu/muad-dweeb/cw" >> ${HOME}/.bashrc

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
sudo python -m pip install --upgrade pip

echo 'Building Python virtual environment...'
sudo python -m pip install virtualenv
mkdir -p $VENV_ROOT
virtualenv -p python3 $VENV_ROOT
echo "Python3 virtual env created at $VENV_ROOT"
source ${VENV_ROOT}/bin/activate
pip install -r requirements.txt

ln -s ${VENV_ROOT}/bin/python ${SCRIPT_DIR}/python



####################
# Install Caffeine #
####################

if [[ -z "$(command -v caffeine)" ]]; then
    echo 'Installing Caffeine...'

    if [[ "$OSTYPE" == "linux-gnu" ]]; then
        echo 'Linux OS detected; skipping.'
        # sudo apt -y install caffeine

    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo 'Mac OS detected'
        brew cask install caffeine

    else
        echo "Unsupported OS detected: $OSTYPE"

    fi
fi


##################
#  Chrome Setup  #
##################

export PYTHONPATH=${SCRIPT_DIR}

${VENV_ROOT}/bin/python ${SCRIPT_DIR}/install/install_chrome.py


##################
#  Add Crontab   #
##################

echo "Installing crontab"
crontab ${SCRIPT_DIR}/lib/crontab
