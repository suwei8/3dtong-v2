"""Shared interface and scoring for three-distinct-digit predictions."""
def top3(probs):
    return sorted(range(10),key=lambda d:(-float(probs[d]),d))[:3]

def hit(predicted, code):
    digits=set(str(d) for d in predicted)
    return bool(digits.intersection(code))

def accuracy(probs,actuals):
    if len(probs)!=len(actuals):
        raise ValueError("predictions and labels differ in length")
    return sum(bool(set(top3(p)) & {d for d,v in enumerate(y) if v}) for p,y in zip(probs,actuals))/len(actuals)
