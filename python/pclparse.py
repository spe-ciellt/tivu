#!/usr/bin/env python
# -*- encoding: utf-8 -*-

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

import re

class pclparse:

    def __init__(self):
        self.data = []
        self.string = ''
        self.pclre = re.compile('((\033[*\&][tkrb])(\d*)([WRAB]))')
        self.state = 'STATE_IDLE'
        self.row = 0
        self.rowlen = 0


    def parse(self, string):
        self.string = ''.join([self.string, string])
        done = False

        while not done:
            done = True
            if self.state ==  'STATE_GRAPHICS_DATA' and \
              len(self.string) >= self.rowlen:
                data = map(ord, list(self.string[0:self.rowlen]))
                self.data.append(data)
                self.string = self.string[self.rowlen:]
                done = False
                self.state = 'STATE_GRAPHICS'

            hits = re.search(self.pclre, self.string)
            if hits:
                txtblk = ''.join([hits.groups()[1], hits.groups()[3]])
                self.string = self.string[hits.end():]
                done = False
                if txtblk == '\033*rA':
                    # print 'Start graphics'
                    self.state = 'STATE_GRAPHICS'
                elif txtblk == '\033*rB':
                    # print 'End Graphics'
                    self.state = 'STATE_IDLE'
                elif self.state == 'STATE_GRAPHICS' and txtblk == '\033*bW':
                    # print 'Graphics Data'
                    self.state = 'STATE_GRAPHICS_DATA'
                    self.rowlen = int(hits.groups()[2])
                elif len(txtblk) > 0 and txtblk[0] == '\033':
                    # print 'Unhandled %s' % (txtblk[1:])
                    pass
                else:
                    # print 'Length: ' + str(len(txtblk))
                    pass


if __name__ == '__main__':

    ## Test of parser (streaming type)
    pcl = pclparse()
    fd = open('../samples/HP-E8285A/rx-test.txt', 'rb')
    while True:
        data = fd.read(100)
        if len(data) == 0:
            break
        pcl.parse(data)
    fd.close()
    print("Image size (E8285A): %dx%d" % (len(pcl.data[0] * 8), len(pcl.data)))

    ## Test of parser (streaming type)
    pcl = pclparse()
    fd = open('../samples/HP-8752A/dump-pcl-8752.txt', 'rb')
    while True:
        data = fd.read(100)
        if len(data) == 0:
            break
        pcl.parse(data)
    fd.close()

    print("Image size (8752A): %dx%d" % (len(pcl.data[0] * 8), len(pcl.data)))
