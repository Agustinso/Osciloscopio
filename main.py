import pygame
from numpy import array, arange, zeros, roll

import threading
from serial import Serial
from serial.tools import list_ports
from struct import unpack

import sys
import os

from tkinter import *
from tkinter import messagebox

pygame.init()

global lock
lock = threading.Lock()


""" serial data structure:

   For synchronization purposes, the following scheme was chosen:
   A0 data:   A09 (MSB) A08 A07 A06 A05 A04 A03 A02 A01 A00 (LSB)
   sent as byte 1:   1 1 1 A09 A08 A07 A06 A05
	   and byte 2:   0 1 1 A04 A03 A02 A01 A00

		   byte 1  A0 5 most significant bits + 224 (128+64+32), legitimate values are between 224 and 255
		   byte 2  A0 5 least significant bits + 96 (64+32)    , legitimate values are between 96 and 127
"""

			
class DataReader(threading.Thread):
		
	#Thread event, stops the thread if it is set.
	stopthread = threading.Event()
	
	def __init__(self):
		for port,name,hwid in list_ports.grep("USB-SERIAL CH340"):
			self.port = port
		try:
			thevariable
		except NameError:
			Tk().wm_withdraw()
			messagebox.showerror('Error','Dispositivo no encontrado')
			os._exit(0)
		else:
			threading.Thread.__init__(self)                     #Call constructor of parent
			self.ser = Serial(self.port,115200)            #Initialize serial port
			self.data_buff_size = 250                           #Buffer size
			self.data = zeros(self.data_buff_size)              #Data buffer
			self.start()
	
	def run(self):      #Run method, this is the code that runs while thread is alive.

		num_bytes = 5                                     #Number of bytes to read at once
		val = 0                                             #Read value
		
		while not self.stopthread.isSet() :
			rslt = self.ser.read(num_bytes)             #Read serial data
			byte_array = unpack('%dB'%num_bytes,rslt)   #Convert serial data to array of numbers

			
			first = False #Flag to indicate weather we have the first byte of the number
			for byte in byte_array:
				if 224 <= byte <= 255: #If first byte of number
					val = (byte & 0b11111) << 5
					first = True
				elif 96 <= byte <= 127: #If second byte of number
					val |= (byte & 0b11111)
					if first:
						lock.acquire()
						self.data = roll(self.data,-1)
						self.data[-1] = val
						lock.release()


					
		self.ser.close()
			
	def stop(self):
		self.stopthread.set()

class Oscilloscope():
	
	def __init__(self):
		self.screen = pygame.display.set_mode((640, 480))
		self.clock = pygame.time.Clock()
		self.data_reader = DataReader()
		self.run()
		
	def plot(self, x, y, xmin, xmax, ymin, ymax):
		w, h = self.screen.get_size()
		x = array(x)
		y = array(y)
		
		#Scale data
		xspan = abs(xmax-xmin)
		yspan = abs(ymax-ymin)
		xsc = 1.0*(w+1)/xspan
		ysc = 1.0*h/yspan
		xp = (x-xmin)*xsc
		yp = h-(y-ymin)*ysc
		
		#Draw grid
		for i in range(10):
			pygame.draw.line(self.screen, (210, 210, 210), (0,int(h*0.1*i)), (w-1,int(h*0.1*i)), 1)
			pygame.draw.line(self.screen, (210, 210, 210), (int(w*0.1*i),0), (int(w*0.1*i),h-1), 1)
			
		#Plot data
		for i in range(len(xp)-1):
			pygame.draw.line(self.screen, (0, 0, 255), (int(xp[i]), int(yp[i])), 
													 (int(xp[i+1]),int(yp[i+1])), 1)
			



	def run(self):
		
		#Things we need in the main loop
		font = pygame.font.Font(pygame.font.match_font(u'mono'), 20)
		data_buff_size = self.data_reader.data_buff_size        
		hold = False

		while 1:
			#Process events
			event = pygame.event.poll()
			if event.type == pygame.QUIT:
				pygame.display.quit()
				pygame.quit()
				self.data_reader.stop()
				sys.exit(0)
			if event.type == pygame.KEYDOWN :
				if event.key == pygame.K_h:
					hold = not hold
					
					
			self.screen.fill((255,255,255))     

			# Plot current buffer
			if not hold:
				lock.acquire()
				x = arange(data_buff_size)
				y = self.data_reader.data
				lock.release()
			self.plot(x,y, 0, data_buff_size, 0, 1024)

			# Display fps
			text = font.render("%d fps"%self.clock.get_fps(), 1, (0, 10, 10))
			self.screen.blit(text, (10, 10))

			pygame.display.flip()
			self.clock.tick(0)

osc = Oscilloscope()
