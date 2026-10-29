import json,re,sys
exec(open('tools/add_batch2.py').read().split('OUT=[]')[0])
T='2026-10-29 13:50 MST'
C4='/workspace/tech-317-qa/checklist-captures/s4-hours/calls-1029.json'
CALLS=json.load(open(C4)); RES=json.load(open('/workspace/tech-317-qa/results/hours/state.json'))['res']
def red2(s): return re.sub(r'token=[0-9a-f]{32}','token=<REDACTED>',re.sub(r'[0-9a-f]{32}','<REDACTED>',s)) if isinstance(s,str) else s
def realdiff(ds):  # only real type / missing issues
    return [d for d in ds if ('vs' in d and ':' in d and 'null' not in d) or 'missing on NEW' in d]
def tc(pid,suf,lab,status,verdict,note=''):
    e=[x for x in CALLS if x['label']==lab][0]
    o=side('old',OLDB+e['path'],e['old']['status'],red2(e['old']['body']),None,True,'2026-10-29 13:4x MST')
    n=side('new',NEWB+e['path'],e['new']['status'],red2(e['new']['body']),None,True,'2026-10-29 13:4x MST')
    c=child(pid,suf,lab,e['method'],e['path'],o,n,status,verdict,note); c['diffs']=realdiff(c['diffs']); return c
def yc(pid,suf,case,lab,status,verdict,note=''):
    e=[x for x in RES[case] if x['label']==lab][0]
    o=side('old',OLDB,e['o']['status'],red2(e['o']['body']),None,True,'2026-10-28 16:0x MST')
    n=side('new',NEWB,e['n']['status'],red2(e['n']['body']),None,True,'2026-10-28 16:0x MST')
    c=child(pid,suf,f'[{case} 10-28 run] {lab}','—','(see http.log)',o,n,status,verdict,note); c['diffs']=[]; return c
L=lambda n:'abcdefghijklmnopqrstuvwxyz'[n]
def kids(pid,specs): return [ (tc if s[0]=='t' else yc)(pid,L(i),*s[1:]) for i,s in enumerate(specs)]
OUT=[]
def add(id,name,linear,simple,status,verdict,specs,note=''): OUT.append(test(id,'hours',name,linear,simple,status,verdict,kids(id,specs),note))
add('S4-01','Worker log hours = 8.00','§4 · 07:00–15:30 with 30-min break → 8.00','Log a day shift with a 30-minute break.','fail','Both-system — OLD and NEW both store 8.50 for 07:00–15:30 with break id 2 (30 min); the break is not taken off. Same on both, so this is not an L13 regression. NEW also returns "8.5" instead of "8.50".',
 [('y','H-03','log Mon 10-26 07:00-15:30 brk2','fail','Both 200, hours 8.50 OLD / "8.5" NEW (expected 8.00).'),
  ('t','paid-hours 07:00-15:30 brk2','fail','Both 8.5 (break not deducted).')])
add('S4-02','Overnight 22:00–06:00 = 8h','§4 · Overnight gives 8 h, not −16 h','Work out paid hours for a night shift.','pass','Pass — 8 h on both, with and without a break; all 7×6 shift/break combinations match (10-28).',
 [('t','paid-hours 22:00-06:00 brk0','pass','8 both.'),('t','paid-hours 22:00-06:00 brk2','pass','8 both.'),('t','paid-hours 01:00-03:00 brk0','pass','2 both.')])
