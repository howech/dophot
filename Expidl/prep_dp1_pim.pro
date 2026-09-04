pro prep_dp1_pim, filroot, outroot, empflag, psfim
;
;
  if(n_params(0) lt 3) then begin
     print, ' Check Usage:  <<  prep_dp1_pim, filroot, outroot, empflag [,psfim] >> '
     print,  ' ... exiting -- retry !! '
     return
  endif
;  
  fitsfile = strjoin([filroot,  '.fits'])
  hhh = headfits(fitsfile)
  im1 = readfits(fitsfile, hh1, exten=1)
  im3 = readfits(fitsfile, hh3, exten=3)
  im2 = readfits(fitsfile, hh2, exten=2)
;
;  lolim = -50.  & hilim = 5000.
;  plot, im1, im3, psym=3, xr=[lolim, hilim], yr=[0., 2000.]
;  ok = where(im1 gt lolim and im1 le hilim)
;  stars, const, coeff, im3(ok), im1(ok)
;  xx = [lolim, hilim]
;  yy = const + coeff(0)*xx
;  oplot, xx, yy, color=255, thick=2
;  gain = 1./coeff(0)            ; electrons per nJy
;  fpdn = coeff(0)
;  sky = const  ;   in nJy
;
;  sky = 0.d0  & fpdn1 = 0.d0 & sky0 = 0.d0
  sky_gain, im1,  im3,  sky,  fpdn1,  sky0
;;;;;;--------------------------------------------------
;  stop
;  ;
;  bsize = 0.1
;  xmin = min(im1)  & xmax = xmin + 10000.
;  xmin = max([xmin, -1000.])
;  hhh = histogram(im1, min = xmin, max = xmax, binsize=bsize)
;  hhx = lindgen(n_elements(hhh)) 
;  hhx = hhx*bsize + xmin
;  maxhhh = max(hhh)
;  blank = where( hhh eq max(hhh) , nblank)
;  xblank = total(im1(blank)) / float(nblank)
;                                ;
;  oklo = where(im1 gt xmin and im1 le xmax, noklo)
;  stats1, im1(oklo), mean, rms, errmean
;  if(mean gt 2.*rms) then begin
;     print, '  Looks like image has background added...'
;     print, ' Mean background = ',  mean,  'Rms = ', rms
;     ok0 = where(im1 gt (mean - 3.*rms) and im1 le (mean +3.*rms)  and  ( im1 lt (xblank -0\.1) or im1 gt (xblank + 0.1) ),  nok0)
;     sky0 = mean
;  endif else begin
;     ok0 = where(im1 gt -10. and im1 le 20. and ( im1 lt (xblank -0.1) or im1 gt (xblank + 0.1) ),  nok0)
;     sky0 = 0.
;  endelse
;
;  stop
;;;;;;  ------------------------------------------------------

;
  badd = where(im2 and 1)
  satu = where(im2 and 2)
  intrp = where(im2 and 4)
  cr = where(im2 and 8)
  edge = where(im2 and 16)


  
  nosat = where( (im2 and  2) eq 0 )
  gain1 = 1./fpdn1
  if( sky0 eq 0) then begin
     im4 = im1 + sky
  endif else begin
     im4 = im1  ;;  sky is already in the input image... no need to add
  endelse
  
  im4 = gain1*im4       ;  in photons:  scales image to favorable integer units
  im4(badd) = -30000.
  im4(satu) = -30000.
  im4(intrp) = -30000.
  im4(cr) = -30000.
 ; im4(edge) = -30000.
  skyval1 = gain1*sky
;  sat1 = max(im1(nosat))*gain1
  sat1 = max(im4)  ;;  i.e. max value in masked working image -- gain1 is already folded in to im4
;
;  pause
  
  noisethresh = sqrt(skyval1 + 225.) ;   assuming 15 electrons readnoise
  maxsky1 = sat1
  maxsky = maxsky1
  print, 'Maxsky = ', maxsky
  lpcnt = 0
