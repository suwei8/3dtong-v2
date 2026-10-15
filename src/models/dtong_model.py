"""Original Main10 six-digit rule used as a separately scored baseline.

The lookup is frozen, not retrained or tuned to hidden draws.
"""
TABLE={
0:"012359",1:"015789",2:"012368",3:"025689",4:"013457",
5:"012467",6:"123789",7:"134679",8:"134589",9:"234579",
}
def rule_top3(previous_code):
    a,b,c=map(int,previous_code)
    key=(a*a+b*b+c*c+4)%10
    return [int(d) for d in sorted(TABLE[key])[:3]]
