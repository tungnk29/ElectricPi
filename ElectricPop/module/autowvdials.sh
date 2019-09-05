#!/bin/bash

net_port=$(dmesg | awk '/GSM.*ttyUSB[0-9]/ {print $NF}' | head -1)

if [[ $net_port != '' ]] ; then
    echo "Found path of GSM Modem ! Setting up config file !"
    sudo sed -i "s|tty.*|$net_port|" /etc/wvdial.conf
    echo "Staring wvdial service"
    wvdial
else
    echo "GSM modem not found or permission denied !"
fi