PRO XYIMG,ximg,yimg,width,height
;
nargs = N_PARAMS(0)
IF nargs LT 1 THEN BEGIN
	PRINT,'>>> HELP for XYIMG,ximg,yimg,width,height
	PRINT,' I produce (square) ramp images in X and Y.
	PRINT,'ximg,yimg - Returned ramp image arrays.
	PRINT,'width,height - Dimensions of image in pixels. [Dft=100]'
	PRINT,'>>> End of Help.'
	RETURN
	ENDIF
IF nargs LT 3 THEN width = 100
IF nargs LT 4 THEN height = width
;
;-----------------------------------------------------------------------
;	Allocate a ramp vector with center at zero.
;
xrow = FINDGEN(width) - width/2
;
;-----------------------------------------------------------------------
;	Through matrix multiplication with a unit vector, build the
;	Cartesian grid for X.
;
ximg = xrow # (INTARR(width)+1)
;-----------------------------------------------------------------------
;	The Y grid is simply the transpose of the X grid.
;
yimg = TRANSPOSE(ximg)
;
RETURN
END
