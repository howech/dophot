;+
; NAME:
;	WritedopX_eposnn
; PURPOSE:
;	Write a DOPHOT output file (text), BUT repeats X and Y pos as extra 
;       columns at end, and calculates near neighbor contamination and
;       inserts in <apminfit> column
; CALLING SEQUENCE:
;      writedop_epos, filename, x, y, mag, magerr, id, type, sky,
;      apmag, apmagerr, apsky, xfwhm, yfwhm, tilt, exten, apminfit, 
;      ERROR = ERROR
; INPUTS:
;	filename  =  String containing name of file (default ext is .DOP).
;	       x, y  :  X, Y coordinates
;	mag, magerr  :  Magnitude and error
;	         id  :  Vector containing object id numbers
;	       type  :  Vector containing object type codes
;	        sky  :  Sky values
;      xfwhm, yfwhm  :  Stellar or galaxy FWHM in each direction
;	       tilt  :  Tilt of galaxy.
; KEYWORD PARAMETERS:
;	ERROR  =  Returns 1 if error occurred, else 0.
; OUTPUTS:
; PROCEDURE:
;	Calls the FORTRAN writedop program (in VARI.EXE).
; MODIFICATION HISTORY:
;	Written by John Krist.
;-
pro writedopX_eposnn, filename, x, y, mag, magerr, id, type, sky,apmag, apmagerr, $
   apsky, xfwhm, yfwhm, tilt, exten, apminfit, ERROR = ERROR

on_error, 2

if ( n_params(0) lt 11 ) then begin
   print,'Call is : writedop_all, filename, x, y, mag, magerr, id, type,'
   print,'     sky, apmag, apmagerr, apsky, xfwhm, yfwhm, tilt, exten, apminfit,  [, ERROR=ERROR]'
   ERROR = 1
   return
endif

n = n_elements(x)
help, n
;
;
print, ' Doing near neighbor contam within half-max radius '
t7 = where(type eq 7 or type eq 17)
rad = max([xfwhm(t7), yfwhm(t7)])
;
nearobj, x, y, mag, type, rad, apminfit
print, ' Done doing near neighbor contam '
;
;
     get_lun, uu
     openw, uu, filename, error=error
       if(error ne 0) then begin
         print, 'Error opening file: ', filename
         print, !err_string
         error = 1
         return
       endif
;
     all = fltarr(n,17)
   help, all
     all(*,0) = float(id)
     all(*,1) = type  
     all(*,2) = x
     all(*,3) = y
     all(*,4) = mag
     all(*,5) = magerr
     all(*,6) = sky
     all(*,7) = xfwhm
     all(*,8) = yfwhm
     all(*,9) = tilt
     all(*,11) = apmag
     all(*,12) = apmagerr
     all(*,13) = apsky
     all(*,10) = exten
     all(*,14) = apminfit
     all(*,15) = x
     all(*,16) = y
;
     all = transpose(all)
;
     printf, uu, $
format='(i8,i3,2f9.2,f9.3,f7.3,f10.2,2f10.3,f8.2,e11.3,f9.3,f7.3,f10.2,f8.3,2f9.2)',$
     all
     close, uu
     free_lun, uu
     error = 0
;
return
end

