# Затемнение волос (насыщенный рыжий) + сглаживание кожи. usage: beauty.py in.mp4 out.mp4 [hair=0.3] [smooth=0.7]
import sys, subprocess, numpy as np, cv2
src, dst = sys.argv[1], sys.argv[2]
HAIR = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3
SM = float(sys.argv[4]) if len(sys.argv) > 4 else 0.7
W, H = 1080, 1920
def proc(img):  # img RGB uint8
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV).astype(np.float32)
    h, s, v = hsv[..., 0], hsv[..., 1] / 255, hsv[..., 2] / 255
    # волосы: рыже-оранжевый (H 0..14 из 180), высокая насыщенность
    hm = np.clip((s - 0.42) / 0.18, 0, 1) * ((h <= 22) | (h >= 172)) * np.clip((v - 0.08) / 0.1, 0, 1)
    hm = cv2.GaussianBlur(hm.astype(np.float32), (0, 0), 3)
    # кожа: YCrCb + умеренная насыщенность
    ycc = cv2.cvtColor(img, cv2.COLOR_RGB2YCrCb).astype(np.float32)
    cr, cb, y = ycc[..., 1], ycc[..., 2], ycc[..., 0]
    sk = ((cr > 135) & (cr < 180) & (cb > 80) & (cb < 130) & (y > 70) & (s < 0.6)).astype(np.float32)
    sk = cv2.GaussianBlur(sk, (0, 0), 6)
    f = img.astype(np.float32)
    sm = cv2.bilateralFilter(img, 0, 30, 12).astype(np.float32)
    sm = cv2.bilateralFilter(sm.astype(np.uint8), 0, 24, 7).astype(np.float32)
    a = (SM * sk)[..., None]
    f = f * (1 - a) + sm * a
    f *= (1 - HAIR * hm)[..., None]
    f[..., 1] *= 1 - 0.12 * hm; f[..., 2] *= 1 - 0.1 * hm  # рыжий → каштаново-медный
    return np.clip(f, 0, 255).astype(np.uint8)
if src.endswith('.png'):
    img = cv2.cvtColor(cv2.imread(src), cv2.COLOR_BGR2RGB)
    cv2.imwrite(dst, cv2.cvtColor(proc(img), cv2.COLOR_RGB2BGR)); sys.exit()
rd = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', src, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
wr = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', '30', '-i', '-',
                       '-i', src, '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-crf', '10', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'copy', dst], stdin=subprocess.PIPE)
n = 0
while True:
    b = rd.stdout.read(W * H * 3)
    if len(b) < W * H * 3: break
    wr.stdin.write(proc(np.frombuffer(b, np.uint8).reshape(H, W, 3)).tobytes()); n += 1
wr.stdin.close(); wr.wait(); print('кадров:', n)
