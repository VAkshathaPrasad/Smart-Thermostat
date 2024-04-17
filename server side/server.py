#!/usr/bin/env python3
#############################################################################
# Filename    : server.py
# Description : Control Server
# Author      : Akshatha Vallampati
# modification: 2024/15/04
########################################################################


import socket

# Define the IP address and port to listen for data
SERVER_IP = '0.0.0.0'  # Listen on all available network interfaces
SERVER_PORT = 12345
heat_led = "ON"
cool_led = "OFF"

def main():
    # Create a UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        # Bind the socket to the server IP address and port
        s.bind((SERVER_IP, SERVER_PORT))
        print("Control server is listening...")
        
        # Initialize variables to store sensor information
        current_temp = 0
        set_temp = 10  # Initial temperature set point
        control_knob_status = False  # False for decrease, True for increase
        
        while True:
            # Receive sensor information from the thermostat
            data, addr = s.recvfrom(1024)
            data = data.decode().split(',')  # Split received data
            
            # Update sensor information based on received data
            # Check the content of the received message
            if len(data) == 1:  # Control knob status message
                control_knob_status = data[0]
                print(f"Received control knob status from {addr}: {control_knob_status}")
            elif len(data) == 2:  # Current temperature and set temperature message
                current_temp = float(data[0])
            
            # Adjust temperature set point based on control knob status
            if control_knob_status == "Increasing":
                set_temp += 1  # Increase set point
            elif control_knob_status == "Decreasing":
                set_temp -= 1  # Decrease set point
            else:
                set_temp = set_temp
            if current_temp > set_temp+2:
                cool_led = 'ON'
                heat_led = 'OFF'
            elif current_temp < set_temp-2:
                cool_led = 'OFF'
                heat_led = 'ON'
            elif abs(current_temp - set_temp) <= 2:
                cool_led = 'OFF'
                heat_led = 'OFF'
                
            # Process sensor information and send control commands to the thermostat
            print(f"Received sensor information from {addr}:")
            print(f"Current temperature: {current_temp} C")
            print(f"New temperature set point: {set_temp} C")
            print(f"Control knob status: {'Increase' if control_knob_status else 'Decrease'}")
            send_control_commands(set_temp,heat_led,cool_led, addr)
            

def send_control_commands(set_temp,heat_led,cool_led, addr):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        # Creating a message containing the set temperature, heat LED status, and cool LED status
        message = f"{set_temp},{cool_led},{heat_led}"
        # Send the message to the client
        s.sendto(message.encode(), addr)
        print("Sent control commands to the client:")
        print(message)

if __name__ == "__main__":
    main()