add('S4-03','DST Nov 1 2026 US vs BC','§4 · DST shift measured in real hours (BUG-5)','A shift on the DST night.','blocked','Blocked — the math uses the server clock date, and Nov 1 is in the future, so you can\'t log it yet. Needs libfaketime on both servers or a rerun on/after Nov 1.',[])
add('S4-04','Edit / late-withdraw / weekly-hours','§4 · PATCH /worker/hour, late-withdraw, weekly totals','Edit an hour, withdraw late, check weekly totals.','pass','Pass — edit 200/400/404 match; late-withdraw validation matches and admin late type 13 is 200 on both; delete matches; weekly-hours totals match.',
 [('y','H-06','edit wed 05:00-09:00 -> 06:00-10:00 w/ request_id','pass','200 both, same fields.'),('y','H-06','edit without request_id','pass','400 both.'),
  ('y','H-08','worker late type 12 -> 400','pass','400 both.'),('y','H-25','admin late type 13 on today seg','pass','200 both.'),('y','H-07','worker delete own (wed seg, dated 10-29)','pass','200 both.'),
  ('t','worker weekly-hours week=0','pass','200 both; totals match.'),('t','worker weekly-hours week=-1','pass','Identical.')])
add('S4-05','Date format Y-m-d H:i:s','§4 · No ISO-8601 dates anywhere','Look at the date fields in hour responses.','fail','Fail — none of the hour reads have ISO dates. But admin PATCH /admin/request/{id} on NEW returns start_date/end_date as a Carbon object {"date":"2026-10-26 00:00:00.000000","timezone_type":3,…}, while OLD returns "2026-10-26".',
 [('y','H-27','admin PATCH request start_date+weekdays objs+total_break 3 (has group)','fail','NEW start_date/end_date: string → object.'),
  ('t','admin/hour/{mon}','pass','No ISO dates.'),('t','contractor/hour','pass','No ISO dates.')])
add('S4-06','Numeric types hours/price','§4 · hours/price types unchanged','Check the type of the number fields.','pass','Pass with a note — types match (strings on both). But NEW drops trailing zeros on decimal strings: hours "8.50"→"8.5", "11.00"→"11", "5.00"→"5". parseFloat().toFixed() still works; a plain string display would show it.',
 [('t','admin/hour/{mon}','pass','hours "8.50" vs "8.5".'),('t','v2 admin worker weekly-hours','pass','Types identical.')],note='Watch for any FE that shows hours as raw strings.')
add('S4-07','Customer approve / approve-all / admin approve-all','§4 · approve, approve-all, v2 admin approve-all','Approve one hour, then all.','pass','Pass — single approve and approve-all 200 on both; empty or nonexistent ids 400 on both; v2 admin approve-all matches. NEW gives 400 where OLD gave 200 when the list includes a foreign segment id (NEW is stricter). The worker notification was not checked.',
 [('y','H-14','approve single mon','pass','200 both.'),('y','H-14','approve-all tue','pass','200 both.'),('y','H-14','approve-all incl foreign id 1 -> 400?','pass','OLD 200 / NEW 400 — NEW is stricter.'),
  ('t','approve-all empty array','pass','400 both.'),('t','approve-all nonexistent id','pass','400 both.'),('y','H-26','v2 approve-all adm + bogus, by name','pass','200 both.')])
add('S4-08','Customer revise','§4 · PATCH /request_segment/{id} revise','Change a logged hour as the customer.','pass','Pass — revise 200 on both with the same revised values; a bad time or an already-approved hour gives 400 on both. The only difference is "11.00" vs "11".',
 [('y','H-13','revise tue 06:00-17:00 -> 07:00-16:00 brk2','pass','Same revised_hours 9.'),('y','H-13','revise bad time 7am','pass','400 both.'),('y','H-13','revise approved mon -> 400','pass','400 both.')])
add('S4-09','Move hour (BUG-48)','§4 · move to another project, no 500','Move an hour to another project.','fail','Fail (both-system) — moving to your own second project works (200 on both). Moving a missing segment returns 500 on both, for contractor and admin. BUG-48 says no 500.',
 [('t','BUG-48 contractor move seg to own project2','pass','200 both.'),('t','BUG-48 move missing segment','fail','500 both.'),('t','BUG-48 move without project_id','pass','400 both.'),('y','H-25','admin move missing segment','fail','500 both.')])
