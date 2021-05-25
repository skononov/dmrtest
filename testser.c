#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <ctype.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>

char* to_le_bytes(int word)
{
    static char ch[2];
    ch[0] = word&0xff;
    ch[1] = (word>>16)&0xff;
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
    int nwords;
    char *twoch, *pos;
    char cmd[100], buf[101];

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
    pos = cmd + strlen(cmd);
    nwords = argc - 2;
    if(nwords >= 0) {
        twoch = to_le_bytes(nwords);
        strncpy(pos, twoch, 2);
        pos += 2;
    }
    for(iarg = 2; iarg < argc; iarg++) {
        twoch = to_le_bytes(atoi(argv[iarg]));
        strncpy(pos, twoch, 2);
        pos += 2;
    }
    strncpy(pos, "END", 3);
    pos += 3;

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

    nb = read(fd, buf, 100);

    if(nb < 0) {
        perror("Reading");
        return -2;
    }

    printf("%ld bytes read:\n", nb);
    print_bytes(buf, nb);

    return 0;
}
