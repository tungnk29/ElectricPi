#!/usr/bin/python3
import socket
import time
import os
status = True

def is_connected():
    try:
        c = socket.create_connection(('8.8.8.8', 53), 2)
        c.close()
        return True
    except:
        pass
    return False

def switch_modem():
    # stop UDP client service
    os.system('sudo systemctl stop UDPClient')
    os.system('sudo systemctl disable UDPClient')

    # start UDP Modem client service
    os.system('sudo systemctl enable modem_udp')
    os.system('sudo systemctl start modem_udp')

    return

def switch_udpsocket():
    # stop UDP Modem client service
    os.system('sudo systemctl stop modem_udp')
    os.system('sudo systemctl disable modem_udp')

    # start UDP client service
    os.system('sudo systemctl enable UDPClient')
    os.system('sudo systemctl start UDPClient')

    return

def main():
    global status
    while True:
        try:
            if is_connected() and status:
                print('Pass...')
            else:
                if not is_connected():
                    if status:
                        status = False
                        switch_modem()
                        print('No UDP connection...!')
                    print('Switched to Modem...')
                elif is_connected() and not status:
                    switch_udpsocket()
                    print('Return to UDP connection !')
                    status = True
                else:
                    print('Nop...!')
            time.sleep(1)
        except:
            print('stop check connection')

if __name__ == '__main__':
    main()
