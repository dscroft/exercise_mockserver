#!/usr/bin/python3
from tornado import websocket, web, ioloop, gen
import tornado
import json
import time, random
import csv, struct
import datetime
import serial

from ws_handler import StreamHandler
from basic_handler import BasicValueHandler

class BaseHandler( web.RequestHandler ):
	def set_default_headers(self):
		self.set_header("Access-Control-Allow-Origin", "*")
		self.set_header("Access-Control-Allow-Headers", "*")
		self.set_header('Access-Control-Allow-Methods', "PUT, GET, OPTIONS")

	def options(self):
		self.set_status(204)
		self.finish()

class RepHandler( BaseHandler ):
	reps = 0
	repstate = "low"

	def get(self):
		self.write( {"value":__class__.reps} )

	def put(self):
		try: 
			value = int( json.loads(self.request.body.decode('utf-8'))["value"] )
			__class__.reps = value
		except:
			self.set_status(400)
		
		self.get()		

	@staticmethod
	def poll( position ):
		# count the reps
		if __class__.repstate == "low" and position > 15000:
			__class__.repstate = "high"
			__class__.reps += 1
		elif __class__.repstate == "high" and position < 10000:
			__class__.repstate = "low"

class ProgrammeHandler( BaseHandler ):
	__options = ("aaa", "bbb", "ccc")
	__value = "aaa"

	def get(self):
		self.write( { "options": __class__.__options, \
					  "value": __class__.__value } )

	def put(self):
		try:
			value = json.loads(self.request.body.decode('utf-8'))["value"]
			if value not in __class__.__options:
				raise
			__class__.__value = value
		except:
			self.set_status(400)

		self.get()

class BasicLoadHandler( BaseHandler ):
	__value = 0

	def get(self):
		self.write( {"value": __class__.__value} )

class VariableLoadHandler( BaseHandler ):
	__value = 0

	def get(self):
		self.write( {"value": __class__.__value} )

	def put(self):
		try:
			value = json.loads(self.request.body.decode('utf-8'))["value"]
			if value not in __class__.__options:
				raise
			__class__.__value = value
		except:
			self.set_status(400)

		self.get()

class SerialHandler:
	def __init__(self, port, baudrate=9800):
		self.__serial = serial.Serial( port=port, baudrate=baudrate )
		self.__buffer = ''

	def poll(self):
		availBytes = self.__serial.inWaiting()

		if availBytes > 0:
			self.__buffer += self.__serial.read( availBytes ).decode()

			messages = self.__buffer.split('\n')

			if self.__buffer == '' or self.__buffer[-1] == '\n':
				self.__buffer = ''
			else:
				self.__buffer = messages[-1]
				messages = messages[:-1]

			return [ i[1:] for i in messages if i!='' and i[0] == '>' ]

		return []


@gen.coroutine
def main():
	""" Websocket publish loop 
		Would be reading from CAN and serial normally """
	sh = SerialHandler( "/dev/ttyACM0" )

	def auto_convert( val ):
		try: return int(val)
		except ValueError: pass
		return float(val)

	while True:
		serialheaders = ('position','force','acceleration','velocity',\
						'repetitions','travel','coil force',\
						'calibration force','power','energy',\
						'kCal','active')
		canheaders = ('voltage','current','temperature','errors',\
					  'force','relay status','12v status')

		for message in sh.poll():
			fields = message.split(',')
			if len(fields) != len(serialheaders)+len(canheaders):
				continue

			serialmessage = { k: auto_convert(v) 
							  for k, v in zip(serialheaders, fields[:len(serialheaders)]) }
			canmessage = { k: auto_convert(v) 
						   for k, v in zip(canheaders, fields[-len(canheaders):]) }

			RepHandler.reps = serialmessage["repetitions"]

			StreamHandler.send_message( serialmessage, "/serial/json" )
			StreamHandler.send_message( canmessage, "/can/json" )

		yield			

if __name__ == '__main__':
	print( "Loading" )


	print( "Running" )
	app = web.Application( ( (r"/(can|serial)/json", StreamHandler), \
							 (r"/reps", RepHandler), \
							 (r"/programme", ProgrammeHandler), \
							 (r"/load/basic", BasicLoadHandler), \
							 (r"/load/variable", VariableLoadHandler), \
							 (r"/gain", BasicValueHandler) ), debug=True )
	app.listen(5001)

	loop = ioloop.IOLoop.instance()
	loop.spawn_callback( main )
	loop.start()

