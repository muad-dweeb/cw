#!/bin/bash

key_file=$1
repo_path=$2
remote_ip=$3


function display_help {
  echo "Example usage:"
  echo "./remote_sync.sh <key_file> <repo_path> <remote_ip>"
}

function verify_not_blank {
  name=$1
  value=$2
  if [ -z "$value" ]; then
    echo "'$name' argument is empty!"
    display_help
    exit -1
  fi
}

function verify_file_exists {
  file_path=$1
  if [ ! -f "$file_path" ]; then
    echo "$file_path does not exist!"
    display_help
    exit -1
  fi
}

function verify_dir_exists {
  dir_path=$1
  if [ ! -d "$dir_path" ]; then
    echo "$dir_path does not exist!"
    display_help
    exit -1
  fi
}


verify_not_blank "key_file" $key_file
verify_not_blank "repo_path" $repo_path
verify_not_blank "remote_ip" $remote_ip


verify_file_exists $key_file
verify_dir_exists $repo_path


rsync -e "ssh -i ${key_file}" -av --exclude-from='rsync_exclusions.txt' ${repo_path} ubuntu@${remote_ip}:/home/ubuntu/muad-dweeb/
