# shared helper for §3-pay/§5/§6 captures (pay_lib.py format)
import json,re
exec(open('tools/add_batch2.py').read().split('OUT=[]')[0])
def red2(s): return re.sub(r'X-Amz-(Credential|Signature)=[^&"\s]+',r'X-Amz-\1=<REDACTED>',re.sub(r'[0-9a-f]{32}','<REDACTED>',s)) if isinstance(s,str) else s
def realdiff(ds): return [d for d in ds if ('vs' in d and ':' in d) or 'missing on NEW' in d]
def mk(CALLS,AT):
  def cc(pid,suf,lab,status,verdict,idx=-1):
    es=[x for x in CALLS if x['label']==lab]
    if not es: raise SystemExit('missing '+lab)
    e=es[idx]
    if 'side' in e:
      s=side('old' if e['side']=='o' else 'new',(OLDB if e['side']=='o' else NEWB)+e['path'],e['status'],red2(e['body']),e.get('req'),True,AT)
      o,n=(s,None) if e['side']=='o' else (None,s)
      c=child(pid,suf,lab,e['method'],e['path'],o,n,status,verdict)
    else:
      o=side('old',OLDB+e['path'],e['old']['status'],red2(e['old']['body']),e.get('req'),True,AT)
      n=side('new',NEWB+e['path_new'],e['new']['status'],red2(e['new']['body']),e.get('req_new'),True,AT)
      c=child(pid,suf,lab,e['method'],e['path'],o,n,status,verdict); c['diffs']=realdiff(c['diffs'])
    return c
  return cc
L=lambda n:'abcdefghijklmnopqrstuvwxyz'[n]
def push(OUT,sec_prefix_re,newsecs=()):
  js='\n'.join('TESTS.push('+json.dumps(t,ensure_ascii=False)+');' for t in OUT).replace('</','<\\/')
  assert 'eyJ' not in js and not re.search(r'[0-9a-f]{32}',js) and 'AKIA' not in js
  p='checklist/index.html';h=open(p).read()
  h=re.sub(r'\nTESTS\.push\(\{"id": "'+sec_prefix_re+r'[^\n]*','',h)
  m=h.rfind("\ndocument.addEventListener('keydown'"); h=h[:m]+'\n'+js+h[m:]
  for s in newsecs:
    if f"'{s}'" not in h.split('const OPEN_SECS=')[1].split(';')[0]: h=h.replace("'reg'])","'"+s+"','reg'])",1)
  open(p,'w').write(h)
