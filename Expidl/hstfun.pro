PRO     HSTFUN, X, A, F, PDER
; 
Z = X/(1.4142*A(1))
F = A(0)/(1. + Z^2 + 0.5*A(2)*Z^4 + .16666667*A(3)*Z^6 + (1./24.)*A(4)*Z^8 )
PDER = fltarr(n_elements(X), 5)
PDER(*,0)=1./(1. + Z^2 + 0.5*A(2)*Z^4 + .16666667*A(3)*Z^6 + (1./24.)*A(4)*Z^8)
dfdt = A(0)*(-1.)*PDER(*,0)*PDER(*,0)
PDER(*,2) = dfdt*0.5*Z^4
PDER(*,3) = dfdt*.16666667*Z^6
PDER(*,4) = dfdt*Z^8 / 24.
PDER(*,1) = dfdt*(2*Z + 2.*A(2)*Z^3 + A(3)*Z^5 +.3333333*A(4)*Z^7)*(-1.)*Z/A(1)
;
return
end
