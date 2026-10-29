import json,re,os
C='/workspace/tech-317-qa/checklist-captures/'
OLDB='http://127.0.0.1:8001';NEWB='https://staging5.faberconnect.com'
T='2026-10-29 13:45 MST'
SECRET_KEYS={'token','auth_token','flow_token','password','password_confirmation','new_password','confirm_password','otp_code','code','confirmation_code','captcha_token','intercom_hash','auth','reset_token'}
def red(v,k=None):
    if isinstance(v,dict): return {a:red(b,a) for a,b in v.items()}
    if isinstance(v,list): return [red(x) for x in v]
    if k in SECRET_KEYS and v not in (None,''): return '<REDACTED>'
    if isinstance(v,str):
        v=re.sub(r'eyJ[\w-]+\.[\w-]+\.[\w-]+','<REDACTED_JWT>',v)
        v=re.sub(r'token=[\w.-]+','token=<REDACTED>',v)
    return v
def rb(s):
    if s is None: return None
    try: return json.dumps(red(json.loads(s)),indent=2,ensure_ascii=False)
    except Exception: return red(s)
def tname(v):
    return {dict:'obj',list:'arr',str:'str',int:'int',float:'float',bool:'bool',type(None):'null'}[type(v)]
def diff(o,n,p=''):
    out=[]
    if isinstance(o,dict) and isinstance(n,dict):
        for k in o:
            cp=f'{p}.{k}'
            if k=='permissionable_id' : continue
            if k not in n: out.append(f'{cp} missing on NEW')
            else: out+=diff(o[k],n[k],cp)
        for k in n:
            if k not in o and k!='laravel_through_key': out.append(f'{p}.{k} only on NEW')
    elif isinstance(o,list) and isinstance(n,list):
        for i in range(min(len(o),len(n))): out+=diff(o[i],n[i],f'{p}[{i}]')
    else:
        a,b=tname(o),tname(n)
        if a!=b and 'null' not in (a,b): out.append(f'{p or "root"}: {a} vs {b}')
    return out
def jd(ob,nb):
    try: return diff(json.loads(ob),json.loads(nb))
    except Exception: return []
NA=lambda lab:{"label":lab,"url":"—","status":"N/A","headers":{},"body":"(not run)","reqHeaders":{},"reqBody":None,"at":"—"}
def side(which,url,status,body,req=None,auth=False,at=T):
    h={"Accept":"application/json"}
    if req is not None: h["Content-Type"]="application/json"
    if auth: h["Authorization"]="Bearer <REDACTED_JWT>"
    return {"label":"OLD · local :8001" if which=='old' else "NEW · staging5","url":url,"status":status,"headers":{},"body":rb(body) if body is not None else "","reqHeaders":h,"reqBody":json.dumps(red(req)) if req is not None else None,"at":at}
def fside(which,d,name,auth=False):
    st=os.path.join(C,d,f'{which}_{name}.status')
    if not os.path.exists(st): return None,None,None
    rq=os.path.join(C,d,f'{which}_{name}.req.json')
    r=json.load(open(rq)) if os.path.exists(rq) else {}
    base=OLDB if which=='old' else NEWB
    return side(which,base+r.get('path',''),int(open(st).read().strip()),open(os.path.join(C,d,f'{which}_{name}.body')).read(),r.get('body'),auth),r.get('method'),r.get('path')
def child(pid,suf,name,method,path,old,new,status,verdict,note=''):
    old=old or NA("OLD · not run");new=new or NA("NEW · not run")
    ds=jd(old['body'],new['body']) if old['status']!='N/A' and new['status']!='N/A' else []
    return {"id":pid+suf,"parentId":pid,"name":name,"method":method,"path":path,"status":status,"verdict":verdict,"diffs":ds,"note":note,"time":T,"old":old,"new":new}
def fchild(pid,suf,name,d,n,status,verdict,note='',auth=False):
    o,m1,p1=fside('old',d,n,auth);nw,m2,p2=fside('new',d,n,auth)
    return child(pid,suf,name,m1 or m2,p1 or p2,o,nw,status,verdict,note)
