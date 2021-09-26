import re, serial, time, sqlite3, pickle
import RPi.GPIO as GPIO
from datetime import datetime

#Setup gpio pin thuc hien mot so chuc nang dac biet
C_PWpin = 27		# chan C_PW dieu khien nguon cap cho RPI Sim808 Shield
PWKpin  = 17 		# chan PWK : bat/tat RPI Sim808 Shield

# setup serial 
ser = serial.Serial(
	port = '/dev/ttyS0',
	baudrate = 9600,
	parity = serial.PARITY_NONE,
	stopbits = serial.STOPBITS_ONE,
	bytesize = serial.EIGHTBITS,
	timeout = 1
)

# setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(C_PWpin, GPIO.OUT)
GPIO.setup(PWKpin, GPIO.OUT)

def GSM_Power(): 
	#
	GPIO.output(PWKpin, 1)
	time.sleep(2)
	GPIO.output(PWKpin, 0)
	time.sleep(2)
	print ("Switched\n")
	return

def GSM_Init():
        print ("Khoi tao cho module SIM808... \n")
        ser.write(b'ATE0\r\n') 				# Tat che do phan hoi (Echo mode)
        time.sleep(1)
        ser.write(b'AT+IPR=9600\r\n') 		# Dat toc do truyen nhan du lieu 9600bps
        time.sleep(1)
        ser.write(b'AT+CMGF=1\r\n')			# Chon che do text mode
        time.sleep(1)
        ser.write(b'AT+CNMI=2,2\r\n') 		# Hien thi truc tiep noi dung tin nhan
        time.sleep(1)
        ser.write(b'AT+CGNSPWR=1\r\n') 		# Bat GPS
        time.sleep(1)
##        ser.write(b'AT+CGNSSEQ="GGA"')
##        time.sleep(1)
        return

def GSM_Check():
        print ("Check phan hoi tu GSM")
        ser.write(b"AT\r\n")
        time.sleep(0.5)
        res = ser.read(100)
        print (str(res, encoding="latin1"))
        if re.search("ERROR", str(res, encoding="latin1")) or res == b'': #
                print ("GSM da bi tat, dang bat lai...")
                GSM_Power()
                GSM_Check()
        else:
                print ("GSM hien tai dang bat")
                GSM_Init()
                res = ser.readall()
                print(str(res, encoding="latin1"))

def GSM_MakeSMS():
	print ("Nhan tin...\n")
	ser.write(b'AT+CMGS=\"0947278250\"\r\n') 	# nhan tin toi sdt
	time.sleep(3)
	ser.write(b'Xin chao ban!!!')
	ser.write(b'\x1A')		# Gui Ctrl Z hay 26, 0x1A de ket thuc noi dung tin nhan va gui di
	time.sleep(3)
	return
                
def GPS_GetInfo():
        print ("Lay thong tin GPS")
        ser.write(b"AT+CGNSINF\r\n")
        time.sleep(1)
        info = ser.readall()
        CGNSINF = str(info, encoding="latin1").split(",")[3:5]
        print (CGNSINF)
        return CGNSINF

def main():
    GSM_Check()
    try:
        while True:
            cmd = input("==> ")
            if cmd == 'q':
                break
            ser.write(bytes(cmd+"\r\n", encoding="latin1"))
            time.sleep(2)
            res = ser.readall()
            if re.search(">", str(res, encoding="latin1")):
                text = input("> ")
                if text != "q":
                        ser.write(bytes(text, encoding="latin1"))
                        ser.write(b"\x1A")
                        time.sleep(0.1)
                else:
                        ser.write(b"AT+CIPCLOSE\r\n")
                res = ser.readall()
            print(str(res, encoding="utf-8"))
            
    except KeyboardInterrupt:
            ser.write(b"AT+CIPCLOSE\r\n")
            ser.close()  
    finally:
            print ("End!\n")
            GSM_Power()
            ser.close()
            GPIO.cleanup()
        

if __name__ == "__main__":
    main()
    
###############
###############
