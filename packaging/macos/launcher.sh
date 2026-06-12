#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
nohup "$DIR/PyGoose" > /dev/null 2>&1 &
disown $!
