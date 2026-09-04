pro getstars6,im,x,y,good, sat
;
        thresh = sat/10.
;;;        window, 0, xs=700, ys=600 
	fwhm = 4.0
	roundlim = [ -1, 1 ]
	sharplim = [ 0.2, 0.6 ]
;        threshmin = 100.
        threshmin = thresh/33. & print, 'threshmin = ', threshmin 

RETRY:	find, im,x,y,flux,sharp,rnd,thresh,fwhm,roundlim,sharplim ,/silent
        starcos, im, x, y, fwhm, shratio
        plot, shratio(sort(shratio))
        wait, 1.
        oks = where(shratio gt 0.05 and shratio lt 1.5, noks)
	n_stars = noks
        x = x(oks) & y = y(oks) & shratio = shratio(oks) 
;        
;        if(n_stars lt 15) then begin 
        if(n_stars lt 100) then begin 
          thresh = thresh/2. & print, ' New thresh: ', thresh
          if(thresh gt threshmin) then begin
            goto, RETRY
          endif else begin
            if(n_stars lt 10) then begin
              print, 'Cannot find enough stars, must give up..'
              return
            endif
          endelse
        endif
        print, 'Found ', n_stars, ' objects.'
        
;
;        starcos, im, x, y, fwhm, shratio
        ss = sort(shratio) & sortrat = shratio(ss)
;        nindex = nint(n_elements(shratio)*0.65)
;;;        nindex = nint(n_elements(shratio)*0.75)
;;;---------------------------------------------------
         ntop = long(n_elements(shratio)*0.95 + 0.5)
         ntop = min([ntop, n_elements(shratio)-1L])
         nbot = long(n_elements(shratio)*.05 - 0.5)
         nbot = max([nbot, 0L]) 
         binsz = 0.02

         hhshr = histogram(sortrat(nbot:ntop), binsize=binsz, min=0., max=sortrat(ntop) )
         hhx  = findgen(n_elements(hhshr))*binsz 
         vdots, 0.4
         plot, hhx, hhshr, psym=8, yr=[-.1, max(hhshr)+5], xtitle='Shratio', ytit='Freq'
         hpk = where(hhshr eq max(hhshr)) & shrval = hhx(hpk(0)) 
         wait, 2.
;         pause
;;;---------------------------------------------------                   
;;;        shrval = sortrat(nindex)
;        shrval = median(shratio)
;;        shrlo = shrval - 0.06 & shrhi = shrval + 0.08
         shrlo = shrval - 0.08 & shrhi = shrval + 0.06
        vdots, 0.4
        plot, sortrat, yr=[shrval-1., shrval+1.], psym=8 
        oplot, [0, n_stars], [shrlo, shrlo], color=255
        oplot, [0, n_stars], [shrhi, shrhi], color=255
        wait, 4.
;
;
;;;;;pre-selection 
        
        gg = where(shratio ge shrlo and shratio le shrhi)
        x = x(gg) & y = y(gg) & flux = flux(gg) & sharp=sharp(gg)
        rnd = rnd(gg) & n_stars = n_elements(x)


;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

	; sort the list by flux
	fluxsrt = reverse(sort(flux))
	if (n_stars gt 10000) then begin
		fluxsrt = fluxsrt[0:9999]
		n_stars = 10000
	endif
	flux = flux[fluxsrt]
	x = x[fluxsrt]
	y = y[fluxsrt]
	sharp = sharp[fluxsrt]
	rnd = rnd[fluxsrt]

	; exclusion of  stars close to the edge.
	xleft = 20
	xright = (size(im))[1] - 21
        ybot = 20
        ytop =  (size(im))[2] - 21

	; set sharp limits
	sharpsort = sharp( sort(sharp) )
	sharplo = sharpsort( long(n_stars*0.2) )
	sharphi = sharpsort( long(n_stars*0.95) )

	; set round limits
	rndsort = rnd(sort(rnd))
	rndlo = rndsort( long(n_stars*0.1))
	rndhi = rndsort( long(n_stars*0.9))

	; find distance to neighbors
	r = x
	for ix = 0,(size(x))[1]-1 do begin
		brite_enuf = where(flux gt 0.1 * flux[ix], nbre)
                if(nbre gt 1) then begin
          	  brite_enuf = brite_enuf[where(brite_enuf ne ix)]
		  rall = (x[brite_enuf] - x[ix])^2 + (y[brite_enuf] - y[ix])^2
		  r[ix] = min(rall)
		  r[ix] = sqrt(r[ix])
              endif else begin
                  r[ix] = max(x)  ;  i.e. set arbitrarily large
              endelse 
	endfor

	; cut by flux
        minflx = sat/50.
        absminflx = thresh
MFLXLOOP:
	try = where(flux gt minflx and flux lt sat, ntry)
        if(ntry lt 100 and absminflx le minflx) then begin
            minflx = minflx/2. 
            goto, MFLXLOOP
        endif

        print, 'median sharp & rnd: ', median(sharp), median(rnd)
        print, 'min-max sharp: ', min(sharp), max(sharp)
        print, 'min=max round: ', min(rnd), max(rnd)
        good = where ( $
               x ge xleft and x le xright and $
               y ge ybot and y le ytop and $
               sharp gt sharplo and sharp le sharphi and $
               rnd gt rndlo and rnd le rndhi and $
               r gt 10. and $
               flux gt minflx and flux le sat $
                     )
;;pause
return
end
