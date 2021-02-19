# -*- coding: utf-8 -*-
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from cryptography.fernet import Fernet
from redis import Redis
from datetime import datetime
import socket, os, subprocess, psutil, time, pickle, json
import sqlite3 as sql
import Adafruit_DHT as DHT

reds = Redis(host='localhost', port=6379, db=0)

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



class PiMethods():
    CWD = os.path.dirname(os.path.realpath(__file__))
    DBPATH = CWD + "/config.db"

    TOKEN = reds.get('TOKEN').decode()
    KEY = reds.get('KEYCRYPT')
    HOST = reds.get('HOST').decode() or 'vtechnic.xyz'
    PORT = reds.get('PORT').decode() or '3001'
    URL = f'http://{HOST}:{PORT}'
    CIPHER = Fernet(KEY)


    COUNTER = 0
    CONNECT_COUNTER = 0
    PHONE = ''

    def getrec(self, table, mode=False):
        db = sql.connect(self.DBPATH)
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

    def read_status_pin(self, pin):
        return bool(GPIO.input(pin))

    def switch_pop(self, boolean = 1):
        if boolean:
            GPIO.output(GPIO_PIN_OUT['ATM_CLOSE_1'], 1)
            time.sleep(2)
            GPIO.output(GPIO_PIN_OUT['ATM_CLOSE_1'], 0)
            time.sleep(2)
            print('Switch Pop from Off =====> On')
        else:
            GPIO.output(GPIO_PIN_OUT['ATM_OPEN_1'], 1)
            time.sleep(2)
            GPIO.output(GPIO_PIN_OUT['ATM_OPEN_1'], 0)
            time.sleep(2)
            print('Switch Pop from On =====> Off')

    def GSM_MakeSMS(self, phone, text):
        os.system(f"bash {self.CWD}/smsgammu.sh '{text}' {phone}")

    def parse_sms(self, content):
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

    def recv_package(self, decrespone):
        print(decrespone)

        def alarm():
            '''Nhan lenh gui tin nhan canh bao'''

            self.PHONE = decrespone["phone"]
            print(COUNTER)
            if decrespone.get("alarm") == True:
                if self.COUNTER % 4 == 0 and self.COUNTER <= 12:
                    self.GSM_MakeSMS(self.PHONE, parse_sms(decrespone['warning']))
                    print("Canh bao nguy hiem")
                self.COUNTER += 1

        def notify(phone):
            GSM_MakeSMS(phone, "Da het su co !")

        def switch():
            '''Dong ngat mach'''

            if decrespone["switch"] != GPIO.input(GPIO_PIN_IN['ATM_LV_CI_OP']):
                self.switch_pop(decrespone["switch"])

            if not decrespone.get("alarm", 0):
                if self.COUNTER > 0 and self.COUNTER % 4 != 0:
                    print(phone)
                    notify(phone=phone)
                    self.COUNTER = 0

        def publish():
            data_powermeter = self.process_data(self.data_powermeter())
            pop_status = self.process_data(self.pop_status())
            try:
                post_data = requests.post(f'{self.URL}/data/push', data={ 'message': data_powermeter })
                post_status = requests.post(f'{self.URL}/pops/status', data={ 'message': pop_status })
            except Exception as err:
                print(err)

        for f in decrespone['func']:
            exec(f)

    def pop_status(self):
    	pins_status = dict()
    	for key, val in GPIO_PIN_IN.items():
    		pins_status[key] = self.read_status_pin(val)

    	return {
        	'status': pins_status,
        	'token': self.TOKEN,
        	'last_update': str(datetime.now()),
        	'temperature': self.sensor_reading()
        }

    def data_powermeter(self):
        pminfo = self.getrec("powermeter")
        uicosfi = [self.register_reading(count=2, **d) for d in pminfo]
        now = str(datetime.now())
        for record in uicosfi:
            record.update({ 'createAt':  now})

        return {
        	'data': uicosfi,
        	'token': self.TOKEN
        }

    def process_data(self, data, encrypt=True):
        if encrypt:
            return self.CIPHER.encrypt(json.dumps(data).encode())

        return json.dumps(data)

    def get_modbus_path(self):
        shell_path = self.CWD + '/mbdevice.sh'

        cmd = subprocess.Popen("bash " + shell_path, stdout=subprocess.PIPE, shell=True)

        (result, err) = cmd.communicate()

        result = str(result, encoding='utf-8')

        return '/dev/' + result.strip()

    def is_connected(self):
        try:
            client = socket.create_connection(('8.8.8.8', 53), 2)
            client.close()
            return True
        except:
            return False

    def sensor_reading(self, sensor=False):
        if not sensor:
            return psutil.sensors_temperatures()['cpu-thermal'][0].current

        humidity,temperature = Adafruit_DHT.read_retry(DHT.DHT11, 14)
        return temperature

    def validator(self, instance):
        '''Decode raw data from register'''
        if not instance.isError():

            decoder = BinaryPayloadDecoder.fromRegisters(
                instance.registers,
                byteorder=Endian.Big, wordorder=Endian.Little
            )
            return float(decoder.decode_32bit_float())


        print("Registers Reading Error!, Try again.")
        return 0

    def register_reading(self, count, **kwargs):
        print("Start reading Power Meter...")
        kwargs.pop('id')
        result = {
            'ids': kwargs.pop('ids')
        }
        try:
            modbus = ModbusClient(method='rtu', port=self.get_modbus_path(), baudrate=9600, timeout=1, parity='E', bytesize=8)
            modbus.connect()

            for key, val in kwargs.items():
                result[key] = self.validator(modbus.read_holding_registers(val - 1, count, unit=result['ids']))
                print(key, ': ', result[key]), 

            modbus.close()

            return result
        except KeyboardInterrupt:
            print('Ctrl + C pressed or any error')

    

