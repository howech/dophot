pro comp_ap_bap, rootname, offset, accu,  fail
;
;@setup_apcorr
;  
fail = 0
dcount = 0
;
if ( n_params(0) lt 2 ) then begin
  print, ' Call is : moscompapwt, rootname, fail '
  return
endif
;
;
apname = strjoin([rootname, '.ap'])
bapname = strjoin([rootname, '.bap'])
print, apname, bapname 
print, ' WARNING: .AP and .BAP files are expected to have exactly 8 different aperture measurements'
;
;
print, ' First reading in .AP file: '
readqap, apname, idap, xap, yap, apmags, naps
apmagerr = fltarr(naps)
for i = 0L, naps-1L do begin
    stats1, apmags(4:7, i),  ave, rms, errmean
    apmagerr(i) = rms
endfor
;
print, ' Then reading in .BAP file: '
readqap, bapname, idbap, xbap, ybap, bapmags, nbaps  
;
if(nbaps le 5) then begin
       print,   ' Less than 5 stars in BAP file   ... applying ZERO offset between small and large Apertures ' 
      offset = 0.00
      accu  =  0.20
      return
endif
;
bapmagerr = fltarr(nbaps)
for i = 0L, nbaps-1L do begin
    stats1, bapmags(4:7, i),  ave, rms, errmean
    bapmagerr(i) = rms
endfor
;
;
;
diffs = []
errdiffsqs = []
rapmag =[]
nmatch = 0
mtc1 = []
mtc2 = []
for m1 = 0L, nbaps-1L do begin 
       m2 = where(idap eq idbap(m1),  n_m2)      
       if( n_m2  eq 1 and  bapmagerr(m1) ge 0.0 and bapmagerr(m1) lt 5.0  and  apmagerr(m2) ge 0.0 and apmagerr(m2) lt 5.0) then begin 
                 diffs = [diffs, bapmags(4, m1) - apmags(4, m2(0))]
                 rapmag = [rapmag, apmags(4, m2(0))]
                 errdiffsqs =  [errdiffsqs, bapmagerr(m1)^2 + apmagerr(m2(0))^2 ]
                 nmatch = nmatch + 1
                 mtc1 = [mtc1, m1]
                 mtc2 = [mtc2, m2]
        endif
endfor
n_diffs = n_elements(diffs)
errdiffs = sqrt(errdiffsqs)
; errdiffs(where(errdiffs le 0.01)) = 0.01
;
; pause
;
brtst = min(rapmag)
maxmagok = brtst + 2.5
ok = where(rapmag le maxmagok, nok)
;;pause
;
if(nok le 5) then begin      ;  try extending faint limit...
   maxmagok = brtst + 3.5
   ok = where(rapmag le maxmagok, nok)
endif   
;
if(nok le 5) then begin
      print, 'Too few points for BAP correction: defaulting to zero'
      offset = 0.00
      accu  =  0.20
      return
endif
;
statswt,  diffs(ok),  errdiffs(ok), wtmean, rms, wterr, chisq_nu
offset = wtmean
if(chisq_nu le 1.) then begin 
    accu = wterr
 endif else begin     
    accu = wterr*chisq_nu
 endelse
;
;;;;;;;;begin plot block
maxy = max(diffs) + 0.2
miny = min(diffs) - 0.2
vcircs, .6
plot,  rapmag,  diffs, yr=[maxy, miny], psym=8, ysty=1,  xth=3, yth=3, charth=2, chars=2
errplot, rapmag, diffs-errdiffs, diffs+errdiffs
vdots, .8
oplot, rapmag(ok), diffs(ok), psym=8, color=255*256L
oplot, [-20., 0.], [offset,offset], color=(255 + 255*256L), thick=2
oplot, [-20., 0.], [offset-accu, offset-accu], color=255
oplot, [-20., 0.], [offset+accu, offset+accu], color=255
;;;;;;;;; end plot block
;
print,  ' Offset =  ', offset,  '   Uncertainty (1-sig) =  ' ,  accu
;
;pause
return
end
