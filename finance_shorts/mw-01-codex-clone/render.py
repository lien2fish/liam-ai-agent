import json,pathlib,shutil,subprocess,html,re
P=pathlib.Path(__file__).resolve().parent; R=P.parent; REPO=R.parent
rows=json.loads((P/'script.json').read_text()); durations=json.loads((P/'durations.json').read_text())
E=lambda s:html.escape(s).replace('\n','<br>')
css='''@font-face{font-family:PingFang;src:local("PingFang TC")}*{box-sizing:border-box;margin:0}body,#root{width:1920px;height:1080px;overflow:hidden;background:#101923;color:#eff3f5;font-family:PingFang,sans-serif} .clip{position:absolute;inset:0}.scene{position:absolute;inset:0;padding:154px 110px 180px}.eyebrow{color:#8ed9c7;font-size:35px;letter-spacing:5px;margin-bottom:24px}.headline{font-size:90px;line-height:1.3;font-weight:800;max-width:1630px}.note{position:absolute;top:790px;font-size:32px;color:#b8c8d1}.top{position:absolute;top:50px;left:110px;font-size:28px;letter-spacing:3px;color:#8ed9c7}.date{position:absolute;right:110px;top:55px;color:#b8c8d1;font-size:24px}.subtitle{position:absolute;bottom:80px;left:150px;width:1620px;text-align:center;font-size:43px;line-height:1.5;background:#101923e8;padding:12px 30px;border-radius:16px}.cards{position:absolute;left:110px;top:500px;display:flex;gap:28px;width:1700px}.card{flex:1;background:#1c2b3b;border:2px solid #3b5364;border-radius:24px;padding:26px;font-size:49px;color:#eff3f5;min-height:170px;display:flex;align-items:center;justify-content:center;text-align:center}.accent{color:#f1c778}.arrow{font-size:70px;color:#8ed9c7;display:flex;align-items:center}.source{position:absolute;bottom:25px;left:110px;color:#8da3b2;font-size:21px}.page{position:absolute;right:110px;bottom:27px;color:#8da3b2;font-size:23px}.track{position:absolute;bottom:0;height:7px;background:#8ed9c7;width:1920px;transform-origin:left}.big{font-size:92px;color:#f1c778}.small{font-size:31px;color:#b8c8d1}'''
blocks=[]; js=[];audio=[]; t=.3
sources={2:'聯準會 2026-09-16；台灣央行 2026-09-17',3:'聯準會：利率與貨幣政策說明',4:'台灣央行 2026-09-17',6:'CFPB：固定與機動利率；台灣央行：指數型房貸',7:'台灣央行：政策傳遞與指數型房貸',8:'假設試算：非銀行報價',9:'本息平均攤還公式；四捨五入至元',10:'假設試算：利率情境比較',11:'請以承貸銀行合約為準',12:'一般利息與實質購買力概念',13:'請以存款合約為準',14:'一般外幣存款與匯率風險說明',15:'台灣央行：外匯市場供需及匯率說明',16:'一般外幣用途與換匯成本說明',17:'美國 SEC：利率風險投資人教育',18:'美國 SEC：債券與利率風險'}
for i,(row,d) in enumerate(zip(rows,durations)):
 ey,h,n,txt,kind=row; start=t; end=t+d+.22; sid=f's{i}'
 body=f'<div class="scene" id="{sid}-inner"><div class="eyebrow">{E(ey)}</div><div class="headline">{E(h)}</div>'
 if kind=='numbers':
  items=['2.0%<br><span class="big">36,962</span><br><span class="small">元／月</span>','2.5%<br><span class="big">39,512</span><br><span class="small">元／月</span>']
 elif kind=='calc':items=['1,000 萬元','30 年','本息平均攤還'] if i==8 else ['每月 +2,550 元','預算還有餘裕嗎？']
 elif kind=='compare':
  items= h.split('｜') if '｜' in h else (['固定利率','機動利率'] if i==6 else ['合約與條件','個人的支出與風險'])
 elif kind=='tri':items= {'房貸｜存款｜美元':['房貸','存款','美元']}.get(h,h.split('｜') if '｜' in h else (h.split(' × ') if ' × ' in h else ['查條件','看用途','算影響']))
 elif kind=='flow':items=h.split(' → ') if ' → ' in h else ['國際事件','市場與銀行','你的合約']
 elif kind=='intro':items=['升息新聞','你的房貸','你的生活']
 else:items=['看懂事件','拆解影響','再做判斷']
 overrides={1:['不自動連動','先看貸款條件'],3:['資金價格提高','借貸與支出調整','物價壓力減輕'],4:['通膨','經濟成長','金融情勢'],6:['固定利率','機動利率'],7:['市場資金成本','銀行定價','合約約定'],11:['計息指標','下次調整日','月付金'],12:['利息收入','物價變動','實際購買力'],13:['固定利率定存','提前解約條件','續存新條件'],14:['美元收到的利息','換回台幣的結果'],15:['兩地利差','資金流向','市場預期'],16:['收入幣別','支出幣別','換匯成本'],17:['市場利率上升','既有固定利率債券價格承壓'],18:['領到的配息','持有期間價格變化'],19:['誰做決定？','調哪種利率？','何時生效？'],20:['房貸：看合約','存款：看條件','外幣：看用途']}
 items=overrides.get(i,items)
 body+='<div class="cards">'
 for j,item in enumerate(items):
  if j and kind=='flow':body+='<div class="arrow">→</div>'
  body+=f'<div class="card" id="{sid}-c{j}"><div>{item}</div></div>'
  js.append(f'tl.fromTo("#{sid}-c{j}",{{opacity:0,y:35}},{{opacity:1,y:0,duration:.45}},{start+.5+j*.28:.3f});')
 body+=f'</div><div class="note">{E(n)}</div></div>'
 blocks.append(f'<section id="{sid}" class="clip" data-start="{start:.3f}" data-duration="{end-start:.3f}" data-track-index="{i+1}">{body}</section>')
 js.append(f'tl.fromTo("#{sid}-inner",{{opacity:0,x:45}},{{opacity:1,x:0,duration:.35}},{start:.3f});')
 # Split subtitles into natural phrases, each phrase occupies proportional speaking time.
 parts=[x for x in re.split('(?<=[，。？！；])',txt) if x.strip()]; totalchars=sum(len(x) for x in parts); elapsed=0
 for j,part in enumerate(parts):
  seg=d*len(part)/totalchars
  blocks.append(f'<div id="sub-{i}-{j}" class="clip" data-start="{start+elapsed:.3f}" data-duration="{seg:.3f}" data-track-index="{len(rows)+2}"><div class="subtitle">{E(part)}</div></div>');elapsed+=seg
 blocks.append(f'<div id="footer-{i}" class="clip" data-start="{start:.3f}" data-duration="{end-start:.3f}" data-track-index="{len(rows)+3}"><div class="source">{E(sources.get(i,"錢的大小事｜一般知識解說"))}</div><div class="page">{i+1:02} / {len(rows):02}</div></div>')
 audio.append(f'<audio id="voice-{i}" src="audio/{i:02}.mp3" data-start="{start:.3f}" data-duration="{d:.3f}"></audio>')
 t=end
