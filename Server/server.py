#This BS is needed to fix an issue that hasnt been patched in gpiozero for Pi5.
#Ugh.
import gpiozero.pins.lgpio
import lgpio

def __patched_init(self, chip=None):
    gpiozero.pins.lgpio.LGPIOFactory.__bases__[0].__init__(self)
    chip = 0
    self._handle = lgpio.gpiochip_open(chip)
    self._chip = chip
    self.pin_class = gpiozero.pins.lgpio.LGPIOPin

gpiozero.pins.lgpio.LGPIOFactory.__init__ = __patched_init
# End of BS.
import gpiozero as gpio
from time import sleep
import socket
import threading

def main():
    previousstate = 0 # 0 1 2 3 4 none forward backward left right
    forwardvar = 0
    backwardvar = 0
    leftvar = 0
    rightvar = 0
    exit_program = 0

    #Definte motor pins using BCM format
    leftMotor = gpio.Motor(19,26) #GPIO 19 & 26 or Board Pins 35 & 37
    rightMotor = gpio.Motor(16, 20) #GPIO 16 & 20 or Board Pins 36 & 38
    robot = gpio.Robot(leftMotor, rightMotor)


    def clear():
        robot.stop()

    def cleanup():
        global previousstate
        clear()
        previousstate = 0

    def forward():
        clear()
        robot.forward()

    def backward():
        clear()
        robot.backward()

    def left():
        clear()
        robot.left()

    def right():
        clear()
        robot.right()

    class robotThread (threading.Thread):
        def __init__(self, threadID, name, counter):
            threading.Thread.__init__(self)
            self.threadID = threadID
            self.name = name
            self.counter = counter

        def run(self):
            global previousstate
            global forwardvar
            global backwardvar
            global leftvar
            global rightvar
            global exit_program

            while True:
                if exit_program == 1:
                    cleanup()
                    print("stopping robot thread")
                    break
                elif 0 == forwardvar and 0 == backwardvar and 0 == leftvar and 0 == rightvar and previousstate != 0:
                    previousstate = 0
                    clear()
                    print("clear")
                elif forwardvar == 1 and backwardvar == 1 and leftvar == 1 and rightvar == 1 and previousstate != 0:
                    previousstate = 0
                    clear()
                elif forwardvar == 0 and backwardvar == 0 and leftvar == 1 and rightvar == 1 and previousstate != 0:
                    previousstate = 0
                    clear()
                elif forwardvar == 1 and backwardvar == 1 and leftvar == 0 and rightvar == 0 and previousstate != 0:
                    previousstate = 0
                    clear()
                elif forwardvar == 1 and backwardvar == 0 and leftvar == 0 and rightvar == 0 and previousstate != 1:
                    forward()
                    previousstate = 1
                    print("forward")
                elif forwardvar == 1 and backwardvar == 0 and leftvar == 1 and rightvar == 0 and previousstate == 3:
                    forward()
                    previousstate = 1
                elif forwardvar == 1 and backwardvar == 0 and leftvar == 0 and rightvar == 1 and previousstate == 4:
                    forward()
                    previousstate = 1
                elif forwardvar == 1 and backwardvar == 0 and leftvar == 1 and rightvar == 1 and previousstate != 1:
                    forward()
                    previousstate = 1
                elif forwardvar == 0 and backwardvar == 1 and leftvar == 0 and rightvar == 0 and previousstate != 2:
                    backward()
                    previousstate = 2
                elif forwardvar == 0 and backwardvar == 1 and leftvar == 1 and rightvar == 0 and previousstate == 3:
                    backward()
                    previousstate = 2
                elif forwardvar == 0 and backwardvar == 1 and leftvar == 0 and rightvar == 1 and previousstate == 4:
                    backward()
                    previousstate = 2
                elif forwardvar == 0 and backwardvar == 1 and leftvar == 1 and rightvar == 1 and previousstate != 2:
                    backward()
                    previousstate = 2
                elif forwardvar == 0 and backwardvar == 0 and leftvar == 1 and rightvar == 0 and previousstate != 3:
                    left()
                    previousstate = 3
                elif forwardvar == 1 and backwardvar == 1 and leftvar == 1 and rightvar == 0 and previousstate != 3:
                    left()
                    previousstate = 3
                elif forwardvar == 0 and backwardvar == 0 and leftvar == 0 and rightvar == 1 and previousstate != 4:
                    right()
                    previousstate = 4
                elif forwardvar == 1 and backwardvar == 1 and leftvar == 0 and rightvar == 1 and previousstate != 4:
                    right()
                    previousstate = 4

    class socketThread (threading.Thread):
        def __init__(self, threadID, name, counter):
            threading.Thread.__init__(self)
            self.threadID = threadID
            self.name = name
            self.counter = counter

        def run(self):
            global forwardvar
            global backwardvar
            global leftvar
            global rightvar
            global exit_program
            #message = 'Send message to client.'
            #message = message.encode()

            #socket.setdefaulttimeout(10)
            server = socket.socket()

            server.bind(("192.168.50.177", 6678))

            while True:
                try:
                    server.listen(4)
                    client_socket, client_address = server.accept()
                    #except socket.timeout:
                        #server.close()
                        #print("Server timeout. Exiting..")
                        #os._exit(1)

                    print(client_address, "has connected")

                    while True:
                        received_data = client_socket.recv(1024)
                        #client_socket.send(message)
                        decoded_data = received_data.decode()
                        
                        if decoded_data == 'exit':
                            exit_program = 1
                            client_socket.close()
                            print(decoded_data)
                            break
                        elif decoded_data == '\'w\' press':
                            forwardvar = 1
                            print(decoded_data)
                        elif decoded_data == '\'w\' release':
                            forwardvar = 0
                            print(decoded_data)
                        elif decoded_data == '\'a\' press':
                            leftvar = 1
                            print(decoded_data)
                        elif decoded_data == '\'a\' release':
                            leftvar = 0
                            print(decoded_data)
                        elif decoded_data == '\'s\' press':
                            backwardvar = 1
                            print(decoded_data)
                        elif decoded_data == '\'s\' release':
                            backwardvar = 0
                            print(decoded_data)
                        elif decoded_data == '\'d\' press':
                            rightvar = 1
                            print(decoded_data)
                        elif decoded_data == '\'d\' release':
                            rightvar = 0
                            print(decoded_data)
                except:
                    if exit_program == 1:
                        print(client_address, "has disconnected")
                        break
                    else:
                        pass

    threads = []
    RobotThread = robotThread(1, "RobotThread", 1)
    SocketThread = socketThread(2, "SocketThread", 2)

    RobotThread.start()
    SocketThread.start()

    threads.append(RobotThread)
    threads.append(SocketThread)
    for t in threads:
        t.join()
        print("Program exited cleanly.")

main()