def test(id,sec,name,linear,simple,status,verdict,children,note=''):
    return {"id":id,"section":sec,"name":name,"linear":linear,"simple":simple,"status":status,"verdict":verdict,"time":T,"note":note,"children":children}
OUT=[]
# ---------- §2
OUT.append(test('S2-11','otp','Flow token reuse','§2 · Reusing a consumed flow_token → 400, not 500','Log in with a flow token, then try the same token again. It must be refused.','pass','Pass — reuse of consumed flow tokens → 400 "Invalid or expired flow token." on both (4/4 calls 400).',[
 fchild('S2-11','a','Reuse consumed flow_token (account 1)','s2-flow-reuse','reuse_Fabe','pass','Pass — 400 both, identical body.'),
 fchild('S2-11','b','Reuse consumed flow_token (account 2)','s2-flow-reuse','reuse_Test','pass','Pass — 400 both, identical body.')]))
OUT.append(test('S2-12','otp','Wrong-app OTP message','§2 · Contractor verifying in worker app → "Please use the Faber Contractor app"','Verify a contractor phone as a worker (role 2). Should be told to use the Contractor app; admin is allowed.','wait','OLD pass (contractor 400 wrong-app message; admin 200). NEW not run — needs a real SMS on staging5. Email-login wrong-app already passed both sides in round 2.',[
 fchild('S2-12','a','Send OTP to contractor phone +14035550587 (OLD only)','s2-wrong-app','contractor_send','wait','OLD 200; NEW not run (needs real SMS).'),
 fchild('S2-12','b','Verify contractor phone as worker (role 2)','s2-wrong-app','contractor_verify_role2','wait','OLD 400 "Please use the Faber Contractor app to log in." — NEW pending.'),
 fchild('S2-12','c','Send OTP to admin phone +14035550101 (OLD only)','s2-wrong-app','admin_send','wait','OLD 200; NEW not run.'),
 fchild('S2-12','d','Verify admin phone as role 2','s2-wrong-app','admin_verify_role2','wait','OLD 200 login (admin allowed); NEW pending.')]))
OUT.append(test('S2-13','otp','Email availability check','§2 · POST /v2/auth/email/check','Check a registered email and an unknown one.','pass','Pass — existing → available:false, unknown → available:true; identical both.',[
 fchild('S2-13','a','Existing email','s2-email-check','exists','pass','Pass — 200 both, identical.'),
 fchild('S2-13','b','Unknown email','s2-email-check','notexists','pass','Pass — 200 both, identical.')]))
OUT.append(test('S2-14','otp','Send verification email','§2 · POST send-verification → 200 generic message + email with copy-paste link','Ask for a verification email. Expect a generic 200 and a mail with a copy-paste link.','pass','Pass — 200 generic message both. OLD mail in laravel.log with copy-paste URL (13:31 MST); NEW inbox msg 4053309 (13:32 MST) has "Or copy and paste this link".',[
 fchild('S2-14','a','Send verification email','s2-send-verification','send','pass','Pass — 200 both, identical; mail evidence in mail-evidence.txt.')]))
OUT.append(test('S2-15','otp','Password reset v2 forgot → verify → reset','§2 · v2 password forgot/verify/reset, token single-use','Request a reset code, verify it, reset the password, then try the token again.','pass','Pass — forgot 200, verify 200 + flow_token, reset 200 + auth_token, reuse 400; identical both.',[
 fchild('S2-15','a','Forgot password','s2-pw-reset-v2','forgot','pass','Pass — 200 both, identical.'),
 fchild('S2-15','b','Verify reset code','s2-pw-reset-v2','verify','pass','Pass — 200 both, flow_token returned.'),
 fchild('S2-15','c','Reset password','s2-pw-reset-v2','reset','pass','Pass — 200 both, auth_token returned.'),
 fchild('S2-15','d','Reuse reset token','s2-pw-reset-v2','reset_reuse','pass','Pass — 400 both "Invalid or expired reset token…".')]))
