#include <math.h>
#include "logh.h"
#include "tuneable.h"
#include "starlist_struct.h"
#include "aperlist_struct.h"
#include "cast_arr.h"
#include "mini_mathlib.h"
#include "elarea.h"
#include "impaper.h"
#include <stdio.h>
#include <stdlib.h>
#include "estuff_struct.h"

/* dophot subroutine converted to c void function 01-29-2012 */
/* 
c
c  This is an independent way of calculating the difference between the
c  aperture and fit mags.  Large values for abs(APPLE[i][2]) for STAR 
c  objects will indicate problems.  This value equals the difference 
c  between the sky and fit mags.
c
*/

void baperts_(int** BIG, int** NOISE, int* NFAST_ptr, int* NSLOW_ptr, int* K_ptr, char* result)
{

     /* dereference pointers */
     int NFAST = *NFAST_ptr; 
     int NSLOW = *NSLOW_ptr; 
     int K     = *K_ptr    ;      
     /* shortening names of common block variables for easier use */
     float* ARECT = tune2_.arect;
     int    lverb = tune14_.lverb;
     float** STARPAR = starlist_.starpar;
     float** APPLE = aperlist_.apple;
     
     /* substance of subroutine begins here */
     double SUMAN, SUMBN, VARA, VARB;
     double STARLUM, RATLUM;
     float skywt, skysum, skyct, skysum_nwt ;
     float SUMB0, SUMB1 ;
     int I, IHI, ILO, J, JHI;
     float TXA, TXB, TYA, TYB;
     float XA, XB, YA, YB, XYA, XYB;
     float ABJYC, ABIXC, DXY;
     int badpix ; //0 for false, 1 for true

     float eperdn = tune11_.eperdn;
     float rnoise =  tune11_.rnoise;
     double  skrms, skvar ;
     float  apradstep;  
     int napertures = 8;
     float  apradmax = 24. ; 
     int napradmax ;  
     float aperrmax = 0.1;
     float  apcorr[napertures],apsum[napertures], aparea[napertures], aprad[napertures], trimx[10000];
     int m, ii, jj, nn;
     int it;
     int jx, jy;
     float x,  y, dist, rdist;
     float stepsky, apskymin, apskymax;
     float  app, fractn, fractnin, fractnout, fracts;
     int lcnt ;
     float abflatlim, flatg, flatgold, delstep, totcnts;
     float fvalue, fdum;
     //     char result[121];  
     int len ;
      
     apradstep = apradmax/napertures;
     napradmax = round(apradmax);

     //
     

 
     /* changed indices */
          double XC = STARPAR[K-1][2];
          int ixcenter = round(XC);  
          double YC = STARPAR[K-1][3]; 
          int iycenter = round(YC);
          double skyguess = STARPAR[K-1][0];    
          int* ITYPE = starlist_.IMTYPE;
          int imtype = ITYPE[K-1];
          if( (imtype != 1) && (imtype != 11) ){
//	    	    printf("Object not of type 1: id, type:  %5d %d\n", K-1, imtype );
                    len = sprintf(result, "") ;
	    goto  DONE;  
	  }
          if( (XC <= (apradmax + tune13_.nbadleft + 3.)) || (XC >= (NFAST - apradmax - tune13_.nbadright - 2.)) ){
//                 printf("Object too close to border: %5d\n",  K);
                    len = sprintf(result, "") ;
            goto DONE;
	  }
          if( (YC <= (apradmax + tune13_.nbadbot +3.)) || (YC >= (NFAST - apradmax - tune13_.nbadtop - 2.)) ) {
//	    	    printf("Object too close to border: %5d\n",  K);
                    len = sprintf(result, "") ;             
            goto DONE;
          } 

     skvar = skyguess*eperdn + rnoise*rnoise;  //  in electrons
     skrms = sqrt(skvar)/eperdn;   // in DN
     stepsky = (float) skrms;
     stepsky = 0.2*stepsky;
   
     
     skywt = 0.0;
     skysum = 0.0; 
     skyct = 0.0;
     skysum_nwt = 0.0;
     it = 0;
   
	for (ii =0; ii < napertures; ii++){
	  aparea[ii] =0.0;
          apsum[ii] = 0.0;
        } 

	/*  Loop over pixels  */
        badpix = 0;
        it = 0;
        for (jy=iycenter-napradmax-1; (jy < iycenter+napradmax);  jy++){
              for (jx = ixcenter-napradmax-1; (jx < ixcenter+napradmax); jx++) {

                      if( NOISE[jy-1][jx-1] >= MAGIC ) {
		            badpix = 1;
		      }
		    
		    x = (float) jx;
                    y = (float) jy;
		    dist =  sqrt( (XC - x)*(XC - x) + (YC-y)*(YC-y) )  ;
		    rdist = dist - 0.5;

		    fractn = 0.f ;
 				 for ( nn = 0;  nn < napertures; nn++){
				       app  = ((float) nn + 1.)*apradmax / ( (float) napertures );  
                                        fractn = fmin(1.0f, app-rdist);
                                        fractn = fmax(0.0f,  fractn);
					//				   printf(" debug rdist --> app:  %f  rdist:  %f   fractn  %f\n ",  app, rdist, fractn);  //
                                        if(  (fractn > 0.0 && badpix != 0)  ) {
					  len = sprintf(result, "") ;					 
					  goto DONE ;
                                        }
					aparea[nn] = aparea[nn] + fractn;
					apsum[nn] = apsum[nn] + fractn*( (float)(BIG[jy-1][jx-1]) ) ; 
				   }
				 /*  Now collect sky pixels (which are taken to be in largest 3 apertures) and stuff values in to trimx */
                                   apskymax = (float)napradmax;
				   fractnout = fmin(1.0f, apskymax-rdist);
                                   fractnout = fmax(0.0f, fractnout);
                                   rdist = rdist + 0.5;
                                   apskymin = apradmax* (float)(napertures-3)/( (float)napertures );
				   fractnin = fmin(1.0f, rdist-apskymin);
                                   fractnin = fmax(0.0f, fractnin);
                                   fracts = fmin(fractnin, fractnout);
                                   if( (fracts > 0.) && (badpix == 0) ){
				     trimx[it] = (float) BIG[jy-1][jx-1];
				         it = it +1;
				   }
                                   
               }     /* close X loop */
	}     /*   close Y loop   */
     

	//	printf("Got this far!! : id, skyguess, skrms, stepsky : %4d %f %f %f\n",  K, skyguess, skrms, stepsky);
	
	float sumsky,  avsky, skysig, trimmed[1000], tsky ;
        double sumskysq ;
        sumsky = 0.f ;
        sumskysq = (double) (0.0) ;
        avsky = 0.f ;
	for (  jj =0 ; jj < it; jj++ ) {      // only the first it items in trimx matter...   the rest should be zero or fossils //
	      sumsky += trimx[jj] ;
	      sumskysq  += (double)trimx[jj]*(double)trimx[jj] ;
	}

	//	float* rtrim[it];        
        //for(jj = 0;  jj < it ; jj++) {
	//	  rtrim[jj] = trimx[jj];
	//	} 
        
	//	qsort(rtrim, it, 4,  compare_float);	
	//        for( ii = 0; ii < it; i++){  
	//	  printf("%.f ", rtrim[ii]);   
	  //       }

        float skyvar; 
	avsky = sumsky / ( (float) it) ;
	skyvar = (sumskysq/( (float) it )) -  avsky*avsky ;
	skysig = sqrt( skyvar ) ;
	int kk;
        kk = 0;
        

        sumsky = 0.;  
        sumskysq = 0.; 
        for( ii = 0;  ii < 1000; ii++) {
	      trimmed[ii] = 0.0f ;
	}
     
	for (  jj =0 ; jj < it; jj++ ) { 
	    if(  (sqrt( trimx[jj] - avsky)*( trimx[jj] - avsky) )  <  5.*skysig  ) {
	          trimmed[kk] = trimx[jj];
		  sumsky += trimmed[kk] ;
                  sumskysq += trimmed[kk]*trimmed[kk] ;  
                  kk += 1 ;
	      } 
	}

 	avsky = sumsky / ((float) kk) ;      // kk is no. of sky pixels in trimmed, and that went into avsky in loop above //
        skyvar = (sumskysq/( (float) kk )) -  avsky*avsky ;  
        skysig  = sqrt(skyvar) ;
   
          //    now calculate fluxes and mags for each of the apertures:  //
            
	//	    for (  nn = 1;  nn < napertures ; nn++ ) {
                  

	/***   Now do the sky loop 
	 .......only works if napertures >= 7   */

	float slope;
        float slopeold ;

	lcnt = 0;
        delstep = 0.0;
        flatgold = 10.;
        slopeold = 0.0f;
        slope = 0.0f;
	abflatlim = 0.005f;

        tsky = avsky;
SLOOP:
        if(lcnt != 0) {
	  flatgold = flatg;
        }
        fvalue = 99.999f;
        fdum = 0.0f;
        for( m=0; m < napertures; m++) {
	      totcnts = apsum[m] - tsky*aparea[m] ;
	       if( totcnts <= 0.){
		 apcorr[m] = 99.99f ;
	         if( m > 0) {
		     len = sprintf(result, "") ;             
                     goto DONE ;       /// object of no further use
		 }    
               } else {
		 fdum = (float) (-2.5*log10((double) totcnts) );  /* note this is really the  apmag -- being held for now in apcorr */
                 apcorr[m] = fdum;
	       } 
	}     
	
	if(napertures > 7 && lcnt <= 250) {
	    slope = 3*apcorr[napertures-1]  + apcorr[napertures-2 ]  - apcorr[napertures-3] - 3*apcorr[napertures-4];
	    slope = slope/10.;   // This is the best fit (least-squares) slope to the last 4 points of teh growth curve //
	} 

	     /*	  flatg = (apcorr[napertures-1] +apcorr[napertures-2] +apcorr[napertures-3])/3   - apcorr[napertures-4] ;
	  delstep = abs(flatgold) - abs(flatg) ;
	  //          printf(" for debugging: apcorr7 %.2f apcorr4 %.2f  tsky  %.2f\n",  apcorr[7],  apcorr[4], tsky) ;  
	  if( (flatg <  -1.*abflatlim) || (  delstep > 0.0 && flatg < 0.0 ) ) {    /* raise sky value */
	if(slope > abflatlim) {
	        if(slopeold < 0.) { 
		  stepsky = stepsky/2. ;     /* slope reversed sign, so search in smaller steps...   */
		 }             
		tsky = tsky - stepsky ;      /* +ve slope means larger aperts have fainter mags, so subtract sky */
		//	     printf("slope, slopeold, stepsky: %.3f,   %.3f,  %.3f\n", slope, slopeold, stepsky)	;
             lcnt = lcnt + 1 ;
             slopeold = slope ;
             if(lcnt > 250) {         //  not converging within acceptable limits... quit on object
	       //	         printf(" Reached 250 steps without converge..\n")      ;				 		  
		  len = sprintf(result, "") ;					 
		  goto  DONE ;
	      }  
	      goto SLOOP ;
	  }	 
	if (slope < -1.*abflatlim)  {     /* lower sky value */
	        if(slopeold  >= 0.) { 
		  stepsky = stepsky/2. ;     /* slope reversed sign, so search in smaller steps...   */
		 }             
	     tsky = tsky + stepsky ;         /* -ve slope means larger aperts have brighter mags, so add sky */
	     //	     printf("slope, slopeold, stepsky: %.3f,  %.3f,  %.3f\n", slope, slopeold, stepsky)	;
             lcnt = lcnt + 1 ;
             slopeold = slope ;
             if(lcnt > 250) {         //  not converging within acceptable limits... quit on object
		  len = sprintf(result, "") ;
		  //                  printf(" Reached 250 steps without converge..\n")    ;			 		  
		  goto  DONE ;
	     }  
		goto SLOOP ;
	  }
	  /* if neither case,  (either slope == 0. or abs(slope) <= abbflatlim then "goldilocks" reached : no further iteration needed */
	/*  Test for even flatness , or throw it out : */
	/*	if( ( abs(apcorr[napertures-1] - apcorr[napertures -2]) >  0.02 )  ||  ( abs(apcorr[napertures-3] - 
										     apcorr[napertures - 4]) >  0.02 ) ) {
 		  len = sprintf(result, "") ;					 		  
		  goto  DONE ;
		  }      */
	/*  End of skyloop */


 //	printf("  object  %4d  at  %f  %f  has avsky  %f  skysig %f good sky pixels  %d\n",  K, XC, YC, avsky, skysig, kk ) ;
//        for( ii = 0;  ii < napertures; ii++) {
//	  printf(" %f  ", apcorr[ii]) ;
//	}
//        printf(" tsky:  %.2f     lcnt:  %d\n", tsky, lcnt) ;

         len = sprintf(result, "%8d  %10.2f  %10.2f",  K, XC, YC) ;
         for( m =0; m < napertures; m++)  {
			   len  += sprintf(result + len,  "%9.3f", apcorr[m]) ;
        }
	len  += sprintf(result + len, "%10.2f", tsky); 
 /*	 Used for watching results -- turned off for speed: 
	 printf(" %d   %s\n", len, result) ;     */


       goto DONE;
     
     printf("How did I  get here?\n");

 DONE:     
     
		 m = m + 1 ;
     

     //      printf("Done with aperts pass\n");

}







//int compare_float(const void *a, const void *b) {
//    if (*(float*)a < *(float*)b) return 1;
//    if (*(float*)a > *(float*)b) return -1;
//    return 0;
//}
