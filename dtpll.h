#ifndef DTPLL_H
# define DTPLL_H

# include <stdint.h>

# define DTFREQLOWLIM 120000000
# define DTFREQUPLIM 800000000

extern int getpllreg(unsigned int setfreq, int maino, int auxo, int mltd, int mainpow, int auxpow, uint32_t R[]);

#endif
