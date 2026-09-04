pro qapcorrect_dp1,  rootnam,  amagflag,  fpdn,  origfits
;
;;; rootname should have chip extension
; if amagflag ge 1 or if empirical mags are absent,   this routine will work
; on analytic profile fittted mags, NOT on empirical mags.
;
;;   this version should convert directly to AB mags when origin is
;;   LSST deep coadd  image with nJy pixels
;
if(n_params(0) lt 3) then begin
  print, 'Call is:  qapcorrect, rootnam, amagflag, fpdn, hh0'
  return
endif
;
fail = 0
;
apname = strjoin([rootnam, '.ap'])
readqap, apname, idap, xap, yap, apmags, naps
idap = long(idap)
;
doqname = strjoin([rootnam, '.doq'])
readdoq, doqname, x, y, amag, amagerr, doqid, type, asky, xfw, yfw, tilt, exten, doqapmag, apmagerr, apsky, apminfit, esky, emag, ex, ey, emagerr, ERROR=ERROR
nobj = n_elements(doqid)
;
avemag = mean(emag)
print,  avemag
if(avemag le -99.9) then begin 
   print,  'Looks like there are no empirical mags here... setting amagflag to 1'
   amagflag = 1
endif
;
if(amagflag  ge 1) then begin 
   print,  ' copying amag and amagerr to emag and emagerr (.doq file unaffected)'
   emag = amag
   emagerr = amagerr 
   esky = asky
   ex = x
   ey = y 
endif  else begin
   t2 = where( (type mod 10) eq 2 )
   emag(t2) = amag(t2)
   emagerr(t2) = amagerr(t2)
   t2z = where(emagerr(t2) eq 0.00)
   emagerr(t2(t2z)) = 99.
endelse


;
apcorrs = apmags
plot, [0.,0.], [0., 0.],  xra=[0, 8], yra=[2., -2], xsty=1, ysty=1, xth=2, yth=2, chars=1.5, charth=2 
apnum = findgen(8)
r5s = [0.]
xs = [0.]
ys = [0.]
mtc1 = [-1]
mtc2 = [-1]
emags = [99.99]
emerrs = [99.99]
for m1 = 0L, naps-1L do begin
        m2 = where(doqid eq idap(m1))
        if(emag(m2(0)) gt - 20.00 and emag(m2(0)) lt 0. and emagerr(m2(0)) gt 0.0) then begin 
             empmag = emag(m2(0))
             emperr  = emagerr(m2(0))
             apcorrs(*,m1) = apmags(*,m1) - empmag
             oplot,  apnum, apcorrs(*,m1)
             r5s = [r5s, apcorrs(4, m1)]
             emags = [emags, empmag]
             emerrs = [emerrs, emperr]
             xs = [xs, xap(m1)]
             ys = [ys, yap(m1)]
             mtc1 = [mtc1, m1]
             mtc2 = [mtc2, m2]
          endif
endfor
wait, 2.
;
mtc1 = mtc1(1,*)
mtc2 = mtc2(1,*)
xs = xs(1:*)
ys = ys(1,*)
r5s = r5s(1:*) 
emags = emags(1:*)
emerrs = emerrs(1:*)
naps = n_elements(r5s)
;
;
!p.multi=[0, 1, 2]
vdots, .8
maxy = max(r5s) + 0.5
miny = min(r5s) - 0.5
plot, emags, r5s, yr = [maxy, miny], psym=8, ysty=1
errplot, emags, r5s-emerrs, r5s+emerrs
brtest = min(emags)
rs = reverse(sort(emags))
fntlim = mean(emags(rs(0:2)))
print,  fntlim
maxemagf = fntlim - 3.
maxemagb = brtest + 2.2
maxemag = max([maxemagb, maxemagf])
;;pause
gg = where(-5 lt r5s and 3. gt r5s   and emags lt maxemag, ngg)    ;;;   eliminates apmgs measured as "Nan"
print, 'picked best ',  ngg, '  objects.'
oplot, emags(gg), r5s(gg), psym=8, color=255*256L
;
if(ngg lt 5) then begin ;;; try a one-time extending of the limiting brightness
   print, '... extending faint limit' 
   maxemag = maxemag + 1.
   gg = where(-5 lt r5s and 3. gt r5s   and emags lt maxemag, ngg)    ;;;   eliminates apmgs measured as "Nan"
   print, 'picked best ',  ngg, '  objects.'
   oplot, emags(gg), r5s(gg), psym=8, color=255*256L
