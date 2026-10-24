"""Reproducible ITCY514 classroom experiment. All evidence is fictitious."""
from pathlib import Path
from collections import defaultdict, deque
import hashlib, json, platform, sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SEED = 6836372
NUMERIC = ['amount_to_allowance','market_rate_ratio','approval_minutes','submission_lag_days',
           'merchant_age_days','claims_prior_30d','merchant_share_prior_90d','receipt_seen_before',
           'self_approved','bank_match','exception_approved','trip_consistent','usual_approver']
CATEGORICAL = ['category','department']
FEATURES = NUMERIC + CATEGORICAL
CAPS = {'Hotel':9000,'Flight':20000,'Meal':2500,'Taxi':1500}
CITY_RATE = {'Bangkok':4200,'Chiang Mai':2900,'Phuket':5600,'Khon Kaen':2400}
SPLITS = {'train':list(range(1,7)), 'validation':[7,8], 'test':[9,10], 'out_of_time':[11,12]}

def write_json(path, obj):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(obj,indent=2,default=lambda x: x.item() if isinstance(x,np.generic) else str(x),allow_nan=False))

def generate():
    rng=np.random.default_rng(SEED)
    employees=[]
    depts=['Sales','Operations','Engineering','Finance','Support','Management']
    for i in range(1,121):
        employees.append(dict(employee_id=f'E{i:03}',employee_name=f'Synthetic Employee {i:03}',
            department=depts[(i-1)%6],supervisor_id=f'E{(i-1)%6+1:03}',bank_account=f'SYN-E-{900000+i}',
            active=1))
    merchants=[dict(merchant_id=f'V{i:03}',merchant_name=f'Synthetic Travel Merchant {i:02}',
        bank_account=f'SYN-V-{800000+i}',registered_date=f'2024-{(i-1)%12+1:02}-01',
        disclosed_employee_link=0) for i in range(1,37)]
    merchants[30]['bank_account']=employees[8]['bank_account']
    merchants[30]['registered_date']='2025-01-01'
    merchants[35]['bank_account']=employees[19]['bank_account']
    merchants[35]['disclosed_employee_link']=1
    em={e['employee_id']:e for e in employees}; vm={v['merchant_id']:v for v in merchants}
    claims=[];truth=[];trips=[];approvals=[];group_history=defaultdict(list)
    ring=['E009','E037','E065']
    for month in range(1,13):
        # Exactly 400 claims/month; source slots and private labels are independent of detector cutoffs.
        month_rows=[]
        for j in range(400):
            idx=(month-1)*400+j+1;cid=f'FC-{idx:05}'
            day=int(rng.integers(2,25));minute=int(rng.integers(0,1440))
            submitted=pd.Timestamp(2025,month,day)+pd.Timedelta(minutes=minute)
            fraud=bool(rng.random()<0.075)
            scheme=str(rng.choice(['inflated_hotel','duplicate_reimbursement','approval_abuse','coordinated_merchant'],p=[.35,.2,.2,.25])) if fraud else 'legitimate'
            eid=f'E{int(rng.integers(7,121)):03}';vid=f'V{int(rng.integers(1,31)):03}'
            cat=str(rng.choice(['Hotel','Flight','Meal','Taxi'],p=[.5,.16,.2,.14]))
            city=str(rng.choice(list(CITY_RATE)));nights=int(rng.integers(1,5)) if cat=='Hotel' else 1
            lag=int(rng.integers(1,17));approval=float(np.exp(rng.normal(5.1,.95)))
            exception=int(rng.random()<.035);trip_ok=1;receipt=f'R-{month:02}-{j:04}'
            # Price variation overlaps fraud and benign observations. High amounts can be legitimate.
            if cat=='Hotel':amount=CITY_RATE[city]*nights*np.exp(rng.normal(0,.27))
            else:amount={'Flight':10500,'Meal':1250,'Taxi':650}[cat]*np.exp(rng.normal(0,.44))
            if exception:amount*=float(rng.uniform(1.6,2.5))
            approver=em[eid]['supervisor_id'] if rng.random()<.86 else f'E{int(rng.integers(1,7)):03}'
            if rng.random()<.012:approver=eid  # Benign administrative violations exist.
            loss=0.; group=f'G-{month:02}-{j:04}';actual=amount
            if scheme=='inflated_hotel':
                cat='Hotel';nights=int(rng.integers(1,5));actual=CITY_RATE[city]*nights*np.exp(rng.normal(0,.2))
                amount=actual*float(rng.uniform(1.45,2.7) if month<11 else rng.uniform(1.2,1.9))
                loss=amount-actual;exception=0
            elif scheme=='approval_abuse':
                approval=float(rng.uniform(2,48));amount*=float(rng.uniform(1.15,1.85))
                approver=eid if rng.random()<.48 else approver;trip_ok=int(rng.random()>.55)
                loss=amount*float(rng.uniform(.35,.85));exception=int(rng.random()<.08)
            elif scheme=='coordinated_merchant':
                eid=str(rng.choice(ring));vid=str(rng.choice(['V031','V032']));approver='E004'
                cat='Hotel';nights=int(rng.integers(1,4));actual=CITY_RATE[city]*nights
                amount=actual*float(rng.uniform(1.2,1.85));loss=amount-actual
                approval=float(rng.uniform(4,90));exception=0
            elif scheme=='duplicate_reimbursement':
                candidates=[r for r in month_rows if r['submitted_at']<submitted.isoformat() and r['category']=='Hotel']
                if candidates:
                    prior=candidates[int(rng.integers(len(candidates)))];eid=prior['employee_id'];vid=prior['merchant_id']
                    receipt=prior['receipt_number'];amount=prior['amount_thb'];nights=prior['nights'];cat='Hotel';city=prior['city']
                    approver=em[eid]['supervisor_id'];group=prior['case_group_id'];loss=amount
                else:
                    scheme='inflated_hotel';cat='Hotel';amount=CITY_RATE[city]*nights*1.8;loss=amount*.4
                exception=0
            elif rng.random()<.012 and month_rows:
                # Reused booking references can be legitimate: a negative control for the receipt rule.
                prior=month_rows[int(rng.integers(len(month_rows)))];receipt=prior['receipt_number'];vid=prior['merchant_id']
            if not fraud and rng.random()<.018:
                eid='E020';vid='V036'  # Disclosed relationship, legitimate claims.
            tripid=f'T-{idx:05}';aid=f'A-{idx:05}'
            allowance=CAPS[cat]*(nights if cat=='Hotel' else 1)
            claim=dict(claim_id=cid,employee_id=eid,merchant_id=vid,approver_id=approver,trip_id=tripid,
                approval_id=aid,receipt_number=receipt,category=cat,city=city,nights=nights,
                amount_thb=round(float(amount),2),submitted_at=submitted.isoformat(),currency='THB',
                business_purpose='Approved customer visit or field service',case_group_id=group)
            month_rows.append(claim)
            trips.append(dict(trip_id=tripid,employee_id=eid,city=city if trip_ok else ('Bangkok' if city!='Bangkok' else 'Phuket'),
                approved_nights=nights,start_date=(submitted-pd.Timedelta(days=lag)).date().isoformat(),approved=1))
            approvals.append(dict(approval_id=aid,approver_id=approver,approved_at=(submitted+pd.Timedelta(minutes=approval)).isoformat(),
                exception_approved=exception,exception_reference=f'EX-{idx:05}' if exception else '',
                approved_allowance_thb=round(max(allowance,float(amount)) if exception else allowance,2)))
            truth.append(dict(claim_id=cid,is_fraud=int(fraud),scheme=scheme,case_group_id=group,
                synthetic_excess_paid_thb=round(max(0.,float(loss)),2)))
        claims.extend(month_rows)
    clean=pd.DataFrame(claims).sort_values(['submitted_at','claim_id']).reset_index(drop=True)
    # Case group is private evaluation metadata, never a public predictor.
    clean=clean.drop(columns='case_group_id')
    raw=clean.copy()
    rejects=[]
    for k in range(12):
        r=clean.iloc[k].to_dict();r['claim_id']=f'BAD-{k+1:03}'
        if k==0:r['claim_id']=clean.iloc[0]['claim_id']
        elif k in [1,2]:r['amount_thb']='invalid' if k==1 else -200
        elif k==3:r['submitted_at']='not-a-date'
        elif k in [4,5]:r['employee_id']='E999'
        elif k in [6,7]:r['merchant_id']='V999'
        elif k==8:r['trip_id']='T-MISSING'
        elif k==9:r['approval_id']='A-MISSING'
        elif k==10:r['nights']=0
        else:r['currency']='USD'
        rejects.append(r)
    raw=pd.concat([raw,pd.DataFrame(rejects)],ignore_index=True)
    data={'employees':pd.DataFrame(employees),'merchants':pd.DataFrame(merchants),'trips':pd.DataFrame(trips),
          'approvals':pd.DataFrame(approvals),'expense_claims':raw}
    for name,frame in data.items():frame.to_csv(ROOT/'data/landing'/f'{name}.csv',index=False)
    pd.DataFrame(truth).to_csv(ROOT/'private/ground_truth.csv',index=False)
    return data

