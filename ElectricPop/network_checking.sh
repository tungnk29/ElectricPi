#!/bin/bash

while true ; do
        ping -c3 -I eth0 8.8.8.8
        if [ $? == 0 ] 
        then
                echo "Eth0 is working"

                current_dni=$(ip route show | awk '/default.*ppp0/ {print $3}')
                if [[ $current_dni == "ppp0" ]] ; then
                    echo "Switching to Ethernet"
                    sudo ip route del default dev ppp0
                fi
        else
                echo "Eth0 is busted.\n"

                current_dni=$(ip route show | awk '/default.*ppp0/ {print $3}')
                if [[ $current_dni != "ppp0" ]] ; then
                    # check connection over ppp0 interface
                    ping -c3 -I ppp0 8.8.8.8

                    if [ $? == 0 ]
                    then
                        echo "Switching to USB 3G..."              
                        sudo ip route add default dev ppp
                    else
                        echo "Fail to Switching to USB 3G :("
                    fi
                fi

        fi
        sleep 5
done