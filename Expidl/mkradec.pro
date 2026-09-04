pro mkradec, x, y,  mag, magerr, doqid, type,  sky,  doqapmag, apmagerr, apsky, xfw, yfw, tilt, exten, apminfit,  xp, yp, origfits, outfile
;
  hh0 = headfits(origfits)
  nhh0 = n_elements(hh0)
  hh1 = headfits(origfits, exten=1)
  hhh = [hh0(0:nhh0-2L), hh1]   ;; add hh1 to hh0, removing END keyword at end of original hh0
  nhhh = n_elements(hhh) 
; Add EQUINOX to hhh:
  heqx = 'EQUINOX =           2000.0'
  hhh = [hhh(0:nhhh-2L),  heqx,  'END']
  nhhh = n_elements(hhh) 
;;   ch = xp*0. -100.
  extast, hhh, astr
  xy2AD,  xp, yp, astr, a, d
;  writerdxyc_all, outfile, a, d, mag, magerr, doqid, type, sky, doqapmag, apmagerr, $
;   apsky, xfw, yfw, tilt, exten, apminfit, xp, yp, ch, ERROR = ERROR
;
  writerdxy, outfile, a, d, mag, magerr, doqid, type, sky, doqapmag, apmagerr, $
  apsky, xfw, yfw, tilt, exten, apminfit, xp, yp, ERROR = ERROR

  
  return
  end
