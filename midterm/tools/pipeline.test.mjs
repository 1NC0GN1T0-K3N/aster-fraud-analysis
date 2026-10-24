import test from 'node:test';
import assert from 'node:assert/strict';
const core = await import('./pipeline_core.mjs').catch(e => { if(e.code === 'ERR_MODULE_NOT_FOUND') return {}; throw e; });
function fn(name) { assert.equal(typeof core[name], 'function', `${name} must implement the revised pipeline behavior`); return core[name]; }
const employee={emp_id:'E1',approval_limit_thb:'100000'};
const vendor={vendor_id:'V1',category:'Office Supplies',registration_date:'2026-01-01'};
const invoice={invoice_id:'I1',invoice_number:'N1',vendor_id:'V1',employee_id:'E1',approver_id:'E1',invoice_date:'2026-01-03',amount_thb:'100'};
test('expense peers exclude the target, wrong departments, categories and dates',()=>{
 const rows=[{...invoice,employee_id:'E1',amount_thb:100},{...invoice,employee_id:'E1',amount_thb:110},{...invoice,employee_id:'E2',amount_thb:10},{...invoice,employee_id:'E2',amount_thb:20},{...invoice,employee_id:'E3',amount_thb:999},{...invoice,employee_id:'E2',vendor_id:'V2',amount_thb:999},{...invoice,employee_id:'E2',invoice_date:'2025-01-03',amount_thb:999}];
 const r=fn('statisticalAnalysis')(rows,[{vendor_id:'V1',category:'Hotel'},{vendor_id:'V2',category:'Meal'}],{target_employee_id:'E1',analysis_category:'Hotel',peer_start:'2026-01-01',peer_end:'2026-01-31',employees:[{emp_id:'E1',department:'Sales'},{emp_id:'E2',department:'Sales'},{emp_id:'E3',department:'IT'}]});
 assert.equal(r.peer.n_a,2);assert.equal(r.peer.n_b,2);assert.equal(r.peer.mean_b,15);assert.deepEqual(r.peer.peer_employee_ids,['E2']);
});
test('invalid and duplicate masters are retained in quarantine',()=>{
 const p=fn('prepareData')({employees:[employee,employee,{emp_id:'E2',approval_limit_thb:'bad'}],vendors:[vendor,{...vendor,vendor_id:'V2',registration_date:'2026-02-30'}],invoices:[invoice]});
 assert.equal(p.employees.length,1);assert.equal(p.vendors.length,1);assert.equal(p.quarantine.length,3);
 assert.equal(p.controls.tables.employees.raw,3);assert.equal(p.controls.tables.employees.quarantined,2);
});
test('blank keys and nonnumeric amounts do not reach production',()=>{
 const p=fn('prepareData')({employees:[employee],vendors:[vendor],invoices:[invoice,{...invoice,invoice_id:'',amount_thb:'abc'}]});
 assert.equal(p.invoices.length,1);assert.equal(p.quarantine.length,1);assert.equal(p.controls.invoice_amounts.unparseable_rows,1);
});
test('numeric quarantine amounts reconcile without silently losing negatives',()=>{
 const p=fn('prepareData')({employees:[employee],vendors:[vendor],invoices:[invoice,{...invoice,invoice_id:'I2',amount_thb:'-10'}]});
 assert.deepEqual(p.controls.invoice_amounts,{raw_numeric:90,production:100,quarantined_numeric:-10,unparseable_rows:0,difference:0,pass:true});
});
test('profiling detects missing values and duplicate keys before cleansing',()=>{
 const p=fn('profileTable')([invoice,{...invoice,description:'',invoice_id:'I1'}],'invoice_id','amount_thb');
 assert.equal(p.rows,2);assert.equal(p.duplicate_key_rows,1);assert.equal(p.amount.median,100);assert.equal(p.amount.iqr,0);
});
test('Welch test computes t, df and two-sided p rather than applying a raw t cutoff',()=>{
 const r=fn('welchTest')([1,2,3],[4,5,6]);
 assert.ok(Math.abs(r.t+3.6742346141747673)<1e-10);assert.ok(Math.abs(r.df-4)<1e-10);
 assert.ok(Math.abs(r.p_value-0.021311641128756727)<1e-10);
});
test('undersized and zero variance comparisons are unavailable, not healthy zero scores',()=>{
 assert.equal(fn('welchTest')([1],[2,3]).status,'insufficient_data');
 assert.equal(fn('welchTest')([1,1],[2,2]).status,'zero_variance');
});
test('scan selects a change from observed transactions and corrects repeated tests',()=>{
 const rows=[1,2,1,2,20,21,20,21].map((amount_thb,i)=>({invoice_id:`I${i}`,invoice_date:`2026-01-${String(i+1).padStart(2,'0')}`,amount_thb}));
 const r=fn('scanBreakpoints')(rows);assert.equal(r.best.split_date,'2026-01-05');assert.equal(r.best.n_old,4);assert.equal(r.best.n_new,4);assert.equal(r.best.significant,true);
});
test('reconciliation gate refuses missing or mismatched controls',()=>{
 const gate=fn('assertReconciled');
 assert.throws(()=>gate({}),/reconcil/i);
 assert.throws(()=>gate({tables:{invoices:{pass:false}},invoice_amounts:{pass:true}}),/reconcil/i);
});
test('peer comparison uses the target category and identical active date window',()=>{
 const rows=[...Array.from({length:8},(_,i)=>({...invoice,invoice_id:`T${i}`,vendor_id:'V1',invoice_date:`2026-07-${String(i+1).padStart(2,'0')}`,amount_thb:100+i})),...Array.from({length:5},(_,i)=>({...invoice,invoice_id:`P${i}`,vendor_id:'V2',invoice_date:`2026-07-${String(i+1).padStart(2,'0')}`,amount_thb:10+i})),{...invoice,invoice_id:'outside',vendor_id:'V2',invoice_date:'2026-01-01',amount_thb:99999},{...invoice,invoice_id:'wrong-category',vendor_id:'V3',invoice_date:'2026-07-02',amount_thb:99999}];
 const r=fn('statisticalAnalysis')(rows,[vendor,{...vendor,vendor_id:'V2'},{...vendor,vendor_id:'V3',category:'Travel'}],{target_vendor_id:'V1',peer_start:'2026-07-01',peer_end:'2026-07-31'});
 assert.equal(r.peer.n_a,8);assert.equal(r.peer.n_b,5);assert.deepEqual(r.peer.peer_vendor_ids,['V2']);
});
test('source-to-staging count mismatch blocks analytics',()=>{
 const p=fn('prepareData')({employees:[employee],vendors:[vendor],invoices:[invoice],landing_controls:{employees:1,vendors:1,invoices:2}});
 assert.equal(p.controls.source_to_staging.invoices.pass,false);
 assert.throws(()=>fn('assertReconciled')(p.controls),/Reconciliation/);
});
test('expense policy and repeated receipts detect reimbursement fraud without procurement splitting',()=>{
 const rows=[{...invoice,invoice_id:'C1',vendor_id:'M1',amount_thb:11000,employee_id:'E1',approver_id:'E2'},{...invoice,invoice_id:'C2',vendor_id:'M1',amount_thb:11000,employee_id:'E1',approver_id:'E1'}];
 const r=fn('expenseRules')(rows,[{vendor_id:'M1',category:'Hotel'}],[{emp_id:'E1',bank_account:'X'},{emp_id:'E2',bank_account:'Y'}],{policy_caps:{Hotel:9000}});
 assert.equal(r.filter(a=>a.model==='Expense policy cap').length,2);
 assert.equal(r.filter(a=>a.model==='Duplicate receipt rule').length,1);
 assert.equal(r.filter(a=>a.model==='Segregation of duties').length,1);
 assert.equal(r.some(a=>a.model==='Split-purchase rule'),false);
});
