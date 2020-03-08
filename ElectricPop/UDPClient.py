from module.pmread import register_reading, sensor_reading
from threading import Thread
from cryptography.fernet import Fernet
import sqlite3 as sql
import os, re, time, serial, pickle, socket
import RPi.GPIO as GPIO

# path to config file
cwd = os.path.dirname(os.path.realpath(__file__))
dbpath = cwd + "/config.db"

# Encrypt/Decrypt package
key = b'ztpn8wdO3ZNiNW3V9GZJlKWy8RioHnPC5-W5TQ0ZSEM='
cipher = Fernet(key)

swPin = 12  # chan swPin dong relay
swPinOff = 16 # chan swPinOff ngat relay
statusPin = 18 # chan tiep diem doc trang thai

# Counter variable
counter = 0
connect_counter = 0
phone = ''

# Setup GPIO mode
GPIO.setmode(GPIO.BCM)
GPIO.setup(swPin, GPIO.OUT)
GPIO.setup(swPinOff, GPIO.OUT)
GPIO.setup(statusPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

GPIO.output(swPin, 0)
GPIO.output(swPinOff, 0)

# Socket Init
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(3)

def getrec(table, mode=False):
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

# Server infomation
config = getrec("config", True)
srv_info = (config["server"], config["port"])

# reload server info
def srv_info_reload():
    global config, srv_info
    config = getrec("config", True)
    srv_info = (config["server"], config["port"])

# read status contact pin 
def read_status_pin():
    return GPIO.input(statusPin)

# switch on pop
def switch_pop(boolean = 1):
    if boolean:
        GPIO.output(swPin, 1)
        time.sleep(2)
        GPIO.output(swPin, 0)
        time.sleep(2)
    else:
        GPIO.output(swPinOff, 1)
        time.sleep(2)
        GPIO.output(swPinOff, 0)
        time.sleep(2)

    print('Pop status switched\n')

# Gui tin nhan
def GSM_MakeSMS(phone, text):
    os.system("bash /opt/ElectricPi/ElectricPop/module/smsgammu.sh '{0}' {1}".format(text, phone))

def parse_sms(content):
    # full package from server
    # {
    #         'address': 'Công Ty TNHH KHC', 
    #         'detail': {
    #             '1': {'vln': [1.000000045813705e-18, False]} 
    #         }
    # }

    text = f'Dia chi: {content['address']} \n'
    for k, v in content['detail'].items():
        text += f'Powermeter {k}: '
        if v.get('vln', False):
            text += f'VLN: {v['vln'][0]} ({">= Vmax" if v['vln'][1] else "< Vmin"}).'
        if v.get('a', False):
            text += f'I: {v['a'][0]} ({">= Imax" if v['a'][1] else "< Imin"}).'
    return text

# Xu li cac phan hoi tu server
def recv_package(decrespone):
    print(decrespone)

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
        GSM_MakeSMS(phone, "Da het su co !")

    def switch():
        '''Dong ngat mach'''

        global phone, counter

        if decrespone["switch"] != GPIO.input(18):
            switch_pop(decrespone["switch"])

        if not decrespone.get("alarm", 0):
            if counter > 0 and counter % 4 != 0:
                print(phone)
                notify(phone=phone)
                counter = 0

    for f in decrespone['func']:
        exec(f)


def uicosfi_package(token):
    pack2send = dict()
    pminfo = getrec("powermeter")

    uicosfi = [register_reading(d["ids"], 2, d["a"], d["a1"], d["a2"], d["a3"], d["vll"], d["vln"], d["v1"], d["v2"],d["v3"], d["v12"], d["v23"], d["v31"], d["pf"], d["pf1"], d["pf2"], d["pf3"]) for d in pminfo]
    pack2send["record"] = uicosfi
    pack2send["token"] = token
    pack2send["temperature"] = sensor_reading()
    pack2send["real_status"] = read_status_pin()

    packg = b'808' + cipher.encrypt(pickle.dumps(pack2send))
    return packg

def main():
    # GSM_Check()
    global srv_info, config
    try:
        while True:
            try:
                srv_info_reload()
                
                s.sendto(uicosfi_package(config['token']), srv_info)

                res = s.recvfrom(4096)

                data = pickle.loads(cipher.decrypt(res[0][3:]))
                recv_package(data)
                # print(res)
            except socket.timeout:
                # srv_info_reload()
                print('Time out to receive data from server ! Try again !')
            except KeyboardInterrupt:
                print('Cancel by keyboard')
                break
            except socket.gaierror:
                print('Wrong server info !')                
            except Exception:
                print('error to decode data from server !')

            time.sleep(0.5)
    except KeyboardInterrupt:
        print('Cancel by keyboard')

            
if __name__ == '__main__':
    main()
  