OUT.append(test('S2-16','otp','Legacy v1 register / resend / confirm / forgot / reset','§2 · Legacy v1 auth endpoints still work','Run the old v1 sign-up and password flow end to end.','wait','OLD pass on all 5. NEW register/resend/forgot 200, but no emails arrived after ~4 min so NEW confirm/reset were not run. Recheck inbox (possible mail delay).',[
 fchild('S2-16','a','v1 register','s2-legacy-v1','register','pass','Pass — 200 both {user_id}.'),
 fchild('S2-16','b','v1 resend confirmation','s2-legacy-v1','resend','pass','Pass — 200 [] both.'),
 fchild('S2-16','c','v1 confirm code','s2-legacy-v1','confirm','wait','OLD 200 []; NEW not run — confirmation mail never arrived.'),
 fchild('S2-16','d','v1 forgot password','s2-legacy-v1','forgot','pass','Pass — 200 [] both.'),
 fchild('S2-16','e','v1 reset password','s2-legacy-v1','reset','wait','OLD 200 []; NEW not run — reset mail never arrived.')],note='NEW v1 emails missing for waz+t317v1n291329 — needs a recheck.'))
# ---------- §1
S1={}
for f in ['captures.json','captures2.json','captures3.json','captures4.json']:
    for x in json.load(open(C+'s1-remaining/'+f)):
        if 'm' in x: S1.setdefault((f,x['tag']),[]).append(x)
def s1side(f,tag,i=0):
    xs=S1.get((f,tag));
    if not xs: return None,None,None
    x=xs[i];which=tag.split('-')[0];path=x['url'].replace(OLDB,'').replace(NEWB,'')
    isauth=not path.startswith('/auth/') or path in('/auth/refresh','/auth/logout')
    req={"email":"<account email>","password":"<REDACTED>"} if x['m']=='POST' and path.startswith('/auth/') and path not in('/auth/refresh','/auth/logout') else None
    return side(which,x['url'],x['status'],x['body'],req,isauth),x['m'],path
def s1child(pid,suf,name,f,tag,status,verdict,i=0,note=''):
    o,m,p=s1side(f,'old-'+tag,i);n,m2,p2=s1side(f,'new-'+tag,i)
    return child(pid,suf,name,m or m2,p or p2,o,n,status,verdict,note)
c2='captures2.json';c1='captures.json'
OUT.append(test('J1-09','jwt','Token refresh (GET /auth/refresh)','§1 · /auth/refresh returns a new token; old token dies','Refresh a token; the old one should stop working, the new one should work.','pass','Pass — route is GET (POST 405 both). GET 200 new token; old token 401 token_invalid immediately and after 17s; new token works. Same both.',[
 s1child('J1-09','a','Admin login','c2'and c2,'2-login','pass','Pass — 200 both.'),
 s1child('J1-09','b','POST /auth/refresh (wrong verb)',c1,'2-refresh','pass','Pass — 405 both (route is GET).'),
 s1child('J1-09','c','GET /auth/refresh',c2,'2-refresh','pass','Pass — 200 new token both.'),
 s1child('J1-09','d','Old token immediately after refresh',c2,'2-old-immediate','pass','Pass — 401 token_invalid both.'),
 s1child('J1-09','e','New token works',c2,'2-new-works','pass','Pass — 200 both (different seeded admins).'),
 s1child('J1-09','f','Old token after 17s',c2,'2-old-after17s','pass','Pass — 401 both.')]))
OUT.append(test('J1-10','jwt','Logout then reuse (GET /auth/logout)','§1 · logout invalidates the token','Log out and try the token again.','pass','Pass — GET /auth/logout 200 []; reuse 401 token_invalid (POST 405). Same both.',[
 s1child('J1-10','a','Admin login',c2,'3-login','pass','Pass — 200 both.'),
 s1child('J1-10','b','POST /auth/logout (wrong verb)',c1,'3-logout','pass','Pass — 405 both (route is GET).'),
 s1child('J1-10','c','GET /auth/logout',c2,'3-logout','pass','Pass — 200 [] both.'),
 s1child('J1-10','d','Reuse token after logout',c2,'3-reuse','pass','Pass — 401 token_invalid both.')]))
