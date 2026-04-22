#!/usr/bin/env bash
# openclaw installer — double-click wrapper. Real work lives in install.sh.
cd "$(dirname "$0")" || exit 1
bash install.sh
status=$?
printf '\n'
read -r -p "Press Enter to close this window..." _
exit "$status"
