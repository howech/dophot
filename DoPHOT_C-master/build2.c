#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "newfits.h"
#include "readfits.h"
#include "undergnd_struct.h"

int main() {

    FILE* tempfile;
    int readerr = 0;
    char* rwa = "r";
   
    char* filein ;
    char* spt = "Enter input image name";
    char* fileout = "testout.fits";
    char tempstring[80];
  
    printf("%s : ",  spt);
    if (scanf("%s", tempstring) != 1){
                    printf("Error in file name.  Try again.\n");
    }
    tempfile = fopen(tempstring, rwa);
    filein = malloc((strlen(tempstring)+1)*sizeof(char));
    strcpy(filein, tempstring);
    printf( "%s: ", filein) ;

    fileout = "testout.fits";



    /* Open input picture.  */
     int nx, ny;
     int** big = rfits_(filein, &nx, &ny);          
     int nfast = undergnd_.NFAST = nx; 
     int nslow = undergnd_.NSLOW = ny;

     /*Write iimage back out. */
     newfits_(nx, ny, big, fileout, 0, "  ");
     
     return  1;
}
     
