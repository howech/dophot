pro percentile_hilo, x, prclo, prchi,  xprclo, xprchi
  ;   x is array
  ; prclo is low percentile value to find
  ; prchi is high percentile value to find
  ;  xprclo  is the prclo percentile of x
  ;  xprchi  is the prchi percentile of x
  
  nn  = n_elements(x)
  xs = x(sort(x))
  nprclo = nint( (prclo/100.)*nn )
  xprclo = xs(nprclo)
  nprchi = nint( (prchi/100.)*nn )
  xprchi = xs(nprchi)

  return
  end
  
