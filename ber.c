#include <stdio.h>
#include <stdlib.h>


//ADC_rate = 25*f_symbol, 5 samples are averaged and then are seed to detector
static const int CORDICDEP = 8;
static const int ang[] = {32768, 19344, 10220, 5188, 2604, 1303, 651, 325};
static const int BITPRD = 25;
static const int BITDEPTH = 10;
static const unsigned char SAMPLEDIF = 3;
static const int PHDIFF = 1415*3;
//pi/2 - 65536


//static int phasehistflt[256];
//static int bdh[256];

#define FLTS 101
static int RRCflt[FLTS] = {45,29,12,-5,-24,-44,-64,-85,-104,-124,-141,-158,-172,-185,-194,-201,-204,-204,-200,-191,-179,-162,-141,-115,-85,-51,-12,29,75,124,176,231,287,345,404,463,522,580,637,691,744,793,838,880,917,948,975,996,1011,1020,1024,1020,1011,996,975,948,917,880,838,793,744,691,637,580,522,463,404,345,287,231,176,124,75,29,-12,-51,-85,-115,-141,-162,-179,-191,-200,-204,-204,-201,-194,-185,-172,-158,-141,-124,-104,-85,-64,-44,-24,-5,12,29,45};
static const int FLTGAIN = 22478;

static unsigned int getbit(unsigned char *val, int vdiff)
{
	if(vdiff>=3*PHDIFF){
		(*val)=1;
		return (vdiff-3*PHDIFF);
	}
	else if(vdiff>=2*PHDIFF){
		(*val)=1;
		return (3*PHDIFF-vdiff);
	}
	else if(vdiff>=PHDIFF){
		(*val)=0;
		return (vdiff-PHDIFF);
	}
	else if(vdiff>=0){
		(*val)=0;
		return (PHDIFF-vdiff);
	}
	else if(vdiff>=-PHDIFF){
		(*val)=2;
		return (vdiff+PHDIFF);
	}
	else if(vdiff>=-2*PHDIFF){
		(*val)=2;
		return (-(PHDIFF+vdiff));
	}
	else if(vdiff>=-3*PHDIFF){
		(*val)=3;
		return (vdiff+3*PHDIFF);
	}
	else{
		(*val)=3;
		return (-(PHDIFF*3+vdiff));
	}
}

static int atancord(int I, int Q)
{
	int aofs, sig, phasehist;
	if (I >= 0 && Q >= 0) { aofs=0; sig=1; }
	else if(I >= 0 && Q < 0) { aofs=4*65536; sig=-1; Q=-Q; }
	else if(I < 0 && Q <= 0) { aofs=2*65536; sig=1; I=-I; Q=-Q; }
	else { aofs=2*65536; sig=-1; I=-I; }
	//CORDIC based calc atan
	int tmp;
	phasehist=0;
	
	for(int i=0; i<CORDICDEP; i++){
		tmp = I>>i;
		if (Q > 0){
			I += (Q>>i);
			Q -= tmp;
			phasehist += ang[i];
		}
		else if(Q<0){
			I -= (Q>>i);
			Q += tmp;
			phasehist -= ang[i];
		}
	}

	if (sig == 1) 
        phasehist += aofs;
	else 
        phasehist = aofs - phasehist;

	return phasehist;
}

static float calcdisc(int i, const int *ph, int dir)
{
	float disc = 0;
	unsigned char dibit;
	for(int j=0; j<BITDEPTH; j++) {
		if (dir) 
            disc += getbit(&dibit, ph[i+j*BITPRD]);
		else
            disc += getbit(&dibit, ph[i-j*BITPRD]);
	}
	return disc;
}

//decode bit sequence
//Is/Qs - reference data sets for FFT
//symlenload[i] - len for sym i	(i=0,1,2,3)
//Is[0] ... Is[symlen[0]-1] - data for 0
//Is[symlenload[0]] ... Is[symlenload[0]+symlenload[1]-1] - data for 1
//....
//maxlen - limit data to load

