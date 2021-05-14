

static double gooderr;
typedef struct pll_set {
	int R;
	int MOD;
	int FRAC;
	int INT;
	int outdiv;
	int BandDiv;
	double freq;
	double err;
} pll_set;


void GetAppr(double val, int  *pr, int *qr, int dmax){
	int a=(int) val;
	val-=a;
	int p1,q1,p2,q2,p,q;
	p2=1; q2=0;
	*pr=p1=a; *qr=q1=1;
	p=q=1;
	
	while (1)
	{
		a=(int)((double)1./val);
		val=(double)1./val-a;
		p=a*p1+p2;
		q=a*q1+q2;
		if(p<=0 || q<=0) break;
		if(q<=dmax) {
			*pr=p;
			*qr=q;
		}
		else break;
		if(val<=0) break;
		p2=p1;
		p1=p;
		q2=q1;
		q1=q;
	}
}



int comp_set (const pll_set *a, const pll_set *b){
	if((*a).err<gooderr && (*b).err<gooderr){
		if((*a).MOD>(*b).MOD) return 1;
		else if((*a).MOD<(*b).MOD) return 0;
		else return((*a).err<(*b).err);
	}
    return((*a).err<(*b).err);
}



//setfreq - desired frequency in Hertz
//num - pll settings number, 0 - the best, num<=10

int pll(unsigned int setfreq, pll_set *resset, int num,
unsigned int Rmin,
unsigned int Rmax,
unsigned int INTmax,
unsigned int INTmin,
unsigned int MODmax,
unsigned int fref,
double vcomax,
double vcomin,
double gooderrin
){
	const int arrs=10;
	gooderr=gooderrin;
	pll_set sets[arrs];
	
	for(int i=0; i<arrs; i++) sets[i].err=3*gooderr;

	pll_set locset, tls;

	double val=setfreq/(fref*(double)1000000);
	double fdf;
	
	int p, q, il, frac;
	uint64_t vallong;
	int apoint=0, minpos;
	

	for(int odiv=1; odiv<=16; odiv*=2){
		if(odiv*(setfreq*(double)1.0)>=vcomin*1000000 && odiv*(setfreq*(double)1.0)<=vcomax*1000000){
				for(int rc=Rmin; rc<=Rmax; rc++){
					frac=1;
					
					//check int mode
					vallong=(uint64_t)setfreq*(uint64_t)rc*(uint64_t)odiv;
					if(vallong%((uint64_t)fref*1000000)==0){
						il=vallong/(fref*1000000);
						if(il>=INTmin && il<=INTmax){
							frac=0;
							locset.INT=il;
							locset.MOD=MODmax;
							locset.FRAC=0;
							locset.R=rc;
							locset.outdiv=odiv;
							locset.freq=setfreq;
							locset.err=0;
							locset.BandDiv=(int)(fref/(double)0.1/rc);
							if(locset.BandDiv==0) locset.BandDiv=1;
							if(locset.BandDiv>255) locset.BandDiv=255;
							
							minpos=0;
							for(int i=0; i<apoint; i++){
								if(comp_set(&locset, &sets[i])) break;
								minpos++;
							}
							for(int i=minpos; i<apoint; i++){
								tls=sets[i];
								sets[i]=locset;
								locset=tls;
							}
								
							if(apoint<arrs) {
								sets[apoint]=locset;
								apoint++;
							}
						}
					}
					if(frac){
					GetAppr(val*odiv*rc, &p, &q, MODmax);
					if(q<=MODmax && q>=2){
						il=p/q;
						if(il>=INTmin && il<=INTmax){
							locset.INT=il;
							locset.MOD=q;
							locset.FRAC=p%q;
							locset.R=rc;
							locset.outdiv=odiv;
							locset.freq=(fref*(double)1000000.*p)/q/rc/odiv;
							fdf=locset.freq-setfreq;
							if(fdf<0) fdf=-fdf;
							locset.err=fdf;
							locset.BandDiv=(int)(fref/(double)0.1/rc);
							if(locset.BandDiv==0) locset.BandDiv=1;
							if(locset.BandDiv>255) locset.BandDiv=255;

							minpos=0;
							for(int i=0; i<apoint; i++){
								if(comp_set(&locset, &sets[i])) break;
								minpos++;
							}
							for(int i=minpos; i<apoint; i++){
								tls=sets[i];
								sets[i]=locset;
								locset=tls;
							}
								
							if(apoint<arrs) {
								sets[apoint]=locset;
								apoint++;
							}
						}
					}
					}
				}
		}
	}

	if(num>apoint-1) (*resset)=sets[apoint-1];
	else (*resset)=sets[num];

	return apoint;
}

//pll_num =0  - MAIN PLL, 1 - EMI PLL



void SetFreq(int pll_num, unsigned int setfreq, int maino, int auxo, int mltd, int mainpow, int auxpow){
	
	pll_set resset;	
	pll(setfreq, &resset, 0, 1, 1023, 65535, 23, 4095, 5, 4400, 2200, 50);
	uint32_t R[6];
	
	int divdeg=-1;
	while(resset.outdiv){
		resset.outdiv=resset.outdiv>>1;
		divdeg++;
	}
	
	int nm;
	if(resset.FRAC==0) nm=1;
	else nm=0;
	//load reg val
	R[0]=(resset.FRAC<<3) + (resset.INT<<15);
	R[1]=1 + (resset.MOD<<3) + (1<<15);
	R[2]=2 + (3<<6) + (nm<<8) + (15<<9) + (resset.R<<14) + (1<<24) + (6<<26);
	R[3]=3 + (156<<3);
	R[4]=4 + (mainpow<<3) + (maino<<5) + (auxpow<<6) + (auxo<<8) + (mltd<<10) + (resset.BandDiv<<12) + (divdeg<<20) + (1<<23);
	R[5]=5+(1<<22) + (3<<19);
	
	//load registers from 5 to 0 to PLL

}


