#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pygame
from numpy import array, arange, zeros, roll
import threading
import sys
from serial import Serial
from serial.serialutil import SerialException
from serial.tools import list_ports
from struct import unpack


def remap_value(value, from1, to1, from2, to2):
    return (value - from1) / (to1 - from1) * (to2 - from2) + from2


class DataReader(threading.Thread):
    def __init__(self):
        super().__init__()
        self.stopthread = threading.Event()
        self.filter = False
        self.data_buff_size = 250
        self.data = zeros(self.data_buff_size)

        for port, _, _ in list_ports.grep("USB-SERIAL CH340"):
            self.port = port
        try:
            print(port)
        except NameError:
            self.error = True
        else:
            self.error = False
            self.ser = Serial(self.port, 115200)
            self.start()

    def run(self):
        num_bytes = 5  # Number of bytes to read at once
        val = 0  # Read value

        while not self.stopthread.isSet():
            try:
                rslt = self.ser.read(num_bytes)  # Read serial data
            except SerialException as _:
                self.error = True
                self.stop()
            
            # Convert serial data to array of numbers
            byte_array = unpack('%dB' % num_bytes, rslt)

            first = False  # Flag to indicate weather we have the first byte of the number
            for byte in byte_array:
                if 224 <= byte <= 255:  # If first byte of number
                    val = (byte & 0b11111) << 5
                    first = True
                elif 96 <= byte <= 127:  # If second byte of number
                    val |= (byte & 0b11111)
                    if first:
                        if self.filter:
                            if (abs(val-self.data[-1]) > 2):
                                lock.acquire()
                                self.data = roll(self.data, -1)
                                self.data[-1] = val
                                lock.release()
                        else:
                            lock.acquire()
                            self.data = roll(self.data, -1)
                            self.data[-1] = val
                            lock.release()
        
        self.ser.close()

    def stop(self):
        self.stopthread.set()

class Oscilloscope():
    def __init__(self):
        self.screen_widght = 773
        self.screen_height = 580
        self.hold = False
        self.screen = pygame.display.set_mode(
            (self.screen_widght, self.screen_height))
        self.icon = pygame.image.load('icono.png')
        pygame.display.set_icon(self.icon)
        pygame.display.set_caption("Osciloscopio")
        self.font = pygame.font.Font("Oswald.ttf", 20)
        self.clock = pygame.time.Clock()
        
        self.reader = DataReader()
        self.run()
    
    def plot(self, x, y, xmin, xmax, ymin, ymax):
        h = self.screen_height - 100
        w = self.screen_widght
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
            pygame.draw.line(self.screen, (210, 210, 210),
                             (0, int(h*0.1*i)), (w-1, int(h*0.1*i)), 1)
            pygame.draw.line(self.screen, (210, 210, 210), (int(
                w*0.1*i), 0), (int(w*0.1*i), h-1), 1)

        pygame.draw.line(self.screen, (0, 0, 0), (0, h), (w, h), 1)

        #Plot data
        for i in range(len(xp)-1):
            pygame.draw.line(self.screen, (0, 0, 0), (int(xp[i]), int(yp[i])),
                             (int(xp[i+1]), int(yp[i+1])), 1)

    def run(self):
        while True:
            # Process events
            event = pygame.event.poll()
            if event.type == pygame.QUIT:
                pygame.display.quit()
                pygame.quit()
                self.reader.stop()
                sys.exit(0)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.hold = not self.hold
                if event.key == pygame.K_o:
                    self.reader.filter = not self.reader.filter

            self.screen.fill((255, 255, 255))

            if self.reader.error:
                error_text = self.font.render(
                    "Dispositivo no encontrado, reintentando...", 1, (0, 0, 0))
                self.screen.blit(error_text, (self.screen_widght/2-300, self.screen_height/2))

                self.reader = DataReader()
            else:
                # Plot current buffer
                if not self.hold:
                    lock.acquire()
                    x = arange(self.reader.data_buff_size)
                    y = self.reader.data
                    lock.release()
                self.plot(x, y, 0, self.reader.data_buff_size, 0, 1024)

                # Display voltage
                remaped = remap_value(self.reader.data[-1], 0, 1023, 0, 5)

                voltage_text = self.font.render("%.3f V" % remaped, 1, (0, 10, 10))

                if self.hold:
                    hold_text = self.font.render("PAUSADO", 1, (0, 10, 10))
                else:
                    hold_text = hold_text = self.font.render("", 1, (0, 10, 10))
                if self.reader.filter:
                    filter_text = self.font.render("FILTRANDO", 1, (0, 10, 10))
                else:
                    filter_text = self.font.render("", 1, (0, 10, 10))

                self.screen.blit(voltage_text, (self.screen_widght-60, self.screen_height-95))
                self.screen.blit(filter_text, (5, self.screen_height-95))
                self.screen.blit(hold_text, (5, self.screen_height-75))
                pygame.draw.rect(self.screen, (179, 179, 179),
                                 (0, self.screen_height-65, 100, 100), 0)

            pygame.display.flip()
            self.clock.tick(0)

if __name__ == "__main__":
    global lock
    lock = threading.Lock()
    pygame.init()
    osc = Oscilloscope()