int bercalc(const int *I, const int *Q, int size, int *numerr, int *numbit, int *Is, int *Qs, int *symlenload, int maxlen)
{
	*numbit = 0;
	*numerr = 0;
	if (size < SAMPLEDIF+FLTS+5+BITDEPTH*25)
        return 0;

	int *ph = calloc(size, sizeof(int));
	int *phdiff = calloc(size, sizeof(int));

    for (int i=0; i<size; i++) {
        ph[i] = atancord(I[i], Q[i]);
    }
	
	for (int i=0; i<SAMPLEDIF; i++) phdiff[i] = 0;

	for (int i=SAMPLEDIF; i<size; i++) {
		phdiff[i] = -ph[i] + ph[i-SAMPLEDIF];
		if (phdiff[i] >  2*65536) phdiff[i] -= 4*65536;
		if (phdiff[i] < -2*65536) phdiff[i] += 4*65536;
	}
	
	for (int i=FLTS/2; i<size-FLTS/2; i++) {
		ph[i] = 0;
		for(int j=0; j<FLTS; j++){
			ph[i] += phdiff[i+j-FLTS/2] * RRCflt[j];
		}
		ph[i] /= FLTGAIN;
	}

	int sympos[4];
	int symlen[4];
	for(int i=0; i<4; i++) symlen[i]=0;
	int cursym=0, curlen, curpos;

	//find the first position
	float disc[BITPRD];
	float bdisc = -1;
	int ofs;
	unsigned char dibit;

	for(int i=0; i<BITPRD; i++) {
		disc[i] = calcdisc(FLTS/2+i, ph, 1);
		if(disc[i] < bdisc || bdisc < 0) {
			bdisc = disc[i];
			ofs = i;
		}
	}

	int bitseq = 0;
	getbit(&dibit, ph[FLTS/2+ofs]);
	bitseq = (bitseq<<2)+(dibit&3);
	int bct = 2, dir;
	cursym = dibit;
	curlen = 1;
	curpos = FLTS/2 + ofs;

	for(int i=FLTS/2+ofs+BITPRD; i<size-FLTS/2-1;){
		if (i < (BITDEPTH+1)*BITPRD)
            dir = 1;
		else
            dir = 0;
		disc[0] = calcdisc(i, ph, dir);
		disc[1] = calcdisc(i+1, ph, dir);
		disc[2] = calcdisc(i-1, ph, dir);
		
		if (disc[1] < disc[0] && disc[1] < disc[2]) {
			getbit(&dibit, ph[i+1]);
			i += (BITPRD+1);
		} else if (disc[2] < disc[0] && disc[2] < disc[1]) {
			getbit(&dibit, ph[i-1]);
			i += (BITPRD-1);
		} else {
			getbit(&dibit, ph[i]);
			i += BITPRD;
		}

		//update symbols intervals
		if (dibit != cursym){
			if (curlen > symlen[cursym]){
				symlen[cursym] = curlen;
				sympos[cursym] = curpos;
			}
			curlen = 1;
			cursym = dibit;
			curpos = i-BITPRD;
		}
		else curlen++;

		bct += 2;

		if (bct > 12){
			(*numbit) += 2;

			if((dibit>>1) != (((bitseq>>8)^(bitseq>>4))&1)) (*numerr)++;
			if((dibit & 1) != (((bitseq>>7)^(bitseq>>3))&1)) (*numerr)++;

            //printf("read dibit=%d%d, expected dibit=%d%d\n", (dibit>>1), (dibit & 1), (((bitseq>>8)^(bitseq>>4))&1), (((bitseq>>7)^(bitseq>>3))&1));
		}
		bitseq = (bitseq<<2)+(dibit&3);

	}

	if((*numerr)<(*numbit)/3) (*numerr)=(*numerr)/3;
	else if((*numerr)<2*(*numbit)/3) (*numerr)=(*numerr)/2;

	free(ph);
	free(phdiff);

	//load symbols intervals
	int index = 0, actlen;
	for(int i=0; i<4; i++){
		symlenload[i] = symlen[i]*BITPRD;
		actlen=0;
		for(int j=sympos[i]; j<sympos[i]+symlenload[i]; j++){
			if(j>=0 && j<size && index<maxlen) {
				Is[index] = I[j];
				Qs[index] = Q[j];
				index++;
				actlen++;
			}
		}
		symlenload[i] = actlen;
	}

	return 1;
}


