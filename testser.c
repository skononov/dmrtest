#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <ctype.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>

char* to_le_bytes(unsigned int word, int size)
{
    static char ch[4];
    ch[0] = word&0xff;
    ch[1] = (word>>8)&0xff;
    if(size==4) {
        ch[2] = (word>>16)&0xff;
        ch[3] = (word>>24)&0xff;
    }
    return ch;
}

void print_bytes(char *buf, size_t n)
{
    for(char* ch=buf; ch<buf+n; ch++) {
        if(isprint((int)*ch))
            printf("%c", *ch);
        else
            printf("\\x%02X", *ch);
    }
    puts("");
}

int main(int argc, char* argv[]) 
{
    int fd;
    ssize_t nb;
    int iarg;
    int nwords, wordsize;
    char *word, *pos;
    char cmd[200], buf[201];

    if(argc == 1) {
        printf("Usage: %s command [data...]\n", argv[0]);
        return 0;
    }

    const char* devfn = "/dev/ttyACM0";
    fd = open(devfn, O_SYNC, O_RDWR);

    if (fd < 0) {
        perror(devfn);
        return -1;
    }

    strcpy(cmd, argv[1]);
    pos = cmd + strlen(cmd) + 1; //null char will be included also
    nwords = argc - 2;
    wordsize = 2;
    for(iarg = 2; iarg < argc; iarg++) {
        if(atoi(argv[iarg]) > (1<<16)-1)
            wordsize = 4;
    }
    if(nwords >= 0) {
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

    nb = write(fd, cmd, n);
    
    if(nb < 0) {
        perror("Writing");
        return -2;
    }

    printf("%ld bytes written\n", nb);

    printf("Expecting reply... (Ctrl+C to exit)\n");
    fflush(stdout);

    nb = read(fd, buf, 200);

    if(nb < 0) {
        perror("Reading");
        return -2;
    }

    printf("%ld bytes read:\n", nb);
    print_bytes(buf, nb);

    return 0;
}
