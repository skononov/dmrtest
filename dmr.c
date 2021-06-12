#include <math.h>

extern int peak_search(const double *amp, int fmin, int fmax, double *ppwr, double *pfpeak);

static const double Fs = 120.;
static const double Fb = 0.648/Fs;
static const int FFTlen = 128;

void upd_br(const double*a, double *ba, double *pos, int cpos)
{
    double p[4];
    int jl;

    p[0]=(a[5]-a[0])*(a[5]-a[0])+(a[4]+a[1])*(a[4]+a[1]);      //+648 dibit=0
    p[2]=(a[5]+a[0])*(a[5]+a[0])+(a[4]-a[1])*(a[4]-a[1]);      //-648 dibit=2
    p[1]=(a[7]-a[2])*(a[7]-a[2])+(a[6]+a[3])*(a[6]+a[3]);      //+1944 dibit=1
    p[3]=(a[7]+a[2])*(a[7]+a[2])+(a[6]-a[3])*(a[6]-a[3]);      //-1944 dibit=3

    if (p[0]>p[1] && p[0]>p[2] && p[0]>p[3]) jl=0;
    else if (p[1]>p[2] && p[1]>p[3]) jl=1;
    else if (p[2]>p[3]) jl=2;
    else jl=3;

    double g = p[jl]/(p[0]+p[1]+p[2]+p[3]-p[jl]+0.000001);
    
    if (g>ba[jl]) {
        ba[jl] = g;
        pos[jl] = cpos+FFTlen/2;
    }
}

int dmr_analysis(const int *I, const int *Q, int num, double *deltaA, double *deltaF)
{

    double bestamp[4] = {0, 0, 0, 0};    //0,2 - 648 Hz, 1,3 - 1944 Hz
    double bestpos[4];

    double a[8] = {0, 0, 0, 0, 0, 0, 0, 0};


    for(int i=0; i<FFTlen; i++) {
        a[0] += I[i]*sin(2*M_PI*Fb*i/Fs);
        a[1] += I[i]*cos(2*M_PI*Fb*i/Fs);
        a[2] += I[i]*sin(2*M_PI*3*Fb*i/Fs);
        a[3] += I[i]*cos(2*M_PI*3*Fb*i/Fs);
        a[4] += Q[i]*sin(2*M_PI*Fb*i/Fs);
        a[5] += Q[i]*cos(2*M_PI*Fb*i/Fs);
        a[6] += Q[i]*sin(2*M_PI*3*Fb*i/Fs);
        a[7] += Q[i]*cos(2*M_PI*3*Fb*i/Fs);

        upd_br(a, bestamp, bestpos, 0);
    }

    for(int i=0; i<num-FFTlen; i++) {
        a[0] += I[(i+FFTlen)]*sin(2*M_PI*Fb*(i+FFTlen)/Fs) - I[i]*sin(2*M_PI*Fb*i/Fs);
        a[1] += I[(i+FFTlen)]*cos(2*M_PI*Fb*(i+FFTlen)/Fs) - I[i]*cos(2*M_PI*Fb*i/Fs);
        a[2] += I[(i+FFTlen)]*sin(2*M_PI*3*Fb*(i+FFTlen)/Fs) - I[i]*sin(2*M_PI*3*Fb*i/Fs);
        a[3] += I[(i+FFTlen)]*cos(2*M_PI*3*Fb*(i+FFTlen)/Fs) - I[i]*cos(2*M_PI*3*Fb*i/Fs);
        a[4] += Q[(i+FFTlen)]*sin(2*M_PI*Fb*(i+FFTlen)/Fs) - Q[i]*sin(2*M_PI*Fb*i/Fs);
        a[5] += Q[(i+FFTlen)]*cos(2*M_PI*Fb*(i+FFTlen)/Fs) - Q[i]*cos(2*M_PI*Fb*i/Fs);
        a[6] += Q[(i+FFTlen)]*sin(2*M_PI*3*Fb*(i+FFTlen)/Fs) - Q[i]*sin(2*M_PI*3*Fb*i/Fs);;
        a[7] += Q[(i+FFTlen)]*cos(2*M_PI*3*Fb*(i+FFTlen)/Fs) - Q[i]*cos(2*M_PI*3*Fb*i/Fs);

        upd_br(a, bestamp, bestpos, i);
    }


    for(int i=0; i<4; i++) {
        if(bestpos[i] < FFTlen/2+1) bestpos[i] = FFTlen/2+1;
        if(bestpos[i] > num-FFTlen/2-1) bestpos[i] = num-FFTlen/2-1;
    }


    /*for each i (0..3) 
    do FFT for I and Q for    bestpos[i]-FFTlen/2 .... bestpos[i]+FFTlen/2-1
    PeakSrch(const double *amp, 648*0.9 Hz, 648*1.1 Hz, pwr, fpeak) for i = 0 & 2
    PeakSrch(const double *amp, 3*648*0.9 Hz, 3*648*1.1 Hz, pwr, fpeak) for i = 1 & 3

    find fabs(fpeak - 648(648*3)) and diplay it

    find max_sqrt(pwr) and min_sqrt(pwr)

    dislay 2*(max_sqrt(pwr)-min_sqrt(pwr))/(max_sqrt(pwr)+min_sqrt(pwr))
    */



}