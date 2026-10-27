import json,pathlib,subprocess,difflib,sys,re
import time
import mlx_whisper
from pypinyin import lazy_pinyin
P=pathlib.Path(__file__).resolve().parent
rows=json.loads((P/'script.json').read_text())
model=sys.argv[1] if len(sys.argv)>1 else 'medium'
wanted=[int(x) for x in sys.argv[2:]] or list(range(len(rows)))
report=P/f'listen_{model}.json';old=json.loads(report.read_text()) if report.exists() else {}
def clean(s):return re.sub(r'[^\w\u4e00-\u9fff]','',s).lower()
def py(s):return ''.join(lazy_pinyin(s))
for i in wanted:
 f=P/'audio'/f'{i:02}.mp3'
 while not f.exists():time.sleep(2)
 sig=str(f.stat().st_mtime_ns)
 if old.get(str(i),{}).get('sig')==sig:continue
 out=P/'audio'/f'{i:02}_13.mp3'
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(f),'-af','atempo=1.3',str(out)],check=True)
 r=mlx_whisper.transcribe(str(out),path_or_hf_repo=f'mlx-community/whisper-{model}-mlx',language='zh',condition_on_previous_text=False,initial_prompt='以下是繁體中文的財經解說錄音。')
 heard=r['text'];ref=rows[i][3];a,b=clean(ref),clean(heard);diff=[]
 for tag,x,y,u,v in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
  if tag=='equal':continue
  xtext,ytext=a[x:y],b[u:v]
  if py(xtext)==py(ytext):continue
  if not any('\u4e00'<=c<='\u9fff' for c in xtext+ytext):continue
  if re.fullmatch(r'[零一二三四五六七八九十百千萬兩點百分之\d]+',xtext+ytext):continue
  ratio=difflib.SequenceMatcher(None,py(xtext),py(ytext)).ratio()
  if ratio>=.78:continue
  diff.append({'ref':xtext,'heard':ytext,'context':a[max(0,x-5):y+5]})
 old[str(i)]={'sig':sig,'ref':ref,'heard':heard,'differences':diff}
 report.write_text(json.dumps(old,ensure_ascii=False,indent=2))
 print(f'{i:02} '+json.dumps(diff,ensure_ascii=False),flush=True)
