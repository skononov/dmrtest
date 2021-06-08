#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>

#include "pll.h"

int main(int argc, char *argv[])
{
	if (argc < 2) {
		printf("Usage: %s frequency [frequency...]\n\n\tfrequency - in Hz from 137000000 to 800000000\n", argv[0]);
		return 0;
	}

	for(int i=1; i<argc; i++) {
		unsigned freq = (unsigned)atoi(argv[i]);
		uint32_t R[6];
		printf("Call getpllreg for frequency %u\n", freq);
		getpllreg(freq, 1, 1, 0, 0, 0, R);
		printf("Registers: %u %u %u %u %u %u\n", R[0], R[1], R[2], R[3], R[4], R[5]);
	}
	
	return 0;
}