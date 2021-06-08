#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <stdint.h>
#include <termios.h>
#include <poll.h>
#include <ctype.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>

#include "pll.h"

#define _POSIX_C_SOURCE 200809L

#define ACK "ACK"
#define END "END"

#define min(a,b) \
    ({ __typeof__ (a) _a = (a); \
	   __typeof__ (b) _b = (b); \
	   _a < _b ? _a : _b; })

int DTSERIALDEBUG = 0;



static char* append_int(char* buf, unsigned int word, size_t size)
{
    char ch[4];
    ch[0] = word&0xff;
    ch[1] = (word>>8)&0xff;
    if (size==4) {
        ch[2] = (word>>16)&0xff;
        ch[3] = (word>>24)&0xff;
    }
    strncpy(buf, ch, size);
    return buf + size;
}

static unsigned int from_le_bytes_to_uint(const char* bytes, size_t size)
{
    unsigned int u=0;
    
    // limit size to avoid overflow
    size = size<=sizeof(int)?size:sizeof(int);

    for(size_t i=0; i<size; i++)
        u += (bytes[i]&0xff)<<(8*i);
    
    return u;
}

static void print_bytes(const char *buf, size_t n)
{
    for(const char* ch=buf; ch<buf+n; ch++) {
        if (isprint((int)*ch))
            printf("%c", *ch);
        else
            printf("\\x%02hhX", *ch);
    }
    puts("");
}

static const char* strpollflags(int revents) 
{
    static char str[200];
    static const char* sflags[] = {"POLLIN", "POLLERR", "POLLHUP", "POLLNVAL", "POLLPRI"};
    static const int flags[] = {POLLIN, POLLERR, POLLHUP, POLLNVAL, POLLPRI};

    str[0] = 0;
    for(int i=0; i<4; i++) {
        if ((revents&flags[i]) != 0) {
            if (str[0] == 0) 
                strcpy(str, sflags[i]);
            else {
                strncat(str, "|", 2);
                strcat(str, sflags[i]);
            }
        }
    }
    if (str[0] == 0)
        strcpy(str, "(none)");

    return str;
}

int openserial(const char* devfn)
{
    int fd = open(devfn, O_RDWR|O_NOCTTY|O_CLOEXEC|O_NONBLOCK);

    if (fd < 0) {
        perror(devfn);
        return fd;
    }

    struct termios tiop;
    if (ioctl(3, TCGETS, &tiop) < 0)  {
        close(fd);
        return -1;
    }

    if (DTSERIALDEBUG) {
        puts("Initial terminal flags:");
        printf("c_iflag=0%o c_oflag=0%o c_cflag=0%o c_lflag=0%o c_ispeed=0%o c_ospeed=0%o c_line=0%o\n", \
            tiop.c_iflag, tiop.c_oflag, tiop.c_cflag, tiop.c_lflag, tiop.c_ispeed, tiop.c_ospeed, tiop.c_line);
        printf("c_cc=");
        print_bytes((const char*)tiop.c_cc, NCCS);
    }

    tiop.c_iflag = tiop.c_oflag = tiop.c_lflag = 0;
    tiop.c_cflag = CS8 | CREAD | CLOCAL | HUPCL;
    tiop.c_cc[VMIN] = 0;
    cfsetispeed(&tiop, B9600); cfsetospeed(&tiop, B9600);
    if (ioctl(fd, TCSETS, &tiop) < 0) {
        close(fd);
        return -1;
    }

    int iocmbits = TIOCM_DTR|TIOCM_RTS;
    if (ioctl(fd, TIOCMBIS, &iocmbits) < 0) {
        close(fd);
        return -1;
    }

    return fd;
}