def prepare(data):
    c=data['expense_claims'].copy(); c['source_row']=np.arange(1,len(c)+1)
    dt=pd.to_datetime(c['submitted_at'],errors='coerce');amount=pd.to_numeric(c['amount_thb'],errors='coerce')
    nights=pd.to_numeric(c['nights'],errors='coerce')
    invalid=pd.DataFrame({
        'duplicate_claim_id':c['claim_id'].duplicated(keep='first'),
        'invalid_amount':amount.isna() | (amount<=0),
        'invalid_timestamp':dt.isna(),
        'unknown_employee':~c.employee_id.isin(data['employees'].employee_id),
        'unknown_merchant':~c.merchant_id.isin(data['merchants'].merchant_id),
        'unknown_trip':~c.trip_id.isin(data['trips'].trip_id),
        'unknown_approval':~c.approval_id.isin(data['approvals'].approval_id),
        'invalid_nights':nights.isna() | (nights<1),
        'unexpected_currency':c.currency.ne('THB'),
        'unknown_category':~c.category.isin(CAPS)})
    for name in ['employees','merchants','trips','approvals']:
        key={'employees':'employee_id','merchants':'merchant_id','trips':'trip_id','approvals':'approval_id'}[name]
        if data[name][key].isna().any() or data[name][key].duplicated().any():raise ValueError(f'Invalid master keys: {name}')
    bad=invalid.any(axis=1);q=c.loc[bad].copy()
    q['reasons']=invalid.loc[bad].apply(lambda row:'; '.join(row.index[row]),axis=1)
    valid=c.loc[~bad].copy();valid['amount_thb']=amount[~bad];valid['nights']=nights[~bad].astype(int)
    valid['submitted_at']=dt[~bad];valid=valid.sort_values(['submitted_at','claim_id']).reset_index(drop=True)
    raw_numeric=round(float(amount.fillna(0).sum()),2);prod_numeric=round(float(valid.amount_thb.sum()),2)
    quarantine_numeric=round(float(amount[bad].fillna(0).sum()),2)
    controls={'raw_claims':len(c),'production_claims':len(valid),'quarantined_claims':len(q),
        'raw_numeric_thb':raw_numeric,'production_thb':prod_numeric,'quarantine_numeric_thb':quarantine_numeric,
        'unparseable_amount_rows':int(amount.isna().sum()),'row_difference':len(c)-len(valid)-len(q),
        'amount_difference_thb':round(raw_numeric-prod_numeric-quarantine_numeric,2),
        'master_counts':{n:len(data[n]) for n in ['employees','merchants','trips','approvals']},
        'source_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'data/landing').glob('*.csv'))}}
    if controls['row_difference'] or abs(controls['amount_difference_thb'])>.01:raise AssertionError('Reconciliation failed')
    q.to_csv(ROOT/'reports/quarantine.csv',index=False)
    valid.to_csv(ROOT/'data/production/expense_claims.csv',index=False)
    write_json(ROOT/'reports/reconciliation.json',controls)
    return valid,controls

def engineer(valid,data):
    x=valid.merge(data['employees'],on='employee_id',validate='many_to_one')
    x=x.merge(data['merchants'],on='merchant_id',suffixes=('_employee','_merchant'),validate='many_to_one')
    x=x.merge(data['trips'],on='trip_id',suffixes=('','_trip'),validate='many_to_one')
    x=x.merge(data['approvals'],on='approval_id',suffixes=('','_approval'),validate='many_to_one')
    x=x.sort_values(['submitted_at','claim_id']).reset_index(drop=True)
    x['approval_minutes']=(pd.to_datetime(x.approved_at)-x.submitted_at).dt.total_seconds()/60
    if (x.approval_minutes<0).any():raise ValueError('Approval precedes submission')
    x['submission_lag_days']=(x.submitted_at.dt.normalize()-pd.to_datetime(x.start_date)).dt.days
    x['merchant_age_days']=(x.submitted_at.dt.normalize()-pd.to_datetime(x.registered_date)).dt.days.clip(lower=0)
    x['amount_to_allowance']=x.amount_thb/x.approved_allowance_thb
    expected=x.city.map(CITY_RATE)*x.nights
    x['market_rate_ratio']=np.where(x.category.eq('Hotel'),x.amount_thb/expected,x.amount_thb/x.category.map(CAPS))
    x['self_approved']=x.employee_id.eq(x.approver_id).astype(int)
    x['bank_match']=x.bank_account_employee.eq(x.bank_account_merchant).astype(int)
    x['trip_consistent']=(x.city.eq(x.city_trip)&x.employee_id.eq(x.employee_id_trip)&x.nights.le(x.approved_nights)).astype(int)
    x['usual_approver']=x.approver_id.eq(x.supervisor_id).astype(int)
    history=defaultdict(deque);seen=set();counts=[];shares=[];reuse=[]
    for r in x.itertuples():
        h=history[r.employee_id]
        while h and h[0][0]<r.submitted_at-pd.Timedelta(days=90):h.popleft()
        counts.append(sum(t>=r.submitted_at-pd.Timedelta(days=30) for t,v in h))
        shares.append(sum(v==r.merchant_id for t,v in h)/len(h) if h else 0.)
        key=(r.merchant_id,r.receipt_number);reuse.append(int(key in seen));seen.add(key)
        h.append((r.submitted_at,r.merchant_id))
    x['claims_prior_30d']=counts;x['merchant_share_prior_90d']=shares;x['receipt_seen_before']=reuse
    x['split']=x.submitted_at.dt.month.map({m:k for k,ms in SPLITS.items() for m in ms})
    x['rule_receipt']=x.receipt_seen_before.eq(1)
    x['rule_self_approval']=x.self_approved.eq(1)
    x['rule_cap']=x.amount_to_allowance.gt(1)
    x['rule_bank']=x.bank_match.eq(1)&x.disclosed_employee_link.eq(0)
    x['rule_alert']=x[['rule_receipt','rule_self_approval','rule_cap','rule_bank']].any(axis=1).astype(int)
    x[['claim_id','split']+FEATURES+['rule_alert']].to_csv(ROOT/'reports/features.csv',index=False)
    return x

def metrics(y,pred,scores=None):
    from sklearn.metrics import precision_score,recall_score,f1_score,confusion_matrix,average_precision_score,roc_auc_score
    tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    d=dict(n=len(y),positives=int(np.sum(y)),tp=int(tp),fp=int(fp),fn=int(fn),tn=int(tn),
        alerts=int(np.sum(pred)),precision=float(precision_score(y,pred,zero_division=0)),
        recall=float(recall_score(y,pred,zero_division=0)),f1=float(f1_score(y,pred,zero_division=0)))
    if scores is not None:
        d['average_precision']=float(average_precision_score(y,scores));d['roc_auc']=float(roc_auc_score(y,scores))
    return d

def train_evaluate(x):
    from sklearn.pipeline import Pipeline
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import StandardScaler,OneHotEncoder
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.inspection import permutation_importance
    from sklearn.metrics import precision_recall_curve
    import joblib,sklearn,scipy,mlxtend
    truth=pd.read_csv(ROOT/'private/ground_truth.csv')
    labelled=x.merge(truth,on='claim_id',validate='one_to_one')
    train=labelled[labelled.split.eq('train')];val=labelled[labelled.split.eq('validation')]
    processor=ColumnTransformer([('numeric',StandardScaler(),NUMERIC),('category',OneHotEncoder(handle_unknown='ignore'),CATEGORICAL)])
    candidates={
      'Logistic regression':Pipeline([('preprocess',processor),('model',LogisticRegression(C=1.,class_weight='balanced',max_iter=2000,random_state=SEED))]),
      'Random Forest':Pipeline([('preprocess',ColumnTransformer([('numeric','passthrough',NUMERIC),('category',OneHotEncoder(handle_unknown='ignore'),CATEGORICAL)])),
          ('model',RandomForestClassifier(n_estimators=240,max_depth=9,min_samples_leaf=8,max_features=.8,class_weight='balanced_subsample',n_jobs=2,random_state=SEED))])}
    results=[];curves={};thresholds={};predictions=labelled.copy();selection=[]
    # Threshold grid defined in advance; no final test enters model or threshold fitting.
    grid=np.round(np.linspace(.05,.95,91),2)
    for name,model in candidates.items():
        model.fit(train[FEATURES],train.is_fraud)
        vp=model.predict_proba(val[FEATURES])[:,1]
        options=[]
        for t in grid:
            m=metrics(val.is_fraud,(vp>=t).astype(int));options.append((m['f1'],m['precision'],float(t),m))
        _,_,t,m=max(options,key=lambda z:(z[0],z[1],z[2]))
        thresholds[name]=t;selection.append(dict(model=name,threshold=t,**m))
        slug='lr' if name.startswith('Logistic') else 'rf'
        joblib.dump(model,ROOT/'models'/f'{slug}.joblib')
        scores=model.predict_proba(labelled[FEATURES])[:,1]
        predictions[f'{slug}_score']=scores;predictions[f'{slug}_alert']=(scores>=t).astype(int)
        for split in SPLITS:
            mask=labelled.split.eq(split); y=labelled.loc[mask,'is_fraud']; s=scores[mask]
            results.append(dict(model=name,split=split,threshold=t,**metrics(y,(s>=t).astype(int),s)))
            pr,re,ts=precision_recall_curve(y,s)
            curves[f'{slug}_{split}']={'precision':pr.tolist(),'recall':re.tolist(),'thresholds':ts.tolist()}
    for split in SPLITS:
        r=labelled[labelled.split.eq(split)]
        results.append(dict(model='Existing rules',split=split,threshold=None,**metrics(r.is_fraud,r.rule_alert)))
    # Select a presentation champion using validation only, before examining final test results.
    champion=max(selection,key=lambda d:(d['f1'],d['precision']))['model']
    lr=candidates['Logistic regression'];coefs=lr.named_steps['model'].coef_[0]
    names=lr.named_steps['preprocess'].get_feature_names_out()
    pd.DataFrame({'feature':names,'coefficient':coefs,'odds_ratio':np.exp(coefs)}).to_csv(ROOT/'reports/logistic_coefficients.csv',index=False)
    imp=permutation_importance(candidates['Random Forest'],val[FEATURES],val.is_fraud,scoring='average_precision',n_repeats=8,random_state=SEED,n_jobs=2)
    pd.DataFrame({'feature':FEATURES,'mean_ap_drop':imp.importances_mean,'sd':imp.importances_std}).sort_values('mean_ap_drop',ascending=False).to_csv(ROOT/'reports/rf_permutation_importance.csv',index=False)
    predictions['selected_model']=champion
    predictions['selected_alert']=predictions['lr_alert' if champion.startswith('Logistic') else 'rf_alert']
    predictions['selected_score']=predictions['lr_score' if champion.startswith('Logistic') else 'rf_score']
    # Full bank-account values never enter published review outputs or AI packets.
    predictions=predictions.drop(columns=['bank_account_employee','bank_account_merchant'])
    predictions.to_csv(ROOT/'private/predictions_with_ground_truth.csv',index=False)
    publish=['claim_id','employee_id','merchant_id','approver_id','category','submitted_at','amount_thb','split',
        'rule_alert','lr_score','lr_alert','rf_score','rf_alert','selected_score','selected_alert']
    predictions[publish].to_csv(ROOT/'reports/claim_scores.csv',index=False)
    pd.DataFrame(results).to_csv(ROOT/'reports/model_metrics.csv',index=False)
    versions={'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__,'scipy':scipy.__version__,'mlxtend':mlxtend.__version__}
    write_json(ROOT/'models/model_card.json',dict(seed=SEED,features=FEATURES,thresholds=thresholds,selected_model=champion,
        selection='Highest validation F1, then validation precision. No test-based tuning.',
        split_months=SPLITS,scoring_time='After approval, before reimbursement; prior-history features only.',
        score_notice='Uncalibrated classifier scores on synthetic data; not real-world fraud probabilities.',versions=versions))
    write_json(ROOT/'reports/pr_curves.json',curves)
    return predictions,results,curves,champion,thresholds

def associations(x):
    from mlxtend.preprocessing import TransactionEncoder
    from mlxtend.frequent_patterns import fpgrowth,association_rules
    # Discovery uses training period only, and no private labels or fraud indicator item.
    train=x[x.split.eq('train')];rows=[]
    for r in train.itertuples():
        rows.append([f'Employee={r.employee_id}',f'Merchant={r.merchant_id}',f'Approver={r.approver_id}'])
    te=TransactionEncoder();matrix=pd.DataFrame(te.fit_transform(rows),columns=te.columns_)
    itemsets=fpgrowth(matrix,min_support=.004,use_colnames=True,max_len=3)
    rules=association_rules(itemsets,metric='confidence',min_threshold=.2)
    selected=[]
    for r in rules.itertuples():
        ant=sorted(r.antecedents);con=sorted(r.consequents)
        if len(con)!=1 or not con[0].startswith('Merchant=') or not any(a.startswith('Employee=') for a in ant):continue
        if r.lift<2:continue
        selected.append({'antecedents':' & '.join(ant),'consequent':con[0],
            'train_support':float(r.support),'train_confidence':float(r.confidence),'train_lift':float(r.lift),
            'train_count':int(round(r.support*len(train))), 'discovery_n':len(train)})
    selected=sorted(selected,key=lambda r:(-r['train_lift'],-r['train_count']))
    def item_mask(frame,item):
        k,v=item.split('=',1);col={'Employee':'employee_id','Merchant':'merchant_id','Approver':'approver_id'}[k]
        return frame[col].eq(v)
    for r in selected:
        for split in ['test','out_of_time']:
            d=x[x.split.eq(split)];ant=np.ones(len(d),dtype=bool)
            for item in r['antecedents'].split(' & '):ant &= item_mask(d,item).to_numpy()
            con=item_mask(d,r['consequent']).to_numpy();joint=ant&con
            r[f'{split}_count']=int(joint.sum());r[f'{split}_antecedent_n']=int(ant.sum())
            r[f'{split}_support']=float(joint.mean());r[f'{split}_confidence']=float(joint.sum()/ant.sum()) if ant.sum() else None
    pd.DataFrame(selected).to_csv(ROOT/'reports/association_rules.csv',index=False)
    write_json(ROOT/'reports/association_discovery.json',dict(method='FP-Growth',training_claims=len(train),min_support=.004,
        min_confidence=.2,min_lift=2.,max_itemset_length=3,rule_count=len(selected),
        notice='Associations are descriptive; no private labels used and no statistical significance or guilt claimed.',rules=selected))
    return selected

def validate(x,pred,controls):
    tests=[]
    def check(name,ok,detail=''):
        tests.append(dict(check=name,pass_=bool(ok),detail=detail))
        if not ok:raise AssertionError(name+': '+detail)
    check('Reconciled rows',controls['row_difference']==0)
    check('Reconciled numeric amounts',abs(controls['amount_difference_thb'])<=.01)
    check('Unique production claim IDs',x.claim_id.is_unique)
    check('No labels or entity IDs in classifier inputs',not set(FEATURES)&{'is_fraud','scheme','case_group_id','synthetic_excess_paid_thb','employee_id','merchant_id','claim_id'})
    check('No missing engineered predictors',not x[FEATURES].isna().any().any())
    for a,b in [('train','validation'),('validation','test'),('test','out_of_time')]:
        check(f'Chronology {a} before {b}',x[x.split.eq(a)].submitted_at.max()<x[x.split.eq(b)].submitted_at.min())
    groups=pred.groupby('case_group_id').split.nunique()
    check('Related duplicate case groups stay within partition',int(groups.max())==1)
    # Future perturbation: feature values on earlier records must be unchanged if later data are absent.
    early=x[x.split.isin(['train','validation'])]
    prefix_valid=pd.read_csv(ROOT/'data/production/expense_claims.csv');prefix_valid['submitted_at']=pd.to_datetime(prefix_valid.submitted_at)
    prefix_valid=prefix_valid[prefix_valid.submitted_at.dt.month.le(8)]
    data={n:pd.read_csv(ROOT/'data/landing'/f'{n}.csv') for n in ['employees','merchants','trips','approvals']}
    prefix=engineer(prefix_valid,data)
    check('Future removal leaves historical features unchanged',np.allclose(early[NUMERIC].to_numpy(float),prefix[NUMERIC].to_numpy(float)))
    # Restore complete feature export after the prefix test.
    x[['claim_id','split']+FEATURES+['rule_alert']].to_csv(ROOT/'reports/features.csv',index=False)
    check('Private truth has complete one-to-one coverage',len(pred)==len(x) and pred.is_fraud.notna().all())
    for split in SPLITS:check(f'Two target classes in {split}',pred[pred.split.eq(split)].is_fraud.nunique()==2)
    write_json(ROOT/'private/validation_checks.json',tests)
    return tests

def run():
    for directory in ['data/landing','data/production','private','reports','models']:
        (ROOT/directory).mkdir(parents=True,exist_ok=True)
    data=generate();valid,controls=prepare(data);x=engineer(valid,data)
    pred,results,curves,champion,thresholds=train_evaluate(x);rules=associations(x);checks=validate(x,pred,controls)
    from graph_analysis import analyze_graph,profile_training
    graph=analyze_graph(x,ROOT,rules);profile=profile_training(x,ROOT)
    summary=dict(seed=SEED,controls=controls,champion=champion,thresholds=thresholds,metrics=results,
        split_counts=pred.groupby('split').is_fraud.agg(['size','sum']).to_dict('index'),
        scheme_counts=pred.groupby('scheme').size().to_dict(),association_rules=rules[:12],
        association_rule_count=len(rules),validation_checks=len(checks),
        total_synthetic_fraud_claims=int(pred.is_fraud.sum()),
        graph_analysis={k:v for k,v in graph.items() if k not in ['node_metrics','community_summary','focus_edge_records','focus_paths']},
        training_profile=profile,
        note='All results describe synthetic classroom data; Peer review is outside the scope of this public portfolio release.')
    write_json(ROOT/'reports/results.json',summary)
    print(json.dumps({'champion':champion,'test':[r for r in results if r['split']=='test'],
        'out_of_time':[r for r in results if r['split']=='out_of_time'],'association_rules':len(rules),'checks':len(checks)},indent=2))
    return summary

if __name__=='__main__':run()
