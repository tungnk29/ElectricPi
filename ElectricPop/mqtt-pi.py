from module.pmread import register_reading, sensor_reading
from cryptography.fernet import Fernet
from datetime import datetime
from threading import Thread
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import sqlite3 as sql
import psutil
import time
import json
import ssl
import re
import os

# path to database config file
cwd = os.path.dirname(os.path.realpath(__file__))
dbpath = cwd + "/config.db"

# Encrypt/Decrypt package
key = b'ztpn8wdO3ZNiNW3V9GZJlKWy8RioHnPC5-W5TQ0ZSEM='
cipher = Fernet(key)

# Pin GPIO and setup
swPinOn = 12  # chan swPinOn dong relay
swPinOff = 16 # chan swPinOff ngat relay
statusPin = 18 # chan tiep diem doc trang thai

# Counter variable
counter = 0
connect_counter = 0
phone = ''

# Setup GPIO mode
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(swPinOn, GPIO.OUT)
GPIO.setup(swPinOff, GPIO.OUT)
GPIO.setup(statusPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

GPIO.output(swPinOn, 0)
GPIO.output(swPinOff, 0)

def getrec(table, mode=False):
    '''
        read infomation from database file
        mode = fasle ==> return list of dictionary record
        mode = true ==> return dictionary one record
    '''
    db = sql.connect(dbpath)
    db.row_factory = sql.Row
    mouse = db.cursor()
    mouse.execute("SELECT * FROM {}".format(table))
    if not mode:
        rows = mouse.fetchall()
        res = [dict(d) for d in rows]
    else:
        rows = mouse.fetchone()
        res = dict(rows)
    db.close()
    return res

# switch on pop
def switch_pop(boolean = 1):
    if boolean:
        GPIO.output(swPinOn, 1)
        time.sleep(2)
        GPIO.output(swPinOn, 0)
        time.sleep(2)
    else:
        GPIO.output(swPinOff, 1)
        time.sleep(2)
        GPIO.output(swPinOff, 0)
        time.sleep(2)

    print('Pop status switched\n')

# read status contact pin 
def read_status_pin():
    return GPIO.input(statusPin)

# Gui tin nhan
def GSM_MakeSMS(phone, text):
    os.system("bash /opt/ElectricPi/ElectricPop/module/smsgammu.sh '{0}' '{1}'".format(text, phone))

# Xu li cac phan hoi tu server
def recv_package(decrespone):
    # print(decrespone)

    def alarm():
        '''Nhan lenh gui tin nhan canh bao'''
        global counter, phone
        phone = decrespone["phone"]
        print(counter)
        if decrespone.get("alarm") == True:
            if counter % 4 == 0 and counter <= 12:
                GSM_MakeSMS(phone, "Canh bao! Co su co !!!")
                print("Canh bao nguy hiem")
            counter += 1

    def notify(phone):
        GSM_MakeSMS(phone, "Da het su co ! ^ _ ^")

    def switch():
        '''Dong ngat mach'''

        global phone, counter

        if decrespone["switch"] != GPIO.input(statusPin):
            # Thread(target=switch_pop, args=(decrespone["switch"],)).start()
            switch_pop(decrespone["switch"])

        if not decrespone.get("alarm", 0):
            if counter > 0 and counter % 4 != 0:
                print(phone)
                notify(phone=phone)
                counter = 0

    for f in decrespone['func']:
        exec(f)

# Data de gui len broker mqtt
def uicosfi_package(token):
    pack2send = dict()
    pminfo = getrec("powermeter")

    uicosfi = [register_reading(d["ids"], 2, d["a"], d["a1"], d["a2"], d["a3"], d["vll"], d["vln"], d["v1"], d["v2"],d["v3"], d["v12"], d["v23"], d["v31"], d["pf"], d["pf1"], d["pf2"], d["pf3"]) for d in pminfo]
    pack2send["record"] = uicosfi
    pack2send["token"] = token
    pack2send["temperature"] = sensor_reading()
    pack2send["real_status"] = read_status_pin()

    packg = cipher.encrypt(json.dumps(pack2send).encode())
    return packg.decode()


# Server infomation
config = getrec("config", True)
broken_url = 'vscada.ddns.net'
broken_port = 8883


topic_status = '/scada/{}/status'.format(config['token'])
topic_execute = '/scada/{}/execute'.format(config['token'])
topic_push = '/scada/{}/push'.format(config['token'])


rc_message = [
        'Connection successful',
        'Connection refused – incorrect protocol version',
        'Connection refused – invalid client identifier',
        'Connection refused – server unavailable',
        'Connection refused – bad username or password',
        'Connection refused – not authorised'
    ]

def on_publish(client, obj, mid):
    print("mid: " + str(mid))

def on_connect(client, userdata, flags, rc):
    if rc==0:
        status_pack = json.dumps({'modem_status': 1, 'pop_status': read_status_pin(), 'token': config['token']}).encode()
        status_pack = cipher.encrypt(status_pack).decode()

        client.connected_flag = True #set flag
        print("connected OK Returned code=",rc)

        client.publish(topic=topic_status, payload=status_obj)

        print("subscribing Topic...")
        client.subscribe(topic=topic_execute, qos=1)

        return
        
    print("Bad connection Returned code= ",rc)
    client.bad_connection_flag = True
    

def on_disconnect(client, userdata, rc):
    print("Client got disconnected!")
    print(rc, ': ', rc_message[rc])

    client.connected_flag = False
    client.disconnect_flag = True

def on_message(mosq, obj, msg):
    print(msg.topic)
    if (msg.topic == topic_execute):
        data = json.loads(cipher.decrypt(msg.payload))

        print("Message to execute: " + str(data))
        
        recv_package(data)
        


client = mqtt.Client()
client.username_pw_set(username='scada', password='Abcd@1234@')
client.tls_set('/etc/ssl/certs/DST_Root_CA_X3.pem', tls_version=ssl.PROTOCOL_TLSv1_2)        

# LWT
status_lwt = json.dumps({'modem_status': 0, 'pop_status': 0}, 'token': config['token']).encode()
status_lwt = cipher.encrypt(status_lwt).decode()
client.will_set(topic=topic_status, payload="Offline", qos=2, retain=True)

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.on_publish = on_publish
client.connect(host=broken_url, port=broken_port, keepalive=10)

client.subscribe(topic=topic_execute, qos=2)

def main():
    while True:
        try:
            status_pack = json.dumps({'modem_status': 1, 'pop_status': read_status_pin()}, 'token': config['token']).encode()
            status_pack = cipher.encrypt(status_pack).decode()

            packs = uicosfi_package(config['token'])
            client.publish(topic=topic_push, payload=packs)
            client.publish(topic=topic_status, payload="Online")
            time.sleep(2)
        except KeyboardInterrupt:
            print("Break program !")
            GPIO.cleanup()
            break

# client.loop_forever()

client.loop_start()

# Thread(target=main, args=()).start()
main()

client.loop_stop()
