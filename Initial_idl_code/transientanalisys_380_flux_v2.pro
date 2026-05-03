;v2 16.04.2026
;simplify
;!-----TRANSIENTANALISYS_380_FLUX_v2-------
;(using files: Tr_380_Flux.csv, GalBackgr20MHz-1.jpg)
;
;;v1.2 23.06.2023
;;added .ps files output
;!-----TRANSIENTANALISYS_380_FLUX-------
;statistical characteristics of Frame1 UPTSNS - UTR-2 pulsar/transient survey of the northern sky
;(using files: Tr_380_Flux.csv, Tr_frame2_corr.csv, preset TrsNumber=380 for Tr_380_flux and TrsNumber=133 for Tr_frame2_corr)
;SNR hist
;DM hist
;Gb hist
;Transient map (use PAR_SHOW)
;Gb with tacking in account SNR
;RAINBOW_SCALE. - generate color "Rainbow" scale, output rs18 - 18 colors (RGB in digits)
;ALLKNOWNPULSHIST - generate a histogram of Gb pulsar distribution (start line: ALLKNOWNPULSHIST? using files: 438_all_kn_PSRs.csv, 195_fast_kn_PSRs.csv, 243_slow_kn_PSRs.csv)
;KNOWNPULSHIST - obsolet ALLKNOWNPULSHIST (only Gb)
;PAR_SHOW - Show transient parameters in the table when the mouse button is pressed (ESC - close the table, press the mouse button on the LEFT FIELD OUTSIDE THE MAP)
;
;-----------------------------------
;v1.1 9.06.2023 (added KnownPulsHist & AllKnownPulsHist)
;v1.0 4.11.2020

pro glactc,ra,dec,year,gl,gb,j, degree=degree, fk4 = fk4, $
   SuperGalactic = superGalactic
;+
; NAME:  
;       GLACTC
; PURPOSE:
;        Convert between celestial and Galactic (or Supergalactic) coordinates.
; EXPLANATION:
;       Program to convert right ascension (ra) and declination (dec) to
;       Galactic longitude (gl) and latitude (gb) (j=1) or vice versa (j=2).
;
; CALLING SEQUENCE: 
;       GLACTC, ra, dec, year, gl, gb, j, [ /DEGREE, /FK4, /SuperGalactic ]
;
; INPUT PARAMETERS: 
;       year     equinox of ra and dec, scalar       (input)
;       j        direction of conversion     (input)
;               1:  ra,dec --> gl,gb
;               2:  gl,gb  --> ra,dec
;
; INPUTS OR OUTPUT PARAMETERS: ( depending on argument J )
;       ra       Right ascension, hours (or degrees if /DEGREES is set), 
;                         scalar or vector
;       dec      Declination, degrees,scalar or vector
;       gl       Galactic longitude, degrees, scalar or vector
;       gb       Galactic latitude, degrees, scalar or vector
;
;       All results forced double precision floating.
;
; OPTIONAL INPUT KEYWORD PARAMETERS:
;       /DEGREE - If set, then the RA parameter (both input and output) is 
;                given in degrees rather than hours. 
;       /FK4 - If set, then the celestial (RA, Dec) coordinates are assumed
;              to be input/output in the FK4 system.    By default,  coordinates
;              are assumed to be in the FK5 system.    For B1950 coordinates,
;              set the /FK4 keyword *and* set the year to 1950.
;       /SuperGalactic - If set, the GLACTC returns SuperGalactic coordinates
;              as defined by deVaucouleurs et al. (1976) to account for the 
;              local supercluster. The North pole in SuperGalactic coordinates 
;              has Galactic coordinates l = 47.47, b = 6.32, and the origin is 
;              at Galactic coordinates l = 137.37, b= 0 
;              
; EXAMPLES:
;       Find the Galactic coordinates of Altair (RA (J2000): 19 50 47 
;       Dec (J2000): 08 52 06)
;
;       IDL> glactc, ten(19,50,47),ten(8,52,6),2000,gl,gb,1
;       ==> gl = 47.74, gb = -8.91
;
; PROCEDURE CALLS:
;       BPRECESS, JPRECESS, PRECESS
; HISTORY: 
;       FORTRAN subroutine by T. A. Nagy, 21-MAR-78.
;       Conversion to IDL, R. S. Hill, STX, 19-OCT-87.
;       Modified to handle vector input, E. P. Smith, GSFC, 14-OCT-94
;       Converted to IDL V5.0   W. Landsman   September 1997
;       Added DEGREE keyword, C. Markwardt, Nov 1999
;       Major rewrite, default now FK5 coordinates, added /FK4 keyword
;       use external precession routines    W. Landsman   April 2002
;       Add /Supergalactic keyword W. Landsman  September 2002
;       Fix major bug when year not 2000 and /FK4 not set W. Landsman July 2003
;-
;ra=67.4412225
;dec=13.708891
;year=2000
;j=1
;coords=glactc,(67.4412225),(13.708891),2000,gl,gb,1 (/DEGREES)

