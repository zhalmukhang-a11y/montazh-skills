import subprocess,numpy as np,sys,json
def load(a,b):
    pcm=subprocess.run(['ffmpeg','-v','error','-ss',str(a),'-to',str(b),'-i','media/raw.mp4','-ac','1','-ar','16000','-f','s16le','-'],capture_output=True).stdout
    return np.frombuffer(pcm,np.int16).astype(np.float32)/32768
res=[]
for a,b in [tuple(map(float,r.split('-'))) for r in (sys.argv[1:] or ['32-62.2','132.5-156.2'])]:
    x=load(a,b); hop=160; win=512
    fr=np.lib.stride_tricks.sliding_window_view(x,win)[::hop]*np.hanning(win)
    S=np.abs(np.fft.rfft(fr,axis=1))[:,:200]+1e-6
    L=np.log(S); db=20*np.log10(np.sqrt((fr**2).mean(1))+1e-9)
    Ln=L-L.mean(1,keepdims=True)
    flux=np.r_[0,np.sqrt(((Ln[1:]-Ln[:-1])**2).mean(1))]
    k=np.ones(5)/5; fl=np.convolve(flux,k,'same')
    stable=(db>-38)&(fl<np.percentile(fl[db>-38],25))
    i=0;n=len(stable)
    while i<n:
        if stable[i]:
            j=i
            while j<n and stable[j]: j+=1
            if (j-i)*0.01>=0.22: res.append((round(a+i*0.01,2),round(a+j*0.01,2)))
            i=j
        else: i+=1
print(res)
json.dump(res,open('work/stable.json','w'))
