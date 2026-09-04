;+
; NAME:
;	STARSWT
; PURPOSE:
;	Front end to REGRESS to fit the function :
;		DEPEND = const + coeff(0)*D0 + ... + coeff(NTERMS-1)*Dn
;           using measurement error estimates for dependent variable
; CATEGORY:
;	Astronomical data processing
; CALLING SEQUENCE:
;	starswt, const, coeff, depend, mserr, d0 [,d1, d2, ..., d7]
; INPUTS:
;	DEPEND 	= Dependent variable array of NPOINTS
;	    D0  = Independent variable.  It can be either a (NTERMS,NPOINTS) 
;		  array, in which case it contains all of the independent
;		  variables, or it can be the first (NPOINTS) vector
;		  containing the first independent variable, with D1 .. D7
;		  containing the others.  In the first case, D0(0,*) = D0,
;		  D0(1,*) = D1, etc.  In either case, there must be NTERMS
;		  independent variables.
;         MSERR = Standard error in DEPEND (variable array, same length as 
;                 DEPEND
; OPTIONAL INPUT PARAMETERS:
;	D1...D7 = Independent variables, each an vector of NPOINTS.
; OUTPUTS:
;	  CONST = Constant term.
;	  COEFF = Vector of NTERMS elements.
; OPTIONAL OUTPUT PARAMETERS:
;	NONE
; COMMON BLOCKS:
;	NONE
; SIDE EFFECTS:
;	The standard deviation for each coefficient is displayed
; RESTRICTIONS:
;	NONE
; MODIFICATION HISTORY:
;	Written by John Krist, STScI, April 23, 1991
;-
pro starswt,const,coeff,depend,mserr,d0,d1,d2,d3,d4,d5,d6,d7

numpars = n_params(0)
if ( numpars lt 5 or numpars gt 12 ) then begin
   print,'Call is : starswt, const, coeff, depend, mserr, d0 [,d1,...,d7]'
   return
endif

s = size(d0)
if ( s(0) eq 2 ) then begin	;-- if D0 is 2-d, it contains the ind. vars
     nterms = s(1)
     npoints = s(2)
     X = D0
endif else begin		;-- Have to put all ind. vars into 2-d array
     nterms = numpars - 4
     npoints = n_elements(d0)
     X = fltarr(nterms,npoints)
     for i = 0, nterms - 1 do begin
         command = 'X(' + string(i) + ',*) = d' + $
	    strcompress(string(i),/REMOVE_ALL)
         status = execute(command)
         if ( not status ) then begin
	    print,'Error loading arrays'
	    return
         endif
     endfor
endelse

w = replicate(1.,npoints)
measure_errors = mserr
;
;coeff = regress(X,depend,w,yfit,const,sigma,ftest,r,rmul,chisq)

;coeff = regress(X,depend,measure_errors,yfit,const,sigma,ftest,r,rmul,chisq)

;
coeff = regress(X,depend,CHISQ=chisq,CONST=const,CORRELATION=corr,/DOUBLE,FTEST=ftest,MCORRELATION=mcorr,MEASURE_ERRORS=mserr,SIGMA=sigma,STATUS=status,YFIT=yfit)
;

print,'Const = ',const
print,'Coeff = ',coeff
print,'Chisq (from REGRESS)  = ',chisq
print,'Stdev = ', sqrt(total((yfit-depend)^2))/npoints
print, 'Chisq (from residuals) = ', total( ((yfit-depend)^2) / (mserr^2) ) / (npoints-(1+n_elements(coeff)))
return
end
