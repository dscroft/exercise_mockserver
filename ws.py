#!/usr/bin/python3

from websocket import create_connection
import sys

ws = create_connection( sys.argv[1] )

while True:
	result =  ws.recv()
	print( "Received '%s'" % result)
	
ws.close()