;    
  LOOP:                                                        ;; LOOP finds the minimum epdn to get MPREC >2 and maximize range
                                                                    ;;  used in medfil
     if(lpcnt ge 1) then maxsky = maxsky/2.
           r2 = max(  [maxsky/32760., 1.0] )
           nt2 = noisethresh/r2
           if(nt2 ge 2.) then begin
              epdn = r2
              fpdn = fpdn1*epdn
              gain = 1./fpdn
              mprec = nint(nt2)
              goto, GO_ON
           endif
              lpcnt = lpcnt+1
              goto, LOOP
;
;
GO_ON:              
;
     
     
;   sat = 3.e+6
;  wsat = sqrt(sky)*3000.  & print, wsat
;
;  fitpsf6deep, img, skyval, sigma, beta4, beta6, beta8 , sat
;; fitpsf6, img, skyval, sigma, beta4, beta6, beta8
;  sat  = max(im1(nosat))*gain  + sky*gain ;;;. adding sky raises the sat value for im4              
;  im4 = (im1 + sky)*gain      
  
;
;;;;;;;;;;;;   Write out the properly scaled PSF appended image for DoPHOT:
   ;
  ;;GO_ON:
  print, ' Using epdn, fpdn, gain, as: ', epdn, fpdn, gain, maxsky
  if(sky0 eq 0) then begin
     im4 = (im1 + sky)*gain
  endif else begin
     im4 = im1*gain
  endelse
  im4(badd) = -30000.
  im4(satu) = -30000.
  im4(intrp) = -30000.
  im4(cr) = -30000.
;  im4(edge) = -30000.
;  sat  = max(im1(nosat))*gain  + sky*gain ;;;. adding sky raises the  sat value for im4
  sat = max(im4) ;;  i.e. max value in masked working image -- gain1 is already folded in to im4
  psfim = 0.
  img = im4
  skyval=0.     ;;  will be returned  by fitpsfim -- so just set here as preliminary..
  fitpsfim_single, img,  skyval, sigma, beta4, beta6, beta8, sat, psfim
  print, max(psfim), max(img(nosat)), '  Maxpsfim and maxunsat img '
;
;  pause
;
;;;   so by construction, thus far im4 (==img) and psfim have same scale
;;;   but psfim needs rescaling to fit within unsaturated range befor attaching:

adjcnt = 0
DOAG:  
  if(max(psfim) gt 0.8*sat) then begin ;;;   psfim needs to be within saturation value
     psfim = (psfim /max(psfim))*0.8*sat
  endif  
;
;;;; make butterworth mask and apply:
  psfszz = size(psfim)
;;   xx = [psfszz(1), psfszz(2)]  
;;  bbww = butterworth(xx, cutoff=5.*sigma*2.35,  order=10, /origin)
  ;; mdnp = median(psfim)
  ;; psfimwrk = psfim - mdnp
;;  psfimwrk = psfim - skyval            ;;; make background = 0
;;  psfimwrk = psfimwrk*bbww
  ;; psfimo = psfim
  ;; psfim = psfimwrk + mdnp
  ;;  psfim = psfimwrk + skyval           ;;; restore background
  pkk = max(psfim)
  tv,  congrid(  bytmap(psfim,  -.1*pkk,  0.6*pkk),  5*psfszz(1),  5*psfszz(2) )
  wait, 5.
  tv, congrid( bytmap(alog10(psfim),  alog10(pkk)-4.,  alog10(pkk)-1.),   5*psfszz(1),  5*psfszz(2) )
;
;  
 ;;;  append psfim to im4 after matching borders:
;
        imgszz = size(im4)
        stripi = im4( 0:(psfszz(1)-1), (imgszz(2)-21):(imgszz(2)-1) )
        oki = where(stripi gt -1000., noki) ;  reject  masked pixels
        if(noki le psfszz(1)*psfszz(2)/4L) then begin
           medstripi = median(im4)
        endif else begin   
           medstripi = median(stripi(oki))
        endelse
;        
        im4( 0:(psfszz(1)-1), (imgszz(2)-21):(imgszz(2)-1) ) = medstripi ;;   "paint" over bad pixels to avoid bad enviro near PSF star
        stripp = psfim( 0:(psfszz(1)-1),  0:4 )
        medstripp = median(stripp)
        psfim = psfim + medstripi - medstripp
        if(max(psfim) gt 0.8*sat) then begin ;;;     check for saturation
           psfim = psfim * 0.75*sat / max(psfim)
           adjcnt = adjcnt + 1
           print, ' adjcnt = ', adjcnt,   '    stop it if adjcnt goes past 5 !!!'  
           goto, DOAG                                                ;;;  loop to match borders
        endif
