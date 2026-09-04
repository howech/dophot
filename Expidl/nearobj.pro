pro nearobj, x, y, mag, type, rad, contam
;
;;; INPUT:
;;;;  x, y, mag, type are arrays of DoPHOT generated objects
;;;;   rad is neighbourhood radius in PIXELS
;;;; 
;;; OUTPUT:
;;;   contam = array with contaminating flux as fraction of object flux 
;;;   expressed in magnitudes   
;;;
;
   nstars = n_elements(x)
   contam = fltarr(nstars)
   contam = contam*0.
;
;
   x2 = x & y2 = y               ;;; copies of input list
;
   close_match_xy, x, y, x2, y2, mtc1, mtc2, rad, 10, miss1
   nmiss1 = n_elements(miss1) 
   if(nmiss1 eq 1 and miss1(0) eq -1) then nmiss1 = 0
   print, 'Missed matches (should be ZERO) : ', nmiss1
;
   mtc1hist = histogram(mtc1, BINSIZE=1L, MIN=0, NBINS=n_elements(x)+5, REVERSE_INDICES = RI)
   multim = where(mtc1hist gt 1) ;; indices of array1 that occur multiply in mtc1
;
;;
;; so that means objects with x(multim), y(multim) are multiply matched.
;;
   nmultim = n_elements(multim)
   print, ' Identified ', nmultim, ' contaminated objects'
   for k = 0L, nmultim-1 do begin   
     i = multim(k)       ;; index of kth object that is multiply matched
       x0 = x(i)  
       y0 = y(i)
       mag0 = mag(i)
;;;       cn = where( x ge x0-rad and x le x0+rad and $
;;;              y ge y0-rad and y le y0+rad, ncn )

       hmm = RI(RI(i): RI(i+1)-1)  ;; indices of mtc1 with value "i"  
       cn = mtc2(hmm) & ncn = n_elements(cn)
;
       if(ncn gt 1) then begin
         ok = where(type(cn) ne 8 and type(cn) ne 18, nok)
         bad = where(type(cn) eq 8 or type(cn) eq 18, nbad)
         if(nbad ne 0) then begin
            contam(i) = -1.*nbad
            goto, SKIP
         endif 
         flux = 10.^(-0.4*mag(cn))
         tflux = total(flux) 
         flux0 = 10.^(-0.4*mag0)         
         contam(i) = 2.5*alog10(tflux/flux0)
        endif
SKIP:
     endfor 
;
;;dd    plot, mtc1hist, psym=10
;;dd      k = 1
;;dd      i = multim(k)
;;dd      print, 'multim(k) = ', multim(k) 
;;dd       hmm = RI(RI(i): RI(i+1)-1)  ;; indices of mtc1 with value "i"
;;dd       hmm_alt = where(mtc1 eq i)   
;;dd       cnf = mtc2(hmm) & ncnf = n_elements(cnf)
;;dd       print, hmm
;;dd       print, hmm_alt
;;dd       print, mtc1(hmm)
;;dd       print, cnf    
;;dd       print, mtc1(hmm_alt)
;;dd       print, mtc2(hmm_alt)
;;dd       x0 = x(i)  
;;dd       y0 = y(i)
;;dd       mag0 = mag(i)
;;dd       print, x0, y0, mag0
;;dd       cn = where( x ge x0-rad and x le x0+rad and $
;;dd              y ge y0-rad and y le y0+rad, ncn )
;;dd       print, cn
;
;;dd    pause
    return
    end
