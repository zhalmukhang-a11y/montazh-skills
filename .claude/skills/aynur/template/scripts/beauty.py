# Затемнение волос (насыщенный рыжий) + сглаживание кожи. usage: beauty.py in.mp4 out.mp4 [hair=0.3] [smooth=0.7]
import sys, subprocess, numpy as np, cv2
src, dst = sys.argv[1], sys.argv[2]
HAIR = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3
SM = float(sys.argv[4]) if len(sys.argv) > 4 else 0.7
EVEN = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0   # выравнивание света на лице (0..1)
MATTE = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0  # убрать блеск кожи (0..1)
RED = float(sys.argv[7]) if len(sys.argv) > 7 else 0.0    # волосы в медный (0..1)
TEX = float(sys.argv[9]) if len(sys.argv) > 9 else 0.35    # сколько мелкой текстуры кожи вернуть
W, H = 1080, 1920
def proc(img):  # img RGB uint8
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV).astype(np.float32)
    h, s, v = hsv[..., 0], hsv[..., 1] / 255, hsv[..., 2] / 255
    # волосы: рыже-оранжевый (H 0..14 из 180), высокая насыщенность
    hm = np.clip((s - 0.42) / 0.18, 0, 1) * ((h <= 22) | (h >= 172)) * np.clip((v - 0.08) / 0.1, 0, 1)
    hm = cv2.GaussianBlur(hm.astype(np.float32), (0, 0), 3)
    yy = np.arange(hm.shape[0], dtype=np.float32)[:, None]; xx = np.arange(hm.shape[1], dtype=np.float32)[None, :]
    hm *= np.clip((yy - 380) / 80, 0, 1) * np.clip((1350 - yy) / 80, 0, 1) * np.clip(1 - np.abs(xx - 540) / 480, 0, 1) ** 0.3  # только волосы, не фон
    # кожа: YCrCb + умеренная насыщенность
    ycc = cv2.cvtColor(img, cv2.COLOR_RGB2YCrCb).astype(np.float32)
    cr, cb, y = ycc[..., 1], ycc[..., 2], ycc[..., 0]
    sk = ((cr > 135) & (cr < 180) & (cb > 80) & (cb < 130) & (y > 70) & (s < 0.6)).astype(np.float32)
    sk = cv2.morphologyEx(sk, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    sk = cv2.GaussianBlur(sk, (0, 0), 7)
    sk *= np.clip((1560 - np.arange(sk.shape[0], dtype=np.float32)) / 60, 0, 1)[:, None]  # стол не трогаем
    f = img.astype(np.float32)
    # частотное разделение: ровный тон (сильно сглаженная основа) + немного мелкой текстуры обратно
    base = cv2.bilateralFilter(img, 0, 38, 16)
    base = cv2.bilateralFilter(base, 0, 30, 10).astype(np.float32)
    base = cv2.GaussianBlur(base, (0, 0), 2.0)
    fine = f - cv2.GaussianBlur(f, (0, 0), 1.6)
    sm = base + TEX * fine
    a = (SM * sk)[..., None]
    f = f * (1 - a) + sm * a
    if EVEN > 0 or MATTE > 0:
        L = f.mean(2) / 255
        if EVEN > 0:  # крупный свет по коже → ровнее (тени светлее, пересвет темнее)
            num = cv2.GaussianBlur((L * sk).astype(np.float32), (0, 0), 40); den = cv2.GaussianBlur(sk, (0, 0), 40) + 1e-4
            big = num / den; tgt = float((L * sk).sum() / (sk.sum() + 1e-4))
            ratio = np.clip((tgt + 1e-3) / (big + 1e-3), 0.75, 1.3) ** EVEN
            f *= (1 + (ratio - 1) * sk)[..., None]
        if MATTE > 0:  # блики: всё что ярче 0.68 на коже сжимаем
            L = f.mean(2) / 255
            over = np.clip(L - 0.62, 0, None)
            k = 1 - MATTE * sk * over / (L + 1e-4) * 0.85
            f *= k[..., None]
    f *= (1 - HAIR * hm)[..., None]
    WARM = float(sys.argv[8]) if len(sys.argv) > 8 else 0.0  # тёплый тон кожи
    if WARM > 0:
        f[..., 0] *= 1 + 0.09 * WARM * sk; f[..., 1] *= 1 + 0.045 * WARM * sk; f[..., 2] *= 1 - 0.02 * WARM * sk
    f[..., 1] *= 1 - (0.12 + 0.12 * RED) * hm; f[..., 2] *= 1 - (0.1 + 0.15 * RED) * hm  # рыжий → каштаново-медный
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
