#!/bin/bash

net_sms=$(dmesg | awk '/GSM.*ttyUSB[0-9]/ {print $NF}' | tail -1)

if [[ $net_sms != '' ]] ; then 
    echo "Found path of GSM Modem !\n Starting send SMS!"
    sed -i "s|tty.*|$net_sms|" ~/.gammurc
    echo "$2" | gammu --sendsms TEXT "$1"
else
    echo "Cannot send SMS! Please try again !"
fi