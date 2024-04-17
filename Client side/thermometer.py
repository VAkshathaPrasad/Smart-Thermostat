#!/usr/bin/env python3
#############################################################################
# Filename    : Thermometer.py
# Description : Thermostat client
# Author      : Akshatha Vallampati
# modification: 2024/15/04
########################################################################
import RPi.GPIO as GPIO
import time
import math
import threading
from ADCDevice import *
from PCF8574 import PCF8574_GPIO
import socket
from Adafruit_LCD1602 import Adafruit_CharLCD

adc = ADCDevice() # Define an ADCDevice class object

# Define the IP address and port of the server (laptop)
SERVER_IP = '192.168.0.110'
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


def loop():
    mcp.output(3, 1)     # turn on LCD backlight
    lcd.begin(16, 2)     # set number of LCD lines and columns
    # Create a UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        prev_tempS = get_set_temperature()
        prev_control_knob_status = None  # Initialize previous control knob status
        while True:
            tempC = getTemperature()
            tempS = get_set_temperature()
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
                s.sendto(send_data.encode(), (SERVER_IP, SERVER_PORT))  # Send data to control server
                prev_control_knob_status = control_knob_status  # Update previous control knob status
            time.sleep(0.5)  # Send data once every second

            # Send temperature data every second
            send_data = f"{tempC},{tempS}"  # Combine sensor data
            s.sendto(send_data.encode(), (SERVER_IP, SERVER_PORT))  # Send data to control server
            time.sleep(1)  # Send data once every second            
            # Receive set temperature from the server and update LED status accordingly
            data, addr = s.recvfrom(1024)
            data = data.decode().split(',')  # Split received data
            set_temp = float(data[0])  # Convert received data to float
            print('set_temp', set_temp)
            display_temperature(tempC, set_temp)  # Display set temperature on the LCD
            print('led_status', data[1], data[2])
            if data[1] == 'ON':
                GPIO.output(cool_led, GPIO.HIGH)
            elif data[1] == 'OFF':
                GPIO.output(cool_led, GPIO.LOW)
            if data[2] == 'ON':
                GPIO.output(heat_led, GPIO.HIGH)
            elif data[2] == 'OFF':
                GPIO.output(heat_led, GPIO.LOW)
                
           # display_temperature(tempC, set_temp)  # Display set temperature on the LCD

            prev_tempS = tempS  # Update previous potentiometer status
            
            #time.sleep(1)  # Send data once every second



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
