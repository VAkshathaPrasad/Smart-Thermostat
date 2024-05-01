#!/usr/bin/env python3
#############################################################################
# Filename    : ThermostatclientwithEncryptionDecryption.py
# Description : Thermostat client
# Author      : Akshatha Vallampati
# modification: 2024/24/04
########################################################################
import RPi.GPIO as GPIO
import time
import math
import threading
from ADCDevice import *
from PCF8574 import PCF8574_GPIO
import socket
from Adafruit_LCD1602 import Adafruit_CharLCD
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad,unpad

adc = ADCDevice() # Define an ADCDevice class object

# Define the IP address and port of the server (laptop)
SERVER_IP = '192.168.0.110'#'192.168.17.88'
SERVER_PORT = 12345

heat_led = 40
cool_led = 38

def setup():
    global adc
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(cool_led, GPIO.OUT)
    GPIO.output(cool_led, GPIO.LOW)
    GPIO.setup(heat_led, GPIO.OUT)  
    GPIO.output(heat_led, GPIO.LOW)
    if adc.detectI2C(0x48): # Detect the pcf8591.
        adc = PCF8591()
    elif adc.detectI2C(0x4b): # Detect the ads7830
        adc = ADS7830()
    else:
        print("No correct I2C address found, \n"
              "Please use command 'i2cdetect -y 1' to check the I2C address! \n"
              "Program Exit. \n")
        exit(-1)

def getTemperature():
    value = adc.analogRead(0)        # read ADC value A0 pin
    voltage = value / 255.0 * 3.3        # calculate voltage
    Rt = 10 * voltage / (3.3 - voltage)    # calculate resistance value of thermistor
    tempK = 1/(1/(273.15 + 25) + math.log(Rt/10)/3950.0) # calculate temperature (Kelvin)
    tempC = tempK -273.15        # calculate temperature (Celsius)
    print('ADC Value : %d, Voltage : %.2f, Temperature : %.2f' % (value, voltage, tempC))
    return tempC

def get_set_temperature():
    value = adc.analogRead(1)  # read ADC value A1 pin (connected to potentiometer)
    voltage = value / 255.0 * 3.3  # calculate voltage
    set_temp = (voltage / 3.3) * 100  # convert voltage to percentage (0-100)
    return set_temp

def display_temperature(tempC, set_temp):
    lcd.clear()
    lcd.setCursor(0, 0)  # set cursor position
    lcd.message('Current: {:.2f} C\n'.format(tempC))
    lcd.message('Set: {:.2f} C'.format(set_temp))

def receive_and_process(s,tempC):
    while True:
        data, addr = s.recvfrom(1024)
        # Extract the secret key and encrypted message from the received data
        secret_key1 = data[:16]
        encrypted_message = data[16:]

        # Decrypt the received message using AES ECB mode and the shared secret key
        cipher = AES.new(secret_key1, AES.MODE_ECB)
        decrypted_message = unpad(cipher.decrypt(encrypted_message), AES.block_size)
        # Print the encrypted and decrypted messages
        print(f"Received encrypted message from {addr}: {encrypted_message.hex()}")
        print(f"Decrypted message: {decrypted_message.decode()}")
        data = decrypted_message.decode().split(',')
        set_temp = float(data[0])
        display_temperature(tempC, set_temp)
        cool_status = data[1]
        heat_status = data[2]
        print(f"Received LED status: Cool: {cool_status}, Heat: {heat_status}")
        if cool_status == 'ON':
            GPIO.output(cool_led, GPIO.HIGH)
        else:
            GPIO.output(cool_led, GPIO.LOW)
        if heat_status == 'ON':
            GPIO.output(heat_led, GPIO.HIGH)
        else:
            GPIO.output(heat_led, GPIO.LOW)

def loop():
    mcp.output(3, 1)     # turn on LCD backlight
    lcd.begin(16, 2)     # set number of LCD lines and columns
    # Generate a random 16-byte (128-bit) secret key for AES encryption
    secret_key = get_random_bytes(16)
    # Create a UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        prev_tempS = get_set_temperature()
        prev_control_knob_status = None  # Initialize previous control knob status
        #receive_thread = threading.Thread(target=receive_and_process, args=(s,))
        #receive_thread.start()
        while True:
            tempC = getTemperature()
            tempS = get_set_temperature()
            receive_thread = threading.Thread(target=receive_and_process, args=(s,tempC))
            receive_thread.start()
            # Determine control knob status
            if tempS > prev_tempS:
                control_knob_status = "Increasing"
            elif tempS < prev_tempS:
                control_knob_status = "Decreasing"
            else:
                control_knob_status = "Not Turned"
            print("control_knob_status", control_knob_status)

            # Send control knob status to the server only if it has changed
            if control_knob_status != prev_control_knob_status:
                send_data = f"{control_knob_status}"  # Combine sensor data
                # Pad the message to align with block boundary
                padded_message = pad(send_data.encode(), AES.block_size)
                # Encrypt the message using AES with the secret key
                cipher = AES.new(secret_key, AES.MODE_ECB)
                # Encrypt the padded message
                encrypted_message = cipher.encrypt(padded_message)

                s.sendto(secret_key + encrypted_message, (SERVER_IP, SERVER_PORT))  # Send data to control server
                prev_control_knob_status = control_knob_status  # Update previous control knob status
            time.sleep(1)  # Send data once every second            
            #display_temperature(tempC, tempS)  # Display temperature on the LCD
            # Send temperature data every second
            send_data = f"{tempC},{tempS}"  # Combine sensor data
            # Pad the message to align with block boundary
            padded_message = pad(send_data.encode(), AES.block_size)
            # Encrypt the message using AES with the secret key
            cipher = AES.new(secret_key, AES.MODE_ECB)
            # Encrypt the padded message
            encrypted_message = cipher.encrypt(padded_message)
            s.sendto(secret_key + encrypted_message, (SERVER_IP, SERVER_PORT))  # Send data to control server
            time.sleep(1)  # Send data once every second         
            prev_tempS = tempS  # Update previous potentiometer status

def destroy():
    adc.close()
    GPIO.cleanup()

PCF8574_address = 0x27  # I2C address of the PCF8574 chip.
PCF8574A_address = 0x3F  # I2C address of the PCF8574A chip.
# Create PCF8574 GPIO adapter.
try:
    mcp = PCF8574_GPIO(PCF8574_address)
except:
    try:
        mcp = PCF8574_GPIO(PCF8574A_address)
    except:
        print('I2C Address Error !')
        exit(1)
# Create LCD, passing in MCP GPIO adapter.
lcd = Adafruit_CharLCD(pin_rs=0, pin_e=2, pins_db=[4, 5, 6, 7], GPIO=mcp)

if __name__ == '__main__':  # Program entrance
    print('Program is starting ... ')
    setup()

    try:
        loop()
    except KeyboardInterrupt: # Press ctrl-c to end the program.
        destroy()

