import json,sys
n,a,b=sys.argv[1],float(sys.argv[2]),float(sys.argv[3])
for s in json.load(open(f"transcripts/IMG_{n}.json")):
    if s["end"]<a or s["start"]>b: continue
    print(f'[{s["start"]:.2f}-{s["end"]:.2f}] '+" ".join(f'{w["w"]}@{w["s"]:.2f}' for w in s["words"]))
