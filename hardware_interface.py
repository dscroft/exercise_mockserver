#!/usr/bin/python3
from tornado import websocket, web, ioloop, gen
import tornado
import json
import time, random
import csv, struct
import datetime

class StreamHandler( websocket.WebSocketHandler ):
	""" Keep track of connected/disconnected websockets """
	cl = {}

	def open( self, *args ):
		print( "open connection" )
		uri = self.request.uri
		if uri not in __class__.cl:
			__class__.cl[uri] = set()

		__class__.cl[uri].add(self)

	def on_close( self ):
		if self in __class__.cl:
			__class__.cl.remove(self)

	@staticmethod
	def __send( message, path ):
		if path not in __class__.cl: return 0

		for client in __class__.cl[path]:
			try:
				client.write_message( message )
			except:
				pass

		return len(__class__.cl[path])

	@staticmethod
	def send_message( data, path ):
		""" Send message as JSON """
		j = json.dumps( data )
		return __class__.__send( j, path )

	@staticmethod
	def send_binary( data, path ):
		ordered = sorted(data.items(), key=lambda i: i[0])
		fmt = "".join([ {int: "i", float: "f"}[type(i[1])] for i in ordered ])
		b = struct.pack( fmt, *[ i[1] for i in ordered ] )

		return __class__.__send( b, path )

class RepHandler( web.RequestHandler ):
	reps = 0
	repstate = "low"

	def get(self):
		self.write( {"value":__class__.reps} )

	def put(self):
		try: 
			value = int( json.loads(self.request.body)["value"] )
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

class ProgrammeHandler( web.RequestHandler ):
	__options = ("aaa", "bbb", "ccc")
	__value = "aaa"

	def get(self):
		self.write( { "options": __class__.__options, \
					  "value": __class__.__value } )

	def put(self):
		try:
			value = json.loads(self.request.body)["value"]
			if value not in __class__.__options:
				raise
			__class__.__value = value
		except:
			self.set_status(400)

		self.get()

class BasicLoadHandler( web.RequestHandler ):
	__value = 0

	def get(self):
		self.write( {"value": __class__.__value} )

class VariableLoadHandler( web.RequestHandler ):
	__value = 0

	def get(self):
		self.write( {"value": __class__.__value} )

	def put(self):
		try:
			value = json.loads(self.request.body)["value"]
			if value not in __class__.__options:
				raise
			__class__.__value = value
		except:
			self.set_status(400)

		self.get()

class GainHandler( web.RequestHandler ):
	__value = 0

	def get(self):
		self.write( {"value": __class__.__value} )

	def put(self):
		try:
			value = json.loads(self.request.body)["value"]
			if value not in __class__.__options:
				raise
			__class__.__value = value
		except:
			self.set_status(400)

		self.get()		

@gen.coroutine
def main( data ):
	""" Websocket publish loop 
		Would be reading from CAN and serial normally """
	row = 0
	repstate = "low"
	prev = datetime.datetime.now()
	while True:
		now = datetime.datetime.now()
		if (now-prev).total_seconds() < 0.0005:	# send frame every 5ms
			yield
			continue

		values = data[row]
		can = filter_values( values, "can" )
		serial = filter_values( values, "serial" )

		RepHandler.poll( serial["position"] )

		StreamHandler.send_message( can, "/can/json" )
		StreamHandler.send_message( serial, "/serial/json" )
		StreamHandler.send_binary( can, "/can/bin" )
		StreamHandler.send_binary( serial, "/serial/bin" )

		prev = now
		row = (row+1)%len(data)

def filter_values( values, condition ):
	return { key[1]: val for key, val in values.items() if key[0] in (None,condition) }

def load_example_data( filename ):
	""" Load in the example data from the .csv file
		File should be one frame per row, first row is column headers. """
	def auto_convert( val ):
		try: return int(val)
		except ValueError: pass
		return float(val)

	data = []

	with open( filename, "r" ) as f:
		for row in csv.DictReader( f ):
			row = { tuple(([None]+key.split("|"))[-2:]): auto_convert(val) 
					for key, val in row.items() }
			data.append(row)

	return data

if __name__ == '__main__':
	print( "Loading" )
	data = load_example_data( "data.csv" )

	print( "Running" )
	app = web.Application( ( (r"/(can|serial)/(json|bin)", StreamHandler), \
							 (r"/reps", RepHandler), \
							 (r"/programme", ProgrammeHandler), \
							 (r"/load/basic", BasicLoadHandler), \
							 (r"/load/variable", VariableLoadHandler), \
							 (r"/gain", GainHandler) ), debug=True )
	app.listen(5001)

	loop = ioloop.IOLoop.instance()
	loop.spawn_callback( main, data )
	loop.start()

