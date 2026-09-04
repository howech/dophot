function bytmap, image, first, last
on_error, 2
;
	if(first le last) then begin
	    bytmage = bytscl(image, first, last)
	    return, bytmage
        endif
;
	bytmage = 255B - bytscl(image, last, first)
;
return, bytmage
end
