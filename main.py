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
            except SerialException:
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

        self.colors = {'background': (255, 255, 255),
                       'foreground': (0, 0, 0),
                       'panel_background': (230, 230, 230),
                       'button_normal': (50, 50, 50),
                       'button_pressed': (150, 150, 150),
                       'button_border': (125, 125, 125),
                       'text_especial': (100, 100, 100),
                       'text_normal': (230, 230, 230)
                      }

        self.hold = False
        self.rect_filter = pygame.Rect(5, self.screen_height-95, 95, 30)
        self.rect_hold = pygame.Rect(5, self.screen_height-55, 95, 30)
        self.screen = pygame.display.set_mode(
            (self.screen_widght, self.screen_height))
        self.icon = pygame.image.load('icon.png')
        pygame.display.set_icon(self.icon)
        pygame.display.set_caption("Osciloscopio")
        self.font = pygame.font.Font("font.ttf", 20)
        self.clock = pygame.time.Clock()

        self.reader = DataReader()
        self.run()

    def button_pause(self):
        self.hold = not self.hold

    def button_filter(self):
        self.reader.filter = not self.reader.filter

    def plot(self, x, y, xmin, xmax, ymin, ymax):
        h = self.screen_height - 100
        w = self.screen_widght
        x = array(x)
        y = array(y)

        # Scale data
        xspan = abs(xmax-xmin)
        yspan = abs(ymax-ymin)
        xsc = 1.0*(w+1)/xspan
        ysc = 1.0*h/yspan
        xp = (x-xmin)*xsc
        yp = h-(y-ymin)*ysc

        # Draw grid
        for i in range(10):
            pygame.draw.line(self.screen, (220, 220, 220),
                             (0, int(h*0.1*i)), (w-1, int(h*0.1*i)), 1)
            pygame.draw.line(self.screen, (220, 220, 220), (int(
                w*0.1*i), 0), (int(w*0.1*i), h-1), 1)

        pygame.draw.line(self.screen, (0, 0, 0), (0, h), (w, h), 1)

        # Plot data
        for i in range(len(xp)-1):
            pygame.draw.aaline(self.screen, (0, 0, 0), (int(xp[i]), int(yp[i])),
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
                    self.button_pause()
                if event.key == pygame.K_o:
                    self.button_filter()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos
                if self.rect_filter.collidepoint(mouse_pos):
                    self.button_filter()
                elif self.rect_hold.collidepoint(mouse_pos):
                    self.button_pause()

            self.screen.fill((255, 255, 255))

            if self.reader.error:
                error_text = self.font.render(
                    "Dispositivo no encontrado, reintentando...", 1, (0, 0, 0))
                self.screen.blit(
                    error_text, (self.screen_widght/2-300, self.screen_height/2))

                self.reader = DataReader()
            else:
                # Plot current buffer
                if not self.hold:
                    lock.acquire()
                    x = arange(self.reader.data_buff_size)
                    y = self.reader.data
                    lock.release()
                self.plot(x, y, 0, self.reader.data_buff_size, 0, 1024)

                pygame.draw.rect(self.screen, self.colors['panel_background'], 
                                 (0, self.screen_height-99, self.screen_widght, self.screen_height))

                # Display voltage
                remaped = remap_value(self.reader.data[-1], 0, 1023, 0, 5)

                voltage_text = self.font.render(
                    "%.3f V" % remaped, 1, (0, 10, 10))

                if self.hold:
                    hold_text = self.font.render("Pausado", 1, self.colors['text_especial'])
                    hold_color = self.colors['button_pressed']
                else:
                    hold_text = hold_text = self.font.render(
                        "Pausar", 1, self.colors['text_normal'])
                    hold_color = self.colors['button_normal']
                if self.reader.filter:
                    filter_text = self.font.render(
                        "Filtrando", 1, self.colors['text_especial'])
                    filter_color = self.colors['button_pressed']
                else:
                    filter_text = self.font.render("Filtrar", 1, self.colors['text_normal'])
                    filter_color = self.colors['button_normal']

                hold_text_rect = hold_text.get_rect()
                hold_text_rect.center = self.rect_hold.center

                filter_text_rect = filter_text.get_rect()
                filter_text_rect.center = self.rect_filter.center

                self.screen.blit(
                    voltage_text, (self.screen_widght-60, self.screen_height-95))

                pygame.draw.rect(self.screen, filter_color,
                                 self.rect_filter)
                pygame.draw.rect(self.screen, hold_color, self.rect_hold)

                pygame.draw.rect(self.screen, self.colors['button_border'],
                                 self.rect_filter, 1)
                pygame.draw.rect(self.screen, self.colors['button_border'],
                                 self.rect_hold, 1)

                self.screen.blit(filter_text, filter_text_rect)
                self.screen.blit(hold_text, hold_text_rect)

            pygame.display.flip()
            self.clock.tick(0)


if __name__ == "__main__":
    global lock
    lock = threading.Lock()
    pygame.init()
    osc = Oscilloscope()
