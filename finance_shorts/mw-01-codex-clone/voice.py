import pathlib,subprocess,json,time,hashlib
P=pathlib.Path(__file__).resolve().parent
DATA=json.loads((P/'script.json').read_text())
A=P/'audio';A.mkdir(exist_ok=True)
meta=P/'voice_meta.json';m=json.loads(meta.read_text()) if meta.exists() else {}
durs=[]
for i,row in enumerate(DATA):
 text=row[3];out=A/f'{i:02}.mp3';sig=hashlib.sha256(text.encode()).hexdigest()
 if not out.exists() or m.get(str(i),{}).get('sig')!=sig:
  p=A/f'raw{i:02}'
  r=subprocess.run(['python3',str(pathlib.Path.home()/'聲音素材/tts/say.py'),text,'-o',str(p)],capture_output=True,text=True)
  if r.returncode:
   print(r.stdout[-1000:],r.stderr[-1000:],flush=True);raise SystemExit(r.returncode)
  subprocess.run(['ffmpeg','-v','error','-y','-i',str(p)+'_000.wav','-ar','48000','-b:a','192k',str(out)],check=True)
  m[str(i)]={'sig':sig,'text':text};meta.write_text(json.dumps(m,ensure_ascii=False,indent=2))
 d=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(out)]))
 durs.append(d);print(f'克隆旁白 {i+1}/{len(DATA)}：{d:.1f} 秒',flush=True)
(P/'durations.json').write_text(json.dumps(durs))
print(f'完成；原速 {sum(durs):.1f} 秒',flush=True)
