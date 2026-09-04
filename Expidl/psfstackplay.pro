pro psfstackplay,  psfstack,  sigma,  qqq
;
  sizz = size(psfstack)
  print, 'Stack size:  -->  ',   sizz
  if(sizz(0) ne 3) then begin
     print, ' PSFSTACKPLAY:   psfstack is not a datacube!!   Stopping!'
     stop
  endif
  ;
  cenimx = nint( (sizz(1) + 1) / 2 )
  cenimy  = nint( (sizz(2) + 1) /2 )
;
  xyimg, ximg, yimg, sizz(1), sizz(2)
  rad = sqrt(  (ximg)^2 + (yimg)^2 )
  radsl = reform(rad, sizz(1)*sizz(2))   ;; single dim array
  outer = where( radsl ge 2.35*sigma*5.  or radsl ge 0.375*min([sizz(1), sizz(2)]) )
;    
;;  create a psf stack normalized to peak of central feature
  normstack = 0.*psfstack
  psfslice = reform( psfstack, sizz(1)*sizz(2), sizz(3) )   ;  
  relbrt = fltarr(sizz(3)) ;  keep track of relative brightness of psfslices in psfstack
  bkgsl  = fltarr(sizz(3)) ; keep track of background value in each slice
;
  for  ii = 0, sizz(3)-1 do begin
;
     percentile, psfslice(outer, ii), 2, xb  & percentile, psfslice(outer, ii), 98, xt
     xr = (xt - xb)
     xmin = xb - 0.1*xr  & xmax = xmin + xr & bsize= min([xr/100., 2.])
     hhh = histogram(psfslice(outer, ii),  min=xmin, max=xmax, binsize=bsize)
     hhx = indgen(n_elements(hhh)) & hhx = hhx*bsize + xmin
     if(ii eq 0) then plot, hhx, hhh, psym=10, lines=1, chars=1.4, charth=2
     plot, hhx, hhh, psym=10, lines=0
     jjj = where(hhh eq max(hhh))
     bckgr =  hhx(jjj(0))
     psfslice(*,ii) = psfslice(*,ii) - bckgr  ;;;  all psfslice now bckg subtracted, psfstack left unchanged
;
     centot = total( psfstack( (cenimx-1):(cenimx+1),  (cenimy-1):(cenimy+1),  ii) - bckgr )
     normstack(*,*,ii) = 9.*(psfstack(*,*,ii) - bckgr) / centot
     relbrt(ii) = centot
     bkgsl(ii) = bckgr
     
  endfor
;
  normslice = reform( normstack, sizz(1)*sizz(2), sizz(3) )
  varim = variance( normstack, dimension=3 )
  normcln = fltarr(sizz(1)*sizz(2))
  psfcln = fltarr(sizz(1)*sizz(2))

  crad = 3.*sigma               ;  about 1-fwhm
  vcm = median(  varim( where(radsl le crad) )  )
  varim2 = varim/vcm
  varim2( where(varim2 le 1.) )  = 1.   ;; unitize  best inverse-weight  
  ;vdots,  .5
  ;plot, radsl, varim2, psym=8, yr = [-1, 8], ysty=1

 for kk = 0L, sizz(1)*sizz(2) -1L do begin
    normthrd = normslice(kk, *)
    psfthrd = psfslice(kk,*)
    percentile_hilo,  normthrd, 10, 60, nmtlo, nmthi
    good = where(normthrd ge nmtlo  and normthrd lt nmthi, ngood)
    normcln(kk) = total(normthrd(good))/float(ngood)
;;;;    normcln(kk) = median(normthrd)   ;;;  test this out, over the stuff imeediately above..
 endfor
 ;
 normclnim = reform(normcln, sizz(1), sizz(2))
 relbrts = relbrt(  reverse( sort(relbrt) )  )
 nbrts = n_elements(relbrts)
 ;;; qqq = total(relbrt) * normclnim  &  qqq = qqq/nbrts
  qqq = total(  relbrts(0:nint(sqrt(nbrts)))) * normclnim /  nint(sqrt(nbrts))
;  
;
;  ppp = total(normstack, 3)
;  ppp = ppp/ float(sizz(3))
;  ppp = ppp/max(ppp)   ;;; sets max value == 1.00
;  var2ppp  = varim/ppp
;  mfloor =  2.*median( var2ppp(where(ppp gt 0.2) ) )
;  percentile, var2ppp, 50, mfloor & print, mfloor
;  ggg = where(var2ppp le mfloor)
;;
;
   ccc = total(psfstack, 3)
;  ccc =  (ccc/varim2)  
;  percentile, ccc, 20, pc20
;  qqq = ccc*0. + median(ccc)
;  qqq(ggg) = ccc(ggg)  
  
;;  qqq = ppp*0. + median(ppp)
;;  ggg = where(varim lt .02*max(varim))
;;  qqq(ggg) = ppp(ggg)
   
;
  tv, congrid(  bytmap(ccc, -.01*max(ccc), .05*max(ccc) ),  5*sizz(1), 5*sizz(2))
  wait, 5.
  tv, congrid(  bytmap(qqq, -.01*max(qqq), .05*max(qqq) ),  5*sizz(1), 5*sizz(2))
  wait, 5.
  rrr = alog10(qqq)
  ttt = qqq^0.25
;;;;;  rrr( where(rrr le 0.)) = alog10(0.002*max(qqq))
  tv, congrid(  bytmap(rrr, max(rrr)-2.7, max(rrr)-0.2),  5*sizz(1), 5*sizz(2) )
  wait, 5.
  tv, congrid( bytmap(ttt, min(ttt), max(ttt)), 5*sizz(1), 5*sizz(2) )

  
;;  pause
return
end



  
