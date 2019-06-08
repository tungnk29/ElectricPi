#!/usr/bin/python3
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from urllib.request import urlopen
from time import sleep
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-k', '--key', help='Key to update to ThingSpeak', type=str, default="ABSIIX9HV6M4F70X")
token = parser.parse_args().key

def validator(instance):
    if not instance.isError():
        '''.isError() implemented in pymodbus 1.4.0 and above.'''
        decoder = BinaryPayloadDecoder.fromRegisters(
            instance.registers,
            byteorder=Endian.Big, wordorder=Endian.Little
        )   
        return float(decoder.decode_32bit_float())

    else:
        # Error handling.
        print("There aren't the registers, Try again.")
        return None

def main():
    try:
        modbus = ModbusClient(method='rtu', port='/dev/ttyUSB0', baudrate=9600, timeout=1, parity='E', bytesize=8)
        modbus.connect()
        voltage = validator(modbus.read_holding_registers(3910, 2, unit=1))
        current = validator(modbus.read_holding_registers(3928, 2, unit=1))
        factor = validator(modbus.read_holding_registers(3922, 2, unit=1))
        freq = validator(modbus.read_holding_registers(3914, 2, unit=1))
        print("Voltage: {} V".format(round(voltage, 2)))
        print("Current: {} A".format(current))
        print("Factor: {}".format(factor))
        print("Frequency: {} Hz".format(freq))
        modbus.close()
        return voltage, current, factor, freq
    except AttributeError as e:
        print(e)
        return None
    
def tspeakup():
    while True:
        try:
            url = "https://api.thingspeak.com/update?api_key={}&field1={}&field2={}&field3={}&field4={}".format(token, *main())
            urlopen(url)
            print("Updated !")
            print("Sleep in 30 s")
            print("-"*30)
            sleep(30)
        except:
            print("Fail to update to ThingSpeak. Try to Input Key!")
            sleep(3)    

if __name__ == "__main__":
    main()


