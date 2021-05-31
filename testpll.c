#include <stdio.h>
#include <stdint.h>

typedef unsigned int uint;

extern void getpllreg(uint setfreq, int maino, int auxo, int mltd, int mainpow, int auxpow, uint32_t R[]);

int main()
{
	const uint minfreq = 137000000, maxfreq = 500000000;
	uint npoints = 10;
	uint freq;
	uint32_t R[6];
	for(int i=0; i<npoints; i++) {
		freq = (uint)(minfreq + (double)(maxfreq-minfreq)/(npoints-1)*i);
        printf("Call getpllreg for frequency %u\n", freq);
		getpllreg(freq, 1, 1, 0, 0, 0, R);
		printf("Registers: [%u, %u, %u, %u, %u, %u]\n", R[0], R[1], R[2], R[3], R[4], R[5]);
	}
	return 0;
}