#!/bin/bash

while true ; do
        ping -c3 -I eth0 8.8.8.8
        if [ $? == 0 ] ; then
                echo eth0 is working
                sudo ip route del default dev ppp0
        else
                echo eth0 is busted
                sudo ip route add default dev ppp0

        fi
        sleep 5
done