if N_params() lt 6 then begin
     print,'Syntax -  glactc, ra, dec, year, gl, gb, j, [/DEGREE, /FK4]'
     print,'j = 1: ra,dec --> gl,gb   j = 2:  gl,gb -->ra,dec'
     return
endif
radeg = 180.0d/!DPI
;
; Galactic pole at ra 12 hrs 49 mins, dec 27.4 deg, equinox B1950.0
; position angle from Galactic center to equatorial pole = 123 degs.

 if keyword_set(SuperGalactic) then begin
    rapol = 283.18940711d/15.0d & decpol = 15.64407736d
    dlon =  26.73153707 
 endif else begin 
   rapol = 12.0d0 + 49.0d0/60.0d0 
   decpol = 27.4d0
   dlon = 123.0d0
 endelse
   sdp = sin(decpol/radeg)
   cdp = sqrt(1.0d0-sdp*sdp)
   radhrs=radeg/15.0d0

; Branch to required type of conversion.   Convert coordinates to B1950 as 
; necessary
case j of                   
    1:  begin
        if not keyword_set(degree) then  ras = ra*15.0d else ras =ra
        decs = dec
        if not keyword_set(fk4) then begin
                 if year NE 2000 then precess,ras,decs,year,2000
                 bprecess,ras,decs,ra2,dec2
                 ras = ra2
                 decs = dec2
       endif else if year NE 1950 then precess,ras,decs,year,1950,/fk4
        ras = ras/radeg - rapol/radhrs 
        sdec = sin(decs/radeg)
        cdec = sqrt(1.0d0-sdec*sdec)
        sgb = sdec*sdp + cdec*cdp*cos(ras)
        gb = radeg * asin(sgb)
        cgb = sqrt(1.0d0-sgb*sgb)
        sine = cdec * sin(ras) / cgb
        cose = (sdec-sdp*sgb) / (cdp*cgb)
        gl = dlon - radeg*atan(sine,cose)
        ltzero=where(gl lt 0.0, Nltzero)
        if Nltzero ge 1 then gl[ltzero]=gl[ltzero]+360.0d0
        return
        end
    2:  begin
        sgb = sin(gb/radeg)
        cgb = sqrt(1.0d0-sgb*sgb)
        sdec = sgb*sdp + cgb*cdp*cos((dlon-gl)/radeg)
        dec = radeg * asin(sdec)
        cdec = sqrt(1.0d0-sdec*sdec)
        sinf = cgb * sin((dlon-gl)/radeg) / cdec
        cosf = (sgb-sdp*sdec) / (cdp*cdec)
        ra = rapol + radhrs*atan(sinf,cosf)
        ra = ra*15.0d
         if not keyword_set(fk4) then begin
                    ras = ra & decs = dec
                  jprecess,ras,decs,ra,dec
                  if year NE 2000 then precess,ra,dec,2000,year
        endif else if year NE 1950 then begin
                  precess,ra,dec,1950,year,/fk4
        endif 
                   
        gt36 = where(ra gt 360.0, Ngt36)
        if Ngt36 ge 1 then ra[gt36] = ra[gt36] - 360.0d0
        if not keyword_set(degree) then      ra = ra / 15.0D0

   
        return
        end
endcase
end

PRO Par_show,RA,dec,DM_corr,SNR_corr,S_o,galmap ; send all data of the transients
DEVICE, CURSOR_STANDARD = 32649;32512 - arrow; type of cursor mark
START: cursor, x, y, /device             ; get cursor position - in picsels: x&y
wset, 17 & plot,-RA, DEC,psym=4, xrange=[-24,0], yrange=[-20,80], /ystyle, /xstyle, XTICKS=6, /noerase, color=0, XTITLE = 'RA, h', YTITLE = 'Dec, deg',xtickname=['24','20','16','12','8','4','0']   ; replot all data (plot cleaning)
if (x LT 71) then goto, FINISH           ; check ESC
if (x GT 900)then window, 18, xsize=200, ysize=190, xpos=600, ypos=600 else window, 18, xsize=200, ysize=190, xpos=1400, ypos=600  ; choise the inform winwow position - right or left part of plot

