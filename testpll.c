#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>

typedef unsigned int uint;

extern void getpllreg(uint setfreq, int maino, int auxo, int mltd, int mainpow, int auxpow, uint32_t R[]);

int main(int argc, char *argv[])
{
	static const uint minfreq = 137000000, maxfreq = 800000000;
	if (argc < 2) {
		printf("Usage: %s frequency [frequency...]\n\n\tfrequency - in MHz from 137 to 800\n", argv[0]);
		return 0;
	}

	for(int i=1; i<argc; i++) {
		uint freq = (uint)(atof(argv[i])*1e6);
		if (freq < minfreq || freq > maxfreq) {
			fprintf(stderr, "Given frequency %s is out of range [137, 800] MHz\n", argv[i]);
			continue;
		}

		uint32_t R[6];
		printf("Call getpllreg for frequency %u\n", freq);
		getpllreg(freq, 1, 1, 0, 0, 0, R);
		printf("Registers: %u %u %u %u %u %u\n", R[0], R[1], R[2], R[3], R[4], R[5]);
	}
	
	return 0;
}