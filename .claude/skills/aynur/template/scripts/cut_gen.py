import json, subprocess, re, os, sys, importlib, numpy as np
sys.path.insert(0,'work'); P=importlib.import_module(sys.argv[1]); SPANS,FILL,FIX=P.SPANS,P.FILL,P.FIX
SRC='media/raw.mp4'
GRADE=getattr(P,'GRADE',open('grade.txt').read().strip()+",eq=contrast=1.04:saturation=1.06")
def load(a,b):
    pcm=subprocess.run(['ffmpeg','-v','error','-ss',str(a),'-to',str(b),'-i',SRC,'-ac','1','-ar','16000','-f','s16le','-'],capture_output=True).stdout
    return np.frombuffer(pcm,np.int16).astype(np.float32)/32768
lo=min(a for a,b in SPANS)-1; hi=max(b for a,b in SPANS)+1
x=load(lo,hi); n=320; db=np.array([20*np.log10(np.sqrt((x[i:i+n]**2).mean())+1e-9) for i in range(0,len(x)-n,n)])
sil=[]; q=db<-42; i=0
while i<len(q):
    if q[i]:
        j=i
        while j<len(q) and q[j]: j+=1
        if (j-i)*0.02>=0.15: sil.append((lo+i*0.02,lo+j*0.02))
        i=j
    else: i+=1
M=0.05
cuts=sorted([(s+M,e-M) for s,e in sil if e-s-2*M>0.05]+FILL)
pieces=[]
for s0,e0 in SPANS:
    cur=s0
    for ca,cb in cuts:
        if cb<=cur or ca>=e0: continue
        if ca-cur>0.08: pieces.append([cur,ca])
        cur=max(cur,cb)
    if e0-cur>0.08: pieces.append([cur,e0])
def remap():
    offs=[];t=0
    for a,b in pieces: offs.append(t); t+=b-a
    return offs,t
offs,dur=remap()
def mp(x):
    for (a,b),o in zip(pieces,offs):
        if x<a: return o
        if x<=b: return o+x-a
    return dur
toks_all=[]
for si,(t0s,t1s,text) in enumerate(FIX):
    t0=mp(t0s); t1=mp(t1s)
    ivs=[(max(o,t0),min(o+b-a,t1)) for (a,b),o in zip(pieces,offs) if o+b-a>t0 and o<t1]
    ivs=[(x,y) for x,y in ivs if y-x>0.05]; tot=sum(y-x for x,y in ivs)
    toks=text.split(); L=[len(re.sub(r'[^\w-]','',k))+1 for k in toks]; LT=sum(L); acc=0
    def at(f):
        r=f*tot
        for x,y in ivs:
            if r<=y-x: return x+r
            r-=y-x
        return ivs[-1][1]
    for k,l in zip(toks,L):
        if not re.sub(r'[^\w-]','',k): acc+=l; continue
        toks_all.append({'w':re.sub(r'[^\w-]','',k).lower(),'s':round(at(acc/LT),2),'sent':si}); acc+=l
subs=[]
for j,w in enumerate(toks_all):
    nxt=toks_all[j+1]['s'] if j+1<len(toks_all) else dur
    subs.append({'words':[[w['w'],w['s']]],'end':round(min(nxt,w['s']+1.2),2),'key':-1})
json.dump({'duration':round(dur,2),'subs':subs},open('work/subs.json','w'),ensure_ascii=False,indent=0)
json.dump(toks_all,open('work/toks.json','w'),ensure_ascii=False)
sent_start=[mp(a) for a,b,_ in FIX]
Z=[1.15,1.45]; HEAD={1.15:680,1.45:560}; SRC_HEAD=640; CX=0.52*1080
P2=[]
for (a,b),o in zip(pieces,offs):
    cur=a
    for s in [s for s in sent_start if o<s<o+b-a]: P2.append([cur,a+s-o]); cur=a+s-o
    P2.append([cur,b])
pieces=P2; offs,dur=remap()
def zoom_at(o):
    k=max([i for i,s in enumerate(sent_start) if s<=o+0.01] or [0]); return Z[k%2]
json.dump({'pieces':pieces,'offs':offs,'sent_start':sent_start},open('work/pieces.json','w'))
print('кусков',len(pieces),'длина',round(dur,1))
if 'nocut' in sys.argv: sys.exit()
os.makedirs('work/c',exist_ok=True); lst=[]
for k,((a,b),o) in enumerate(zip(pieces,offs)):
    z=zoom_at(o); cw=round(1080/z/2)*2; ch=round(1920/z/2)*2
    y0=int(max(0,min(1920-ch,SRC_HEAD-HEAD[z]/z))); x0=int(max(0,min(1080-cw,CX-cw/2)))
    fn=f'work/c/p{k:03d}.mov'
    subprocess.run(['ffmpeg','-v','error','-y','-ss',f'{a:.3f}','-i',SRC,'-t',f'{b-a:.3f}','-vf',f'fps=30,{GRADE},crop={cw}:{ch}:{x0}:{y0},scale=1080:1920:flags=lanczos,setsar=1,format=yuv420p',
        '-af','afade=t=in:d=0.01,afade=t=out:st=%.3f:d=0.01,aresample=48000'%(b-a-0.01),'-c:v','libx264','-crf','12','-preset','veryfast','-c:a','pcm_s16le',fn],check=True)
    lst.append(fn)
open('work/c/list.txt','w').write(''.join(f"file '{os.path.basename(x)}'\n" for x in lst))
subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i','work/c/list.txt','-c:v','copy','-c:a','aac','-b:a','320k','work/cut.mp4'],check=True)
