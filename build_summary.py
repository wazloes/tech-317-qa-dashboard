#!/usr/bin/env python3
"""Derives data/summary.js + per-case files from data/data.js. Mechanical only — no hand-entered evidence."""
import json,os
s=open('data/data.js').read();d=json.loads(s[s.index('{'):].rstrip().rstrip(';'))
RANK=['BOTH-BUG','MISMATCH','INVALID','PARTIAL','BLOCKED','SKIPPED','EXPECTED-DIFF','PASS']
def short(v,n=140):
    t=v if isinstance(v,str) else json.dumps(v)
    return t if len(t)<=n else t[:n]+'…'
def st(side):
    if not side: return None
    r=side.get('response') or {}
    if side.get('transport_error'): return 'ERR'
    return r.get('status')
def why(c,probes):
    v=c['result']['verdict'];cov=c['result']['coverage']
    bad=[p for p in probes if p['verdict'] not in('PASS',) and p['status']=='ran']
    nr=[p for p in probes if p['status']!='ran']
    if v in('MISMATCH','BOTH-BUG','EXPECTED-DIFF') and bad:
        p=bad[0]
        if p['old_status']!=p['new_status']:
            s_=f"OLD returned {p['old_status']}, NEW returned {p['new_status']}"
        else: s_=f"Both returned {p['old_status']}"
        if p['diffs']:
            e=p['diffs'][0]; s_+=f"; {p["diff_count"]} field{"s differ" if p["diff_count"]!=1 else " differs"} (first: {e['path'].replace('$body.','')})"
        if p['exp_old'] not in('met','n/a') or p['exp_new'] not in('met','n/a'):
            W={'met':'correct','violated':'wrong','n/a':'n/a'}
            s_+=f"; vs. spec: OLD {W.get(p['exp_old'],p['exp_old'])}, NEW {W.get(p['exp_new'],p['exp_new'])}"
        more=len(bad)-1
        return s_+(f" — +{more} more failing check(s)" if more>0 else '')
    if nr and v in('BLOCKED','PARTIAL','SKIPPED'):
        r=nr[0]['not_run_reason'] or nr[0]['status']
        return f"{cov['ran']} of {cov['planned']} checks ran. Not run: {short(r,110)}"
    if v=='PASS': return f"All {cov['ran']} checks matched between OLD and NEW."
    return short(c['result']['verdict_reason'].split(' — calls:')[0],170)
DEBUG={'exception','file','line','trace'}
def classify(c):
    """Shape oracle over existing diff entries: status change / type / missing / extra = real; value-only = env noise."""
    v=c['result']['verdict']
    if v in('PASS','EXPECTED-DIFF'): return 'ok',[]
    if v in('BLOCKED','SKIPPED'): return 'norun',[]
    if v in('PARTIAL','INVALID'): return 'incomplete',[]
    reasons=[];vals=0;extra=[]
    for p in c.get('probes',[]):
        if p['status']!='ran' or p.get('verdict')=='PASS': continue
        ents=(p.get('diff') or {}).get('entries') or []
        if not ents: reasons.append(f"{p['probe_id']}: spec expectation not met (no field diff)")
        for e in ents:
            path=e['path'].split(' ')[-1];leaf=path.split('.')[-1]
            if path=='$status': reasons.append(f"{p['probe_id']}: status {e.get('old')} vs {e.get('new')}")
            elif e['kind']=='changed': vals+=1
            elif leaf in DEBUG and e['kind']=='removed': vals+=1
            elif e['kind']=='type' and (e.get('old') is None or e.get('new') is None): vals+=1  # null on one DB = data, not schema
            elif e['kind']=='added': extra.append(path.replace('$body.',''))
            else: reasons.append(f"{p['probe_id']}: {path.replace('$body.','')} {e['kind']}"+(f" ({type(e.get('old')).__name__}→{type(e.get('new')).__name__})" if e['kind']=='type' and type(e.get('old'))!=type(e.get('new')) else (f" format {json.dumps(e.get('old'))[:20]} vs {json.dumps(e.get('new'))[:20]}" if e['kind']=='type' else '')))
    if v=='BOTH-BUG': return 'look',(reasons or ['both sides violate the spec'])
    if reasons: return 'look',reasons
    if extra: return 'extra',[f'NEW adds field: {x}' for x in extra]
    return 'noise',[]
out=[]
for sec in d['sections']:
    os.makedirs(f"data/cases/{sec['key']}",exist_ok=True)
    cs=[]
    for c in sec['cases']:
        json.dump(c,open(f"data/cases/{sec['key']}/{c['id']}.json",'w'))
        probes=[]
        for p in c.get('probes',[]):
            ec=p.get('expectation_check') or {}
            dd=(p.get('diff') or {})
            nr=p.get('not_run') or {}
            probes.append({'id':p['probe_id'],'intent':p.get('intent'),'status':p['status'],'verdict':p.get('verdict'),
              'old_status':st(p.get('old')),'new_status':st(p.get('new')),
              'exp_old':ec.get('old'),'exp_new':ec.get('new'),'expected':(p.get('expected') or {}).get('statement'),
              'diff_count':dd.get('count',0),
              'diffs':[{'path':e['path'],'kind':e['kind'],'old':short(e.get('old')),'new':short(e.get('new')),'cls':e.get('class')} for e in (dd.get('entries') or [])[:6]],
              'not_run_reason':(nr.get('reason_code','')+': '+nr.get('reason','')).strip(': ') if nr else None})
        cs.append({'id':c['id'],'name':c['name'],'intent':c.get('intent'),'expected':(c.get('expected') or {}).get('statement'),
          'verdict':c['result']['verdict'],'coverage':c['result']['coverage'],'override':c['result'].get('override'),
          'reason':c['result']['verdict_reason'],'bucket':classify(c)[0],'shape':list(dict.fromkeys(classify(c)[1]))[:8],'shape_n':len(set(classify(c)[1])),'why':why(c,probes),'probes':probes})
    cs.sort(key=lambda x:(RANK.index(x['verdict']) if x['verdict'] in RANK else 99,x['id']))
    out.append({'key':sec['key'],'title':sec['title'],'cases':cs})
open('data/summary.js','w').write('window.SUM='+json.dumps(out)+';')
print({s['key']:len(s['cases']) for s in out})
