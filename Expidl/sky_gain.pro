pro sky_gain, img, var, sky, fpdn, sky0
;
  print, 'Entering "sky_gain" ...  with ',  n_params(), ' parameters'
;
;;;  tries to get a median gain (photon/nJy) and median subtracted
;;;  sky, from image and variance plane of deep coadd images from
;;;  Rubin obs

  plot, img, var, psym=3, chars=2, xr=[-100., 11000.]
;
;;;;   reject blank pixels when computing sky;;
  bsize = 0.1
  xmin = min(img)  
  xmin = max([xmin, -1000.])
  xmax = xmin + 10000.
  hhh = histogram(img, min = xmin, max = xmax, binsize=bsize)
  hhx = lindgen(n_elements(hhh)) 
  hhx = hhx*bsize + xmin
  maxhhh = max(hhh)
  blank = where( hhh eq max(hhh) , nblank)
  xblank = total(img(blank)) / float(nblank)
                                ;
 ; pause
  ;
  oklo = where(img gt xmin and img le xmax, noklo)
  stats1, img(oklo), mean, rms, errmean
  stats1, var(oklo), meanvar, varrms, errvarmean
 
  if(mean gt rms) then begin
     print, '  Looks like image has background added...'
     print, ' Mean background = ',  mean,  '     Rms = ', rms,  '   Mean_noise_sigma = ',  sqrt(meanvar) 
     ok0 = where(img gt (mean - 3.*rms) and img le (mean +3.*rms)  and var le 1.e12 and  ( img lt (xblank - bsize) or img gt (xblank + bsize) ) ,  nok0)
     sky0 = mean
  endif else begin
     ok0 = where(img gt -10. and img le 20. and ( img lt (xblank - bsize) or img gt (xblank + bsize) ),  nok0)
     sky0 = 0.
  endelse
  
;  pause
  
  ok5H  = where(img-sky0 gt 450.  and img-sky0 le 550. and var le 1.e12 , nok5H)
  ok1K = where(img-sky0 gt 950. and img-sky0 le 1050. and var le 1.e12, nok1K)
  ok2K = where(img-sky0 gt 1900. and img-sky0 le 2100. and var le 1.e12, nok2K)
  ok3K = where(img-sky0 gt 2800. and img-sky0 le 3200. and var le 1.e12, nok3K)
  ok4K = where(img-sky0 gt 3700. and img-sky0 le 4300. and var le 1.e12, nok4K)
  ok5K  = where(img-sky0 gt 4500.  and img-sky0 le 5500. and var le 1.e12, nok5K)
  ok10K  = where(img-sky0 gt 9000. and img-sky0 le 11000. and var le 1.e12, nok10K)
;
     
  stats1, var(ok0), mean, rms, errmean
  uncok0 = rms/sqrt(nok0-1L)

  stats1, var(ok5H), mean, rms, errmean
  uncok5H = rms/sqrt(nok5H-1L)
  
  stats1, var(ok1K), mean, rms, errmean
  uncok1K = rms/sqrt(nok1K-1L)

  stats1, var(ok2K), mean, rms, errmean
 uncok2K = rms/sqrt(nok2K-1L)

  stats1, var(ok3K), mean, rms, errmean
  uncok3K = rms/sqrt(nok3K-1L)

   stats1, var(ok4K), mean, rms, errmean
  uncok4K = rms/sqrt(nok4K-1L)

  stats1, var(ok5K), mean, rms, errmean
  uncok5K = rms/sqrt(nok5K-1L)

  stats1, var(ok10K), mean, rms, errmean
  uncok10K = rms/sqrt(nok10K-1L)
 ;
  
 ; pause
 ;
  
  X = [ median(img(ok0)),  median(img(ok5H)), median(img(ok1K)),  median(img(ok2K)), median(img(ok3k)), median(img(ok4k)), median(img(ok5K)), median(img(ok10K)) ]
  W  =  [ nok0,  nok5H,  nok1K, nok2K, nok3K, nok4K, nok5K, nok10K]
  Unc = [uncok0, uncok5H, uncok1K, uncok2K, uncok3K,  uncok4k, uncok5K, uncok10K]
  Y = [ median(var(ok0)),  median(var(ok5H)), median(var(ok1K)),  median(var(ok2K)),  median(var(ok3K)),  median(var(ok4K)),  median(var(ok5K)), median(var(ok10K)) ]
  ;
  vdots, 1.5
  oplot, X, Y, psym=8, color=255*256L
  errplot, x, y-unc, y+unc, color=255*256L
  starswt, const, coeff, Y, Unc, X
 ;
  xx = [0., 11000.]
  yy = const + coeff(0)*xx
  oplot, xx, yy, color=255, thick=3
;
  if(sky0 eq 0) then   begin
     sky = const                ; (in nJy)
  endif else begin
     sky = sky0
  endelse
                                ;
  fpdn = coeff(0)               ;   (nJy/photon)
  gain = 1./fpdn                ; (photons/nJy)
  
 ; pause
  return
  end
  
