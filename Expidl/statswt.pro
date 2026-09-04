pro statswt, X, err, wtmean, rms, wterr, chisq_nu
;
if ( n_params(0) lt 4 ) then begin
  print, ' Call is : statswt, array, stderr_array, wtmean, rms, wterr [, chisq_nu] '
  return
endif
;
if(n_elements(x) lt 2) then begin
      print, ' Not enough points for calculating mean and rms... '
      return
endif
;
;
wt = 1./err^2
;
wtmean = total(wt*X)/total(wt)
wterr = sqrt( 1./total(wt) )
rms = sqrt(  (total( ( (X-wtmean)^2 )*wt) ) / (total(wt)) )
chisq = total(  wt*(X-wtmean)^2 )
chisq_nu = chisq/(n_elements(X)-1L)
;
; print, 'Chisq_nu = ', chisq_nu
;
return
end
