#!/usr/bin/env python3
"""X7 native USB controls: dry-run by default; --apply explicitly sends writes.
Wire format from alcatron/mb-x7-control PROTOCOL.md; no DSP readback claim.
"""
import argparse,json,os,select,struct,time
from pathlib import Path
PARAMS={'surround':0x00,'crystalizer':0x0e,'dialog':0x04,'smart-volume':0x08,'eq':0x12}
AMOUNTS={'surround':0x02,'crystalizer':0x10,'dialog':0x06,'smart-volume':0x0a}
BANDS=['31','62','125','250','500','1k','2k','4k','8k','16k']
def device():
 for p in Path('/sys/class/hidraw').glob('*'):
  if 'HID_ID=0003:0000041E:0000323A' in (p/'device/uevent').read_text(): return '/dev/'+p.name
 raise RuntimeError('X7 HID device unavailable')
def dsp(param,value):
 return bytes.fromhex('2000160ad50208')+bytes([param])+bytes.fromhex('2096')+struct.pack('>f',value)+bytes.fromhex('4d00')
def packet(control,value):
 if control in PARAMS and value in ('on','off'): return dsp(PARAMS[control],float(value=='on'))
 if control.endswith('-amount') and control[:-7] in AMOUNTS:
  v=float(value)
  if not 0<=v<=100: raise ValueError('Amount must be 0..100')
  return dsp(AMOUNTS[control[:-7]],v/100)
 if control.startswith('eq-') and control[3:] in ['level']+BANDS:
  v=float(value)
  if not -12<=v<=12: raise ValueError('EQ must be -12..12 dB')
  return dsp(0x14 if control=='eq-level' else 0x16+2*BANDS.index(control[3:]),v)
 if control=='smart-volume-mode' and value in ('normal','loud','night'): return dsp(0x0c,('normal','loud','night').index(value))
 if control=='output' and value in ('speakers','headphones'): return bytes.fromhex('234e00000080' if value=='speakers' else '234e01000000')
 raise ValueError('Unsupported control or value')
def query():
 fd=os.open(device(),os.O_RDWR|os.O_NONBLOCK)
 try:
  os.write(fd,bytes.fromhex('002312'));end=time.monotonic()+1
  while time.monotonic()<end:
   if select.select([fd],[],[],.1)[0]:
    reply=os.read(fd,128)
    if len(reply)>=5 and reply[1:3]==b'\x23\x12': return {'headphonesInserted':bool(reply[4]&4),'usbVerified':True}
  raise RuntimeError('X7 status query timed out')
 finally: os.close(fd)
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');parser.add_argument('control');parser.add_argument('value',nargs='?');a=parser.parse_args()
 if a.control=='status': print(json.dumps(query()))
 else:
  p=packet(a.control,a.value)
  if a.apply:
   fd=os.open(device(),os.O_RDWR)
   try: os.write(fd,b'\0'+p)
   finally: os.close(fd)
  print(json.dumps({'control':a.control,'value':a.value,'sent':a.apply,'packet':p.hex(),'readbackVerified':False}))
