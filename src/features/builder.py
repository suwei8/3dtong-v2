"""Lagged numeric features; each row is constructed without the target draw."""
from collections import Counter
import numpy as np

WINDOWS=(10,30,100)
WARMUP=100

def feature_vector(history):
    if len(history)<WARMUP:
        raise ValueError(f"need at least {WARMUP} known draws")
    x=[]
    for n in WINDOWS:
        recent=history[-n:]
        counts=Counter(d for row in recent for d in set(row["KaiJiang"]))
        x.extend(counts.get(str(d),0)/n for d in range(10))
    for digit in map(str,range(10)):
        gap=next((i for i,row in enumerate(reversed(history)) if digit in row["KaiJiang"]),200)
        x.append(min(gap,200)/200)
    recent100=history[-100:]
    for pos in range(3):
        counts=Counter(row["KaiJiang"][pos] for row in recent100)
        x.extend(counts.get(str(d),0)/100 for d in range(10))
    last=tuple(int(ch) for ch in history[-1]["KaiJiang"])
    x.extend(d/9 for d in last)
    x.extend([sum(last)/27, (max(last)-min(last))/9])
    return np.array(x,dtype=np.float32)

def build_dataset(history, warmup=WARMUP):
    if len(history)<=warmup:
        raise ValueError("insufficient historical samples")
    features=[feature_vector(history[:i]) for i in range(warmup,len(history))]
    labels=[[int(str(d) in history[i]["KaiJiang"]) for d in range(10)] for i in range(warmup,len(history))]
    return np.stack(features),np.asarray(labels,dtype=np.int8)
