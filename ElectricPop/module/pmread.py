# -*- coding: utf-8 -*-
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

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

def register_reading(ids, count, *args):
    rgs = list(args)
    print("Start reading Power Meter...")
    try:
        modbus = ModbusClient(method='rtu', port='/dev/ttyUSB0', baudrate=9600, timeout=1, parity='E', bytesize=8)
        modbus.connect()

        a = validator(modbus.read_holding_registers(rgs[0] - 1, count, unit=ids))
        a1 = validator(modbus.read_holding_registers(rgs[1] - 1, count, unit=ids))
        a2 = validator(modbus.read_holding_registers(rgs[2] - 1, count, unit=ids))
        a3 = validator(modbus.read_holding_registers(rgs[3] - 1, count, unit=ids))

        vll = validator(modbus.read_holding_registers(rgs[4] - 1, count, unit=ids))
        vln = validator(modbus.read_holding_registers(rgs[5] - 1, count, unit=ids))
        v1 = validator(modbus.read_holding_registers(rgs[6] - 1, count, unit=ids))
        v2 = validator(modbus.read_holding_registers(rgs[7] - 1, count, unit=ids))
        v3 = validator(modbus.read_holding_registers(rgs[8] - 1, count, unit=ids))
        v12 = validator(modbus.read_holding_registers(rgs[9] - 1, count, unit=ids))
        v23 = validator(modbus.read_holding_registers(rgs[10] - 1, count, unit=ids))
        v31 = validator(modbus.read_holding_registers(rgs[11] - 1, count, unit=ids))

        pf = validator(modbus.read_holding_registers(rgs[12] - 1, count, unit=ids))
        pf1 = validator(modbus.read_holding_registers(rgs[13] - 1, count, unit=ids))
        pf2 = validator(modbus.read_holding_registers(rgs[14] - 1, count, unit=ids))
        pf3 = validator(modbus.read_holding_registers(rgs[15] - 1, count, unit=ids))

        print("A: {}".format(a))
        print("A1: {}".format(a1))
        print("A2: {}".format(a2))
        print("A3: {}".format(a3))
        
        print("VLL: {}".format(vll))
        print("VLN: {}".format(vln))
        print("V1: {}".format(v1))
        print("V2: {}".format(v2))
        print("V3: {}".format(v3))
        print("V12: {}".format(v12))
        print("V23: {}".format(v23))
        print("V31: {}".format(v31))

        print("PF: {}".format(pf))
        print("PF1: {}".format(pf1))
        print("PF2: {}".format(pf2))
        print("PF3: {}".format(pf3))

        modbus.close()

        return {"ids": ids, "a":a, "a1":a1, "a2":a2, "a3":a3, "vll":vll, "vln":vln, "v1":v1, "v2":v2, "v3":v3, "v12":v12, "v23":v23, "v31":v31, "pf": pf, "pf1":pf1, "pf2":pf2, "pf3":pf3}
    except:
        print("Error!")
        return {"ids": 0, "a":0, "a1":0, "a2":0, "a3":0, "vll":0, "vln":0, "v1":0, "v2":0, "v3":0, "v12":0, "v23":0, "v31":0, "pf": 0, "pf1":0, "pf2":0, "pf3":0}
