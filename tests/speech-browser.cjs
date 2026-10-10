const { chromium } = require('C:/Users/ASUS/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');

function wavDuration(buffer) {
  let byteRate = 0, dataBytes = 0;
  assert.equal(buffer.toString('ascii', 0, 4), 'RIFF');
  for (let offset = 12; offset + 8 <= buffer.length;) {
    const kind = buffer.toString('ascii', offset, offset + 4), size = buffer.readUInt32LE(offset + 4);
    if (kind === 'fmt ') byteRate = buffer.readUInt32LE(offset + 16);
    if (kind === 'data') dataBytes = size;
    offset += 8 + size + (size % 2);
  }
  assert.ok(byteRate > 0 && dataBytes > 0);
  return dataBytes / byteRate;
}

(async () => {
  const evidence = path.resolve(__dirname, '..', 'evidence');
  await fs.mkdir(evidence, { recursive: true });
  const browser = await chromium.launch({ executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  const errors = [], blocked = [], checks = [];
  page.on('pageerror', error => errors.push(error.message));
  await context.route('**/*', route => {
    const url = route.request().url();
    if (/^(http:\/\/(127\.0\.0\.1|localhost)(:\d+)?\/|blob:|data:)/.test(url)) return route.continue();
    blocked.push(url);
    return route.abort();
  });
  try {
    await page.goto('http://127.0.0.1:5173');
    await page.getByRole('textbox', { name: 'Editable transcript' }).fill('Every sign connects. Help. Yes. Learn.');
    await page.getByRole('button', { name: 'Speak transcript', exact: true }).waitFor({ state: 'visible' });
    await page.waitForFunction(() => !document.querySelector('.speech-play').disabled);
    const voices = await page.getByRole('combobox', { name: 'Offline speech voice' }).locator('option').allTextContents();
    assert.ok(voices.includes('Microsoft Zira Desktop'));
    checks.push('Installed local SAPI voice appears in the app');

    await page.getByRole('button', { name: 'Speak transcript', exact: true }).click();
    await page.waitForFunction(() => {
      const audio = document.querySelector('audio');
      return audio?.src.startsWith('blob:') && audio.duration > 1 && audio.currentTime > 0.1 && !audio.paused;
    }, null, { timeout: 30000 });
    const playback = await page.locator('audio').evaluate(async audio => {
      const response = await fetch(audio.src);
      const buffer = await response.arrayBuffer();
      const header = String.fromCharCode(...new Uint8Array(buffer.slice(0, 4)));
      const decoder = new AudioContext();
      const decoded = await decoder.decodeAudioData(buffer.slice(0));
      const samples = decoded.getChannelData(0);
      let amplitude = 0;
      for (let i = 0; i < samples.length; i++) amplitude = Math.max(amplitude, Math.abs(samples[i]));
      const state = { blobBytes: buffer.byteLength, header, duration: audio.duration, decodedDuration: decoded.duration,
        currentTime: audio.currentTime, readyState: audio.readyState, paused: audio.paused, amplitude, sampleRate: decoded.sampleRate };
      await decoder.close();
      return state;
    });
    assert.equal(playback.header, 'RIFF');
    assert.ok(playback.blobBytes > 10000 && playback.amplitude > 0.01 && playback.currentTime > 0.1 && !playback.paused);
    checks.push('Speech button receives real WAV bytes, decodes audible PCM and advances local audio playback');
    await page.getByRole('button', { name: 'Stop speech', exact: true }).click();
    const stopped = await page.locator('audio').evaluate(audio => ({ paused: audio.paused, currentTime: audio.currentTime }));
    assert.ok(stopped.paused && stopped.currentTime === 0);
    checks.push('Stop speech pauses and resets audio');

    const downloadWait = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Audio', exact: true }).click();
    await (await downloadWait).saveAs(path.join(evidence, 'browser-speech.wav'));
    const downloaded = await fs.readFile(path.join(evidence, 'browser-speech.wav'));
    assert.equal(downloaded.toString('ascii', 0, 4), 'RIFF');
    assert.equal(downloaded.length, playback.blobBytes);
    checks.push('Audio download saves the actual locally synthesized WAV');

    await page.getByRole('combobox', { name: 'Speech speed' }).selectOption('1.5');
    const speedResponse = page.waitForResponse(response => response.url().endsWith('/api/speech') && response.request().postDataJSON().rate === 1.5);
    const fasterDownloadWait = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Audio', exact: true }).click();
    assert.equal((await speedResponse).status(), 200);
    await (await fasterDownloadWait).saveAs(path.join(evidence, 'browser-speech-fast.wav'));
    const fasterDownloaded = await fs.readFile(path.join(evidence, 'browser-speech-fast.wav'));
    const fasterDuration = wavDuration(fasterDownloaded);
    assert.ok(fasterDuration < playback.duration * 0.8);
    checks.push('Changing speed invalidates the cached WAV; the next download contains faster synthesized speech');
    assert.deepEqual(errors, []);
    const report = { passed: true, checks, playback, stopped, fasterDuration, voices, pageErrors: errors, blockedExternalRequests: blocked,
      network: 'External browser requests denied; loopback and local blob URLs only' };
    await fs.writeFile(path.join(evidence, 'speech-browser-verification.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
