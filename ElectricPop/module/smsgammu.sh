#!/bin/bash

net_sms=$(bash lsusb.sh | awk '/Mobile/ {print $1}' | tail -1)

if [[ $net_sms != '' ]] ; then 
    echo "Found path of GSM Modem ! Starting send SMS!"
    sed -i "s|tty.*|$net_sms|" ~/.gammurc
    echo $1 | gammu --sendsms TEXT $2
else
    echo "Cannot send SMS! Please try again !"
fi