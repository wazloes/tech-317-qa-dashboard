import json
exec(open('tools/capx.py').read())
C=json.load(open('/workspace/tech-317-qa/checklist-captures/s5-pay/calls.json'))
c=mk(C,'2026-10-29 14:10 MST'); OUT=[]
def S5(id,name,linear,simple,status,verdict,specs,note=''):
  OUT.append(test(id,'pay',name,linear,simple,status,verdict,[c(id,L(i),*s) for i,s in enumerate(specs)],note))
S5('S5-01','Generate payment drafts','§5 · POST /v2/admin/payment/draft (queued)','Build worker pay drafts for 10-26..10-28.','pass','Pass — 200 "drafts have been generated" on both; list shows one draft per worker, status id 1 as an integer on both (NEW adds void_reason/sms fields).',
 [('S5 admin payment draft (10-26..10-28)','pass','Same.'),('S5 admin payment list for worker','pass','Integer status ids.')])
S5('S5-02','Payment line items','§5 · GET /v2/admin/payment/{id}/line-item','See the lines in a draft.','pass','Pass — same shape; reg 8h at $20 + OT lines on both (amounts differ by fixture hours).',
 [('S5 line-items OLD','pass','200.'),('S5 line-items NEW','pass','200.')])
S5('S5-03','Export payment CSV','§5 · POST /v2/admin/payment/export','Download the Payment Rails CSV.','pass','Pass — without mark_paid → 400 on both. With mark_paid=0 → same CSV headers on both. NEW fills country "CA"; OLD leaves it blank (worker fixture data).',
 [('S5 export OLD','pass','400 validation.'),('S5 export NEW','pass','400 validation.'),('S5 export mark_paid=0 OLD','pass','CSV.'),('S5 export mark_paid=0 NEW','pass','CSV.')])
S5('S5-04','Weekly pay CSV','§5 · GET /admin/payments/export-worker-weekly-pay-csv','Weekly pay export.','pass','Pass — missing week → 400, week must be an integer → 400, week=44 → 200 with the same CSV header on both.',
 [('S5 weekly pay csv','pass','400 both.'),('S5 weekly pay csv OLD','pass','400.'),('S5 weekly pay csv NEW','pass','400.'),('S5 weekly pay csv week=44','pass','200 both.')])
S5('S5-05','Refresh worker pay owed','§5 · PATCH /v2/admin/payment/refresh-worker-pay-owed','Recalculate what workers are owed.','warn','Warn — OLD 200 instantly. NEW timed out after 60 s twice. The code loops over EVERY segment with worker_pay_owed (ignores the ids), so it is slow on the bigger staging5 DB. Not proven to be a regression, but it would hit a gateway timeout in the admin UI. A wrong path (/{id}/…) gives 404 on both.',
 [('S5 refresh owed OLD','pass','404 wrong path.'),('S5 refresh owed NEW','pass','404 wrong path.'),('S5 refresh-worker-pay-owed OLD','pass','200.'),('S5 refresh-worker-pay-owed NEW','fail','Timeout 60s.'),('S5 refresh-worker-pay-owed NEW retry','fail','Timeout 60s.')],note='NEW refresh-worker-pay-owed > 60 s (full table scan).')
S5('S5-06','Cancel money transfers / cancel payment','§5 · PATCH payment/cancel-money-transfers, payment/cancel','Cancel a draft payment.','pass','Pass — POST gives 405 on both (route is PATCH). PATCH cancel-money-transfers and cancel return 200 on both; the payment is listed in successful_payment_cancellations on both.',
 [('S5 cancel OLD','pass','405.'),('S5 cancel NEW','pass','405.'),('S5 cancel-money-transfers OLD','pass','200.'),('S5 cancel-money-transfers NEW','pass','200.'),('S5 cancel OLD','pass','Cancelled id 1.',1),('S5 cancel NEW','pass','Cancelled id 7607.',1)])
S5('S5-07','VoPay webhook bad key','§5 · POST /webhook/vopay','Send a fake webhook.','pass','Pass (parity) — both return 200 "success" and do nothing.',[('S5 vopay webhook bad key','pass','Same.')])
S5('S5-08','Worker bank widget','§5 · GET /user/bank-widget','Get the Payment Rails widget link.','pass','Pass — signed widget URL on both. NEW has the Payment Rails key set; the local OLD key is empty (env).',[('S5 worker bank-widget','pass','Same shape.')])
S5('S5-09','Worker request Quick Pay','§5 · GET /v2/worker/request-instant-pay','Worker asks for Quick Pay before 4:30 PM.','pass','Pass — NEW 200 "Quick Pay successfully requested" (worker is instant_payable). OLD 422 "not eligible" because the OLD fixture worker has instant_payable off; the code path matches. The after-4:30 PM check was not run (run time was ~14:05 MST).',[('S5 worker request-instant-pay','pass','Expected for the data.')])
S5('S5-10','Pay workers (VoPay)','§5 · pay-workers','Send real money.','skip','Skipped by rule (P4 VoPay).',[])
push(OUT,'S5-')
