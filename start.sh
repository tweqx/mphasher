#!/bin/bash

exit_code=137
while [ $exit_code == 137 ]
do
  # In case the process is killed by SIGKILL (such as when oom-killer triggers), relaunch it
  python3 -u main.py list.txt >> output.txt

  exit_code=$?
done
