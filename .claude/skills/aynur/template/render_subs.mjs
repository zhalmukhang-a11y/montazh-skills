// node render_subs.mjs           -> out/готово.mp4 (нарезка + субтитры, громкость под Reels)
// node render_subs.mjs still 2.5 -> work/still_2.5.png (проверить кадр с субтитром)
import puppeteer from 'puppeteer-core';
import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';

const [mode, ...ts] = process.argv.slice(2);
const CHROME = ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe', '/usr/bin/google-chrome'].find(f => fs.existsSync(f));
if (!CHROME) { console.error('Не нашёл Google Chrome. Установи его с google.com/chrome и запусти снова.'); process.exit(1); }
const { duration, subs } = JSON.parse(fs.readFileSync('work/subs.json', 'utf8'));
const STYLE = process.env.STYLE || 'subs.html';
const BG = process.env.BG || 'work/cut.mp4';
const OUT = process.env.OUT || 'out/готово.mp4';
const titles = fs.existsSync('work/titles.json') && STYLE !== 'subs.html' ? JSON.parse(fs.readFileSync('work/titles.json', 'utf8')) : [];
fs.mkdirSync('work/subframes', { recursive: true }); fs.mkdirSync('out', { recursive: true });

const browser = await puppeteer.launch({ headless: true, executablePath: CHROME, args: ['--allow-file-access-from-files'] });
const page = await browser.newPage();
await page.setViewport({ width: 1080, height: 1920 });
await page.goto('file://' + path.resolve(STYLE), { waitUntil: 'networkidle0' });
await page.evaluate((s, ti) => { window.SUBS = s; window.TITLES = ti; }, subs, titles);
await page.evaluate(() => document.fonts.ready);

if (mode === 'still') {
  for (const t of ts.map(Number)) {
    execFileSync('ffmpeg', ['-v', 'error', '-y', '-ss', String(t), '-i', BG, '-frames:v', '1', 'work/_bg.png']);
    await page.evaluate(t => render(t), t);
    await page.screenshot({ path: 'work/_sub.png', omitBackground: true });
    execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', 'work/_bg.png', '-i', 'work/_sub.png', '-filter_complex', 'overlay', `work/still_${t}.png`]);
  }
  console.log('Кадры: work/still_*.png');
} else {
  fs.readdirSync('work/subframes').forEach(f => fs.rmSync('work/subframes/' + f));
  const n = Math.round(duration * 30);
  for (let i = 0; i < n; i++) {
    await page.evaluate(t => render(t), i / 30);
    await page.screenshot({ path: `work/subframes/s${String(i).padStart(5, '0')}.png`, omitBackground: true });
    if (i % 30 === 0) process.stdout.write(`\rсубтитры: ${Math.round(i / n * 100)}%`);
  }
  console.log('\nсклеиваю…');
  // Instagram Reels: 1080×1920, 30 fps, H.264 High, 14 Мбит/с, AAC 320 кбит/с, −14 LUFS
  execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', BG, '-framerate', '30', '-i', 'work/subframes/s%05d.png',
    '-filter_complex', '[0:v][1:v]overlay=eof_action=pass,fps=30,format=yuv420p[v];[0:a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]', '-map', '[v]', '-map', '[a]',
    '-c:v', 'libx264', '-profile:v', 'high', '-level', '4.2', '-preset', 'slow', '-b:v', '14M', '-maxrate', '14M', '-bufsize', '28M',
    '-r', '30', '-g', '60', '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
    '-c:a', 'aac', '-b:a', '320k', '-ar', '48000', '-movflags', '+faststart', OUT]);
  console.log('Готово: ' + OUT);
}
await browser.close();
