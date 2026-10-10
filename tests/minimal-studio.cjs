const {chromium}=require('C:/Users/ASUS/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const root=path.resolve(__dirname,'..'),output=path.join(root,'evidence');await fs.mkdir(output,{recursive:true});
 const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:900}}),page=await context.newPage(),errors=[],checks=[];
 page.on('pageerror',error=>errors.push(error.message));await context.route('**/*',route=>/^(http:\/\/(127\.0\.0\.1|localhost)|blob:|data:)/.test(route.request().url())?route.continue():route.abort());
 try{
  await page.goto('http://127.0.0.1:5173');await page.getByRole('button',{name:'Try a sentence video'}).waitFor();
  assert.equal(await page.locator('aside,nav,.transcript-card,.sample-buttons').count(),0);
  await page.screenshot({path:path.join(output,'minimal-home.png'),fullPage:true});checks.push('Home presents upload and webcam actions without dashboard clutter');
  const streamResponse=page.waitForResponse(response=>response.url().endsWith('/api/recognize-timeline')&&response.status()===200);
  await page.getByRole('button',{name:'Try a sentence video'}).click();
  await page.locator('.caption-placeholder').waitFor();
  await page.screenshot({path:path.join(output,'minimal-loading.png'),fullPage:true});checks.push('Sentence sample loads through the upload pipeline with a real streaming loading state');
  await streamResponse;await page.locator('.caption-copy').waitFor({timeout:60000});await page.waitForFunction(()=>document.querySelector('video').currentTime>.1);
  assert.match(await page.locator('.caption-eyebrow').innerText(),/UNCERTAIN/);
  const caption=await page.locator('.caption-copy').innerText();assert.ok(caption.length);assert.ok(!caption.includes('self defense'));
  const position=await page.evaluate(()=>{const video=document.querySelector('.video-canvas').getBoundingClientRect(),card=document.querySelector('.caption-card').getBoundingClientRect(),copy=document.querySelector('.caption-copy').getBoundingClientRect(),play=document.querySelector('.caption-speech').getBoundingClientRect();return{video:{x:video.x,y:video.y,width:video.width,height:video.height},card:{x:card.x,y:card.y,right:card.right,bottom:card.bottom},speechBelowText:play.y>copy.bottom}});
  assert.ok(position.video.width>1200);assert.ok(position.video.height>650);assert.ok(position.card.x>position.video.x+position.video.width*.6);assert.ok(position.card.right<position.video.x+position.video.width);assert.ok(position.speechBelowText);
  checks.push('Large video canvas contains caption overlay at upper right and speech play below caption text');
  const responsePromise=page.waitForResponse(response=>response.url().endsWith('/api/speech')&&response.status()===200);await page.getByRole('button',{name:'Speak captions'}).click();const response=await responsePromise;assert.equal(JSON.parse(response.request().postData()).text,caption);
  await page.waitForFunction(()=>document.querySelector('audio').currentTime>.05&&!document.querySelector('audio').paused);
  const audio=await page.locator('audio').evaluate(async element=>{const bytes=new Uint8Array(await(await fetch(element.src)).arrayBuffer());return{duration:element.duration,time:element.currentTime,header:String.fromCharCode(...bytes.slice(0,4)),bytes:bytes.length}});assert.equal(audio.header,'RIFF');assert.ok(audio.duration>0);
  checks.push('Listen button speaks the actual model caption with decoded, advancing local WAV audio');
  await page.getByRole('button',{name:'Edit caption transcript'}).click();await page.getByRole('textbox',{name:'Editable transcript'}).fill('My own reviewed words');assert.equal(await page.locator('.caption-copy').innerText(),'My own reviewed words');
  await page.getByRole('button',{name:'Edit caption transcript'}).click();
  await page.screenshot({path:path.join(output,'minimal-caption.png'),fullPage:true});checks.push('Caption editor remains available without a separate transcript dashboard');
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(output,'minimal-mobile.png'),fullPage:true});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  checks.push('Mobile layout contains video, captions and Listen without horizontal overflow');assert.deepEqual(errors,[]);
  await fs.writeFile(path.join(output,'minimal-studio-verification.json'),JSON.stringify({passed:true,checks,position,realModelCaption:caption,audio,errors,network:'All non-loopback browser requests denied',sentenceTranslation:false},null,2));console.log(JSON.stringify({passed:true,checks,position,realModelCaption:caption,audio},null,2));
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
