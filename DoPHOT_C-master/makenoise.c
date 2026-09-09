#include <math.h>
#include "tuneable.h"
#include "search_struct.h"
#include "cast_arr.h"
#include "mini_mathlib.h"
#include "makenoise.h"

/* dophot subroutine converted to c void function 02-02-2012 */

void makenoise_(int** BIG, int** NOISE, int* NFAST_ptr, int* NSLOW_ptr)
{

     /* dereferecne pointers */
     int NFAST = *NFAST_ptr;
     int NSLOW = *NSLOW_ptr;
    
     /* rename common block variables */
     int ITOP = (int)tune3_.itop;
     int IBOT = (int)tune3_.ibot;
     float RNOISE = tune11_.rnoise;
     float EPERDN = tune11_.eperdn;
     int NBADBOT   = tune13_.nbadbot;
     int NBADTOP   = tune13_.nbadtop;
     int NBADLEFT  = tune13_.nbadleft;
     int NBADRIGHT = tune13_.nbadright;
 
     /* substance of subroutine begins here */
     int BADLINE, BADPIX;
     int JTOP, JBOT;
     float TEMP1, TEMP2;
     int I, J;

//     JTOP = min(ITOP, ( 32767));
//     JBOT = max(IBOT, (-32768));
     JTOP = min(ITOP, MAGIC);
     JBOT = max(IBOT, OBLITVAL);
     TEMP1 = (RNOISE/EPERDN)*(RNOISE/EPERDN);
     TEMP2 = 1.0f/EPERDN;

     for (I = 0; I < NSLOW; I++){
          BADLINE = ( (I <= (NBADBOT - 1)) || (I > (NSLOW - NBADTOP - 1)) );
          for (J = 0; J < NFAST; J++){
               if (BADLINE){
                    NOISE[I][J] = MAGIC;
               }
               else{
                    BADPIX = ( (J <= (NBADLEFT - 1)) || (J > (NFAST - NBADRIGHT - 1)) );
                    if (   (BADPIX) 
                        || (BIG[I][J] >= JTOP) 
                        || (BIG[I][J] <= JBOT) ){
                         NOISE[I][J] = MAGIC;
                    }
                    else{
                         if (BIG[I][J] > 0){
                              NOISE[I][J] = BIG[I][J]*TEMP2 + TEMP1;
                         }
                         else{
                              NOISE[I][J] = TEMP1;
                         }
                    }
               }
          } // end J (pix) loop
     } // end I (line) loop


}

// Variant: compute noise for DN data using pre-computed variance
// Variance should be in electrons², converts to DN units
void makenoise_from_variance_(
     float** variance,      // Input: variance in electrons²
     int** noise,           // Output: noise in DN
     int* ndx, int* ndy)
{
     int NFAST = *ndx;
     int NSLOW = *ndy;
     int NBADBOT   = tune13_.nbadbot;
     int NBADTOP   = tune13_.nbadtop;
     int NBADLEFT  = tune13_.nbadleft;
     int NBADRIGHT = tune13_.nbadright;
     float EPERDN = tune11_.eperdn;

     float TEMP = 1.0f / EPERDN;  // Convert from electrons to DN
     int BADLINE, BADPIX;
     int JTOP = (int)tune3_.itop;
     int JBOT = (int)tune3_.ibot;
     int I, J;

     for (I = 0; I < NSLOW; I++){
          BADLINE = ( (I <= (NBADBOT - 1)) || (I > (NSLOW - NBADTOP - 1)) );
          for (J = 0; J < NFAST; J++){
               if (BADLINE){
                    noise[I][J] = MAGIC;
               }
               else{
                    BADPIX = ( (J <= (NBADLEFT - 1)) || (J > (NFAST - NBADRIGHT - 1)) );
                    if (BADPIX){
                         noise[I][J] = MAGIC;
                    }
                    else{
                         // variance in electrons², convert to DN
                         if (variance[I][J] > 0.0f){
                              noise[I][J] = (int)(sqrtf(variance[I][J]) * TEMP);
                         } else {
                              noise[I][J] = 1;  // Floor value
                         }
                    }
               }
          }
     }
}
