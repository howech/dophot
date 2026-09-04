
pro params_dp1_pim,  img,  fitsimage, filroot,  sigdef, b4def, b6def, b8def, skyval, epdn, fpdn, sat, cmax, mprec, topheader,  empflag, empstarx, empstary, empstarz,  origroot 
;
;
;
;;;  Modified from: pro d4prep_mkparamdecam_f, fitsimage, extnum, filroot, sigdef, b4def, b6def, b8def, apply_mask, maskfile, chpnam, empflag
;
  
;;;   skyval and fpdn are passed -- they were created when img was rescaled..
;  
;  ....   apply passed values for parameters:
;
         sigma = sigdef
         beta4 = b4def
         beta6 = b6def
         beta8 = b8def
         filrootx = filroot
;
;
	fwhm = 2.35*sigma
        pxth = 1.0/(0.5*!pi*sigma*sigma) ;; i.e  1./(# of pixels within 0.7 sigma radius)  ........   or 1/!pi times full area under Gaussian 
        pxth = min([1., pxth])
        pxth = max([pxth, 0.1])
;;;        pxth = max([pxth, 0.06])

;              pxth = 1.   ;; for now... good for deep images
	if(beta4 ge 1.) then nfitbox = 2*nint( fwhm )  + 1
        if(beta4 lt 1. and beta4 gt 0.5) then nfitbox = 2*nint(1.25*fwhm )  + 1
        if(beta4 lt 0.5) then nfitbox = 2*fix( 1.5*fwhm )  + 1
        nfitbox = min([nfitbox, 31])
        nfitbox = max([nfitbox, 9])
	maskbox = fix(1.5*(fwhm)) + 1
	apbox = 31
;        empbox = 2.*nint(4.*fwhm) + 1
        empbox = min([35, 3*nint(nfitbox)])    ;; 3x odd number = odd number !!
        empbox = max([15, empbox])
        empbox = long(empbox)
;
;	epdn = fxpar(imheader, 'GAINA')
;        epdn = 1  ;;; its the way the deep image has been scaled to  photons...
;       epdn is now passed to this routine...        
;	rdne = fxpar(imheader, 'RDNOISEA')
        rdne = 15  ;;;;    placeholder for future needs 
        if(rdne le 1.) then rdne = 8.  ;; provided in case RDNOISEA is missing 
        rdne = max([rdne, epdn + 1.])
;       
;;        skyval = median(img)
;;;;;    skyval is passed to this routine.....         
;;;;        skyval = skyval/2.  ; scale sky to match image division when integerizing 
	nse_dn = sqrt(skyval*epdn + rdne*rdne)/epdn
;;;;        stats1, img/2., skymean, skyrms, skymeanerr 
        stats1, img, skymean, skyrms, skymeanerr 
;        bottom = nint( skyval - 8.*nse_dn 
        bottom = min([ ( skyval - 4.*nse_dn ), (skyval - 1.5*skyrms), -100. ])
        bottom = max([bottom, -1000.])
;        bottom = max([ bottom, 1.+ epdn ])
;        bottom = nint(bottom)
;        thmin = 3.*nse_dn
;;        thmin = nse_dn
        thmax = empstarz/2.
        thmin = 0.5*nse_dn
;	hmedwid = nint(1.5*fwhm)
        hmedwid = nint(2.0*fwhm)
;
;        mprec = nint(thmin)
        mprec = nint(mprec) 
;
         if(empflag le 0) then begin
             themp = 0.00
          endif else begin
;              themp =  thmin*(2.^12) + skyval
              themp = thmin*(2.^5)
              themp = max( [themp,  200.] )
              themp = min([themp, 25000.])
              themp = max( [themp, empstarz/8.])
           endelse  
;                      
;	pardef = '/Users/saha/MOSstuff/PDM3.dat'
;	pardef = '/home/saha/Ephot/PDM4.dat'
        pardef = '/home/saha/p_decam_c'

;;;        etime = fxpar(topheader, 'EXPTIME')
            etime = 1.      ;;;;   fudged...
;;;        if(etime eq 0) then 	etime = fxpar(imheader, 'EXPTIME')
;;;	airmass = fxpar(topheader, 'AIRMASS')
;;;        if(airmass eq 0) then   airmass = fxpar(imheader, 'AIRMASS')
;;;        if(airmass eq 0) then begin
;;;            zd = fxpar(topheader, 'ZD')
;;;             airmass = 1./cos(ZD*!pi/180.)
;;;         endif
;;        chpnam = ' '
;;        chpnam = fxpar(imheader, 'EXTNAME')
          filter = '  '
          filter = fxpar(topheader, 'HIERARCH LSST BUTLER DATAID BAND')    ;;;; topheader needs to be passed
;;        if(filter eq '  ') then filter = fxpar(imheader, 'FILTER')
;                 
;
	SFWHM  = strjoin( ['FWHM = ', strtrim(string(fwhm), 2)] )
        SPXTH = strjoin( ['PIXTHRESH = ', strtrim(string(pxth), 2)] )
	SSKY   = strjoin( ['SKY = ', strtrim(string(skyval), 2)] )
	SNFITX = strjoin( ['NFITBOX_X = ', strtrim(string(nfitbox), 2)] )
	SNFITY = strjoin( ['NFITBOX_Y = ', strtrim(string(nfitbox), 2)] )
	SNMSKX = strjoin( ['MASKBOX_X = ', strtrim(string(maskbox), 2)] )
	SNMSKY = strjoin( ['MASKBOX_Y = ', strtrim(string(maskbox), 2)] )
	SNAPX  = strjoin( ['APBOX_X = ', strtrim(string(apbox), 2)] )
	SNAPY  = strjoin( ['APBOX_Y = ', strtrim(string(apbox), 2)] )
	SPARDF = strjoin( ['PARAMS_DEFAULT = ', "'", pardef, "'"] )
	SBOT   = strjoin( ['IBOTTOM = ', strtrim(string(bottom), 2)] )
        STHMIN = strjoin( ['THRESHMIN = ', strtrim(string(thmin), 2)] )
        STHMAX = strjoin( ['THRESHMAX = ', strtrim(string(thmax), 2)] )
        SEPDN  = strjoin( ['EPERDN = ', strtrim(string(epdn), 2)] )
	SRDNE  = strjoin( ['RDNOISE = ', strtrim(string(rdne), 2)] )
	SBETA4 = strjoin( ['BETA4 = ', strtrim(string(beta4), 2)] )
	SBETA6 = strjoin( ['BETA6 = ', strtrim(string(beta6), 2)] )
	SBETA8 = strjoin( ['BETA8 = ', strtrim(string(beta8), 2)] )
	SHMDWX = strjoin( ['JHXWID = ', strtrim(string(hmedwid), 2)] )
	SHMDWY = strjoin( ['JHYWID = ',  strtrim(string(hmedwid), 2)] )
        SRESID = strjoin( ['RESIDNOISE = ', '0.3'] )
        SEMPRESID = strjoin(['EMP_RESIDNOISE = ', ' 0.03'])
        SEMPBOX = strjoin( ['NEMP_PSF_BOX = ', strtrim(string(empbox), 2)] ) 
        STHEMP = strjoin( ['THRESHEMP = ',  strtrim( string(themp), 2) ] )
        SCMAX   = strjoin(['CENTINTMAX = ', strtrim( string(cmax), 2) ] )
        SITOP     =  strjoin(['ITOP = ', strtrim( string(sat), 2) ] )
        SCTPERSAT = strjoin(['CTPERSAT = ', strtrim(  string( 0.5*(cmax+sat) ), 2) ] )
        SMPREC = strjoin(['MPREC = ', strtrim( string(mprec), 2) ] )
        SNPHSUB = strjoin(['NPHSUB = ',  strtrim( string(2*thmin), 2) ] )
        SNPHOB = strjoin(['NPHOB = ',  strtrim( string(2*thmin), 2) ] )
        SFTPRNTNSE = strjoin(['FOOTPRINT_NOISE = ',   '2.0'])

        SEMPSTARX = strjoin( ['EMP_STAR_X = ', strtrim( string(empstarx), 2)] )
        SEMPSTARY = strjoin( ['EMP_STAR_Y = ', strtrim( string(empstary), 2)] )
        SEMPSTARZ = strjoin( ['EMP_STAR_Z = ', strtrim( string(empstarz), 2)] )
;                     
	;;; Open DOIT file ;;;
	get_lun, u2
	openw, u2, strjoin( ['doit_', strtrim(filrootx, 2)] )
	printf, u2, '#!/bin/csh'
        ;;; Open Followup file with commands subsequent to Dophot:
	get_lun, u20
	openw, u20, strjoin( ['finish_', strtrim(filrootx, 2)] )
	printf, u20, '#!/bin/csh'

		xtn = ''

;;;;	   imname  = strjoin( [strtrim(filrootx, 2), xtn, '.fit'] )
	   imname  = strjoin( [strtrim(filrootx, 2), xtn, '.fits'] )
	   outfil  = strjoin( [strtrim(filrootx, 2), xtn, '.doq'] )
	   apname  = strjoin( [strtrim(filrootx, 2), xtn, '.ap'] )
	   apbname = strjoin( [strtrim(filrootx, 2), xtn, '.apb'] )
	   metaname = strjoin( [strtrim(filrootx, 2), xtn, '.meta'] )
	   parname = strjoin( ['p_', strtrim(filrootx), xtn, '.dat'] )
	   parname = strcompress(parname, /remove_all)  
           pointer = 'AAA'
           origfits = strjoin( [origroot, '.fits'] )
	

	   get_lun, unit
	   openw, unit, parname
	    printf, unit, SFWHM
            printf, unit, SPXTH
	    printf, unit, SSKY
	    printf, unit, SNFITX
	    printf, unit, SNFITY
	    printf, unit, SNMSKX
	    printf, unit, SNMSKY
	    printf, unit, SNAPX
	    printf, unit, SNAPY
	    printf, unit, SPARDF
	    printf, unit, SBOT
            printf, unit, STHMAX
            printf, unit, STHMIN
	    printf, unit, SEPDN
	    printf, unit, SRDNE
	    printf, unit, SBETA4
	    printf, unit, SBETA6
	    printf, unit, SBETA8
	    printf, unit, SHMDWX
	    printf, unit, SHMDWY
            printf, unit, SRESID
            printf, unit, SEMPRESID
            printf, unit, SEMPBOX
            printf, unit, SEMPSTARX
            printf, unit, SEMPSTARY
            printf, unit, SEMPSTARZ
            printf, unit, STHEMP
            printf, unit, SITOP
            printf, unit, SCTPERSAT
            printf, unit, SCMAX
            printf, unit, SMPREC
            printf, unit, SNPHSUB
            printf, unit, SNPHOB

;;**********            add ITOP, NPHSUB, NPHOB,  CENTINTMAX ***  Done!!
;
	    if( 3.*fwhm gt 35.) then begin
		apmax2 = 3.*fwhm
		apmax2 = 5*( nint(apmax2/5. + 0.5) )
		apmax2 = 8*apmax2/5
		SAPMAX2 = strjoin( ['APMAX2 = ', strtrim( string(apmax2), 2 )] )
		apskmin2 = nint( 40.*apmax2/56.)
		apskmax2 = nint( 60.*apmax2/56.)
		SAPSKMIN2 = strjoin(['APSKYMIN2 = ', $
				strtrim( string(apskmin2), 2 )] )
		SAPSKMAX2 = strjoin(['APSKYMAX2 = ', $
				strtrim( string(apskmax2), 2 )] )

		printf, unit, SAPMAX2
		printf, unit, SAPSKMIN2
		printf, unit, SAPSKMAX2
	    endif

	    printf, unit, strjoin( ['IMAGE_IN = ', "'", imname, "'"] )
	    printf, unit, strjoin( ['OBJECTS_OUT = ', "'", outfil, "'"] )
;;;	    printf, unit, strjoin( ['APCORRFILE = ', "'", apname, "'"] )
;;;	    printf, unit, strjoin( ['APCORRFILE2 = ', "'", apbname, "'"] )

            printf, unit, 'END'
;            
	    close, unit
	    free_lun, unit
;
;;   Image should already be written from calling program...
;            
	    get_lun, u3
	    openw, u3, metaname
;	    printf, u3, etime,   '               etime '
;	    printf, u3, airmass, '               airmass '
            printf, u3, filter,  '               filter '
            printf, u3, fpdn,   '             nJy per DN'
	    close, u3
	    free_lun, u3

;	    printf, u2, strjoin( ['/home/saha/D4phot << ', pointer] )
	    printf, u2, strjoin( ['/home/saha/D7phot << ', pointer] )
	    printf, u2, parname
	    printf, u2, pointer

	printf, u20, ' idl     << BB1 '
;;        printf, u20, ' @setup_apcorr '
;;        printf, u20, '.run mosapprocwtX'
;;        printf, u20, '.run sfitwtonechipX'
;;        printf, u20, '.run readdopx_all'
;;        printf, u20, '.run writedopx_all'
;;        printf, u20, '.run approcwtxonechip'
;;        printf, u20, '.run moscompapwtx'
        printf, u20, '.run writedopx_eposnn'
;;	if n_ext ne 0 then begin
;;	    printf, u20, ' mosapprocwt,  ', strjoin(["'",filrootx,"'"])
;;	endif else begin
;;	    printf, u20, ' approcwtXonechip, ',  strjoin(["'",filrootx,"'"]), $
;;			', ', 1000, ',', 2000
;;     endelse
        sfpdn = strtrim( string(fpdn), 2 )
        printf, u20, '.run qapcorrect_dp1'
;;;        ss = strjoin(['qapcorrect_dp1, ',  "'",filrootx,"'", ',  ',    '1, ',  sfpdn ]) ;; change 1 to 0 if you want to work on  empirical mags
        ss = strjoin(['qapcorrect_dp1, ',  "'",filrootx,"'", ',  ', '0, ',  sfpdn ]) ;; change 0 to 1 if you want to work on analytic mags        
        ss = ss + "  ,  '" + origfits +"'"
;        pause
        printf, u20, ss
;;        printf, u20, ' exit '
        printf, u20, ';'
        
;;;	printf, u20, 'BB1'

;;;;;;;;;;;;;   should bypass the writing of commands and files  to call
;;;;;;;;;;;;;   IRAF/mscctran with IDL wcs implementation (built into qap_correct_dp1)
;;;;;;;;;;;;;  Leaving code alone, so it can be recalled, but  uing
;;;;;;;;;;;;;  GOTO to bypass
        GOTO, BYPASS
        	
        radecproc = strjoin([filrootx , '.rdproc'])
;
        get_lun, u21
        fnm = strjoin( [filrootx, '_xyrd.pro'])
        openw, u21, fnm
        printf, u20,  'get_lun, xyz'
                printf, u21,  'get_lun, xyz'
          printf, u20, 'response = strarr(10)'
                 printf, u21, 'response = strarr(10)'
         printf, u20, "spawn, 'cl',  unit=xyz,  /noshell"
                 printf, u21, "spawn, 'cl',  unit=xyz,  /noshell"
;
        comm = strjoin([ "' ",  " cl < ",  radecproc, " '" ])
        fff = strjoin( ['printf,  xyz,', comm, ' '])
;        fff = strjoin(["'", fff, "'"])
        printf, u20, fff
                printf, u21, fff
         printf, u20,  '  readf, xyz,  response '
                printf, u21,  '  readf, xyz,  response '
         printf, u20,  'print, response'
                printf, u21,  'print, response'
         printf, u20, fff
                printf, u21, fff
         printf, u20, 'wait, 10.'
          printf, u20, 'close, xyz'
                printf, u21, 'close, xyz'
         printf, u20, 'free_lun, xyz'
                printf, u21, 'free_lun, xyz'
         printf, u20, " print, 'done!' "
                printf, u21, " print, 'done!' "
;
                printf, u20, ' exit '

        close, u21
        free_lun, u21

;                
	get_lun, u5
	openw, u5, radecproc

        
;	printf, u5, 'cl'
;;;	printf, u20, strjoin(['cl < ' , strtrim(radecproc)])
	printf, u5, 'mscred'
;
        s_ext = '1'
        strext = strjoin([ '[', s_ext, ']' ])
        fitsimage_n = strjoin([ strtrim(fitsimage, 2), strext ])

        n_ext = 0
	    infile = strjoin([filrootx, '.doqcap'])
	    outfile = strjoin([filrootx, '.rdcap1'])
	    stline = strjoin(['mscctran ', infile, ' ', outfile, $
			      ' ', fitsimage_n, ' logical world columns="3 4"  min_sig = 9'])
            printf, u5, 'set clobber = yes'
	    printf,u5, stline
	
	printf, u5, 'logout'
	close, u5
	free_lun, u5

   BYPASS:   	printf, u20, 'BB1'
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;        
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;


        
;;;;;   This is for doing the WCS in IDL, which will do teh distortion
;;;;;   terms from teh SIPs -- sets up the ".pro file to execite"
;;;;;;         code Pending  !!

        
        
	close, u2
	free_lun, u2
	close, u20
        free_lun, u20

;;;	file_chmod, strjoin( ['doit_', strtrim(filrootx, 2)] ) ,/a_execute
        com = 'chmod 755  ' + strjoin( ['doit_', strtrim(filrootx, 2)] )
        spawn, com
        com = 'chmod 755  ' + strjoin( ['finish_', strtrim(filrootx, 2)] )
        spawn, com

;;;;PAUSE

return
end
    

  