int writecommand(int fd, const char* command, unsigned int* odata, int ndata)
{
    char *packet, *pos;
    int nb;

    size_t maxlen = strlen(command) + 4*ndata + strlen(ACK) + strlen(END) + 4;
    
    packet = (char*)malloc(maxlen);
    if (!packet) {
        perror("Can not allocate buffer.");
        return -1;
    }

    if (ioctl(fd, TCFLSH, TCIFLUSH) < 0) {
        perror("Can not flush input data.");
        return -1;
    }

    packet[0] = 0;
    size_t clen = strlen(command);
    strncpy(packet+1, command, clen+1);
    pos = packet + clen + 2; //include also trailing null char

    if (strncmp(command, "LOAD PLL", clen) == 0) {
        if (ndata != 7) {
            fprintf(stderr, "7 arguments to command 'LOAD PLL' are expected, %d are provided.\n", ndata);
            return -1;
        }
        pos = append_int(pos, 13, 2); //number of 16-bit words
        pos = append_int(pos, odata[0], 2);
        for(int i = 1; i < ndata; i++)
            pos = append_int(pos, odata[i], 4);
    } else if (strncmp(command, "SET LFDAC", clen) == 0) {
        if (ndata != 2) {
            fprintf(stderr, "2 arguments to command 'SET LFDAQ' are expected, %d are provided.\n", ndata);
            return -1;
        }
        pos = append_int(pos, 3, 2); //number of 2-byte words
        pos = append_int(pos, odata[0], 2); //AMP
        pos = append_int(pos, odata[1], 4); //FREQ
    } else if (strncmp(command, "SET PLLFREQ", clen) == 0) {
        if (ndata != 1) {
            fprintf(stderr, "1 argument to command 'SET PLLFREQ' is expected, %d was provided.\n", ndata);
            return -1;
        }
		uint32_t R[6];
        if (DTSERIALDEBUG) 
		    printf("Call getpllreg for frequency %u\n", odata[0]);
		if (!getpllreg(odata[0], 1, 1, 0, 0, 0, R)) // convert frequency to register values
            return -1; 
        unsigned odata1[7] = {2, R[0], R[1], R[2], R[3], R[4], R[5]};
        return writecommand(fd, "LOAD PLL", odata1, 7); // recursive call
    } else {
        pos = append_int(pos, ndata, 2); //number of 2-byte words
        for(int i = 0; i < ndata; i++) 
            pos = append_int(pos, odata[i], 2); //assume 2 bytes for all data words
    }
    strncpy(pos, END, strlen(END)+1);
    pos += strlen(END)+1;

    size_t n = pos-packet;

    if (DTSERIALDEBUG) {
        printf("Sending command of %lu bytes: ", n);
        print_bytes(packet, n);
    }

    nb = write(fd, packet, n);

    free(packet);

    if (nb < 0) {
        perror("Writing packet");
        return -1;
    }

    if (DTSERIALDEBUG)
        printf("%d bytes written\n", nb);

    return nb;
}

int readreply(int fd, float timeout, unsigned int *reply, unsigned int nreply)
{
    static const size_t lenack = strlen(ACK), lenend = strlen(END);

    const size_t lenbuf = 2*32768+8;
    char buf[lenbuf], *pos;

    size_t ntotb = 0;
    size_t nexpected = min(lenbuf, lenack + 2 + nreply*2 + lenend);
    ssize_t nb;

    clock_t startclock = clock();
    int toms = (int)(timeout*1000);

    struct pollfd pfd = {fd, POLLIN, 0};
    const int chunksize = 3;
    int ntry, endread = 0;

    while (ntotb < nexpected) {
        clock_t curclock = clock();
        
        if (timeout > 0) {
            toms = (int)(timeout*1000 - (curclock-startclock)*1000./CLOCKS_PER_SEC);
            if (toms <= 0)
                break;
        }

        int rp = poll(&pfd, 1, toms);
        //fprintf(stderr, "Received poll flags: %s\n", strpollflags(pfd.revents));

        if (rp > 0) {
            ntry = (chunksize<nexpected-ntotb) ? chunksize : nexpected-ntotb;
            nb = read(fd, buf+ntotb, ntry);
            if (nb < 0) {
                perror("Reading device");
                break;
            } else if (nb == 0) {
                errno = ECOMM;
                perror("Zero character read while poll returned that input data available");
                break;
            }
            ntotb += nb;

            if (ntotb>=lenend && strncmp(buf+ntotb-lenend, END, lenend) == 0) {
                endread = 1;
                break;
            }
        } else if (rp < 0) {
            perror("Polling available data");
            return -1;
        } else { // timeout
            break;
        }
    }

    size_t ireply = 0;
    if (ntotb > 0) {
        if (DTSERIALDEBUG) {
            printf("%ld bytes received: ", ntotb);
            print_bytes(buf, ntotb);
        }
        if (strncmp(ACK, buf, lenack)!=0)
            fprintf(stderr, "%s is not received\n", ACK);
        else {
            char *final = buf + (endread?ntotb-lenend:ntotb);
            pos = buf+lenack;
            size_t rlength = from_le_bytes_to_uint(pos, 2);
            pos += 2;
            for (; pos<final && ireply<nreply; pos+=2, ireply++) {
                reply[ireply] = from_le_bytes_to_uint(pos, 2);
            }
            if (rlength != ireply) 
                fprintf(stderr, "Length word read (%lu) differs from received number of words (%lu)\n", rlength, ireply);
        }
        if (!endread)
            fprintf(stderr, "%s is not received\n", END);
    } else
        printf("No data received\n");

    return ireply;
}