OUT.append(test('J1-11','jwt','Admin token_version on double login','§1 · Admin logs in twice — token_version behaviour','Log the admin in twice and check both tokens.','pass','Noted — token_version 0 on both tokens (no bump); token A still 200 after B. Same on both sides.',[
 s1child('J1-11','a','Admin login A',c1,'5-loginA','pass','200 both.'),
 s1child('J1-11','b','Admin login B',c1,'5-loginB','pass','200 both; tv=0 for A and B on both sides.'),
 s1child('J1-11','c','GET /user with token A after B',c1,'5-A-after-B','pass','200 both — A not invalidated.'),
 s1child('J1-11','d','GET /user with token B',c1,'5-B','pass','200 both.')]))
OUT.append(test('J1-12','jwt','Role middleware','§1 · Wrong role hitting admin routes → 403','A worker and a customer try admin-only routes.','pass','Pass — worker PATCH /admin/hour 403 (GET is 405); customer PATCH /v2/admin/permission/company/{id} 403. Same both.',[
 s1child('J1-12','a','Worker login',c2,'7-wlogin','pass','200 both.'),
 s1child('J1-12','b','Worker PATCH /admin/hour',c2,'7-worker-admin-hour-PATCH','pass','Pass — 403 "Access restricted." both.'),
 s1child('J1-12','c','Worker GET /admin/hour',c1,'7-worker-admin-hour','pass','405 both (GET not a route).'),
 s1child('J1-12','d','Contractor login',c1,'7-clogin','pass','200 both.'),
 s1child('J1-12','e','Customer PATCH admin permission',c1,'7-cust-patch-perm','pass','Pass — 403 both.')]))
o8,_,_=s1side(c1,'new-8-worker2378',1);o8b,_,_=s1side(c1,'new-8-worker2378',0)
OUT.append(test('J1-13','jwt','Existing (bcrypt) passwords still log in','§1 · Existing passwords work on NEW; change then log in on 5.7','Log in with accounts whose passwords were set before the upgrade.','pass','Pass (login half) — jordan+1 /auth/admin 200 on staging5; worker 2378 logs in. Change-then-5.7-login not run (5.7 offline).',[
 child('J1-13','a','jordan+1 admin login on staging5','POST','/auth/admin',None,s1side(c2,'new-2-login')[0],'pass','Pass — 200 token on NEW.'),
 child('J1-13','b','Worker 2378 login (first attempt, wrong password)','POST','/auth/worker',None,o8b,'pass','401 — wrong password tried first.'),
 child('J1-13','c','Worker 2378 login (correct password)','POST','/auth/worker',None,o8,'pass','Pass — 200 token on NEW.')]))
OUT.append(test('J1-14','jwt','Past refresh window → 401','§1 · Token past JWT_REFRESH_TTL → 401 token_expired','Needs a token older than the refresh window.','skip','Skipped — no token that old; can\'t mint without the staging5 secret; OLD refresh_ttl=null.',[]))
OUT.append(test('J1-15','jwt','Deleted user → 404','§1 · Token for a deleted user → 404','Use a token whose user no longer exists.','skip','Skipped on NEW — no user soft delete / delete API. OLD: forged token with missing sub → 404 "User not found".',[
 s1child('J1-15','a','OLD GET /user with forged missing-user sub','captures4.json','4-missing-user-sub','skip','OLD 404 User not found; NEW not run.')]))
OUT.append(test('J1-16','jwt','Cross-host token 5.7 → staging5','§1 · Token minted on 5.7 rejected/accepted on staging5','Needs the 5.7 staging host.','skip','Skipped — 5.7 staging offline.',[]))
# ---------- §7
R=json.load(open(C+'s7-regression/captures.json'))
pairs=[(R[i],R[i+1]) for i in range(0,len(R),2)]
def rchild(pid,suf,pr,name,status,verdict,auth=True):
    o,n=pr;rq=o['req'].get('json',o['req'].get('data'))
    return child(pid,suf,name,o['method'],o['path'],side('old',OLDB+o['path'],o['status'],o['body'],rq,auth,'2026-10-29 '+o['t']+' MST'),side('new',NEWB+n['path'],n['status'],n['body'],n['req'].get('json',n['req'].get('data')),auth,'2026-10-29 '+n['t']+' MST'),status,verdict)
