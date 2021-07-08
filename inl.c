#include <stdio.h>
#include <math.h>

 #define max(a,b) \
    ({ __typeof__ (a) _a = (a); \
	   __typeof__ (b) _b = (b); \
	   _a > _b ? _a : _b; })
 
 #define min(a,b) \
    ({ __typeof__ (a) _a = (a); \
	   __typeof__ (b) _b = (b); \
	   _a < _b ? _a : _b; })

 #define limit(v,a,b) \
    ({ __typeof__ (v) _v = (v); \
	   __typeof__ (a) _a = (a); \
	   __typeof__ (b) _b = (b); \
	   _v < _a ? _a : (_v > _b ? _b : _v); })
 

//fmin, fmax - span in amp[] index
//if peak is bad, return 0
int peak_search(const double *amp, int fmin, int fmax, double *ppwr, double *pfpeak)
{
	static const double eps = 0.000001;
	static const double epsraw = 0.01;

	*pfpeak = *ppwr = 0;

	if(fmin == fmax) return 0;

	int fpeak = fmin;
	double pwr = 0;
	for(int i=fmin; i<=fmax; i++) {
		if(amp[i]>amp[fpeak]) fpeak = i;
	}
	pwr = amp[fpeak]*amp[fpeak];
	if(pwr == 0) return 0;
	
	int bp = fpeak, bm = fpeak;
	double pnew;
	int out;
	while (bp <= fmax || bm >= fmin)
	{
		out=1;
		if (bp <= fmax) {
			pnew = pwr + amp[bp]*amp[bp];
			if ((pnew-pwr)/pwr > epsraw || ((pnew-pwr)/pwr <= epsraw && ((pnew-pwr)/pwr > eps) && amp[bp] < amp[bp-1])) {
				pwr = pnew; 
				bp++; 
				out = 0; 
			}
		}
		if (bm >= fmin) {
			pnew = pwr + amp[bm]*amp[bm];
			if((pnew-pwr)/pwr > epsraw || ((pnew-pwr)/pwr <= epsraw && ((pnew-pwr)/pwr > eps) && amp[bm] < amp[bm+1])) {
				pwr = pnew; 
				bm--; 
				out = 0;
			}
		}
		if (out) break;
	}
	
	*pfpeak = 0;
	*ppwr = 0;
	for(int i=bm+1; i<bp; i++){
		*ppwr += amp[i]*amp[i];
		*pfpeak += amp[i]*amp[i]*i;
	}
	*pfpeak /= *ppwr;

	//if(bp>fmax || bm<fmin) return 0;

	return 1;
}

#define NH 38
#define HMIN 0.1
#define HMAX 3.8
static const double hstep = (HMAX-HMIN)/(NH-1);
static double lmitable[NH];
static int mitabcalc = 0;

static void calc_lmi_table()
{
	double h = HMIN;
	for (int i=0; i<NH; i++) {
		lmitable[i] = log(jn(2, h)/jn(1, h));
		h += hstep;
	}
}

//return 1 if OK, 0 if bad
//fm - modulation frequency
//*pinl - total harmonic distortion?
//*ph - modulation index
//amp is FFT amplitude of I or Q channel
int get_inl(const double *amp, int num, double fm, double *pinl, double *ph)
{
	//relative bandwidth
	static const double freqwh=0.1;

	double p1, p2, pn, ptot, perror=0, fest, tmp, h;

	if (!mitabcalc) {
		calc_lmi_table();
		mitabcalc = 1;
	}

	*pinl = *ph = 0;

	int fmin = (int)limit((fm*(1-freqwh)), 0, num-1);
	int fmax = (int)limit((fm*(1+freqwh)), 0, num-1);

	//find the main harmonic frequency & power
	if (fmin==fmax || !peak_search(amp, fmin, fmax, &p1, &fest)) {
		fprintf(stderr, "Could not find the main frequency peak\n");
		return 0;
	}

	fmin = (int)limit((2*fest*(1-freqwh)), 0, num-1);
	fmax = (int)limit((2*fest*(1+freqwh)), 0, num-1);

	//find the second harmonic frequency & power
	if (fmin==fmax || !peak_search(amp, fmin, fmax, &p2, &tmp)) {
		fprintf(stderr, "Could not find the second harmonic peak\n");
		return 0;
	}

	double g = log(sqrt(p2/p1));
	int ih;
	//determine h for a given ratio of second and first harmonics amplitudes
	for(ih=0; ih<NH; ih++) {
		if(g < lmitable[ih]) break;
	}
	
	if(ih==NH) {
		//too high modulation index
		fprintf(stderr, "Could not evaluate modulaiton index, too large harmonic fraction %3g\n", sqrt(p2/p1));
		return 0;
	} else {
		//interpolate modulaiton index to obtain more accurate value
		int ih2 = ih==0?ih+1:ih-1;
		h = HMIN + hstep*(ih-(lmitable[ih]-g)/(lmitable[ih]-lmitable[ih2]));
		//debug
		//printf("(%d %f)-(%d %f) => %f\n", ih2, lmitable[ih2], ih, lmitable[ih], g);
		//printf("interpolated power deviation: %f\n", fabs(jn(2, h)/jn(1, h)/exp(g)-1));
	}
	*ph = h;
	
	ptot = p1+p2;
	double pref, jnref;
	if(p2 > p1){
		pref = p2;
		jnref = jn(2, h);
	}
	else {
		pref = p1;
		jnref = jn(1, h);
	}

	double pnr, jnratio2;
	int i;
	
	for(i=3; i<30; i++) {
		fmin = (int)limit(i*fest*(1-freqwh), 0, num-1);
		fmax = (int)limit(i*fest*(1+freqwh), 0, num-1);
		if (fmin==fmax || !peak_search(amp, fmin, fmax, &pn, &tmp)) break;
		jnratio2 = jn(i, h) / jnref;
		jnratio2 *= jnratio2;
		pnr = pref * jnratio2;
		ptot += pnr;
		perror += fabs(pn-pnr);
	}
	//printf("stopped at harmonic %d\n", i);

	if (perror==0) return 0;

	*pinl = sqrt(perror/ptot);

	return 1;
}
