/*
 * A PCL file parser for simple PCL sent out from HP instrument
 * when pressing "Print Screen" to a DeskJet.
 *
 * Copyright (c) 2010-2012, Ciellt/Stefan Petersen (spe@ciellt.se)
 *All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * 3. Neither the name of the author nor the names of any contributors
 *    may be used to endorse or promote products derived from this
 *    software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
 * FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 * COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
 * INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
 * BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 * CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 * LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
 * ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 */

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/queue.h>
#include <unistd.h>

#include <SDL.h>

#define DEBUG 0
#define dprintf if (DEBUG) printf

#define PCL_ESC_CHARACTER 27

enum pcl_command {
    PCL_COMMAND_NONE,
    PCL_COMMAND_GRAPHICS_DATA,
    PCL_COMMAND_COMPRESSION_MODE,
    PCL_COMMAND_START_GRAPHICS,
    PCL_COMMAND_END_GRAPHICS,
    PCL_COMMAND_RESOLUTION,
    PCL_COMMAND_KW,
    PCL_COMMAND_UNKNOWN,
};

/*
 * Parsed image is stored in a tailq with each element being one line.
 */
struct pcl_line_element {
    unsigned char *buf;
    int len;
    STAILQ_ENTRY(pcl_line_element) entry;
};
STAILQ_HEAD(parsed_head, pcl_line_element);


/*
 * SDL support variables 
 */
static SDL_Surface *screen;
static Uint32 black;
static Uint32 white;
#define DISPW 512
#define DISPH 300
#define BITS_PER_PIXEL 8
/* Currently we use 8 bits of color. Could probably be reduced to two. */
const static int colorDepth = 8;

/*
 * SDL Window initialisation
 */
int
pcl_display_init_SDL(int w, int h)
{
    Uint32 video_flags = SDL_SWSURFACE | SDL_ANYFORMAT | SDL_DOUBLEBUF;

    SDL_WM_SetCaption("Don't know yet", "noidea");

    screen = SDL_SetVideoMode(w, h, colorDepth, video_flags);

    if (screen == NULL) {
        fprintf(stderr, "Couldn't set %dx%d video mode: %s\n",
                w, h, SDL_GetError());
        SDL_Quit();
        exit(1);
    }

    black = SDL_MapRGB(screen->format, 0x00, 0x00, 0x00);
    white = SDL_MapRGB(screen->format, 0xff, 0xff, 0xff);

    if (SDL_MUSTLOCK(screen)) {
        if (SDL_LockSurface(screen) < 0) {
            return -1;
        }
    }

    /* Clear screen by setting grey background  */
    SDL_FillRect(screen, NULL, white);

    if (SDL_MUSTLOCK(screen)) {
        SDL_UnlockSurface(screen);
    }

    SDL_Flip(screen);

    return 0;
} /* pcl_display_init_SDL */


void
pcl_display_row_SDL(unsigned char *buf, int len, int y)
{
    int x;
    int bpp = screen->format->BytesPerPixel;
    Uint8 *bufp;
    int idx;
    unsigned char mask;

    //assert(screen);

    for (x = 0; x < len; x++) {
	for (idx = 0, mask = 0x80; idx < BITS_PER_PIXEL; mask >>= 1, idx++) {
	    bufp = (Uint8 *)screen->pixels + y*screen->pitch + 
		((x * BITS_PER_PIXEL) + idx)*bpp;
	    if (buf[x] & mask) {
		switch (bpp) {
		case 1:
		    *bufp = black;
		    break;
		case 2:
		    *(Uint16 *)bufp = black;
                break;
		case 3:
		    if (SDL_BYTEORDER == SDL_BIG_ENDIAN) {
			bufp[0] = (black >> 16) & 0xff;
			bufp[1] = (black >> 8) & 0xff;
			bufp[2] = black & 0xff;
		    } else {
			bufp[0] = black & 0xff;
			bufp[1] = (black >> 8) & 0xff;
			bufp[2] = (black >> 16) & 0xff;
		    }
		    break;
		case 4:
		    *(Uint32 *)bufp = black;
		    break;
		default:
		    ;
		}
	    }
	}
    }

} /* pcl_diplay_row_SDL */


/*
 * Read integer from file. Reads until a non-number is detected.
 */
int
pcl_readint(FILE *fd)
{
    int num = 0;
    int c;

    while (1) { 
	if ((c = fgetc(fd)) == EOF) {
	    return num;
	}

	if (!isdigit(c)) {
	    ungetc(c, fd);
	    return num;
	}
	num = num * 10 + (c - '0');
    }

    return -1;
} /* pcl_readint */


/*
 * This function determines which command was detected. To get here you 
 * must just have read an ESC character.
 */
