#!/usr/bin/env python3
"""Mechanically builds data/data.js from round2 case JSON. No hand-entered evidence."""
import json,glob,os
R='/workspace/tech-317-qa/rerun/round2'
S=[('jwt','§1 JWT','01-jwt'),('otp','§2 OTP','02-otp'),('hours','§4 Hours','04-hours'),('reg','§7 Regression','07-regression')]
out={'sections':[]}
for key,title,d in S:
    cases=[]
    for f in sorted(glob.glob(f'{R}/{d}/cases/*.json')):
        j=json.load(open(f)); c=j['case']; c['_file']=f; c['_run']=j.get('run',{})
        cases.append(c)
    out['sections'].append({'key':key,'title':title,'dir':d,'cases':cases})
os.makedirs('data',exist_ok=True)
open('data/data.js','w').write('window.QA='+json.dumps(out)+';')
print({s['key']:len(s['cases']) for s in out['sections']})