endif   
;
;;; if still too few, then abort....
;
if(ngg lt 5)  then begin
     print, ' Fewer than 5 stars available for APCORR;  Aborting, fail = 1 '
     fail = 1
     return
endif
;
statswt, r5s(gg), emerrs(gg), wtmean, rms, wterr, chisq_nu
print, 'wtmean, rms, wterr, chisq_nu:  ', wtmean, rms, wterr, chisq_nu
oplot, [-20., 0.], [wtmean, wtmean], color=(255 + 255*256L)
oplot, [-20., 0.], [wtmean-wterr, wtmean-(wterr*max([1., chisq_nu]))], color=255
oplot, [-20., 0.], [wtmean+wterr, wtmean+(wterr*max([1.,chisq_nu]))], color=255
wait, 5.
;
offset = wtmean
print, ' Offset aperture magnitude correction: ',  offset
offserr = wterr
if(chisq_nu gt 1.) then offserr = chisq_nu*wterr
print, 'Offset aperture correction uncertainty (mags) = ', offserr
offsetsmall = offset
offserrsmall = offserr
;
;
;;;;;;;   Now get comparison to Big aperture:
;
comp_ap_bap, rootnam,  bapminap, apdiffaccu, fff
;
offset = offset + bapminap
offserr =  sqrt(  offserr^2 + apdiffaccu^2 )
print,  ' Offset and uncertainty after correction to large aperture: ',   offset, offserr
;
;
;;;;;;;;;apply corrections and update errors:
;
if(ngg ge 5) then begin
   jmtype = type mod 10
 ;  ok = where(jmtype eq  1 or jmtype eq 3 or jmtype eq 7, nok)
   ok = where(jmtype ne 8)
   mag = amag & mag(ok) = emag(ok) ;; mag will become  the output mag for types 1,3,7
   mag(ok) = mag(ok) + offset
   magerr = amagerr  & magerr(ok) = emagerr(ok)
   magerr(ok) = sqrt(magerr(ok)^2 + offserr^2) ;; add unc in ap correction to err estimate
   sky = asky  & sky(ok) = esky(ok)
endif
;
;;;; can do better if ngg > 50 ?  ;;;;;;;
;
if(ngg gt 50) then begin
   print,  " add to code  here to insert any pattern spatial systematics for offset.."
endif
;
;
;;;;   write out results:   ;;;;;;;
;
;;;;   read  exptime from meta file:
;;    metafile = strjoin([rootnam, '.meta'])
;;    get_lun, uu3
;;    openr, uu3, metafile
;;    readf, uu3, exptim
;;    readf, uu3, filter
;;    readf, uu3, fpdnm
;;    close, uu3
;;    free_lun, uu3
;
;;; Convert mags to instrumental system:
;
st = where(jmtype ne 8)
;  adjust = 2.5*alog10(exptim) + 30.75 ; ... so that same as system of older DoPHOT
                                ;   derivatives with fac of 2 dividing
                                ;   of image
  adjust = -2.5*alog10(fpdn) + 80.  - 48.60   ;   +80. because 1 nJY = 10^-32 cgs units
  mag(st) = mag(st) + adjust
;
  nnx = n_elements(x)
  apsky = replicate(offsetsmall, nnx)
  doqapmag = replicate(offset, nnx)
  apmagerr = replicate(offserr, nnx)
;
qapf  = strjoin([rootnam, '.doqcap'])
writedopx_eposnn,  qapf,  x, y,  mag, magerr, doqid, type,  sky,  doqapmag, apmagerr, apsky, xfw, yfw, tilt, exten, apminfit, ERROR = ERROR 
;
; pause
;
xp = x
yp = y
qrdcap =  strjoin([rootnam, '.rdcap'])
mkradec,  x, y,  mag, magerr, doqid, type,  sky,  doqapmag, apmagerr, apsky, xfw, yfw, tilt, exten, apminfit,  xp, yp, origfits, qrdcap
;
;p.multi=[0, 1, 1]
;;pause
return
end