enum pcl_command
pcl_find_command(FILE *fd, int *parameter)
{
    char c;

    if ((c = fgetc(fd)) == EOF) {
	return PCL_COMMAND_UNKNOWN;
    }

    if (c == '*') {
	if ((c = fgetc(fd)) == EOF) {
	    return PCL_COMMAND_UNKNOWN;
	}

	switch (c) {
	case 'b': /* Graphics information */
	    *parameter = pcl_readint(fd);
	    if ((c = fgetc(fd)) == EOF) {
		return PCL_COMMAND_UNKNOWN;
	    }
	    switch (c) {
	    case 'W':
		return PCL_COMMAND_GRAPHICS_DATA;
	    case 'M':
		return PCL_COMMAND_COMPRESSION_MODE;
	    default:
		;
	    }
	    break;
	case 'r': /* Start and Finish graphics */
	    *parameter = pcl_readint(fd);
	    if ((c = fgetc(fd)) == EOF) {
		return PCL_COMMAND_UNKNOWN;
	    }
	    if (c == 'A') {
		return PCL_COMMAND_START_GRAPHICS;
	    } else if (c == 'B') {
		return PCL_COMMAND_END_GRAPHICS;
	    }
	    return PCL_COMMAND_UNKNOWN;
	case 't': /* Resolution */
	    *parameter = pcl_readint(fd);
	    if ((c = fgetc(fd)) == EOF) {
		return PCL_COMMAND_UNKNOWN;
	    }
	    if (c == 'R') {
		return PCL_COMMAND_RESOLUTION;
	    }
	    return PCL_COMMAND_UNKNOWN;
	default:
	    ;
	}
    } else if (c == '&') {
	if ((c = fgetc(fd)) == EOF) {
	    return PCL_COMMAND_UNKNOWN;
	}
	if (c != 'k') {
	    return PCL_COMMAND_UNKNOWN;
	}
	*parameter = pcl_readint(fd);
	if ((c = fgetc(fd)) == EOF) {
	    return PCL_COMMAND_UNKNOWN;
	}	
	if (c != 'W') {
	    return PCL_COMMAND_UNKNOWN;
	}
	return PCL_COMMAND_KW;
    } else {
	return PCL_COMMAND_UNKNOWN;
    }
    
    return PCL_COMMAND_UNKNOWN;
} /* pcl_find_command */


int
pcl_read_file(FILE *fd, struct parsed_head *parsed)
{
    int read;
    enum pcl_command command;
    int parameter, i, nuf_rows = 0;
    int in_graphics = 0;
    struct pcl_line_element *ple;

    while (!feof(fd)) {
	if ((read = fgetc(fd)) == EOF) {
	    break;
	}

	/* Search for commands that start with ESC */
	if (read == PCL_ESC_CHARACTER) {
	    command = pcl_find_command(fd, &parameter);
	    switch (command) {
	    case PCL_COMMAND_NONE:
		dprintf("No Command, probably error\n");
		break;
	    case PCL_COMMAND_GRAPHICS_DATA:
		dprintf("Graphics data %d\n", parameter);
		if (in_graphics) {
		    ple = malloc(sizeof(struct pcl_line_element));
		    ple->buf = malloc(parameter);
		    ple->len = parameter;
		    for (i = 0; i < parameter; i++) {
			read = fgetc(fd);
			if (read == EOF) {
			    fprintf(stderr, "EOF error in data stream\n");
			    exit(0);
			}
			ple->buf[i] = (char)read;
		    }
		    STAILQ_INSERT_TAIL(parsed, ple, entry);
		    nuf_rows++;
		}
		break;
	    case PCL_COMMAND_COMPRESSION_MODE:
		dprintf("Compression mode\n");
		break;
	    case PCL_COMMAND_START_GRAPHICS:
		dprintf("Start Graphics\n");
		in_graphics = 1;
		break;
	    case PCL_COMMAND_END_GRAPHICS:
		dprintf("End Graphics\n");
		in_graphics = 0;
		break;
	    case PCL_COMMAND_RESOLUTION:
		dprintf("Resolution %d DPI\n", parameter);
		break;
	    case PCL_COMMAND_KW:
		dprintf("KW command %d\n", parameter);
		break;
	    case PCL_COMMAND_UNKNOWN:
		dprintf("Command unknown\n");
		break;
	    default:
		;
	    }
	} else {
	    ;
	}
	
    }

    return nuf_rows;
} /* pcl_read_file */


int
main(int argc, char *argv[])
{
    FILE *fd;
    struct parsed_head parsed;
    struct pcl_line_element *ple;
    int nuf_rows, row;
    SDL_Event event;

    if (argc != 2) {
	fprintf(stderr, "%s <pcl file>\n", argv[0]);
	exit(0);
    }

    fd = fopen(argv[1], "rb");
    if (fd == NULL) {
	perror("fopen");
	exit(0);
    }

    STAILQ_INIT(&parsed);

    nuf_rows = pcl_read_file(fd, &parsed);

    pcl_display_init_SDL(DISPW, nuf_rows);

    row = 0;
    STAILQ_FOREACH(ple, &parsed, entry) {
	pcl_display_row_SDL(ple->buf, ple->len, row++);
	free(ple->buf);
	free(ple);
    }

    SDL_Flip(screen);

    fclose(fd);
    
    /*
     * SDL Main Event Loop
     */
    while (SDL_WaitEvent(&event)) {
	if (event.type == SDL_KEYDOWN) {
	    if (event.key.keysym.sym == SDLK_q) {
		SDL_Quit();
	    }
	}
    }

    return 0;
} /* main */
