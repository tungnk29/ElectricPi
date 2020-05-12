from module.funcs import srv_info_reload, uicosfi_package, cipher, recv_package, CONFIG
import time, pickle, socket, json

# chan swPin dong relay
# swPin = 12  

# chan swPinOff ngat relay
# swPinOff = 16 

# chan tiep diem doc trang thai
# statusPin = 18

# Socket Init
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(3)

# Server infomation
srv_info = (CONFIG["server"], CONFIG["port"])

def main():
    # GSM_Check()
    global srv_info, CONFIG
    while True:
        try:
            srv_info_reload()
            
            s.sendto(uicosfi_package(CONFIG['token']), srv_info)

            res = s.recvfrom(4096)

            data = json.loads(cipher.decrypt(res[0]))
            recv_package(data)
            # print(res)
        except socket.timeout:
            print('Time out to receive data from server ! Try again !')
        except KeyboardInterrupt:
            print('Cancel by keyboard')
            break
        except socket.gaierror:
            print('Wrong server info !')                
        except Exception:
            print('error to decode data from server !')

        time.sleep(0.5)

if __name__ == '__main__':
    # time.sleep(15)
    main()

    pass
