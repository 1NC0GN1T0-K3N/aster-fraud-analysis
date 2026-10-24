"""Render the public analytical figures from saved pipeline outputs."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from build_graph_outputs import graph_figure


def render(root):
    root = Path(root)
    reports = root / 'reports'
    figures = reports / 'figures'
    figures.mkdir(parents=True, exist_ok=True)
    metrics = pd.read_csv(reports / 'model_metrics.csv')
    test = metrics.loc[metrics['split'].eq('test')].set_index('model')
    order = ['Existing rules', 'Logistic regression', 'Random Forest']
    x = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for i, (metric, label) in enumerate([('precision', 'Precision'), ('recall', 'Recall'), ('f1', 'F1')]):
        ax.bar(x + (i - 1) * .24, test.loc[order, metric], width=.24, label=label)
    ax.set(xticks=x, xticklabels=order, ylim=(0, 1), ylabel='Score', title='Synthetic test performance (800 claims, 60 planted fraud)')
    ax.legend()
    fig.tight_layout()
    fig.savefig(figures / 'model_comparison.png', dpi=180)
    plt.close(fig)

    curves = json.loads((reports / 'pr_curves.json').read_text())
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for slug, label in [('lr', 'Logistic regression'), ('rf', 'Random Forest')]:
        curve = curves[f'{slug}_test']
        ax.plot(curve['recall'], curve['precision'], label=label)
    rules = test.loc['Existing rules']
    ax.scatter(rules['recall'], rules['precision'], marker='x', color='black', label='Existing rules')
    prevalence = float((test.iloc[0]['tp'] + test.iloc[0]['fn']) / test.iloc[0][['tp', 'fp', 'fn', 'tn']].sum())
    ax.axhline(prevalence, linestyle='--', color='grey', label=f'Test prevalence ({prevalence:.1%})')
    ax.set(xlabel='Recall', ylabel='Precision', xlim=(0, 1), ylim=(0, 1.03), title='Test precision–recall performance')
    ax.legend(loc='lower left')
    fig.tight_layout()
    fig.savefig(figures / 'precision_recall.png', dpi=180)
    plt.close(fig)

    importance = pd.read_csv(reports / 'rf_permutation_importance.csv').nlargest(8, 'mean_ap_drop').sort_values('mean_ap_drop')
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(importance['feature'], importance['mean_ap_drop'], xerr=importance['sd'])
    ax.set(xlabel='Mean decrease in validation average precision', title='Random Forest permutation importance (8 repeats)')
    fig.tight_layout()
    fig.savefig(figures / 'feature_importance.png', dpi=180)
    plt.close(fig)

    graph_figure(json.loads((reports / 'graph_analysis.json').read_text()), figures / 'graph_relationships.png')
    print(f'Rendered four analytical figures in {figures}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1], help='Directory containing pipeline reports/')
    render(parser.parse_args().root)
