# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for full license information.

import random
import time
import threading
import RPi.GPIO as GPIO
import bme280
import smbus2
from datetime import datetime

# Using the Python Device SDK for IoT Hub:
#   https://github.com/Azure/azure-iot-sdk-python
# The sample connects to a device-specific MQTT endpoint on your IoT Hub.
from azure.iot.device import IoTHubDeviceClient, Message, MethodResponse

# The device connection string to authenticate the device with your IoT hub.
# Using the Azure CLI:
# az iot hub device-identity show-connection-string --hub-name {YourIoTHubName} --device-id MyNodeDevice --output table
CONNECTION_STRING = "HostName=IoTEmbebidos.azure-devices.net;DeviceId=MyPythonDevice;SharedAccessKey=NlQKN2MHFNKeCkYXxq8G+qgx29sZVNiAtHNOT2R3qLk="

# Define the JSON message to send to IoT Hub.
MSG_TXT = '{{"parking:" {id} ,"tiempo:" {tiempo} ,"estado:" {estado},"temperatura:" {temperatura}}}'

port = 1
address = 0x76 # Adafruit BME280 address. Other BME280s may be different
bus = smbus2.SMBus(port)
bme280.load_calibration_params(bus,address)
id="Parqueadero1"
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(11, GPIO.IN)         #Read output from PIR motion sensor
GPIO.setup(13, GPIO.OUT)         #LED output pin
Accion = 0

def iothub_client_init():
    # Create an IoT Hub client
    client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
    return client


def device_method_listener(device_client):
    global INTERVAL
    while True:
        method_request = device_client.receive_method_request()
        print (
            "\nMethod callback called with:\nmethodName = {method_name}\npayload = {payload}".format(
                method_name=method_request.name,
                payload=method_request.payload
            )
        )
        if method_request.name == "LED":
            try:
                Accion = int(method_request.payload)
            except ValueError:
                response_payload = {"Response": "Invalid parameter"}
                response_status = 400
            else:
                if Accion == 1:
			response_payload = {"Response": "Encendiendo led "}
                	response_status = 201
			GPIO.output(13, 1)
		elif Accion == 0:
			response_payload = {"Response": "Apagando led "}
                	response_status = 200
			GPIO.output(13, 0)
		else:
			response_payload = {"Response": "No se encontro comando"}
                	response_status = 209

        else:
            response_payload = {"Response": "Direct method {} not defined".format(method_request.name)}
            response_status = 404

        method_response = MethodResponse(method_request.request_id, response_status, payload=response_payload)
        device_client.send_method_response(method_response)



def iothub_client_telemetry_sample_run():

	try:
		client = iothub_client_init()
		print ( "IoT Hub device sending periodic messages, press Ctrl-C to exit" )

		# Start a thread to listen 
		device_method_thread = threading.Thread(target=device_method_listener, args=(client,))
		device_method_thread.daemon = True
		device_method_thread.start()

		while True:
			i=GPIO.input(11)
			if i==0:                 #When output from motion sensor is LOW
				estado="evaluando"
				print (estado)
				#GPIO.output(13, 0)  #Turn OFF LED
				time.sleep(1)

			elif i==1:               #When output from motion sensor is HIGH
				estado="ocupado"
				print (estado)
				#GPIO.output(13, 1)  #Turn ON LED
				now = datetime.now()
				hora_ingreso = now.strftime("%Y%m%d:%H:%M:%S")
				tiempo=hora_ingreso
				print("Hora de deteccion", hora_ingreso)
				bme280_data = bme280.sample(bus,address)
				pressure  = bme280_data.pressure
				temperatura = bme280_data.temperature
				print(pressure, temperatura)
				msg_txt_formatted = MSG_TXT.format(id=id,tiempo=tiempo,estado=estado,temperatura=temperatura)
				message = Message(msg_txt_formatted)
				print( "Sending message: {}".format(message) )
				client.send_message(message)
				print ( "Message successfully sent" )

				time.sleep(10)

				estado="disponible"
				now = datetime.now()
				hora_salida = now.strftime("%Y%m%d:%H:%M:%S")
				tiempo=hora_salida
				temperatura = bme280_data.temperature
				print("Hora de salida", hora_salida)
				print("temperatura salida",temperatura)
				msg_txt_formatted = MSG_TXT.format(id=id,tiempo=tiempo,estado=estado,temperatura=temperatura)
				message = Message(msg_txt_formatted)
				print( "Sending message: {}".format(message) )
				client.send_message(message)
				print ( "Message successfully sent" )

	except KeyboardInterrupt:
		print ( "IoTHubClient sample stopped" )

if __name__ == '__main__':
	print ( "IoT Hub Quickstart #2 - Simulated device" )
	print ( "Press Ctrl-C to exit" )
	iothub_client_telemetry_sample_run()
