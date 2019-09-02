#!/bin/bash

dmesg | awk '/uart.+ttyUSB[0-9]/{print $NF;exit}'