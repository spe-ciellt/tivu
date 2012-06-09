#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# Tivu: Display program for printouts from HP/Agilent instruments.
#
# Copyright (c) 2010-2012, Ciellt/Stefan Petersen (spe@ciellt.se)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the author nor the names of any contributors
#    may be used to endorse or promote products derived from this
#    software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#

import wx
import os
import glob
import threading
import serial
import tivuGUI
import bitimage
import pclparse


#----------------------------------------------------------------------
# Create an own event type, so that GUI updates can be delegated
# this is required as on some platforms only the main thread can
# access the GUI without crashing. wxMutexGuiEnter/wxMutexGuiLeave
# could be used too, but an event is more elegant.

SERIALRX = wx.NewEventType()
# bind to serial data receive events
EVT_SERIALRX = wx.PyEventBinder(SERIALRX, 0)

class SerialRxEvent(wx.PyCommandEvent):
    eventType = SERIALRX
    def __init__(self, windowID, data):
        wx.PyCommandEvent.__init__(self, self.eventType, windowID)
        self.data = data

    def Clone(self):
        self.__class__(self.GetId(), self.data)



class TivuFrame(tivuGUI.MainFrame):

    nufRows = 276
    
    def __init__(self, *args, **kwds):
        tivuGUI.MainFrame.__init__(self, *args, **kwds)
        self.ser = None
        self.speed = 9600

        self.pcl = pclparse.pclparse()
        self.streaming = False
        
        ## Thread specific variables
        self.thread = None
        self.alive = threading.Event()

        ## Bind residual events
        self.Bind(EVT_SERIALRX, self.OnSerialRead)
        self.Bind(wx.EVT_CLOSE, self.OnQuit)

        self.gauge = 0
        self.gaugemeter = None

        
    def OnNew(self, event):
        self.BitWindow.SetData([])


    def OnOpen(self, event):
        dlg = wx.FileDialog(None, 'Select file to read in')
        modal = dlg.ShowModal()
        filename = dlg.GetPath()
        dlg.Destroy()
        if modal != wx.ID_OK:
            return
        
        ## Create a parser and run the file thru it
        pcl = pclparse.pclparse()
        fd = open(filename, 'rb')
        while True:
            data = fd.read(100)
            if len(data) == 0:
                break
            pcl.parse(data)
        fd.close()

        ## Blit the parsed data to the bit window
        self.BitWindow.SetData(pcl.data)


    defaultFile = 'Image'
    wildcards = 'PNG (*.png)|*.png|JPEG (*.jpg)|*.jpg|BMP (*.bmp)|*.bmp|TIFF (*.tiff)|*.tiff'
    
    def OnSaveAs(self, event):
        dlg = wx.FileDialog(None, 'Select file name of file to save to',
                            defaultDir  = os.getcwd(),
                            defaultFile = self.defaultFile,
                            wildcard = self.wildcards,
                            style = wx.FD_SAVE | wx.FD_CHANGE_DIR)
        modal = dlg.ShowModal()
        filename = dlg.GetPath()
        filteridx = dlg.GetFilterIndex()
        dlg.Destroy()
        if modal != wx.ID_OK:
            return

        if filteridx == 0:
            filepostfix = '.png'
            bitmaptype = wx.BITMAP_TYPE_PNG
        elif filteridx == 1:
            filepostfix = '.jpg'
            bitmaptype = wx.BITMAP_TYPE_JPEG
        elif filteridx == 2:
            filepostfix = '.bmp'
            bitmaptype = wx.BITMAP_TYPE_BMP
        elif filteridx == 3:
            filepostfix = '.tiff'
            bitmaptype = wx.BITMAP_TYPE_TIF
        else:
            filepostfix = '.bmp'
            bitmaptype = wx.BITMAP_TYPE_BMP

        ## If postfix of filename is already there we don't add it
        filepostfixlen = len(filepostfix)
        if filename[-filepostfixlen:] == filepostfix:
            completefilename = filename
        else:
            completefilename = filename + filepostfix
        
        image = wx.ImageFromBitmap(self.BitWindow.buffer)
        image.SaveFile(completefilename, bitmaptype)

 
    def OnSerialPort(self, event):
        ## Calculate all ports available on per OS level
        if os.name == 'nt':
            allports = range(256)
        elif os.name == 'posix':
            allports = glob.glob('/dev/tty[A-Z]*')
            ## allports = range(1024)
            ## = ['/dev/ttyS0', '/dev/ttyS1', '/dev/ttyS2', '/dev/ttyS3',
            ##   '/dev/ttyS4', '/dev/ttyS5', '/dev/ttyS6', '/dev/ttyS7',
            ##   '/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyUSB2', '/dev/ttyUSB3',
            ##   '/dev/ttyUSB4', '/dev/ttyUSB5', '/dev/ttyUSB6', '/dev/ttyUSB7',
            ##   '/dev/ttyACM0', '/dev/ttyACM1', '/dev/ttyACM2', '/dev/ttyACM3',
            ##   '/dev/ttyACM4', '/dev/ttyACM5', '/dev/ttyACM6', '/dev/ttyACM7',
            ##   ]

        else:
            #print 'Unknown OS'
            os.exit()

        ## Search for all available ports, ie possible to open
        available = []
        for dev in allports:
            try:
                s = serial.Serial(dev)
                available.append((dev, s.portstr))
                s.close()   #explicit close 'cause of delayed GC in java
            except serial.SerialException:
                pass

        ## Build port list and open port selection list window
        if available == []:
            portnames = ["No comport"]
        else:
            # Pick out only the names, not indices
            portnames = [i[1] for i in available]

        dlg = wx.SingleChoiceDialog(None, "Select com port", "Com port",
                                    portnames)
        modal = dlg.ShowModal()
        serialport = dlg.GetStringSelection()
        dlg.Destroy()

        if modal == wx.ID_OK:
            # If serial port is open we must close it and make sure serial
            # receiving thread is stopped.
            if self.ser and self.ser.isOpen():
                self.StopThread()
                self.ser.close()
                self.ser = None
                self.statusbar.SetStatusText('No Comport', 1)
                
            ## Open serial port with requested speed
            try:
                self.ser = serial.Serial(serialport, self.speed, timeout = 1)
            except:
                wx.MessageBox("Serial port %s is not available" % serialport,
                              "Open serial port",
                              style = wx.OK | wx.ICON_ERROR)
                return

            ## Check if we managed to open port. At least in Linux it seems
            ## that sometimes serial.Serial does not generate an exception
            ## despite port is not opened.
            if not self.ser or not self.ser.isOpen():
                wx.MessageBox("Serial port %s failed to open" % serialport,
                              "Open serial port",
                              style = wx.OK | wx.ICON_ERROR)
                return

            ## Update statusbar
            self.statusbar.SetStatusText('%s' % serialport, 1)

            ## Start receiving thread
            self.StartThread()


    def OnSerialPortSpeed(self, event):
        dlg = wx.SingleChoiceDialog(None, "Select Speed", "Speed",
                                    ['300','600','1200','2400','4800','9600',
                                     '19200','38400','57600'])
        modal = dlg.ShowModal()
        speedstring = dlg.GetStringSelection()
        dlg.Destroy()

        if modal == wx.ID_OK:
            self.speed = int(speedstring)
            if self.ser and self.ser.isOpen():
                port = self.ser.port
                self.StopThread()
                self.ser.close()
                self.ser = serial.Serial(port, self.speed, timeout = 1)
                self.StartThread()
            self.statusbar.SetStatusText('%d' % self.speed, 2)


    def OnSerialRead(self, event):
        data = event.data
        self.pcl.parse(data)

        # Found start of graphical block
        if self.streaming == False and self.pcl.state != 'STATE_IDLE':
            self.streaming = True
            self.gauge = 0
            self.gaugemeter = wx.ProgressDialog('Receiving Data',
                                                'Receiving data from instrument...',
                                                maximum = self.nufRows,
                                                style = wx.PD_AUTO_HIDE |
                                                        wx.PD_CAN_ABORT)

        # Receiving graphical datablock
        if self.streaming and len(self.pcl.data) > self.gauge:
            self.gauge = len(self.pcl.data)
            (cont, skip) = self.gaugemeter.Update(self.gauge)
            wx.SafeYield()
            if not cont:
                self.pcl.state = 'STATE_IDLE'
                self.streaming = False
                self.pcl.data = []
                self.gaugemeter.Destroy()
                self.gaugemeter = None
            
        # Found end of graphical block
        if self.streaming and self.pcl.state == 'STATE_IDLE':
            self.streaming = False
            self.BitWindow.SetData(self.pcl.data)
            self.pcl.data = []
            wx.MilliSleep(100)
            self.gaugemeter.Destroy()
            self.gaugemeter = None


    def StartThread(self):
        """Start the receiver thread"""
        self.thread = threading.Thread(target = self.ComPortThread)
        self.thread.setDaemon(1)
        self.alive.set()
        self.thread.start()


    def StopThread(self):
        """Stop the receiver thread, wait util it's finished."""
        if self.thread is not None:
            self.alive.clear()          #clear alive event for thread
            self.thread.join()          #wait until thread has finished
            self.thread = None


    def ComPortThread(self):
        """Thread that handles the incoming traffic. Generates an
           SerialRxEvent"""
        while self.alive.isSet():               #loop while alive event is true
            text = self.ser.read(1)          #read one, with timeout
            if text:                            #check if not timeout
                n = self.ser.inWaiting()     #look if there is more to read
                if n:
                    text = text + self.ser.read(n) #get it
                event = SerialRxEvent(self.GetId(), text)
                self.GetEventHandler().AddPendingEvent(event)

                
    def OnAbout(self, event):
        description = """tivu acts as a printer connected to a testinstrument. It is mainly developed for HP E8285A, but can probably be used for other instruments using PCL printer output. When the program is started it waits silently for user to press "screen shot" button on the test instrument. tivu can currently save image as png, jpg, bmp and tiff.
"""

        licence = """Copyright (c) 2010-2012, Ciellt/Stefan Petersen (spe@ciellt.se)
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.

3. Neither the name of the author nor the names of any contributors
   may be used to endorse or promote products derived from this
   software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""


        info = wx.AboutDialogInfo()

        info.SetIcon(wx.Icon('tivu.png', wx.BITMAP_TYPE_PNG))
        info.SetName('Test Instrument Viewer')
        info.SetVersion('1.0')
        info.SetDescription(description)
        info.SetCopyright('(C) 2010 - 2012 Ciellt/Stefan Petersen')
        info.SetWebSite('http://www.ciellt.se/')
        info.SetLicence(licence)
        info.AddDeveloper('Stefan Petersen')
        #info.AddDocWriter('')
        #info.AddArtist('')
        #info.AddTranslator('')

        wx.AboutBox(info)

    def OnQuit(self, event):
        self.StopThread()
        self.Destroy()
        
