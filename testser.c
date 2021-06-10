#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>
#include "dtserial.h"

int main(int argc, char* argv[]) 
{
    unsigned int *odata = NULL, idata[32768];
    int iarg = 1;

    const char* devfn = "/dev/ttyACM0";
    int fd = openserial(devfn);

    if (fd < 0)
        return 1;

    if (argc > 1 && strcmp(argv[1], "-v") == 0) {
        DTSERIALDEBUG = 1;
        iarg = 2;
    }

    if (argc-iarg < 1) {
        printf("Usage: %s [-v] command [data...]\n", argv[0]);
        return 0;
    }

    const char* command = argv[iarg++];

    int ndata = argc - iarg;
    if (ndata > 0) {
        odata = (unsigned int*)calloc(ndata, sizeof(int));
        for (int i=0; i<ndata; i++, iarg++)
            odata[i] = atoi(argv[iarg]);
    }

    int nwritten = writecommand(fd, command, odata, ndata);

    if (odata) free(odata);

    if (nwritten < 0) {
        close(fd);
        return 1;
    }

    printf("Expecting reply with timeout of 3s... (Ctrl+C to exit)\n");

    int nread = readreply(fd, 3, idata, sizeof(idata)/sizeof(int));

    if (nread < 0) {
        close(fd);
        return -1;
    } else if (nread==0) {
        puts("Empty reply");
    } else {
        printf("%d words received: ", nread);
        for(int i = 0; i < nread; i++) 
            printf("%u ", idata[i]);
        puts("");
    }

    close(fd);

    return 0;
}
