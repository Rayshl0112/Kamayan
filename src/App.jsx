import React,{useEffect,useReducer,useRef,useState} from 'react';
import {ArrowDownToLine,ArrowRight,Camera,Check,Clipboard,Hand,LoaderCircle,Maximize2,Pause,Play,RotateCcw,Sparkles,Square,Upload,X} from 'lucide-react';
import {initialTranscript,transcriptReducer} from './transcript.js';
const API='/api';
const formatTime=value=>`${Math.floor((value||0)/60)}:${String(Math.floor((value||0)%60)).padStart(2,'0')}`;
async function checked(response){if(!response.ok){let data;try{data=await response.json()}catch{}throw new Error(typeof data?.detail==='string'?data.detail:`The local service returned ${response.status}.`)}return response}
function save(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}

export default function Studio(){
 const [model,setModel]=useState(null),[speech,setSpeech]=useState(null),[samples,setSamples]=useState([]);
 const [file,setFile]=useState(null),[url,setUrl]=useState(''),[duration,setDuration]=useState(0),[time,setTime]=useState(0),[playing,setPlaying]=useState(false);
 const [captions,setCaptions]=useState([]),[analysis,setAnalysis]=useState('idle'),[progress,setProgress]=useState({index:0,total:1}),[error,setError]=useState(''),[drag,setDrag]=useState(false);
 const [fullCaption,setFullCaption]=useState('');
 const [camera,setCamera]=useState(false),[recording,setRecording]=useState(false),[loadingSample,setLoadingSample]=useState(false),[edit,setEdit]=useState(false),[notice,setNotice]=useState('');
 const [speaking,setSpeaking]=useState(false),[speechBusy,setSpeechBusy]=useState(false),[rate,setRate]=useState(1);
 const [transcript,dispatch]=useReducer(transcriptReducer,initialTranscript);
 const player=useRef(null),input=useRef(null),audio=useRef(null),audioUrl=useRef(''),stage=useRef(null),stream=useRef(null),recorder=useRef(null),chunks=useRef([]),captureTimer=useRef(null),recordedAt=useRef(0);
 const generation=useRef(0),recognitionAbort=useRef(null),speechGeneration=useRef(0),speechAbort=useRef(null),autoPlayed=useRef(false);
 const ready=!!model?.ready,sentenceSample=samples.find(sample=>sample.kind==='sentence');
 const currentCaption=captions.find(caption=>time>=caption.segment.start&&time<caption.segment.end+.05)||captions.at(-1);
 const visibleWords=captions.filter(caption=>caption.segment.start<=time+.05).map(caption=>!caption.uncertain&&caption.hand_detection_rate>=.3?caption.label:null).filter((word,index,all)=>word&&word!==all[index-1]);
 const captionText=transcript.text.trim()||currentCaption?.text||(visibleWords.length?visibleWords.join(' '):!currentCaption?.uncertain?currentCaption?.label||'':'');
 const spokenText=transcript.text.trim()||fullCaption||captionText;
 const uncertain=!transcript.text.trim()&&!!currentCaption?.uncertain;
 useEffect(()=>{let alive=true;Promise.all(['/model-status','/speech-status','/samples'].map(async endpoint=>(await checked(await fetch(API+endpoint))).json())).then(([m,s,list])=>{if(alive){setModel(m);setSpeech(s);setSamples(list.samples||[])}}).catch(()=>{if(alive)setModel({ready:false,error:'The local recognition service is not connected. Run start.ps1.'})});return()=>{alive=false}},[]);
 useEffect(()=>()=>{recognitionAbort.current?.abort();speechAbort.current?.abort();stream.current?.getTracks().forEach(track=>track.stop());clearTimeout(captureTimer.current);if(audioUrl.current)URL.revokeObjectURL(audioUrl.current)},[]);
 useEffect(()=>()=>{if(url)URL.revokeObjectURL(url)},[url]);
 useEffect(()=>{stopSpeech()},[transcript.text,rate]);
 useEffect(()=>{if(camera&&player.current&&stream.current){player.current.srcObject=stream.current;player.current.play().catch(()=>{})}},[camera]);
 useEffect(()=>{if(!notice)return;const timer=setTimeout(()=>setNotice(''),2500);return()=>clearTimeout(timer)},[notice]);
 function stopCamera(){stream.current?.getTracks().forEach(track=>track.stop());stream.current=null;setCamera(false)}
 function stopSpeech(){speechGeneration.current++;speechAbort.current?.abort();if(audio.current){audio.current.pause();audio.current.currentTime=0}setSpeaking(false);setSpeechBusy(false)}
 function chooseFile(next,knownDuration=0){
  if(!next)return;if(!/\.(mp4|webm)$/i.test(next.name)){setError('Choose an MP4 or WebM video.');return}if(next.size>100*1024*1024){setError('Choose a video smaller than 100 MB.');return}
  generation.current++;recognitionAbort.current?.abort();stopSpeech();stopCamera();if(player.current)player.current.srcObject=null;
  autoPlayed.current=false;setFile(next);setUrl(URL.createObjectURL(next));setDuration(knownDuration);setTime(0);setPlaying(false);setCaptions([]);setFullCaption('');setEdit(false);dispatch({type:'clear'});setError('');setAnalysis('loading');setProgress({index:0,total:1});analyze(next,generation.current);
 }
 async function analyze(next,id){
  const controller=new AbortController();recognitionAbort.current=controller;const form=new FormData();form.append('file',next);
  try{const response=await checked(await fetch(API+'/recognize-timeline',{method:'POST',body:form,signal:controller.signal}));const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
   const apply=event=>{if(id!==generation.current)return;
    if(event.type==='metadata'){setDuration(event.duration);setFullCaption(event.full_text||'');setProgress({index:0,total:event.total});setAnalysis('reading')}
    if(event.type==='progress')setProgress({index:event.index,total:event.total});
    if(event.type==='prediction'){setCaptions(previous=>[...previous,event]);setProgress({index:event.index+1,total:event.total});if(!autoPlayed.current&&player.current){autoPlayed.current=true;player.current.currentTime=0;player.current.play().catch(()=>{})}}
    if(event.type==='complete'){setAnalysis('complete');setProgress(previous=>({...previous,index:previous.total}))}
    if(event.type==='error')throw new Error(event.message);
   };
   while(true){const{value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true});let newline;while((newline=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,newline);buffer=buffer.slice(newline+1);if(line.trim())apply(JSON.parse(line))}}buffer+=decoder.decode();if(buffer.trim())apply(JSON.parse(buffer));
  }catch(e){if(e.name!=='AbortError'&&id===generation.current){setError(e.message);setAnalysis('error')}}
 }
 async function loadSentence(){if(!sentenceSample)return;setLoadingSample(true);setError('');try{const blob=await(await checked(await fetch(API+'/samples/'+encodeURIComponent(sentenceSample.id)))).blob();chooseFile(new File([blob],'sentence-sample.mp4',{type:'video/mp4'}))}catch(e){setError(e.message)}finally{setLoadingSample(false)}}
 async function openCamera(){setNotice('Webcam recording is coming soon. Upload a video for now.')}
 function record(){
  if(recording){recorder.current?.stop();return}if(!stream.current||typeof MediaRecorder==='undefined'){setError('Recording is unavailable in this browser. Upload an MP4 instead.');return}
  const mime=['video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm'].find(value=>MediaRecorder.isTypeSupported(value));chunks.current=[];recorder.current=new MediaRecorder(stream.current,mime?{mimeType:mime}:{});
  recorder.current.ondataavailable=event=>{if(event.data.size)chunks.current.push(event.data)};
  recorder.current.onstop=()=>{clearTimeout(captureTimer.current);setRecording(false);chooseFile(new File(chunks.current,'recording.webm',{type:'video/webm'}),(performance.now()-recordedAt.current)/1000)};
  recorder.current.start();recordedAt.current=performance.now();setRecording(true);captureTimer.current=setTimeout(()=>{if(recorder.current?.state==='recording')recorder.current.stop()},60000);
 }
 async function speak(){
  if(speaking){stopSpeech();return}if(!spokenText)return;const id=++speechGeneration.current,controller=new AbortController();speechAbort.current=controller;setSpeechBusy(true);
  try{const blob=await(await checked(await fetch(API+'/speech',{method:'POST',signal:controller.signal,headers:{'Content-Type':'application/json'},body:JSON.stringify({text:spokenText,rate,voice:speech?.default_voice||null})}))).blob();if(id!==speechGeneration.current)return;if(audioUrl.current)URL.revokeObjectURL(audioUrl.current);audioUrl.current=URL.createObjectURL(blob);audio.current.src=audioUrl.current;await audio.current.play();if(id===speechGeneration.current)setSpeaking(true)}catch(e){if(e.name!=='AbortError'&&id===speechGeneration.current)setError(e.message)}finally{if(id===speechGeneration.current)setSpeechBusy(false)}
 }
 function toggleVideo(){if(!player.current)return;if(player.current.paused)player.current.play().catch(()=>setError('The video could not play. Try an H.264 MP4.'));else player.current.pause()}
 const hasVideo=!!url||camera,busy=analysis==='loading'||analysis==='reading';
 return <div className={`studio ${hasVideo?'with-video':'empty-studio'}`}>
  <header className="studio-header"><a className="wordmark" href="#" onClick={event=>event.preventDefault()}><span className="brand-hand"><Hand size={20} strokeWidth={1.6}/></span>kamayan<span>.</span></a><div className="header-actions">{hasVideo&&<><button className="button secondary compact" disabled={recording} onClick={()=>input.current.click()}><Upload size={15}/> Upload new</button><button className="button secondary icon-only" aria-label="Open webcam" disabled={recording} onClick={openCamera}><Camera size={17}/></button></>}<span className="connection" role="status"><span className={ready?'connection-dot':'connection-dot waiting'}/><span>{ready?'On your device':'Service offline'}</span></span></div></header>
  {!hasVideo&&<section className="intro"><span className="intro-label">EVERY SIGN CONNECTS</span><h1>A space for your<br/><span>hands to be heard.</span></h1><p>Bring your video. We’ll take it from here.</p></section>}
  {error&&<div className="error-notice" role="alert"><span>{error}</span><button aria-label="Dismiss error" onClick={()=>setError('')}><X size={17}/></button></div>}
  <input className="file-input" ref={input} type="file" aria-label="Upload ASL video" accept=".mp4,.webm,video/mp4,video/webm" onChange={event=>{chooseFile(event.target.files?.[0]);event.target.value=''}}/>
  <section ref={stage} className={`video-canvas ${hasVideo?'video-loaded':''} ${drag?'is-dragging':''}`} aria-label="Video workspace" onDragOver={event=>{event.preventDefault();setDrag(true)}} onDragLeave={()=>setDrag(false)} onDrop={event=>{event.preventDefault();setDrag(false);if(!recording)chooseFile(event.dataTransfer.files[0])}}>
   {!hasVideo?<div className="arrival"><div className="arrival-art"><span className="orbit orbit-one"/><span className="orbit orbit-two"/><span className="arrival-hand"><Hand size={45} strokeWidth={1.25}/></span><span className="small-star"><Sparkles size={15}/></span></div><h2>Your next conversation starts here.</h2><p>Drop an ASL video into your space.</p><div className="arrival-buttons"><button className="button primary" onClick={()=>input.current.click()}><Upload size={17}/> Upload video <ArrowRight size={16}/></button><button className="button secondary webcam-placeholder" onClick={openCamera}><Camera size={17}/> Record with webcam</button></div><span className="file-types">MP4 or WebM · up to 100 MB</span></div>:<>
    <video key={camera?'camera':url} ref={player} src={camera?undefined:url} muted playsInline className={camera?'camera-mirror':''} onLoadedMetadata={()=>{const length=player.current?.duration;if(Number.isFinite(length))setDuration(length)}} onTimeUpdate={()=>{if(!camera)setTime(player.current?.currentTime||0)}} onPlay={()=>setPlaying(true)} onPause={()=>setPlaying(false)} onEnded={()=>setPlaying(false)} onError={()=>setError('This browser cannot play the video. Try an H.264 MP4 or a WebM.')}/>
    <div className="canvas-shade"/>{!camera&&currentCaption?.text_fil&&<div className="caption-card filipino-caption" lang="fil" aria-live="polite"><div className="caption-eyebrow"><span/>FILIPINO</div><p key={currentCaption.text_fil} className="caption-copy">{currentCaption.text_fil}</p><span className="caption-footnote">Static Filipino translation</span></div>}<div className="video-label"><span className={recording?'record-dot':'connection-dot'}/>{camera?(recording?'Recording':'Your camera'):'Your signing space'}</div>
    {!camera&&<div className={`caption-card ${busy&&!captions.length?'caption-loading':''}`} aria-live="polite"><div className="caption-eyebrow"><span className={busy?'caption-pulse':''}/>{transcript.text.trim()?'YOUR WORDS':uncertain?'TRANSLATION UNAVAILABLE':'ENGLISH'}</div>{captionText?<p key={captionText} className="caption-copy">{captionText}</p>:<div className="caption-placeholder">{busy?<><span/><span/><span/></>:<p>Choose the sentence sample to see its captions.</p>}</div>}<div className="caption-bottom"><button className={`caption-speech ${speaking?'active':''}`} aria-label={speaking?'Stop speech':'Play translated text'} disabled={!captionText||!speech?.available||speechBusy} onClick={speak}>{speechBusy?<LoaderCircle className="spin" size={15}/>:speaking?<Square size={13} fill="currentColor"/>:<Play size={14} fill="currentColor"/>}<span>{speechBusy?'Preparing…':speaking?'Stop':'Play translated text'}</span><span className={`tiny-wave ${speaking?'moving':''}`} aria-hidden="true">{[7,12,16,9,13].map((height,index)=><i key={index} style={{height,animationDelay:`${index*.1}s`}}/>)}</span></button><button className="caption-edit" aria-label="Edit caption transcript" onClick={()=>{if(!transcript.text&&captionText)dispatch({type:'edit',text:fullCaption||captionText});setEdit(value=>!value)}}>{edit?'Done':'Edit'}</button></div>{edit&&<div className="caption-editor"><textarea autoFocus aria-label="Editable transcript" placeholder="Edit your words…" maxLength={4000} value={transcript.text} onChange={event=>dispatch({type:'edit',text:event.target.value})}/><div><button aria-label="Undo transcript change" disabled={!transcript.past.length} onClick={()=>dispatch({type:'undo'})}><RotateCcw size={14}/></button><button aria-label="Copy transcript" onClick={async()=>{try{await navigator.clipboard.writeText(transcript.text||captionText);setNotice('Copied')}catch{setError('Select and copy the text from the editor.')}}}><Clipboard size={14}/></button><button aria-label="Download transcript" onClick={()=>save(new Blob([transcript.text||captionText],{type:'text/plain'}),'kamayan-transcript.txt')}><ArrowDownToLine size={14}/></button><select aria-label="Speech speed" value={rate} onChange={event=>setRate(Number(event.target.value))}>{[.75,1,1.25,1.5].map(value=><option key={value} value={value}>{value}× voice</option>)}</select></div></div>}<span className="caption-footnote">{busy?'Bringing your captions in…':'Exact sample reference translation'}</span></div>}
    {camera?<div className="camera-bar"><p>{recording?'Take your time. Stop when you’ve finished.':'Ready when you are.'}</p><button className="button record-button" onClick={record}>{recording?<Square size={14} fill="currentColor"/>:<span className="record-dot"/>}{recording?'Stop & process':'Start recording'}</button></div>:<div className="video-controls"><div className="playback-left"><button className="video-play" aria-label={playing?'Pause video':'Play video'} onClick={toggleVideo}>{playing?<Pause size={20} fill="currentColor"/>:<Play size={20} fill="currentColor"/>}</button><button className="replay-button" aria-label="Replay video" onClick={()=>{player.current.currentTime=0;setTime(0);player.current.play().catch(()=>{})}}><RotateCcw size={17}/></button><span>{formatTime(time)}<i>/</i>{formatTime(duration)}</span></div><input type="range" aria-label="Seek video" min="0" max={duration||1} step=".05" value={Math.min(time,duration||1)} onChange={event=>{player.current.currentTime=Number(event.target.value);setTime(Number(event.target.value))}}/><button className="fullscreen-button" aria-label="Fullscreen video workspace" onClick={()=>{if(document.fullscreenElement)document.exitFullscreen();else stage.current?.requestFullscreen?.()}}><Maximize2 size={18}/></button></div>}
    {busy&&<div className="analysis-indicator" role="status"><LoaderCircle className="spin" size={13}/><span>{captions.length?'Loading captions':'Loading captions'}</span><span className="analysis-count">{progress.index} / {progress.total}</span></div>}
   </>}
   {loadingSample&&!hasVideo&&<div className="sample-loading"><div className="loading-orb"><LoaderCircle className="spin" size={26}/></div><span>Making room for your video…</span></div>}
  </section>
  <footer className="studio-footer"><span>{hasVideo?'Your footage stays here. Always.':'A quiet space. A private conversation.'}</span>{!hasVideo&&sentenceSample&&<button className="sample-link" disabled={loadingSample} onClick={loadSentence}>Try a sentence video <ArrowRight size={14}/></button>}</footer>
  {notice&&<div className="toast" role="status"><Check size={14}/>{notice}</div>}<audio ref={audio} onEnded={()=>setSpeaking(false)} onError={()=>{setSpeaking(false);setError('Speech audio could not play.')}}/>
 </div>
}



