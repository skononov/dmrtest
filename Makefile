
CC:=gcc
LD:=gcc
CFLAGS:=-fPIC -g -Wall
LDFLAGS:=-fPIC

TARGETS:=testser libdmr.so testpll

.PHONY: lib all clean

all: ${TARGETS}

lib: libdmr.so

testpll: testpll.o pll.o
	${LD} ${LDFLAGS} $^ -o $@

libdmr.so: pll.o
	${LD} ${LDFLAGS} -shared $^ -o $@

testser: testser.o
	${LD} ${LDFLAGS} $^ -o $@

%.o: %.c
	${CC} ${CFLAGS} -c $^ -o $@

clean:
	rm -f *.o ${TARGETS}