import json,os
exec(open('tools/capx.py').read())
T='2026-10-29 15:39 MST'
D=C+'s2-lockout/'
SO='/v2/auth/phone/send-otp'; VO='/v2/auth/phone/verify-otp'
steps=[('t0_send',SO,'Send OTP to +17787240103 (role 2)','200 both.')]+[(f'wrong{i}',VO,f'Wrong code #{i}'+(' (after 120s cooldown)' if i>3 else ''),'400 Invalid verification code, both.') for i in range(1,7)]+[('wrong7_after_lock',VO,'Verify again after 6 wrong','423 "Account locked…" both.'),('send_after_lock',SO,'send-otp after lock','423 "Phone number is temporarily locked…" both.')]
ch=[]
for i,(n,p,lab,v) in enumerate(steps):
  def sd(w):
    return side(w,(OLDB if w=='old' else NEWB)+p,int(open(D+f'{w}_{n}.status').read()),open(D+f'{w}_{n}.body').read(),json.load(open(D+f'{w}_{n}.req.json')),False,T)
  c=child('S2-17',L(i),lab,'POST',p,sd('old'),sd('new'),'pass',v); c['time']=T; ch.append(c)
t=test('S2-17','otp','6 wrong codes → 423 permanent lock','§2 · 6 wrong verify attempts → 423 locked; send-otp also 423','Enter the wrong code 6 times (waiting out the 2-minute cooldown after #3, #4, #5). Then both verify and send should say locked (423).','pass',
 'Pass, identical on both. Wrong #1–6 → 400 (attempts 4–6 sent after waiting out each 120s cooldown, so they count). 7th verify → 423 "Account locked. Please contact Faber support to regain access." send-otp → 423 "Phone number is temporarily locked…". Unlock: OLD reset in local DB (send 200 after). NEW needs Forge tinker to clear the phone_numbers row; there is no API unlock.',ch,
 'Earlier VER-03 note ("6 not reachable") was only true when hammering inside the cooldown.')
t['time']=T
push([t],'S2-17')
