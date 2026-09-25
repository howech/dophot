#ifndef FITTING_MATRICES_STRUCT_H
#define FITTING_MATRICES_STRUCT_H

// having grown weary of the mallocs
#ifndef DOPHOT_DEFINE_GLOBALS
extern
#endif
struct{
     float** c_mat; //[npmax+1, npmax+1] +1s because chisq ancient
     float**    lu; //[npmax+1, npmax+1]
     float** b_mat; //[npmax+1, npmax+1]
     float* c_list; //[npmax]
     float*      v; //[mmax]
     float*   vsol; //[mmax]
     int*    index; //[mmax]
}fitting_matrices_;

#endif