;        
        bigstrip = fltarr( imgszz(1),  psfszz(2) )  - 30000.    
        bigstrip( 0:psfszz(1)-1,  0:psfszz(2)-1 ) = psfim
        img = fltarr(imgszz(1),  imgszz(2)+psfszz(2))
        img( 0:imgszz(1)-1, 0:imgszz(2)-1 ) = im4
        img( 0:imgszz(1)-1,  imgszz(2):imgszz(2)+psfszz(2)-1 )  = bigstrip
;
        psfcenx = (psfszz(1)-1)/2 + 1
        psfceny = (psfszz(2)-1)/2 +1 + imgszz(2)
;
        
;;;      
  outfits = strjoin([outroot, '.fits'])
  img = long(img)
  psfcenz = float(img(psfcenx, psfceny))
  psfcenx = float(psfcenx)
  psfceny = float(psfceny)
 ;; swap_endian_inplace, img      ;;; seems to need this to write a correct fits file
  writefits, outfits, img

  
  skyval = gain*sky
  swap_endian_inplace, img      ;;; restore img to IDL  working form...
  
;;;;;;;;;;;;   composite image written


  print, 'Final values for sigma, beta4, beta6, beta8 :  ',  sigma, beta4, beta6, beta8
;
goto, SKIP
bad = 0
;
;         if(beta4 lt .1  or beta4 gt 10.) then bad = 1 + bad 
         if(beta4 lt -.2  or beta4 gt 10.) then bad = 1 + bad 
         if(beta6 lt 0. or beta6 gt 10.)  then bad = 2 + bad
         if(beta8 lt -1. or beta8 gt 20.) then bad = 4 + bad
         if(sigma lt 0.8 or sigma gt 10.0) then bad = 8 + bad
         if(ccode ne 0) then bad = 16 + bad
         
 
         sigdef = 2.5
         b4def  = 1.0
         b6def  = 0.5
         b8def  = 0.

         if( bad ge 8) then sigma = sigdef
         if( bad gt 0) then begin
            beta4 = b4def
            beta6 = b6def
            beta8 = b8def
         endif
;
;
SKIP:
;        if( bad ne 0 ) then begin 
;         vcircs, 1.
;         plot, R(rout), Yall, psym=8, yr=[-100., 1200.], ystyle=1, xtitle=' Radius', ytitle=' Intensity (peak at 1000)', xra=[-1.*max(R(rout)), max(R(rout))]
;         vdots, 1.
;         oplot, XPP, YPP, PSYM=8
;
;         rxx = findgen(200)
;         rxx = rxx*outrad/200. 
;         z = rxx/(1.4142*sigma)
;         denom = 1.+ z^2 + 0.5*beta4*z^4 + 0.1666667*beta6*z^6 + (beta8/24.)*z^8
;         prof = 1000./denom
;         rxx = [ -1.*reverse(rxx), rxx(1:*) ]
;         prof = [ (reverse(prof)), prof(1:*) ]
;         oplot, rxx, prof, color=255, thick=3
;        endif
;
        xyouts, 0., 500., outroot, alignment=0.5, charsize=2, color=255*256L
        wait, 2. 
;

   print,  ' FINAL  sigma,  b4, b6, b8 :  '  ,   sigma, '  ', beta4, '  ',   beta6, '  ',   beta8 
;
;pause
;
;;;;;;enter param file writing code here...
;
   cmax = 1.3*sat
   params_dp1_pim, img, fitsfile, outroot, sigma, beta4, beta6, beta8, skyval,  epdn, fpdn, sat,  cmax, mprec, hhh, empflag, psfcenx, psfceny, psfcenz, filroot
;
;
;;;;;;;;
do_it = strjoin(['source  ', 'doit_', outroot])
finish_it = strjoin(['source  ', 'finish_', outroot])
;
print, do_it, '    ', finish_it
;
;pause
;
spawn, do_it
spawn, finish_it 
;
; pause
;
return
end
 


        
