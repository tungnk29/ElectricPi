# -*- coding: utf-8 -*-
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from cryptography.fernet import Fernet
from redis import Redis
from datetime import datetime
from gpiozero import CPUTemperature
import requests, socket, os, subprocess, time, pickle, json
import sqlite3 as sql
import Adafruit_DHT as DHT

try:
    import RPi.GPIO as GPIO

    # Setup GPIO mode
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

except:
    pass

reds = Redis(host='localhost', port=6379, db=0)

class Public():
    def __init__(self):
        self.CWD = os.path.dirname(os.path.realpath(__file__))
        self.DBPATH = self.CWD + "/config.db"

        self.TOKEN = reds.get('TOKEN').decode()
        self.KEY = reds.get('KEYCRYPT')
        self.HOST = reds.get('HOST').decode() or 'vinsys.vn'
        self.PORT = reds.get('PORT').decode() or '3001'
        self.URL = reds.get('API_URL').decode() 
        self.CIPHER = Fernet(self.KEY)

        self.COUNTER = 0
        self.CONNECT_COUNTER = 0
        self.PHONE = ''

    def getrec(self, table, mode=False):
        ''' 
            Get record from table from sqlite
            table: table name to get record
            mode: return [{...}] if False, return {...} if True

        '''
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

    def GSM_MakeSMS(self, phone, text):
        ''' Send SMS tool '''
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

    def data_powermeter(self):
        ''' Read data from Powermeter '''
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
        ''' Encrypt data to send to server over HTTP API '''
        if encrypt:
            return self.CIPHER.encrypt(json.dumps(data).encode())

        return json.dumps(data)

    def get_modbus_path(self):
        ''' Get RS485 path device to read data from Power Meter '''
        shell_path = self.CWD + '/mbdevice.sh'

        cmd = subprocess.Popen("bash " + shell_path, stdout=subprocess.PIPE, shell=True)

        (result, err) = cmd.communicate()

        result = str(result, encoding='utf-8')

        return '/dev/' + result.strip()

    def is_connected(self):
        ''' Check network on or off '''
        try:
            client = socket.create_connection(('8.8.8.8', 53), 2)
            client.close()
            return True
        except:
            return False

    def sensor_reading(self, sensor=False):
        ''' Read temperature from Pi hardware or DHT11 sensor '''
        if not sensor:
            cpu = CPUTemperature()
            return cpu.temperature

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
        ''' Read data from powermeter with registers value '''
        print(f"{datetime.now()} Start reading Power Meter...")
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

class PiMethods(Public):

    def __init__(self):
        super(PiMethods, self).__init__()
        self.GPIO_PIN_IN = {
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

        self.GPIO_PIN_OUT = {
            'ATM_CLOSE_1': 17,
            'ATM_CLOSE_2': 18,
            'ATM_OPEN_1': 19,
            'ATM_OPEN_2': 20
        }

        for val in self.GPIO_PIN_IN.values():
            GPIO.setup(val, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        for val in self.GPIO_PIN_OUT.values():
            GPIO.setup(val, GPIO.OUT)



    def read_status_pin(self, pin):
        ''' Read Raspberry Pi status Pin '''
        return bool(GPIO.input(pin))

    def switch_pop(self, boolean = 1):
        ''' Close or open Electric Pop '''
        if boolean:
            GPIO.output(self.GPIO_PIN_OUT['ATM_CLOSE_1'], 1)
            time.sleep(2)
            GPIO.output(self.GPIO_PIN_OUT['ATM_CLOSE_1'], 0)
            time.sleep(2)
            print('Switch Pop from Off =====> On')
        else:
            GPIO.output(self.GPIO_PIN_OUT['ATM_OPEN_1'], 1)
            time.sleep(2)
            GPIO.output(self.GPIO_PIN_OUT['ATM_OPEN_1'], 0)
            time.sleep(2)
            print('Switch Pop from On =====> Off')

    def recv_package(self, decrespone):
        ''' Receive data response from server over MQTT protocol and execute command '''
        print(decrespone)

        def alarm():
            '''Nhan lenh gui tin nhan canh bao'''

            self.PHONE = decrespone["phone"]
            print(self.COUNTER)
            if decrespone.get("alarm") == True:
                if self.COUNTER % 4 == 0 and self.COUNTER <= 12:
                    self.GSM_MakeSMS(self.PHONE, parse_sms(decrespone['warning']))
                    print("Canh bao nguy hiem")
                self.COUNTER += 1

        def notify(phone):
            GSM_MakeSMS(phone, "Da het su co !")

        def switch():
            '''Dong ngat mach'''

            if decrespone["switch"] != GPIO.input(self.GPIO_PIN_IN['ATM_LV_CI_OP']):
                self.switch_pop(decrespone["switch"])

            if not decrespone.get("alarm", 0):
                if self.COUNTER > 0 and self.COUNTER % 4 != 0:
                    print(phone)
                    notify(phone=phone)
                    self.COUNTER = 0

        def publish():
            ''' Push data to API server '''
            data_powermeter = self.process_data(self.data_powermeter())
            pop_status = self.process_data(self.pop_status())
            try:
                # post_data = requests.post(f'{self.URL}/data/push', data={ 'message': data_powermeter })
                # post_status = requests.post(f'{self.URL}/pops/status', data={ 'message': pop_status })
                os.system(f"curl -X POST -d message={pop_status.decode()} {self.URL}/pops/status &")
                os.system(f"curl -X POST -d message={data_powermeter.decode()} {self.URL}/data/push &")
            except Exception as err:
                print(err)

        # for f in decrespone['func']:
        #     exec(f)

        if decrespone.get('switch') != None:
            switch()
        if decrespone.get('publish') != None:
            publish()

    def pop_status(self):
        ''' Read Pi status to send to API server '''
        pins_status = dict()
        for key, val in self.GPIO_PIN_IN.items():
            pins_status[key] = self.read_status_pin(val)

        return {
        	'status': pins_status,
        	'token': self.TOKEN,
        	'last_update': str(datetime.now()),
         	'temperature': self.sensor_reading()
        }

