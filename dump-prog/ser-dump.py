#/usr/bin/env python

import serial

reading = False
ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=10)
fd = open('foo.txt', 'wb')

while True:
    read = ser.read()
    if reading and len(read) == 0:
        break
    if len(read) > 0 and not reading:
        print 'Started reading'
        reading = True
    fd.write(read)

fd.close()
ser.close()
