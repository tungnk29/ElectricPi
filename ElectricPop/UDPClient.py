from module.pmread import register_reading, sensor_reading
from threading import Thread
from cryptography.fernet import Fernet
import sqlite3 as sql
import os, re, time, serial, pickle, socket
import RPi.GPIO as GPIO

# Cai dat cong ket noi Serial
ser = serial.Serial(port='/dev/ttyS0',
                    baudrate=9600,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS,
                    timeout=1)

# path to config file
cwd = os.path.dirname(os.path.realpath(__file__))
dbpath = cwd + "/config.db"

# Encrypt/Decrypt package
key = b'ztpn8wdO3ZNiNW3V9GZJlKWy8RioHnPC5-W5TQ0ZSEM='
cipher = Fernet(key)

# Pin GPIO and setup
C_PWpin = 27  # chan C_PW dieu khien nguon cap cho RPI Sim808 Shield
PWKpin = 17  # chan PWK : bat/tat RPI Sim808 Shield
swPin = 12  # chan swPin dong relay
swPinOff = 16 # chan swPinOff ngat relay
statusPin = 18 # chan tiep diem doc trang thai

# Counter variable
counter = 0
connect_counter = 0
phone = ''

# Server infomation
config = getrec("config", True)
srv_info = (config["server"], config["port"])

# Setup GPIO mode
GPIO.setmode(GPIO.BCM)
GPIO.setup(C_PWpin, GPIO.OUT)
GPIO.setup(PWKpin, GPIO.OUT)
GPIO.setup(swPin, GPIO.OUT)
GPIO.setup(swPinOff, GPIO.OUT)
GPIO.setup(statusPin, GPIO.IN)

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

# Ham bat/tat modem
def GSM_Power():
    GPIO.output(PWKpin, 1)
    time.sleep(2)
    GPIO.output(PWKpin, 0)
    time.sleep(2)
    print("Switched\n")
    return

# Ham khoi tao cho modem
def GSM_Init():
    print("Khoi tao cho module SIM808... \n")
    ser.write(b'ATE0\r\n')  # Tat che do phan hoi (Echo mode)
    time.sleep(1)
    ser.write(b'AT+IPR=9600\r\n')  # Dat toc do truyen nhan du lieu 9600bps
    time.sleep(1)
    ser.write(b'AT+CMGF=1\r\n')  # Chon che do text mode
    time.sleep(1)
    ser.write(b'AT+CNMI=2,2\r\n')  # Hien thi truc tiep noi dung tin nhan
    time.sleep(1)
    ser.write(b'AT+CGNSPWR=1\r\n')  # Bat GPS
    time.sleep(1)
    return

# KIem tra xem modem dang bat hay tat cho den khi da bat.
def GSM_Check():
    print("Check phan hoi tu GSM")
    ser.write(b"AT\r\n")
    time.sleep(1)
    res = ser.read(100)
    print(str(res, encoding="latin1"))
    if re.search("ERROR", str(res, encoding="latin1")) or res == b'':  #
        print("GSM da bi tat, dang bat lai...")
        GSM_Power()
        GSM_Check()
    else:
        print("GSM hien tai dang bat")
        GSM_Init()
        res = ser.readall()
        print(str(res, encoding="latin1"))


# Gui tin nhan
def GSM_MakeSMS(phone, text):
    print("Nhan tin...\n")
    cmd = "AT+CMGS=\"{}\"\r\n".format(phone)
    ser.write(bytes(cmd, encoding='latin1'))
    time.sleep(0.5)
    ser.write(bytes(text, encoding='latin1'))
    ser.write(b'\x1A')  # Gui Ctrl Z hay 26, 0x1A de ket thuc noi dung tin nhan va gui di
    return


# Xu li cac phan hoi tu server
def recv_package(decrespone):
    print(decrespone)

    def alarm():
        '''Nhan lenh gui tin nhan canh bao'''
        global counter, phone
        phone = decrespone["phone"]
        print(counter)
        if decrespone.get("alarm") == True:
            if counter % 4 == 0:
                GSM_MakeSMS(phone, "Canh bao! Co su co !!!")
                print("Canh bao nguy hiem")
            counter += 1

    def notify(phone):
        GSM_MakeSMS(phone, "Da het su co ! ^ _ ^")

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

    packg = b'808' + cipher.encrypt(pickle.dumps(pack2send))
    return packg

def main():
    GSM_Check()
    try:
        while True:
            x_start = time.time()
            s.sendto(uicosfi_package(config['token']), srv_info)
            try:
                res = s.recvfrom(4096)
                data = pickle.loads(cipher.decrypt(res[0][3:]))
                recv_package(data)
                # print(res)
            except socket.timeout:
                srv_info_reload()
                print('Time out to receive data from server ! Try again !')
            except KeyboardInterrupt:
                print('Cancel by keyboard')
                break                
            except Exception:
                print('error to decode data from server !')

            time.sleep(0.5)
    except KeyboardInterrupt:
        print('Cancel by keyboard')
            
if __name__ == '__main__':
    main()
  


