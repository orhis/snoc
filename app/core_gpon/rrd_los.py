# -*- coding: utf-8 -*-
"""Czytnik RRD optycznego (Cacti v0003, 64-bit LE) — seria 30-min MIN onuRxOpticalLevel + detekcja LOS.
Bez rrdtool. Layout zweryfikowany (rozmiar pliku = suma sekcji)."""
import struct, math

def read_rra(fn, rra_idx=5, ds_name="onuRxOpticalLevel"):
    """Odczyt dowolnego RRA (idx wg nagłówka; MIN: 4=5-min/50h, 5=30-min/14dni)."""
    b=open(fn,"rb").read()
    ds_cnt,rra_cnt,pdp_step=struct.unpack("<QQQ",b[24:48]); off=48+80
    ds=[]
    for _ in range(ds_cnt): ds.append(b[off:off+20].split(b'\0')[0].decode('latin1')); off+=120
    rra=[]
    for _ in range(rra_cnt):
        cf=b[off:off+20].split(b'\0')[0].decode('latin1'); o2=off+20; o2+=(8-(o2%8))%8
        rows,pdp=struct.unpack("<QQ",b[o2:o2+16]); rra.append((cf,rows,pdp)); off=o2+16+80
    last_up=struct.unpack("<q",b[off:off+8])[0]; off+=16
    off+=ds_cnt*112+rra_cnt*ds_cnt*80
    rra_ptr=struct.unpack("<%dQ"%rra_cnt,b[off:off+8*rra_cnt]); off+=8*rra_cnt
    base=off
    for i in range(rra_idx): base+=rra[i][1]*ds_cnt*8
    cf,rows,pdp=rra[rra_idx]; step=pdp*pdp_step; cur=rra_ptr[rra_idx]; dsi=ds.index(ds_name)
    last_slot=(last_up//step)*step; out=[]
    for k in range(rows):
        row=(cur-k)%rows; t=last_slot-k*step
        v=struct.unpack("<d",b[base+(row*ds_cnt+dsi)*8:base+(row*ds_cnt+dsi)*8+8])[0]
        out.append((t,v))
    out.reverse(); return last_up,step,out

def read_min30(fn, ds_name="onuRxOpticalLevel"):
    b=open(fn,"rb").read()
    ds_cnt,rra_cnt,pdp_step=struct.unpack("<QQQ",b[24:48]); off=48+80
    ds=[]
    for _ in range(ds_cnt): ds.append(b[off:off+20].split(b'\0')[0].decode('latin1')); off+=120
    rra=[]
    for _ in range(rra_cnt):
        cf=b[off:off+20].split(b'\0')[0].decode('latin1'); o2=off+20; o2+=(8-(o2%8))%8
        rows,pdp=struct.unpack("<QQ",b[o2:o2+16]); rra.append((cf,rows,pdp)); off=o2+16+80
    last_up=struct.unpack("<q",b[off:off+8])[0]; off+=16
    off+=ds_cnt*112+rra_cnt*ds_cnt*80
    rra_ptr=struct.unpack("<%dQ"%rra_cnt,b[off:off+8*rra_cnt]); off+=8*rra_cnt
    data_off=off
    # RRA[5] = MIN 30-min (złota reguła)
    base=data_off
    for i in range(5): base+=rra[i][1]*ds_cnt*8
    cf,rows,pdp=rra[5]; step=pdp*pdp_step; cur=rra_ptr[5]; dsi=ds.index(ds_name)
    last_slot=(last_up//step)*step; out=[]
    for k in range(rows):
        row=(cur-k)%rows; t=last_slot-k*step
        v=struct.unpack("<d",b[base+(row*ds_cnt+dsi)*8:base+(row*ds_cnt+dsi)*8+8])[0]
        out.append((t,v))
    out.reverse(); return last_up,step,out

def is_dark(series, at_ts, win=4):
    """LOS jeśli ostatnie `win` próbek <= at_ts są NaN (utrzymany brak sygnału)."""
    pre=[v for t,v in series if t<=at_ts][-win:]
    return len(pre)==win and all(math.isnan(v) for v in pre)