dead=[];k=0
for i in range(0,12,2):
    for j,lab in ((0,'admin token'),(1,'no token')):
        pr=pairs[i+j];k+=1
        dead.append(rchild('S7-01',chr(96+k),pr,f'{pr[0]["method"]} {pr[0]["path"]} ({lab})','pass',f'Pass — NEW {pr[1]["status"]} (OLD {pr[0]["status"]}: the fixed bug / unauthenticated).',auth=(j==0)))
OUT.append(test('S7-01','reg','Dead routes removed','§7 · Dead routes → 404/405, not 500','Call routes whose controllers were deleted.','pass','Pass — NEW 5×404 + DELETE /admin/quiz/1 → 405, with and without a token. OLD admin → 500 on all 6 (the fixed bug).',dead))
bl=['missing socket_id','missing channel_name','both present (admin)','both present (customer)']
bc=[rchild('S7-02',chr(97+i),pairs[12+i],'Broadcast auth — '+lab,'pass','Pass — NEW %s.'%pairs[12+i][1]['status']) for i,lab in enumerate(['missing socket_id + channel','missing socket_id','missing channel_name','admin, valid','customer, valid'])]
OUT.append(test('S7-02','reg','Broadcast auth','§7 · /broadcasting/auth guards channels','Ask for channel auth with missing params, as admin and as customer.','pass','Pass — NEW missing params → 403; admin valid → 200 {auth}; customer → 403. OLD 200 empty for all (local log broadcaster).',bc,note='OLD uses the log broadcaster locally so its 200s are not meaningful.'))
vl=[rchild('S7-03',chr(97+i),pairs[17+i],lab,'pass','Pass — byte-identical.') for i,lab in enumerate(['POST /user/worker {}','POST /user/worker bad fields','POST /user/quiz {}','POST /v2/admin/worker-leads/import {}'])]
OUT.append(test('S7-03','reg','Validation response shape','§7 · Validation errors keep the same shape','Send invalid input to a few endpoints.','pass','Pass — identical 400/422 shapes. Hour store and invoice pay not checked.',vl))
pg=[rchild('S7-04',chr(97+i),pairs[21+i],lab,'pass','Pass — same pagination keys; NEW adds links.') for i,lab in enumerate(['/admin/company page 1','/admin/company page 99999','/invoice'])]
OUT.append(test('S7-04','reg','Pagination shape','§7 · Paginated endpoints keep data/current_page/last_page/total','Read paged lists.','pass','Pass — data, current_page, last_page, total on both; NEW adds links.',pg))
OUT.append(test('S7-05','reg','Queue failed_jobs','§7 · failed_jobs empty after run','Needs Forge/DB access.','blocked','Blocked — needs Forge/DB access.',[]))
OUT.append(test('S7-06','reg','Email listeners on failure','§7 · Mail failure handled by listeners','Needs a forced mail failure.','skip','Skipped — no easy way to force a mail failure.',[]))
OUT.append(test('S7-07','reg','Sentry staging-l13','§7 · Errors reach Sentry','Needs Sentry access.','blocked','Blocked — no Sentry access.',[]))
# ---------- §3
def st(n): 
    d=C+'s3-stripe/new_'+n
    return int(open(d+'.status').read()),open(d+'.body').read()
def nchild(pid,suf,name,m,p,n,status,verdict,req=None,auth=True,old=None):
    s,b=st(n);return child(pid,suf,name,m,p,old,side('new',NEWB+p,s,b,req,auth,'2026-10-29 13:40 MST'),status,verdict)
OUT.append(test('S3-01','stripe','Admin list company cards','§3 · GET /admin/company/{id}/credit-card','List company 938\'s cards as admin.','pass','Pass — 200, card 108 (Visa 4242) listed, with nested `user` (BUG-44).',[
 nchild('S3-01','a','List cards for company 938','GET','/admin/company/938/credit-card','list_938_with_user','pass','Pass — 200 with nested user (BUG-44). OLD not run (no Stripe key locally).')],note='Card 108 on 938 is left over from P3\'s earlier successful add.'))
