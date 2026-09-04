pro readqap,  name,  idap,  x, y,  apmags,  nstar, sky

  ON_IOERROR,  error_handler 
;;; name is the name of the aperture file, whether .ap, or .bap

; name = strjoin([rootname, '.ap'])

openr,lun,name,/get_lun

nstar = 100000l

idap = fltarr(nstar)
x  = fltarr(nstar)
y  = fltarr(nstar)
;fitmag = fltarr(nstar)
;sky = fltarr(nstar)
;apminfit = fltarr(8,nstar)
;dopapmag = fltarr(nstar)
;apmagerr = fltarr(nstar)
;fitmagerr = fltarr(nstar)
apmags = fltarr(8,nstar)
sky = fltarr(nstar)
temp = fltarr(12)   ;;; with the new output on .ap with sky

READ:
ii = 0L
while not eof(lun) do begin
   readf,lun, temp
   idap(ii) = temp(0)
   x(ii) = temp(1)
   y(ii) = temp(2)
   sky(ii) = temp(11)
;   sky(ii) = temp(3)
;   fitmag(ii) = temp(4)
;   apminfit(*,ii) = temp(5:12)
;   fitmagerr(ii) = temp(13)
;   dopapmag(ii) = temp(14) 
;   apmagerr(ii) = temp(15)
   apmags(*,ii) = temp(3:10)
   ii = ii + 1L
   if(ii eq nstar) then goto, Compl
endwhile

Compl:
   nstar = ii
   idap = idap(0:nstar-1)
   x = x(0:nstar-1)
   y = y(0:nstar-1)
   sky = sky(0:nstar-1)
;   sky = sky(0:nstar-1)
;   fitmag = fitmag(0:nstar-1)
;   apminfit = apminfit(*,0:nstar-1)
;   fitmagerr = fitmagerr(0:nstar-1)
;   dopapmag = dopapmag(0:nstar-1)
;   apmagerr = apmagerr(0:nstar-1)
    apmags = apmags(*, 0:nstar-1)
close, lun
free_lun, lun
goto, done
;
error_handler:
print, ' error in I/O:  most likely it tripped on an EOF,in read loop, so lets try to recover with what was read"
print, 'No. of lines read =   ',  ii-1
if(ii-1  ge 1) then begin
    ii = ii-1
    goto, Compl
 endif else begin
    print, 'Did not even read one item... so aborting..'
    print, 'This is an unrecoverable error'
    PRINT, !ERROR_STATE.MSG
   stop
 endelse
;
done:
;;pause
return
end


   
