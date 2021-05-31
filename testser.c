#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <poll.h>
#include <ctype.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>

static FILE* fs; //file stream

void closefs() {
    fclose(fs);
}

char* to_le_bytes(unsigned int word, size_t size)
{
    static char ch[4];
    ch[0] = word&0xff;
    ch[1] = (word>>8)&0xff;
    if (size==4) {
        ch[2] = (word>>16)&0xff;
        ch[3] = (word>>24)&0xff;
    }
    return ch;
}

unsigned int from_le_bytes_to_uint(const char* bytes, size_t size)
{
    unsigned int u=0;
    
    // limit size to avoid overflow
    size = size<=sizeof(int)?size:sizeof(int);

    for(size_t i=0; i<size; i++)
        u |= (bytes[i]>>8*i) & 0xff;
    
    return u;
}

void print_bytes(const char *buf, size_t n)
{
    for(const char* ch=buf; ch<buf+n; ch++) {
        if (isprint((int)*ch))
            printf("%c", *ch);
        else
            printf("\\x%02X", *ch);
    }
    puts("");
}

const char* strpollflags(int revents) 
{
    static char str[200];
    static const char* sflags[] = {"POLLERR", "POLLHUP", "POLLNVAL", "POLLPRI"};
    static const int flags[] = {POLLERR, POLLHUP, POLLNVAL, POLLPRI};

    str[0] = 0;
    for(int i=0; i<4; i++) {
        if ((revents&flags[i]) != 0) {
            if (str[0] == 0) 
                strcpy(str, sflags[i]);
            else
                snprintf(str, 1000, "%s|%s", str, sflags[i]);
        }
    }
    if (str[0] == 0)
        strcpy(str, "(none)");

    return str;
}

ssize_t fpollread(FILE* f, int timeout, char* buf, size_t size) 
{
    struct pollfd pfd = {fileno(fs), POLLIN, 0};

    int rp = poll(&pfd, 1, timeout);
    fprintf(stderr, "Received poll flags: %s\n", strpollflags(pfd.revents));

    if (rp > 0) {
        size_t nb = fread(buf, 1, size, fs);
        printf("%lu bytes received: ", nb);
        print_bytes(buf, nb);
        return nb;
    } else if (rp < 0) {
        perror("Polling available data");
        return -1;
    }

    printf("No data received for %.1f sec\n", (float)timeout/1000);
    return 0;
}


int main(int argc, char* argv[]) 
{
    size_t nb;
    int iarg;
    int nwords, wordsize, len;
    char *word, *pos;
    char cmd[200], buf[200];

    if (argc == 1) {
        printf("Usage: %s command [data...]\n", argv[0]);
        return 0;
    }

    const char* devfn = "/dev/ttyACM0";
    fs = fopen(devfn, "r+b");

    if (fs == NULL) {
        perror(devfn);
        return -1;
    }

    atexit(closefs);

    cmd[0] = 0;
    len = strlen(argv[1]);
    strncpy(cmd+1, argv[1], len+1);
    pos = cmd + len + 2; //null char will be included also
    nwords = argc - 2;
    wordsize = 2;
    for(iarg = 2; iarg < argc; iarg++) {
        if(atoi(argv[iarg]) > (1<<16)-1)
            wordsize = 4;
    }
    if (nwords >= 0) {
        word = to_le_bytes(nwords, 2);
        strncpy(pos, word, 2);
        pos += 2;
    }
    for(iarg = 2; iarg < argc; iarg++) {
        word = to_le_bytes(atoi(argv[iarg]), wordsize);
        strncpy(pos, word, wordsize);
        pos += wordsize;
    }
    strncpy(pos, "END\0", 4);
    pos += 4;

    size_t n = pos-cmd;

    printf("Sending command of %lu bytes: ", n);
    print_bytes(cmd, n);

    nb = fwrite(cmd, 1, n, fs);
    
    if (ferror(fs)) {
        perror("Writing");
        return -2;
    }

    printf("%ld bytes written\n", nb);

    printf("Expecting reply... (Ctrl+C to exit)\n");

    nb = fpollread(fs, 3000, buf, 4);

    if (nb < 4 || strcmp(buf, "ACK") != 0) {
        fputs("ACK is not received\n", stderr);
        return -3;
    }

    nb = fpollread(fs, 3000, buf, 200);

    if (nb == 0)
        return 0;

    if (nb<4 || strcmp(&buf[nb-5], "END") !=0)
        fputs("END is not received\n", stderr);

    len = from_le_bytes_to_uint(buf, 2);

    if (len != (nb-6)/2)
        fprintf(stderr, "Length read (%d) does not match received data length (%lu)\n", len, (nb-6)/2);

    return 0;
}
