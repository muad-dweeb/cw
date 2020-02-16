#!/bin/bash

function exit_on_error {
  exit_code=$1
  if [ $exit_code != 0 ]
  then
    echo "Last command failed; exiting"
    exit -1
  fi
}

sudo sed -ie 's/PasswordAuthentication no/PasswordAuthentication yes/g' /etc/ssh/sshd_config
exit_on_error $?

sudo /etc/init.d/ssh restart
exit_on_error $?

sudo apt update
exit_on_error $?

sudo apt -y upgrade
exit_on_error $?

sudo apt -y install ubuntu-desktop
exit_on_error $?

sudo apt -y install vnc4server
exit_on_error $?

sudo apt -y install gnome-panel gnome-settings-daemon metacity nautilus gnome-terminal htop
exit_on_error $?

vncserver
exit_on_error $?

vncserver -kill :1
exit_on_error $?

mv ~/.vnc/xstartup ~/.vnc/xstartup.bak
exit_on_error $?

cat <<EOT >> ~/.vnc/xstartup
#!/bin/sh

export XKL_XMODMAP_DISABLE=1
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS

[ -x /etc/vnc/xstartup ] && exec /etc/vnc/xstartup
[ -r $HOME/.Xresources ] && xrdb $HOME/.Xresources
xsetroot -solid grey
vncconfig -iconic &

gnome-panel &
gnome-settings-daemon &
metacity &
nautilus &
gnome-terminal &
EOT
exit_on_error $?

sudo chmod +x ~/.vnc/xstartup
exit_on_error $?

sudo iptables -A INPUT -p tcp --dport 5901 -j ACCEPT
exit_on_error $?

# unnecessary if full repo has already been synced, but whatever
mkdir -p ${HOME}/muad-dweeb
exit_on_error $?

# For running cw repo code
echo '' >> ${HOME}/.bashrc
echo 'export PYTHONPATH=/home/ubuntu/muad-dweeb/cw' >> ${HOME}/.bashrc

sudo reboot now
