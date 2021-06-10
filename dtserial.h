#ifndef DTSERIAL_H
# define DTSERIAL_H

extern int DTSERIALDEBUG;

// Open, setup a device file and return a file descriptor or -1 in case of a failure
extern int openserial(const char* devfn);

// Write command to serial device with optional data
// Number of written words is returned or -1 on case of an error.
// fd - file desciptor
// command - command null-terminated string
// odata - array of output data words
// ndata - size of odata
extern int writecommand(int fd, const char* command, const unsigned int* odata, int ndata);

// Read serial device until END is received or nreply words is read or timeout expired.
// Actual number of received words is returned.
// fd - file desciptor
// timeout - poll timeout in seconds
// reply - buffer to store data
// nreply - number of 2-byte words expected not exceeding the reply buffer size
extern int readreply(int fd, float timeout, unsigned int *reply, unsigned int nreply);

#endif //DTSERIAL_H