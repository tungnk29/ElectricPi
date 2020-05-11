# -*- coding: utf-8 -*-
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from cryptography.fernet import Fernet
import socket, os, subprocess, psutil, time, pickle, json
import sqlite3 as sql

cwd = os.path.dirname(os.path.realpath(__file__))
dbpath = cwd + "/config.db"

key = b'ztpn8wdO3ZNiNW3V9GZJlKWy8RioHnPC5-W5TQ0ZSEM='
cipher = Fernet(key)

counter = 0
connect_counter = 0
phone = ''

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

CONFIG = getrec("config", True)
srv_info = (CONFIG["server"], CONFIG["port"])

GPIO_PIN_IN = {
    'RMU_C_II': 2,
    'RMU_C_FUSE_CB': 3,
    'RMU_C_Out': 4,
    'RMU_P_Air_Low': 5,
    'RMU_F_Cable_SMS': 6,
    'MBA_P_HIGHT': 7,
    'MBA_Oil_HIGHT': 8,
    'MBA_Oil_LOW': 9,
    'MBA_T_Over': 10,
    'MBA_SPARE': 11,
    'ATM_LV_CI_OP': 12,
    'DOOR_F_ALaRM': 13,
}

GPIO_PIN_OUT = {
    'ATM_CLOSE_1': 17,
    'ATM_CLOSE_2': 18,
    'ATM_OPEN_1': 19,
    'ATM_OPEN_2': 20
}

try:
    import RPi.GPIO as GPIO
    # Setup GPIO mode
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    for val in GPIO_PIN_IN.values():
        GPIO.setup(val, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    for val in GPIO_PIN_OUT.values():
        GPIO.setup(val, GPIO.OUT)
except:
    pass

def srv_info_reload():
    global CONFIG, srv_info
    CONFIG = getrec("config", True)
    srv_info = (CONFIG["server"], CONFIG["port"])

def read_status_pin(pin):
    return GPIO.input(pin)

def switch_pop(boolean = 1):
    if boolean:
        GPIO.output(GPIO_PIN_OUT['ATM_CLOSE_1'], 1)
        time.sleep(2)
        GPIO.output(GPIO_PIN_OUT['ATM_CLOSE_1'], 0)
        time.sleep(2)
    else:
        GPIO.output(GPIO_PIN_OUT['ATM_OPEN_1'], 1)
        time.sleep(2)
        GPIO.output(GPIO_PIN_OUT['ATM_OPEN_1'], 0)
        time.sleep(2)

    print('Pop status switched\n')

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

    text = f'Dia chi: {content["address"]} \n'
    for k, v in content['detail'].items():
        text += f'Powermeter {k}: '
        if v.get('vln', False):
            text += f'VLN: {v["vln"][0]} ({">= Vmax" if v["vln"][1] else "< Vmin"}).'
        if v.get('a', False):
            text += f'I: {v["a"][0]} ({">= Imax" if v["a"][1] else "< Imin"}).'
    return text

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

        if decrespone["switch"] != GPIO.input(GPIO_PIN_IN['RMU_C_Out']):
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

    uicosfi = [register_reading(count=2, **d) for d in pminfo]
    pack2send["record"] = uicosfi
    pack2send["token"] = token
    pack2send["temperature"] = sensor_reading()
    pack2send["real_status"] = read_status_pin(GPIO_PIN_IN['RMU_C_Out'])

    packg = cipher.encrypt(json.dumps(pack2send).encode())
    return packg

def get_modbus_path():
    shell_path = cwd + '/mbdevice.sh'

    cmd = subprocess.Popen("bash " + shell_path, stdout=subprocess.PIPE, shell=True)

    (result, err) = cmd.communicate()

    result = str(result, encoding='utf-8')

    return '/dev/' + result.strip()


def is_connected():
    try:
        c = socket.create_connection(('8.8.8.8', 53), 2)
        c.close()
        return True
    except:
        pass
    return False

def sensor_reading():
    return psutil.sensors_temperatures()['cpu-thermal'][0].current


def validator(instance):
    '''Decode raw data from register'''
    if not instance.isError():

        decoder = BinaryPayloadDecoder.fromRegisters(
            instance.registers,
            byteorder=Endian.Big, wordorder=Endian.Little
        )
        return float(decoder.decode_32bit_float())

    else:
        # Error handling.
        print("Registers Reading Error!, Try again.")
        return 0

def register_reading(count, **kwargs):
    print("Start reading Power Meter...")
    result = {
        'ids': kwargs.pop('ids')
    }
    
    try:
        modbus = ModbusClient(method='rtu', port=get_modbus_path(), baudrate=9600, timeout=1, parity='E', bytesize=8)
        modbus.connect()

        for key, val in kwargs.items():
            result[key] = validator(modbus.read_holding_registers(val - 1, count, unit=result['ids']))
            print(key, ': ', result[key]), 

        modbus.close()

        return result
    except KeyboardInterrupt:
        print('Ctrl + C pressed or any error')
    # except:
    #     print("Error!")
    #     return {"ids": 0, "a":0, "a1":0, "a2":0, "a3":0, "vll":0, "vln":0, "v1":0, "v2":0, "v3":0, "v12":0, "v23":0, "v31":0, "pf": 0, "pf1":0, "pf2":0, "pf3":0}
