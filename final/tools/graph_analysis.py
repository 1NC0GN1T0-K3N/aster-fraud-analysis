"""EP14 descriptive graph investigation. Uses observed training records, never labels."""
from pathlib import Path
from itertools import combinations
import hashlib, json
import networkx as nx
import numpy as np
import pandas as pd

GRAPH_COLUMNS = ['claim_id','employee_id','merchant_id','approver_id','amount_thb','submitted_at','split']

def analyze_graph(frame, output_root, association_rows):
    root = Path(output_root)
    out = root / 'reports'
    out.mkdir(parents=True, exist_ok=True)
    # Explicit whitelist prevents private labels and model scores from entering the graph.
    train = frame.loc[frame['split'].eq('train'), GRAPH_COLUMNS].copy()
    train = train.sort_values(['employee_id','merchant_id','claim_id']).reset_index(drop=True)
    graph = nx.Graph(period='2025-01 through 2025-06', relation='observed expense affiliation')
    for employee in sorted(train.employee_id.unique()):
        graph.add_node(employee, node_type='Employee', bipartite=0)
    for merchant in sorted(train.merchant_id.unique()):
        graph.add_node(merchant, node_type='Merchant', bipartite=1)
    edges = []
    for (employee, merchant), rows in train.groupby(['employee_id','merchant_id'], sort=True):
        props = dict(claim_count=len(rows), amount_thb=round(float(rows.amount_thb.sum()),2),
                     claim_ids=sorted(rows.claim_id), approver_ids=sorted(rows.approver_id.unique()))
        graph.add_edge(employee, merchant, **props)
        edges.append(dict(employee_id=employee,merchant_id=merchant,claim_count=props['claim_count'],
                          amount_thb=props['amount_thb'],claim_ids=';'.join(props['claim_ids']),
                          approver_ids=';'.join(props['approver_ids'])))
    edge_table = pd.DataFrame(edges)
    between = nx.betweenness_centrality(graph, normalized=True, weight=None)
    # Claim-count weights express repeated affiliation, not monetary distance or verified ownership.
    communities = list(nx.community.greedy_modularity_communities(graph, weight='claim_count', resolution=1))
    communities = sorted(communities, key=lambda c:(-len(c),tuple(sorted(c))))
    membership = {node:i+1 for i,community in enumerate(communities) for node in community}
    nodes = []
    for node in sorted(graph):
        incident = list(graph.edges(node,data=True))
        kind = graph.nodes[node]['node_type']
        opposite_n = sum(graph.nodes[x]['node_type'] != kind for x in graph)
        nodes.append(dict(node_id=node,node_type=kind,unique_counterparties=graph.degree(node),
                          counterpart_fraction=graph.degree(node)/opposite_n,
                          claim_count=sum(e[2]['claim_count'] for e in incident),
                          amount_thb=round(sum(e[2]['amount_thb'] for e in incident),2),
                          betweenness=between[node],community_id=membership[node]))
    node_table = pd.DataFrame(nodes)
    community_rows = []
    for i,community in enumerate(communities,1):
        internal = graph.subgraph(community)
        community_rows.append(dict(community_id=i,nodes=len(community),
            employees=sum(graph.nodes[n]['node_type']=='Employee' for n in community),
            merchants=sum(graph.nodes[n]['node_type']=='Merchant' for n in community),
            internal_edges=internal.number_of_edges(),
            internal_claims=sum(d['claim_count'] for *_,d in internal.edges(data=True)),
            members=';'.join(sorted(community))))
    # Focus derives from training FP-Growth outputs and repeat affiliation, not private suspect IDs.
    focus_merchants = sorted({r['consequent'].split('=',1)[1] for r in association_rows})
    focus_edges = edge_table.loc[edge_table.merchant_id.isin(focus_merchants) & edge_table.claim_count.ge(3)].copy()
    focus_nodes = set(focus_edges.employee_id) | set(focus_edges.merchant_id)
    focus_paths = []
    for merchant, rows in focus_edges.groupby('merchant_id',sort=True):
        by_employee = rows.set_index('employee_id')
        for left,right in combinations(sorted(rows.employee_id),2):
            a=by_employee.loc[left]; b=by_employee.loc[right]
            focus_paths.append(dict(employee_a=left,via_merchant=merchant,employee_b=right,
                left_claim_count=int(a.claim_count),right_claim_count=int(b.claim_count),
                left_claim_ids=a.claim_ids,right_claim_ids=b.claim_ids,
                interpretation='Both employees claimed this merchant. No direct employee relationship is established.'))
    path_table = pd.DataFrame(focus_paths,columns=['employee_a','via_merchant','employee_b','left_claim_count',
        'right_claim_count','left_claim_ids','right_claim_ids','interpretation'])
    n_employee=int(node_table.node_type.eq('Employee').sum());n_merchant=len(node_table)-n_employee
    checks = [
        ('Training snapshot has 2400 claims', len(train)==2400),
        ('Graph sources exclude labels and scores', list(train.columns)==GRAPH_COLUMNS),
        ('Graph is bipartite', nx.is_bipartite(graph)),
        ('Each source claim belongs to one graph edge', int(edge_table.claim_count.sum())==len(train)),
        ('Graph amounts reconcile to training claims', abs(edge_table.amount_thb.sum()-train.amount_thb.sum())<.01),
        ('Communities partition observed nodes', set(membership)==set(graph) and sum(map(len,communities))==len(graph)),
        ('Focus selection has source edges', all(graph.has_edge(r.employee_id,r.merchant_id) for r in focus_edges.itertuples())),
        ('Every two-hop path uses observed links', all(graph.has_edge(r.employee_a,r.via_merchant) and graph.has_edge(r.employee_b,r.via_merchant) for r in path_table.itertuples())),
    ]
    for name,passed in checks:
        if not passed: raise AssertionError(name)
    summary = dict(method='Training-only employee–merchant affiliation graph',networkx_version=nx.__version__,
        input_columns=GRAPH_COLUMNS,training_claims=len(train),employees=n_employee,merchants=n_merchant,
        nodes=len(graph),edges=graph.number_of_edges(),components=nx.number_connected_components(graph),
        bipartite_density=graph.number_of_edges()/(n_employee*n_merchant),
        community_count=len(communities),weighted_modularity=nx.community.modularity(graph,communities,weight='claim_count'),
        centrality='Exact normalized unweighted shortest-path betweenness on all observed training nodes.',
        community_method='Greedy modularity on claim-count weights, resolution 1. Descriptive partition of a bipartite graph.',
        focus_selection='Merchants in qualifying training FP-Growth rules; display employee–merchant edges with at least 3 training claims.',
        focus_nodes=len(focus_nodes),focus_edges=len(focus_edges),focus_shared_merchant_paths=len(path_table),
        focus_merchants=focus_merchants,
        node_metrics=node_table.to_dict('records'),community_summary=community_rows,
        focus_edge_records=focus_edges.to_dict('records'),focus_paths=focus_paths,
        training_source_sha256=hashlib.sha256(train.to_csv(index=False).encode()).hexdigest(),
        no_predictive_graph_claim='No graph-derived fraud score, label propagation, link prediction, ownership or funds-flow inference. Existing classifiers unchanged.',
        checks=[dict(check=name,passed=bool(passed)) for name,passed in checks])
    edge_table.to_csv(out/'graph_edges.csv',index=False)
    node_table.to_csv(out/'graph_nodes.csv',index=False)
    pd.DataFrame(community_rows).to_csv(out/'graph_communities.csv',index=False)
    focus_edges.to_csv(out/'graph_focus_edges.csv',index=False)
    path_table.to_csv(out/'graph_paths.csv',index=False)
    (out/'graph_analysis.json').write_text(json.dumps(summary,indent=2))
    return summary