yDEC=(y-42)/888.*100.-20                 ; calculation y picsel position in degrees - DECLINATION
xRAp=(1500-x)                            ; calculation x picsel position (inverse) in picsel
xRAf=xRAp*24/1430.                       ; RA - in hours (float data)
xRAh=floor(xRAf)                         ; RA - in hours (integer data)
xRAm=(xRAf-xRAh)*60                      ; RA - in minutes (float data)

ld=RA                                    ; make array ld - lisr of distances - with same dimention as RA[]
ld=sqrt((RA-xRAf)^2+(dec-yDEC)^2)        ; calculation of distances
ldsort=ld                                ; make array ldsort with same dimention as ld[]
idx=sort(ld)                             ; calculate index array by distance increasing
ctrn=idx[0]                              ; Closest TRansient Number
wset, 17 & plot,[-RA[ctrn],-RA[ctrn]], [DEC[ctrn], DEC[ctrn]],psym=4, xrange=[-24,0], /xstyle, XTICKS=6, yrange=[-20,80], /ystyle, /noerase, color=255, XTITLE = 'RA, h', YTITLE = 'Dec, deg',xtickname=['24','20','16','12','8','4','0']   ; plot selected transient in RED color
wset, 17 & plot,-RA, DEC,psym=4, xrange=[-24,0], yrange=[-20,80], /ystyle, /xstyle, XTICKS=6, /noerase, /nodata, color=0, XTITLE = 'RA, h', YTITLE = 'Dec, deg',xtickname=['24','20','16','12','8','4','0']                                ; plot BLACK frame with no data
;STOP
wset,18 & xyouts, 10, 10, 'b ='+STRMID(string(galmap[1,ctrn]),4,10), /device, color=255+255L*256+255*65536L                                       ; plot by xyouts transient informatios
wset,18 & xyouts, 10, 30, 'l ='+STRMID(string(galmap[0,ctrn]),4,10), /device, color=255+255L*256+255*65536L                                       ; plot by xyouts transient informatios
wset,18 & xyouts, 10, 50, 'DEC ='+STRMID(string(DEC[ctrn]),4,10), /device, color=255+255L*256+255*65536L                                       ; plot by xyouts transient informatios
wset,18 & xyouts, 10, 70, 'RA ='+STRMID(string(floor(RA[ctrn])),4,10)+'h:'+STRMID(string((RA[ctrn]-floor(RA[ctrn]))*60.),4,10)+'m', /device, color=255+255L*256+255*65536L
wset,18 & xyouts, 10, 90, 'SNR_CORR ='+STRMID(string(SNR_CORR[ctrn]),4,10), /device, color=255+255L*256+255*65536L
wset,18 & xyouts, 10, 110, 'FLUX ='+STRMID(string(S_o[ctrn]),4,10), /device, color=255+255L*256+255*65536L
wset,18 & xyouts, 10, 130, 'DM_CORR ='+STRMID(string(DM_CORR[ctrn]),4,10), /device, color=255+255L*256+255*65536L
wset,18 & xyouts, 10, 170, 'TRS # '+STRMID(string(ctrn+1),4,10), /device, color=255+255L*256+255*65536L
;STOP
wait, 1                                   ; waiting for mouse buffer cleaning
goto, START                               ; return to transient choise
FINISH: wait, 0.01                        ; waiting for mouse buffer cleaning
end ;PRO Par_show


PRO TransientAnalisys_380_flux_v2

!P.COLOR=0
!P.BACKGROUND=16777215
!P.FONT=-1

;Time_from_start,RA,dec,DM,SNR,DM_corr,SNR_corr,Tx1000_K,S_o,S_o50
filename = DIALOG_PICKFILE(/READ, FILTER = '*.csv')
OPENR, 1, filename
all=string(1)
str=string(1)
;READ_JPEG ,'C:\Users\Ryzen7\IDLWorkspace71\Default\GalBackgr20MHz-forSurvey.jpg', GalBackgr , /GRAYSCAL
;READ_JPEG ,'GalBackgr20MHz-1.jpg', GalBackgr , /GRAYSCAL
imname = DIALOG_PICKFILE(/READ, FILTER = '*.jpg'); GalBackgr20MHz-1.jpg
READ_JPEG , imname, GalBackgr , /GRAYSCAL

;TrsNumber=1082 ; frame1
;TrsNumber=133 ; frame2
TrsNumber=380 ; Tr_380_flux

