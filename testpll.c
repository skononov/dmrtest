#include <stdio.h>
#include <stdint.h>

extern void getpllreg(unsigned int setfreq, int maino, int auxo, int mltd, int mainpow, int auxpow, uint32_t R[]);

int main()
{
	unsigned int freqs[5] = {444357, 313567, 184566, 330778, 352783};
	uint32_t R[6];
	for(int i=0; i<5; i++) {
        printf("Call getpllreg for frequency %u\n", freqs[i]);
		getpllreg(freqs[i], 1, 1, 0, 0, 0, R);
		printf("Registers: [%u, %u, %u, %u, %u, %u]\n", R[0], R[1], R[2], R[3], R[4], R[5]);
	}
	return 0;
}