OUT.append(test('S3-02','stripe','Webhook without Stripe-Signature','§3 · Stripe webhook with no signature → rejected','Post to the Stripe webhook with no signature header.','pass','Pass — 400 "Failed".',[
 nchild('S3-02','a','Webhook, no Stripe-Signature header','POST','(Stripe webhook route)','webhook_no_sig','pass','Pass — 400 "Failed". OLD not run.',req={},auth=False)]))
os_,ob=int(open(C+'s3-stripe/old_cx_add_card.status').read()),open(C+'s3-stripe/old_cx_add_card.body').read()
OUT.append(test('S3-03','stripe','Add card (admin + customer)','§3 · Add a card with a Stripe test token','Add a Visa test card as admin and as customer.','fail','Fail/blocked — tok_visa → 500 on NEW for companies 938 and 939 (admin) and customer; pm_card_visa → 400. P3 succeeded at ~11:47 MST (card 108). OLD can\'t be compared: STRIPE_SECRET empty locally.',[
 nchild('S3-03','a','Admin add tok_visa to 938','POST','/v2/admin/company/credit-card/stripe','admin_add_938','fail','Fail — 500 "An error occurred while trying to add credit card."'),
 nchild('S3-03','b','Admin add tok_visa to 939','POST','/v2/admin/company/credit-card/stripe','admin_939_tok_visa','fail','Fail — 500.'),
 nchild('S3-03','c','Admin add tok_visa_debit to 939','POST','/v2/admin/company/credit-card/stripe','admin_939_tok_visa_debit','fail','Fail — 500.'),
 nchild('S3-03','d','Admin add pm_card_visa to 939','POST','/v2/admin/company/credit-card/stripe','admin_939_pm_card_visa','fail','400 verify failed (pm_ ids not accepted).'),
 child('S3-03','e','Customer add card','POST','/company/credit-card/stripe',side('old',OLDB+'/company/credit-card/stripe',os_,ob,None,True,'2026-10-29 13:40 MST'),side('new',NEWB+'/company/credit-card/stripe',*st('cx_add_card'),None,True,'2026-10-29 13:40 MST'),'fail','Fail — NEW 500 Server Error. OLD 400 only because STRIPE_SECRET is empty locally.'),
 nchild('S3-03','f','Customer add tok_visa','POST','/company/credit-card/stripe','cx_tok_visa','fail','Fail — 500 Server Error.'),
 nchild('S3-03','g','Customer add pm_card_visa','POST','/company/credit-card/stripe','cx_pm_card_visa','fail','400.')],note='Company 939 now has customer_stripe_id but no cards (orphan from the failed add).'))
for t in OUT:
    if t['id'] in ('S7-01','S7-02'):
        for c in t['children']: c['diffs']=[]  # status differs by design; bodies are error pages
js='\n'.join('TESTS.push('+json.dumps(t,ensure_ascii=False)+');' for t in OUT)
assert 'eyJ' not in js
p='/workspace/tech-317-qa-dashboard/checklist/index.html';h=open(p).read()
anchor='</script>';i=h.rfind(anchor)
# insert before the final render() call? place before last render invocation
m=h.rfind("\ndocument.addEventListener('keydown'")
pos=m if m!=-1 else i
h=h[:pos]+'\n'+js+h[pos:]
h=h.replace("const empty=['stripe','hours','pay','invoice','reg'].map((id,i)=>sec(id,['§3 Stripe','§4 Hours','§5 Worker pay','§6 Invoices / PDFs','§7 Regression'][i],`<p class=\"sec-empty\">Not started.</p>`)).join('');","const empty=['stripe','hours','pay','invoice','reg'].map((id,i)=>sec(id,['§3 Stripe','§4 Hours','§5 Worker pay','§6 Invoices / PDFs','§7 Regression'][i],rows(id))).join('');")
h=h.replace("new Set(['pre','jwt','otp'])","new Set(['pre','jwt','otp','stripe','reg'])")
h=h.replace("skip:{cls:'skip',badge:'skip',label:'Skipped'}};","skip:{cls:'skip',badge:'skip',label:'Skipped'},blocked:{cls:'wait',badge:'wait',label:'Blocked'}};")
h=h.replace("${c('skip')} skipped ·","${c('skip')} skipped · ${c('blocked')} blocked ·")
open(p,'w').write(h);print([t['id'] for t in OUT])
