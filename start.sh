#!/bin/bash

exit_code=137
while [ $exit_code == 137 ] || [ $exit_code == 139 ]
do
  # In case the process is killed by SIGKILL (such as when oom-killer triggers)/SIGSEV (when the faulty JH implementation crashes), relaunch it
  python3 -u main.py $1 >> output.txt

  exit_code=$?
done
