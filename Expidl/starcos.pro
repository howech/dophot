pro starcos, im, x, y, fwhm, shratio
;
nf = nint(1.5*fwhm)
nout = nint(3.*fwhm)
sz = size(im)
nx = sz(1)
ny = sz(2)
shratio = x*0.
for  i = 0L, n_elements(x) -1L do begin 
   if(x(i) gt nout and x(i) lt nx-nout and y(i) gt nout and y(i) lt ny-nout) then begin
      psmall = im(x(i)-1:x(i)+1, y(i)-1:y(i)+1)
      plarge =  im(x(i)-nf:x(i)+nf, y(i)-nf:y(i)+nf)
      pout   =  im(x(i)-nout:x(i)+nout, y(i)-nout:y(i)+nout)
      bkg = median(pout)
      flux1 = total(psmall-bkg)
      flux2 = total(plarge-bkg)
      shratio(i) = flux1/flux2
  endif else begin
      shratio(i) = 2.
  endelse
endfor
;help,shratio
return
end