Time_from_start=fltarr(TrsNumber)
RA=fltarr(TrsNumber)
dec=fltarr(TrsNumber)
DM=fltarr(TrsNumber)
SNR=fltarr(TrsNumber)
DM_corr=fltarr(TrsNumber)
SNR_corr=fltarr(TrsNumber)
Tx1000_K=fltarr(TrsNumber)
S_o=fltarr(TrsNumber)
S_o50=fltarr(TrsNumber)
galmap=dblarr(2,TrsNumber)

readf,1,str & str=strcompress(str, /REMOVE_ALL)
Title = Str_Sep(str,',')
;STOP
all=n_elements(pt)
num=0
while not eof(1) do begin
  readf,1,str & str=strcompress(str)
  all = Str_Sep(str,',')
  Time_from_start[num]=float(all[0])
  RA[num]=float(all[1])
  dec[num]=float(all[2])
  DM[num]=float(all[3])
  SNR[num]=float(all[4])
  DM_corr[num]=float(all[5])
  SNR_corr[num]=float(all[6])
  Tx1000_K[num]=float(all[7])
  S_o[num]=float(all[8])
  S_o50[num]=float(all[9])
  num=num+1
endwhile;file
close,1
Threshold=8.
;-----------------------------------------
inds=where((SNR_corr gt Threshold) and (dec lt 75.))
;-----------------------------------------
!P.COLOR=0
!P.BACKGROUND=16777215
!P.FONT=-1

window, 2, title='Galactic latitude', xsize=350, ysize=210, xpos=0, ypos=45
for k=0,TrsNumber-1 do begin
 raj=RA[k]
 decj=DEC[k]
 glactc, raj,decj,2000,gl,gb,1
 galmap[0,k]=gl
 galmap[1,k]=gb
 endfor; k
wset, 2 & plot,indgen(18)*10-85, histogram(galmap[1,inds],bins=10), psym=10, xrange=[-90,90], /xstyle, XTICKLEN=0.02, YTICKLEN=0.02, XTICKS=6, XTITLE = 'b, deg', YTITLE = 'N'

window, 3, title='SNR', xsize=350, ysize=210, xpos=0, ypos=290
wset, 3 & plot, Threshold+indgen(21), 0.1+histogram(SNR_corr[inds], bins=1),/ylog,/xstyle,xrange=[Threshold,30],yrange=[0.5,300],/ystyle,  psym=10, XTITLE = 'S/N ratio', YTITLE = 'N'

window, 4, title='Flux', xsize=350, ysize=210, xpos=0, ypos=535
wset, 4 & f_b=5 & h_flux=histogram(Tx1000_K[inds], bins=f_b) & n_h=n_elements(h_flux) & h_f=intarr(n_elements(h_flux)*f_b) & for m=0,n_h-1 do h_f[f_b*m:f_b*(m+1)-1]=h_flux[m]
plot, 21+indgen(100), 0.1+h_f, /ylog, /xstyle, xrange=[21,120],  yrange=[0.5,300],/ystyle  ,  psym=10, XTITLE = 'Flux, Jy', YTITLE = 'N'

window, 5, title='DM', xsize=350, ysize=210, xpos=0, ypos=780
wset, 5 & plot,indgen(30)+1, histogram(DM_corr[inds],bins=1), psym=10, XTITLE = 'DM, pc/cc', YTITLE = 'N'

window, 17, title='Transient map', xsize=24*60+80, ysize=900+50, xpos=380, ypos=45
wset, 17 & plot,-RA[inds], DEC[inds],psym=4, xrange=[-24,0], /xstyle, XTICKS=6, yrange=[-20,80], /ystyle, XTITLE = 'RA, h', YTITLE = 'Dec, deg',xtickname=['24','20','16','12','8','4','0']
wset, 17 & tv, rebin(GalBackgr/2.+127,1430,888),72,42
wset, 17 & plot,-RA[inds], DEC[inds],psym=4, xrange=[-24,0], /xstyle, XTICKS=6, yrange=[-20,80], /ystyle, /noerase, color=0, XTITLE = 'RA, h', YTITLE = 'Dec, deg',xtickname=['24','20','16','12','8','4','0']
wset, 17 & XYOUTS, 10, 900, 'ESC', charsize=2.2 ,/device, FONT=2 , ORIENTATION=0, color=0; 16777215L
Par_show,RA,dec,DM_corr,SNR_corr,S_o,galmap

WDELETE, 17

STOP
END

