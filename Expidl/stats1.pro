pro stats1, x, mean, rms, errmean
;
   if(n_elements(x) lt 2) then begin
      print, ' Not enough points for calculating mean and rms... '
      return
   endif
; 
   mean = total(x)/n_elements(x)
   rms = sqrt( total( (x-mean)^2 )/(n_elements(x)-1) )
   errmean = rms / sqrt(n_elements(x))
;
   return
   end
   
