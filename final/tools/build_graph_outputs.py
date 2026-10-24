"""Evidence-based EP14 report extension, scientific figure and course map."""
from pathlib import Path
import json
import pandas as pd

COVERAGE = [
    ['EP01–02','Fraud definition, business cycle and investigation lifecycle','Case narrative distinguishes intent, error and document verification. n8n setup is optional.'],
    ['EP03','Acquisition, profiling, control totals and cleansing','Source hashes, 12-row quarantine, count/amount reconciliation, training monthly profiles.'],
    ['EP04','Duplicates, logical checks, limits and segregation of duties','Receipt reuse, self-approval, allowance and undisclosed account-match baseline.'],
    ['EP05','Distributions, robust scores and peer comparisons','Training hotel price-ratio quartiles, MAD and robust z-scores; employee peer profiles.'],
    ['EP06–07','Peer and temporal comparison design','Descriptive employee and monthly training comparisons. No significance-test or Benford claim.'],
    ['EP08','Temporal behaviour and anomaly interpretation','Prior 30-day frequency, prior 90-day merchant share and legitimate unusual cases. No SOM or clustering classifier.'],
    ['EP10','Supervised learning and logistic regression','Training-only preprocessing, logistic coefficients, validation and unseen evaluation.'],
    ['EP11','Random Forest and imbalance','Class-weighted forest, interactions and validation permutation importance.'],
    ['EP12–13','Evaluation, association mining and AI accountability','Confusion matrices, precision/recall/F1, AP, FP-Growth and checked evidence summaries.'],
    ['EP14','Network properties, communities, paths and visualization','Observed affiliation graph, degree/betweenness, weighted communities and two-hop paths with source claim IDs.'],
]

def graph_figure(graph, destination):
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    # A scientific figure of the selected observed graph, not an illustrative asset.
    positions={'E009':(0,2),'E037':(0,1),'E065':(0,0),'V031':(2,1.6),'V032':(2,.4),
               'E020':(3.5,1),'V036':(5,1)}
    fig,ax=plt.subplots(figsize=(10,5.6))
    for e in graph['focus_edge_records']:
        a=positions[e['employee_id']];b=positions[e['merchant_id']]
        ax.plot([a[0],b[0]],[a[1],b[1]],color='#A0ADB5',lw=1+e['claim_count']**.5*.45,zorder=1)
    for node,(x,y) in positions.items():
        employee=node.startswith('E')
        ax.scatter(x,y,s=2200,marker='o' if employee else 's',color='#087F83' if employee else '#B96517',zorder=2)
        ax.text(x,y,node,color='white',ha='center',va='center',weight='bold',fontsize=12,zorder=3)
    ax.text(4.25,.38,'Disclosed relationship\n38 training claims',ha='center',fontsize=11,color='#142C43')
    ax.text(1,-.55,'E037 – V032 – E065 is an observed two-hop affiliation path.',ha='center',fontsize=10)
    ax.text(2.5,2.8,'Training-only focus selected from FP-Growth and repeat use',ha='center',fontsize=14,weight='bold')
    ax.legend(handles=[Line2D([],[],marker='o',color='white',markerfacecolor='#087F83',markersize=10,label='Employee'),
        Line2D([],[],marker='s',color='white',markerfacecolor='#B96517',markersize=10,label='Merchant')],loc='upper right',frameon=False)
    ax.text(2.5,-1.05,'Solid links represent expense claims. Width reflects claim count. Layout does not encode community membership.\nSelected view omits other training links. Shared merchants do not establish direct ties, ownership or guilt.',ha='center',fontsize=9,color='#5B6A75')
    ax.set(xlim=(-.7,5.7),ylim=(-1.2,3));ax.axis('off');fig.tight_layout()
    fig.savefig(destination,dpi=180);plt.close(fig)
