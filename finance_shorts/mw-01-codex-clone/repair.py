import pathlib,json,subprocess,sys,shutil,time,re
P=pathlib.Path(__file__).resolve().parent
rows=json.loads((P/'script.json').read_text());A=P/'audio'
overrides={'房貸':'房代','資金':'資今','貸款':'代款','攤還':'灘環','計息':'計希','授信':'授信','新聞':'新文','借錢':'借前','壓力':'壓立','按鈕':'按扭','續存':'序存','資料':'姿料','餘額':'魚額','確認':'確任','哪裡':'哪理'}
B=P/'備份'/time.strftime('配音修正前_%Y%m%d_%H%M%S');B.mkdir(parents=True,exist_ok=True)
for idx in map(int,sys.argv[1:]):
 text=rows[idx][3]
 for old,new in overrides.items():text=text.replace(old,new)
 out=A/f'{idx:02}.mp3'
 if out.exists():shutil.copy(out,B/out.name)
 pref=A/f'repair{idx:02}'
 r=subprocess.run(['python3',str(pathlib.Path.home()/'聲音素材/tts/say.py'),text,'-o',str(pref)],capture_output=True,text=True)
 if r.returncode:print(r.stderr[-500:]);raise SystemExit(r.returncode)
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(pref)+'_000.wav','-ar','48000','-b:a','192k',str(out)],check=True)
 print(f'已修正 {idx:02}（只替換發音用字）',flush=True)
# 更新時間軸，字幕仍由原稿產生。
if all((A/f'{i:02}.mp3').exists() for i in range(len(rows))):
 d=[float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(A/f'{i:02}.mp3')])) for i in range(len(rows))]
 (P/'durations.json').write_text(json.dumps(d))