add('S4-10','Email approve-hours link','§4 · /email/approve-hours opens, approves, PO saves','Use the link from the weekly email.','pass','Pass — the admin reminder sent the email (NEW inbox msg 4056040 at 13:41 MST; OLD in laravel.log). The landing page is 200 on both, the list matches, approve_all is 200 on both, the PO number saves, and a bad token gives 401 on both.',
 [('t','admin send-hour-approval-email-reminder week=0','pass','200 both.'),('t','email approve-hours landing page','pass','200 HTML both.'),('t','sms/approve-hours/list (email token)','pass','200 both.'),
  ('t','approve-hours list bad token','pass','401 both.'),('t','POST approve-hours approve_all=false no match_ids','pass','400 both.'),('t','POST approve-hours approve_all=true','pass','200 both.'),('t','save PO number via approve-hours token','pass','200 both.')])
add('S4-11','SMS approve-hours','§4 · /sms/approve-hours (only with a real SMS)','Needs a real SMS.','skip','Skipped — the supervisor phones are fake +1403555 numbers. Sending to the VoIP DID would need the project phone changed and a real SNS send. The list/approve endpoints are the same ones that passed in S4-10.',[])
add('S4-12','Admin hours list / CSV','§4 · dash hours list + weekly CSV export','Load the admin hours list and the CSV.','pass','Pass — company weekly-hours, statistics/hours and the CSV export are 200 on both. Content-type is "UTF-8" vs "utf-8". There is no GET /admin/hour (405 on both; the dash uses the weekly endpoints).',
 [('t','admin company weekly-hours week=0 (dash hours list)','pass','200 both.'),('t','admin statistics/hours','pass','Identical.'),('t','admin hour weekly export CSV','pass','200 CSV both.')])
add('S4-13','Admin store/update/destroy/recalculate/force-delete','§4 · admin hour CRUD + recalc','Admin edits hours.','pass','Pass with notes — update, recalculate and force-delete are 200 on both. Store over a paid segment is 200 on both. One store gave OLD 200 / NEW 400 because NEW already had hours from the first run that day (fixture state). update_multiple without hour_status and destroy of a missing id return 500 on both (both-system).',
 [('y','H-21','admin update revised fields','pass','200 both.'),('y','H-23','recalculate adm','pass','200 both.'),('y','H-22','force-delete worker-paid seg','pass','200 both.'),
  ('y','H-20','admin store over paid seg','pass','200 both.'),('y','H-21','update_multiple w/o hour_status','fail','500 both.'),('y','H-22','admin destroy missing','fail','500 both.')])
add('S4-14','Mark worker paid','§4 · PATCH worker-paid','Mark an approved hour paid.','pass','Pass — approved → 200, unapproved → 400, unknown → 404 on both.',
 [('y','H-24','worker-paid approved','pass','200 both.'),('y','H-24','worker-paid unapproved','pass','400 both.'),('y','H-24','worker-paid unknown -> 404','pass','404 both.')])
add('S4-15','Edit request with no group (BUG-32)','§4 · PATCH /admin/request/{id}, no group, no 500','Edit a request that has no group.','blocked','Blocked — every request created through the API gets a request_group, and the staging5 DB can\'t be edited. Grouped-request edits are 200 on both (with the date-object difference from S4-05).',
 [('y','H-27','admin PATCH request start_date (request HAS group)','pass','400 both.')])
add('S4-16','hours:auto-approve','§4 · optional artisan run','Needs Forge.','skip','Skipped — needs a Forge SSH run.',[])
js='\n'.join('TESTS.push('+json.dumps(t,ensure_ascii=False)+');' for t in OUT).replace('</','<\\/')
assert 'eyJ' not in js and not re.search(r'[0-9a-f]{32}',js)
p='checklist/index.html';h=open(p).read()
h=re.sub(r'\nTESTS\.push\(\{"id": "S4-[^\n]*','',h)
m=h.rfind("\ndocument.addEventListener('keydown'"); h=h[:m]+'\n'+js+h[m:]
h=h.replace("new Set(['pre','jwt','otp','stripe','reg'])","new Set(['pre','jwt','otp','stripe','hours','reg'])")
open(p,'w').write(h); from collections import Counter; print(Counter(t['status'] for t in OUT))
