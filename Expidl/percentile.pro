pro percentile, x, prc, xprc
  ;   x is array
  ; prc is percentile value to find
  ;  xprc  is the prc percentile of x
  
  nn  = n_elements(x)
  xs = x(sort(x))
  nprc = nint( (prc/100.)*nn )
  xprc = xs(nprc)

  return
  end
  
