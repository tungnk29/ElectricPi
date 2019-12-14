from module.pmread import register_reading, sensor_reading
from cryptography.fernet import Fernet
from datetime import datetime
from gmqtt import Message, Client as MQTTClient
import RPi.GPIO as GPIO
import sqlite3 as sql
import asyncio
import signal
import uvloop
import json
import time
import os


asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
STOP = asyncio.Event()

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
    return 1

# read status contact pin 
def read_status_pin():
    return GPIO.input(statusPin)

# Gui tin nhan
def GSM_MakeSMS(phone, text):
    os.system("bash /opt/ElectricPi/ElectricPop/module/smsgammu.sh '{0}' '{1}' &".format(text, phone))

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
                GSM_MakeSMS(phone, parse_sms(decrespone['warning']))
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
    pack2send["datetime"] = str(datetime.now())

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

def ask_exit(*args):
    STOP.set()

def status_package():
    status_pack = json.dumps({'modem_status': 1, 'pop_status': read_status_pin(), 'token': config['token']}).encode()
    status_pack = cipher.encrypt(status_pack).decode()

    return status_pack

def on_connect(client, flags, rc, properties):
    print("connected OK Returned code=",rc)

    client.publish(topic_status, status_package())

    print(f'subscribing topic {topic_execute} ...')
    client.subscribe(topic_execute, qos=1)

def on_disconnect(client, packet, exc=None):
    print('Disconnected')

def on_subscribe(client, mid, qos):
    print('SUBSCRIBED')

def on_message(client, topic, payload, qos, properties):
    print(f"Message arrive from {topic} ")
    if (topic == topic_execute):
        data = json.loads(cipher.decrypt(payload))

        print("Message to execute: " + str(data))
        
        recv_package(data)

async def main_push(client):
    while True:
        packs = uicosfi_package(config['token'])
        await asyncio.sleep(2)
        client.publish(topic_push, payload=packs)
        client.publish(topic_status, payload=status_package())
        
        
async def main():
    # LWT
    status_lwt = json.dumps({'modem_status': 0, 'pop_status': 0, 'token': config['token']}).encode()
    status_lwt = cipher.encrypt(status_lwt).decode()

    will_message = Message(topic_status, status_lwt, will_delay_interval=5) 
    client = MQTTClient(config['token'], will_message=will_message)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.on_subscribe = on_subscribe

    client.set_auth_credentials('scada', 'Abcd@1234@')
    await client.connect(broken_url, broken_port, ssl=True)

    # client.subscribe(topic=topic_execute, qos=2)

    loop.create_task(main_push(client))

    await STOP.wait()
    await client.disconnect()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    loop.add_signal_handler(signal.SIGINT, ask_exit)
    loop.add_signal_handler(signal.SIGTERM, ask_exit)

    loop.run_until_complete(main())

    GPIO.cleanup()