def profile_training(frame, output_root):
    """Earlier-lecture distributions and peer comparisons, kept descriptive."""
    train = frame.loc[frame['split'].eq('train')].copy()
    hotel = train.loc[train.category.eq('Hotel')].copy()
    ratio = hotel.market_rate_ratio
    median=float(ratio.median());mad=float((ratio-median).abs().median())
    hotel['robust_z']=.67448975*(ratio-median)/mad if mad else 0.0
    peers=hotel.groupby('employee_id').agg(hotel_claims=('claim_id','size'),
        median_price_ratio=('market_rate_ratio','median'),mean_price_ratio=('market_rate_ratio','mean'),
        high_robust_z_count=('robust_z',lambda z:int((z>3.5).sum())))
    peers['overall_hotel_median_ratio']=median
    peers['median_ratio_to_peer_median']=peers.median_price_ratio/median
    peers=peers.sort_values(['median_ratio_to_peer_median','hotel_claims'],ascending=False)
    monthly=train.groupby(train.submitted_at.dt.month).agg(claims=('claim_id','size'),
        gross_amount_thb=('amount_thb','sum'),median_allowance_ratio=('amount_to_allowance','median'))
    monthly.index.name='month_2025'
    root=Path(output_root)/'reports'
    peers.to_csv(root/'training_peer_profile.csv');monthly.to_csv(root/'training_monthly_profile.csv')
    summary=dict(training_hotel_claims=len(hotel),median_price_ratio=median,
        q1=float(ratio.quantile(.25)),q3=float(ratio.quantile(.75)),mad=mad,
        robust_z_over_3_5=int((hotel.robust_z>3.5).sum()),
        interpretation='Descriptive training-only peer and monthly comparisons. Robust scores are contextual leads, not p-values or fraud labels. No formal significance test or Benford claim.')
    (root/'training_profile.json').write_text(json.dumps(summary,indent=2))
    return summary

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    frame=pd.read_csv(root/'private/predictions_with_ground_truth.csv',parse_dates=['submitted_at'])
    rows=pd.read_csv(root/'reports/association_rules.csv').to_dict('records')
    graph=analyze_graph(frame,root,rows);profile_training(frame,root)
    print(json.dumps({k:graph[k] for k in ['nodes','edges','community_count','weighted_modularity','focus_nodes','focus_edges','focus_shared_merchant_paths']}))
