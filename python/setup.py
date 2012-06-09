#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# Setup file for py2exe to generate a binary distribution of
# tivu (Test Instrument Viewer)

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

from distutils.core import setup
import py2exe
import sys,os

# This script is useful for py2exe so just run that distutils commands.
# That allows to run it with a simple double click
sys.argv.append('py2exe')

# Get an icon from somewhere. The Python installation should have one.
#icon = os.path.join(os.path.dirname(sys.executable), 'DLLs\py.ico')
icon = 'tivu.ico'

setup(
    options = {'py2exe': {
            'excludes': ['javax.comm'],
            'optimize': 2,
            'dist_dir': 'tivu',
            }
    },

    name = 'tivu',
    windows = [
        {
            'script': "tivu.py",
            'icon_resources': [(0x0004, icon)],
        },
    ],
    zipfile = "stuff.lib",

    description = 'Act as very simple PCL compatible printer to take screenshoots from testinstruments',
    version = '0.1',
    author = 'Stefan Petersen',
    author_email = 'spe@ciellt.se',
)