T=round(t+.7,3)
js.append(f'tl.fromTo(".track",{{scaleX:0}},{{scaleX:1,duration:{T},ease:"none"}},0);')
page=f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=1920,height=1080"><title>美國升息，你的房貸就會漲？</title><style>{css}</style><script src="vendor/gsap.min.js"></script></head><body><div id="root" data-composition-id="moneycodex" data-start="0" data-duration="{T}" data-width="1920" data-height="1080" data-fps="24"><div id="bg" class="clip" data-start="0" data-duration="{T}" data-track-index="0" style="background:radial-gradient(at 80% 20%,#203c47,#101923 70%)"></div>{''.join(blocks)}<div id="chrome" class="clip" data-start="0" data-duration="{T}" data-track-index="{len(rows)+4}"><div class="top">錢的大小事</div><div class="date">資料截至 2026.10.19</div><div class="track"></div></div>{''.join(audio)}</div><script>window.__timelines=window.__timelines||{{}};const tl=gsap.timeline({{paused:true}});{''.join(js)}window.__timelines.moneycodex=tl;</script></body></html>'''
(P/'index.html').write_text(page)
(P/'vendor').mkdir(exist_ok=True);shutil.copy(REPO/'hyperframes_trial/vendor/gsap.min.js',P/'vendor/gsap.min.js')
shutil.copy(REPO/'hyperframes_trial/coldchain-03/hyperframes.json',P/'hyperframes.json')
(P/'meta.json').write_text(json.dumps({'id':P.name,'name':'美國升息，你的房貸就會漲？'},ensure_ascii=False))
print(f'總長 {T:.1f} 秒，{len(rows)} 場',flush=True)
subprocess.run(['npx','--yes','hyperframes@0.8.30','render'],cwd=P,check=True)
f=max((P/'renders').glob('*.mp4'),key=lambda p:p.stat().st_mtime)
out=R/'試做成品'/'mw-01-codex_中文克隆聲音版_美國升息你的房貸就會漲.mp4';subprocess.run(['ffmpeg','-v','error','-y','-i',str(f),'-filter_complex','[0:v]setpts=PTS/1.3[v];[0:a]atempo=1.3[a]','-map','[v]','-map','[a]','-r','24','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',str(out)],check=True);print('成品',out,flush=True)
