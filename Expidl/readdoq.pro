	pro readdoq, doqfile, x, y, amag, amagerr, id, type, asky, xfw, yfw, tilt, exten, apmag, apmagerr, apsky, apminfit, esky, emag, ex, ey, emagerr,  ERROR=ERROR, SORTX=SORTX

;
 	ON_IOERROR, DONE
;
     on_error, 2
 
if ( n_params(0) lt 4 ) then begin
     print,'Call is : readdoq, doqfile, x, y, amag [, amagerr, id, type, asky, xfw, yfw, tilt, exten, apmag, apmagerr, apsky, apminfit, esky, emag, ex, ey, emagerr,  ERROR=ERROR, SORTX=SORTX] '
     ERROR = 1
     return
endif
   

;======================OLD DOP FILE READING=====================================
        ostring = ' '
        spawn, 'wc '+doqfile+' ', ostring
        nitems = long(ostring(0))
        print, ' There appear to be', nitems, ' objects...'
;
        get_lun, u1
	openr, u1, doqfile, error = error
         if(error ne 0) then begin 
           print, error
           print, 'Error opening file : ', doqfile 
           error = 1
           return
         endif
;
;
	all = fltarr(20, nitems)
        line = fltarr(20)
        on_ioerror, DONE
	for i = 0L, nitems-1L do begin 
           readf, u1, $
;;;;           format='(i8,i3,2f9.2,f9.3,f7.3,f10.2,2f10.3,f8.2,e11.3,f9.3,f7.3,f10.2,f8.3)',$       
           line
            all(*,i) = line
            CATCH, err  ; Check for errors
            if err ne 0 then begin
                    print, "Error occurred: ", !ERROR_STATE.MSG
                    print, ' skipping bad record in ', doqfile
             endif  
         endfor
         on_ioerror, DONE
;
        goto, SKIPDONE
  DONE:  print, !err_string
  SKIPDONE: print, ' Normal read completion '

	close, u1
        free_lun, u1
;
	nz = where( all(0,*) ne 0. )
	all = all(*,nz)
	help, all, nz
        all = transpose(all)
        x = all(*,2)
        y = all(*,3)
        amag = all(*,4)
        amagerr = all(*,5)
        asky = all(*,6)
        type = all(*,1)
        id = nint( all(*,0))
        apmag = all(*,11)
        apmagerr = all(*,12) 
        apsky = all(*,13)
        xfw = all(*,7)
        yfw = all(*,8)
        tilt = all(*,9) 
        exten = all(*,10)
        apminfit = all(*,14)
        esky = all(*,15)
        emag = all(*,16)
        ex = all(*,17)
        ey = all(*,18)
        emagerr = all(*,19)
         
    ERROR = 0
;
if ( keyword_set(SORTX) ) then begin
   w = sort(x)
   id = id(w)  &  type = type(w)  &  x = x(w)  &  y = y(w)  &  amag = amag(w)
   amagerr = amagerr(w)  &  asky = asky(w)  &  xfw = xfw(w) & yfw = yfw(w)  
   tilt = tilt(w) & exten = exten(w) & apmag = apmag(w) & apmagerr = apmagerr(w)
   apsky = apsky(w) & esky = esky(w) & emag = emag(w) & ex = ex(w) & ey = ey(w)
   emagerr = emagerr(w)
endif
;
return
end 
