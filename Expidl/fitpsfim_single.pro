pro fitpsfim_single, im,sky,sigma,beta4,beta6,beta8,  sat, psfim
;	getstars6,im,x,y,good, 1000
       getstars6, im, x, y, good, sat
print, ' Got ', n_elements(good), ' stars for processing.'
wait, 4.
;

        if(n_elements(good) lt 3) then begin
          sigma = 0.1 & beta4 = -1. & beta6 = -1 & beta8 = -1.
           return
        endif
;
        inrad = 30
        outrad = 40
;
        fitvals = findgen(5, 2)
         psfimsz = 2.*nint(outrad) + 1
        psfim = fltarr(psfimsz, psfimsz)
        central = nint(outrad)+1
        psfstack = []
        nnn = 0
        
	for ix = 0,n_elements(good)-1 do begin
           fitaper3, im,x[good[ix]],y[good[ix]], inrad, outrad, fitvals, psfim
           if(total( psfim( (central-1):(central+1), (central-1):(central+1) ) ) ne 0.) then begin 
                psfstack = [psfstack, reform(psfim, psfimsz*psfimsz)]
                nnn = nnn+1 
            endif     
	endfor
	fitvals = fitvals[*, 2:(size(fitvals))[2] - 1]
;;        fitvals = fitvals[*, 1:(size(fitvals))[2] - 1]
        psfstack = reform(psfstack, psfimsz, psfimsz, nnn, /overwrite)
;
; get rid of values that are beta=1.5 and beta6=1.0 and beta8=0.
;;;   these are starting guesses -- if they did not change, then fit 
;;   did not converge
;
       bbb = where( fitvals(2,*) ne 1.500 or fitvals(3,*) ne 1.000 or fitvals(4,*) ne  0.000, nbbb)
       print, nbbb, ' objects appear to  have converged fits '
       fitvals = fitvals(*,bbb)
       psfstack = psfstack(*,*, bbb)
;
;       
        print, ' Number of stars available for betas: ', (size(fitvals))[2]
	if (size(fitvals))[2] gt 10 then begin
;		fitvals = fitvals[*,0:9]
        endif else begin
           print,'WARNING: found fewer than 10 stars for PSF fit.'
        endelse
;
        percentile, im, 20, sky
;
        if(size(fitvals))[2] lt 1 then begin
           print, ' No good stars for calculating betas '
           print, '  setting default values: '
           sigma = 2.0
           beta4 = 1.0
           beta6 = .5
           beta8 = 0.
           goto, SKIP
       endif 

;	samples = im[0]
;	for i=1,9999 do begin
;		f = i / 10000.
;		ix = n_elements(im) * f
;		samples = [samples, im[long(ix)]]
;	endfor
;	samples = (samples[sort(samples)])[0:5000]
;	sky = 3 * median(samples) - 2 * mean(samples)

	; compute medians to use as a result.
	sigma = median(fitvals[1,*])
	beta4 = median(fitvals[2,*])
	beta6 = median(fitvals[3,*])
	beta8 = median(fitvals[4,*])

        print, sigma, beta4, beta6, beta8

        rxx = findgen(200)/10.
        z = rxx/(1.4142*sigma)
        denom = 1.+ z^2 + 0.5*beta4*z^4 + 0.1666667*beta6*z^6 + (beta8/24.)*z^8
        prof = 1./denom
        prof = [ (reverse(prof)), prof(1:*) ]
        rxx = [ -1.*reverse(rxx), rxx(1:*) ]
        plot, rxx, prof, yr = [-.2, 1.2], ystyle=1
        xxx = [0, 0]
        yyy = [-1, 2]
        oplot, xxx, yyy

        peaks  = total(fitvals(0,*),1)
        sigmas = total(fitvals(1,*),1)
        beta4s = total(fitvals(2,*),1)
        beta6s = total(fitvals(3,*),1)
        beta8s = total(fitvals(4,*),1)
;        gg = where(peaks le 20000. and peaks ge 500. and sigmas ge .8
;        and sigmas lt 13., ngg)
        gg = where(peaks le sat/5. and peaks ge sat/100. , ngg) 

        if(ngg lt 1) then begin
          print, ' No sigma estimate is possible '
          print, ' using unfiltered values: '
          goto, SKIP
        endif
        sigma = median(sigmas(gg))
        beta4 = median(beta4s(gg))
        beta6 = median(beta6s(gg))
        beta8 = median(beta8s(gg))

SKIP:

	if (beta6 lt 0 and beta8 lt abs(beta6)) then beta8 = abs(beta6)

	if beta8 lt 0 then beta8 = 0

        print, sigma, beta4, beta6, beta8
;        rxx = findgen(200)/10.
;        z = rxx/(1.4142*sigma)
        denom = 1.+ z^2 + 0.5*beta4*z^4 + 0.1666667*beta6*z^6 + (beta8/24.)*z^8
        prof = 1./denom
        prof = [ (reverse(prof)), prof(1:*) ]
        rxx = [ -1.*reverse(rxx), rxx(1:*) ]
        oplot, rxx, prof, thick=3
        xxx = [0, 0]
        yyy = [-1, 2]
        oplot, xxx, yyy

        psfstack = psfstack(*,*, gg)
        fitvals = fitvals(*, gg)
;
        psfstackplay, psfstack, sigma,  psfim
        
;;       pause
return        
end

