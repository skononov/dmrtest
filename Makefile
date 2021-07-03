
CC:=gcc
LD:=gcc
CFLAGS:=-fPIC -g -Wall
LDFLAGS:=-fPIC

SOURCES:=pll.c inl.c ber.c serial.c
DEPS:=$(SOURCES:.c=.c.d)
EXECS:=testser testpll
TARGETS:=${EXECS} libdmr.so
LIBDIR:=${HOME}/dmr/lib

.PHONY: lib all install clean depclean

all: ${TARGETS}

lib: libdmr.so

${EXECS}: %: %.o
	${LD} ${LDFLAGS} $^ -o $@

%.o: %.c
	${CC} ${CFLAGS} -c $< -o $@

libdmr.so: pll.o inl.o ber.o serial.o 
	${LD} ${LDFLAGS} -shared $^ -o $@

testpll: pll.o

testser: serial.o pll.o

%.c.d: %.c
	@echo "Generating dependencies for $<"
	@$(CC) -MM $(CFLAGS) $< -MF $@

ifeq ($(findstring clean,$(MAKECMDGOALS)),)
  -include $(DEPS)
endif

install: libdmr.so
	@echo "Installing $^ to ${LIBDIR}"
	@mkdir -p ${LIBDIR}
	@cp -a $^ ${LIBDIR}

clean:
	rm -f *.o ${TARGETS}

depclean: clean
	rm -f ${DEPS}
