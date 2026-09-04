pro fitaper3, img,x0,y0,inrad,outrad,fitvals, psfim
	eperdn = 1
	erdnoise = 7

	x00 = x0 - outrad
	x11 = x0 + outrad
	y00 = y0 - outrad
	y11 = y0 + outrad

	nx = (size(img))[1]
	ny = (size(img))[2]

	if (x00 le 0 or x11 ge (nx - 1) or y00 le 0 or y11 ge (ny - 1))   then begin
                print,'Skipping star at ',x0,', ',y0,': too close to edge.'
                psfim = psfim*0.
;;;pause
                return
             endif

        

	p = img[x00:x11, y00:y11]
	cntrd,p,outrad,outrad,xcen,ycen, 2.5
        print,'Centroid: ', xcen,ycen

;        re-extracted image for best (1-pix) alignment over objects

        x0 = nint(xcen + x00) & y0 = nint(ycen + y00)   ;; returning to coords on big image

        x00 = x0 - outrad
	x11 = x0 + outrad
	y00 = y0 - outrad
	y11 = y0 + outrad

	if (x00 le 0 or x11 ge (nx - 1) or y00 le 0 or y11 ge (ny - 1)) $
	then begin
               print,'Skipping star at ',x0,', ',y0,': too close to edge.'
               psfim = psfim*0.
;;;pause               
	       return
	endif
       

	size = 2*outrad + 1
	ximg = (findgen(size)) # (intarr(size)+1)
	yimg = transpose(ximg)
	r = sqrt((ximg - xcen)^2 + (yimg - ycen)^2)

	out = where (r gt inrad)
	enclosed = where (r le inrad)

	; create the fitting data
	backgrnd = median(p[where(r gt inrad)])
  print, backgrnd
	xp = r[enclosed]
	yp = p[enclosed] - backgrnd
;	yp = yp * 1000. / max(yp)
;	rfac = 1000. / max(yp)
        ; get 2nd moments:
        tot = total(yp)
        mom2sq = total( yp*r[enclosed] ) / (tot)        
        mom2 = sqrt(mom2sq)
    
  print, 'initial calc of sigma : ', mom2

    if(mom2 gt 0.5 and mom2 le 10.) then begin 
        ; recompute array size to fit within.. radius of 2.*fwhm
        nfwhm = fix(2.35*mom2) + 1
        nfitrad = min([2.*nfwhm, inrad])
        nfitrad = max([nfitrad, 4])
        enclosed2 = where(r le nfitrad)
     endif else begin
        enclosed2 = enclosed
     endelse

	; resize fit box and compute weights
        xp = r[enclosed2]
        yp = p[enclosed2] - backgrnd
	a = [ max(yp), mom2, 1.5, 1., 0. ]
        w = p[enclosed2] 
	noise = sqrt(w * eperdn + (erdnoise^2))
	w = min(noise) / noise

	; perform the fit
	yfit = curvefit(xp, yp, w, a, function_name="hstfun")

        fitvals = [[fitvals], [a]] 
        psfim = p - backgrnd
        
return        
end
