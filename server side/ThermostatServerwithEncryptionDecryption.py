#!/usr/bin/env python3
#############################################################################
# Filename    : ThermostatserverwithEncryptionDecryption.py
# Description : Control Server
# Author      : Akshatha Vallampati
# modification: 2024/24/04
########################################################################


import socket
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad,pad
from Crypto.Random import get_random_bytes

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
            # Extract the secret key and encrypted message from the received data
            secret_key = data[:16]
            encrypted_message = data[16:]
            # Decrypt the received message using AES ECB mode and the shared secret key
            cipher = AES.new(secret_key, AES.MODE_ECB)
            decrypted_message = unpad(cipher.decrypt(encrypted_message), AES.block_size)
            # Print the encrypted and decrypted messages
            print(f"Received encrypted message from {addr}: {encrypted_message.hex()}")
            print(f"Decrypted message: {decrypted_message.decode()}")
            data = decrypted_message.decode().split(',')  # Split received data        
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
            print(f"Control knob status: {control_knob_status}")
            send_control_commands(set_temp,heat_led,cool_led, addr)
            

def send_control_commands(set_temp,heat_led,cool_led, addr):
    secret_key1 = get_random_bytes(16)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        # Creating a message containing the set temperature, heat LED status, and cool LED status
        message = f"{set_temp},{cool_led},{heat_led}"
        # Pad the message to align with block boundary
        padded_message = pad(message.encode(), AES.block_size)

        # Encrypt the message using AES with the secret key
        cipher = AES.new(secret_key1, AES.MODE_ECB)
        # Encrypt the padded message
        encrypted_message = cipher.encrypt(padded_message)

        # Send the message to the client
        s.sendto(secret_key1 + encrypted_message, addr)
        print("Sent control commands to the client:")
        print(message)

if __name__ == "__main__":
    main()
