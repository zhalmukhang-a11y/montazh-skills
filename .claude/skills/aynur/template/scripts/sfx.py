# usage: sfx.py events.json duration out.wav
import json,sys,numpy as np,wave
ev=json.load(open(sys.argv[1])); D=float(sys.argv[2]); SR=48000
rng=np.random.default_rng(1)
def whoosh(L=0.32):
    n=int(L*SR); x=rng.standard_normal(n)
    X=np.fft.rfft(x); f=np.fft.rfftfreq(n,1/SR); X*=((f>250)&(f<5000))*(1/np.maximum(f,250)**0.5); x=np.fft.irfft(X,n)
    t=np.linspace(0,1,n); env=np.sin(np.pi*t**0.6)**2
    x=x*env; return x/np.abs(x).max()
def chime(L=0.45):
    n=int(L*SR); t=np.arange(n)/SR
    x=(np.sin(2*np.pi*1320*t)+0.6*np.sin(2*np.pi*1980*t)+0.3*np.sin(2*np.pi*2640*t))*np.exp(-t*9)*np.minimum(1,t/0.005)
    return x/np.abs(x).max()
W=whoosh(); C=chime()
out=np.zeros(int((D+1)*SR))
for t,k in ev:
    s=whoosh() if k=='w' else C
    g=0.03 if k=="w" else 0.015
    i=max(0,int((t-(0.12 if k=='w' else 0.0))*SR)); out[i:i+len(s)]+=g*s[:len(out)-i]
out=out[:int(D*SR)]
pcm=(np.clip(out,-1,1)*32767).astype(np.int16)
st=np.stack([pcm,pcm],1)
w=wave.open(sys.argv[3],'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes()); w.close()
