
#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include "logh.h"
#include "tuneable.h"
#include "aperlist_struct.h" //yes
#include "estuff_struct.h"
#include "changed_struct.h"
#include "probpass_struct.h"
#include "starlist_struct.h"  // yes
#include "search_struct.h"   // yes   
#include "subraster_struct.h"
#include "crudestat_struct.h"
#include "fitarrays_struct.h"
#include "eoff_struct.h"
#include "unitize_struct.h"
#include "passimp_struct.h"
#include "fixpass_struct.h"
#include "galpass_struct.h"
#include "addobj_struct.h"
#include "model_struct.h"
#include "cast_arr.h"
#include "mini_mathlib.h"
#include "transmask.h"
#include "offpic.h"
#include "toofaint.h"
#include "empiricals.h" //contains oneemp
#include "guess.h"
#include "fillerup.h"
#include "chisq.h"
#include "onefit.h"
#include "elarea.h"
#include "probgal.h"
#include "add_analytic_or_empirical_obj.h"
#include "parupd.h"
#include "errupd.h"
#include "impaper.h"
#include "pgauss.h"
#include "improve.h" 
#include "onefit.h"


//#define napple 5
//#define npmax 100
//#define nsmax 100
//#define napmax 100
//#define magic 2147483547
//#define eperdn 1.0
//#define skyguess 1.0
//#define rnoise 1.0
//#define itop 1.0
#define aperrmax 1.0
#define apmax 8.0
#define apskymax 1.0
#define apskymin 1.0
//#define nbadleft 0
//#define nbadright 0
//#define nbadbot 0
//#define nbadtop 0
//#define napertures 5


/* void addstar(void (*onestar)(), int** BIG, int** noise, int nfast, int nslow, float starpar[], int iadd); */

void apcorr2(double (*ONESTAR_7P)(short int*, float*, float*, int*, int*), int** BIG, int** NOISE, int* NFAST_ptr, int* NSLOW_ptr);

    int nfast = *NFAST_ptr;
    int nslow = *NSLOW_ptr;
    //
    int nstot = search_.nstot;
    float thresh = search_.thresh;
    float** starpar = starlist_.starpar;
    int*  imtype = starlist_.IMTYPE;
    float**  shadow = starlist_.shadow;
    float**  errshad = starlist_.shaderr;
    float**   apple = aperlist_.apple;
    float skyguess = tune1_.skyguess;
    float eperdn = tune11_.eperdn;
    float rnoise = tune11_.rnoise;
    int napmax = 5000;
    float apcorr[napmax], apsum[napmax], aparea[napmax], trimx[10000];
    int lcnt;
    float abflatlim = 0.05; 
    float stepsky, flatg, flatgold;
    int iunit = 30;
    int ierr;
    float area=1.0, unc=1.0
    

    area = 3.142*apmax*apmax;
    unc = float (sqrt(skyguess*eperdn + rnoise*rnoise) / sqrt(area) );
    //    stepsky = stepsky * 0.2;
//   stepsky = stepsky / eperdn;     // make it in DN
//    printf("stepsky = %f\n", stepsky);

    return ;
}


      /*
    for (int i = 1; i <= nstot; i++) {
        if (imtype[i] != 1 && imtype[i] != 11) continue;
        if (starpar[2][i] > itop) continue;
        if (apple[4][i] > aperrmax) continue;

        float xcenter = starpar[3][i];
        float ycenter = starpar[4][i];
        int ixcenter = (int)xcenter;
        int iycenter = (int)ycenter;

        int iapsize = fmax((int)apskymin, (int)apmax);
        int ixlow = ixcenter - iapsize;
        if (ixlow <= nbadleft) continue;
        int ixhigh = ixcenter + iapsize + 1;
        if (ixhigh > nfast - nbadright) continue;

        int iylow = iycenter - iapsize;
        if (iylow <= nbadbot) continue;
        int iyhigh = iycenter + iapsize + 1;
        if (iyhigh > nslow - nbadtop) continue;

        addstar(onestar, BIG, noise, nfast, nslow, starpar[1], 1);

        float skywt = 0.0;
        float skysum = 0.0;
        float skyct = 0.0;
        float skysum_nwt = 0.0;

        for (int ii = 1; ii <= napertures; ii++) {
            aparea[ii] = 0.0;
            apsum[ii] = 0.0;
        }

        for (int jy = iylow; jy <= iyhigh; jy++) {
            for (int jx = ixlow; jx <= ixhigh; jx++) {
                int badpix = noise[jx][jy] >= magic;

                float x = (float)jx;
                float y = (float)jy;
                float dist = sqrt((xcenter - x) * (xcenter - x) + (ycenter - y) * (ycenter - y));
                float rdist = dist - 0.5;

                for (int k = 1; k <= napertures; k++) {
                    float app = ((float)k / (float)napertures) * apmax;
                    float fractn = fmax(0.0, fmin(1.0, app - rdist));
                    if (fractn > 0.0 && badpix) continue;
                    aparea[k] += fractn;
                    apsum[k] += fractn * BIG[jx][jy];
                }

                float fractnout = fmax(0.0, fmin(1.0, apskymax - rdist));
                rdist = dist + 0.5;
            }
        }
    }
}

          */
