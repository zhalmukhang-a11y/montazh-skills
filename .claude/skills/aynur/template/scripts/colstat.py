import cv2,numpy as np,sys,subprocess
def frames(src,ts,vf=None):
    out=[]
    for t in ts:
        cmd=['ffmpeg','-v','error','-ss',str(t),'-i',src,'-frames:v','1']+(['-vf',vf] if vf else [])+['-f','rawvideo','-pix_fmt','rgb24','-']
        b=subprocess.run(cmd,capture_output=True).stdout
        out.append(np.frombuffer(b,np.uint8).reshape(1920,1080,3))
    return out
def stats(fs):
    sk=[];bg=[];hair=[]
    for f in fs:
        ycc=cv2.cvtColor(f,cv2.COLOR_RGB2YCrCb).astype(int); hsv=cv2.cvtColor(f,cv2.COLOR_RGB2HSV).astype(int)
        m=(ycc[...,1]>135)&(ycc[...,1]<175)&(ycc[...,2]>85)&(ycc[...,2]<128)&(ycc[...,0]>90)
        m[:500]=0; m[1400:]=0
        sk.append(f[m].mean(0)); bg.append(f[50:240,:].reshape(-1,3).mean(0))
    return np.round(np.mean(sk,0),1),np.round(np.mean(bg,0),1)
if __name__=='__main__':
    print('ref ',stats(frames('ref/ref.mov',[5,12,17,27,33,45,50,56])))
    print('ours',stats(frames(sys.argv[1],[2,8,14,20,27,35,42,47])))
