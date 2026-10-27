"""60 秒房貸解說的圖片動畫版；沿用原版已核准的克隆音軌。"""
import html,json,pathlib,shutil,subprocess,math,re
P=pathlib.Path(__file__).resolve().parent; R=P.parent; REPO=R.parent
rows=json.loads((P/'script.json').read_text());durations=json.loads((P/'durations.json').read_text())
E=lambda s:html.escape(s).replace('\n','<br>')
CSS='''@font-face{font-family:PingFang;src:local("PingFang TC")}*{box-sizing:border-box;margin:0}body,#root{width:1920px;height:1080px;overflow:hidden;background:#101923;color:#eff3f5;font-family:PingFang,sans-serif}.clip,.inside{position:absolute;inset:0}.brand{position:absolute;top:49px;left:96px;font-size:27px;letter-spacing:2px;color:#8ed9c7}.date{position:absolute;right:96px;top:54px;color:#b5c6ce;font-size:24px}.eyebrow{position:absolute;left:96px;top:146px;font-size:33px;color:#8ed9c7;letter-spacing:3px}.h{position:absolute;left:96px;top:214px;font-size:91px;font-weight:800;line-height:1.28;max-width:1720px}.art{position:absolute;object-fit:contain;filter:drop-shadow(0px 24px 28px #0005)}.halo{position:absolute;border-radius:50%;background:radial-gradient(circle,#5ec5aa24,transparent 68%)}.panel{position:absolute;background:linear-gradient(145deg,#223745dd,#192b36ee);border:2px solid #52738188;border-radius:26px}.label{position:absolute;color:#eff3f5;text-align:center;font-weight:600;line-height:1.4}.muted{color:#bdccd3}.gold{color:#f1c778}.mint{color:#8ed9c7}.subtitle{position:absolute;bottom:80px;left:150px;width:1620px;text-align:center;font-size:43px;line-height:1.4;background:#101923ec;padding:12px 28px;border-radius:16px}.source{position:absolute;bottom:27px;left:96px;font-size:21px;color:#98acb8}.page{position:absolute;bottom:27px;right:96px;font-size:24px;color:#a9bac6}.progress{position:absolute;bottom:0;left:0;height:7px;width:1920px;transform-origin:left;background:#8ed9c7}.dot{position:absolute;border-radius:50%;width:14px;height:14px;background:#f1c778;box-shadow:0 0 15px #f1c77888}.badge{position:absolute;border-radius:999px;border:2px solid #f1c77888;background:#253541;color:#f1c778;text-align:center}.bartrack{position:absolute;height:12px;background:#0b151d;border-radius:8px;overflow:hidden}.barfill{height:100%;border-radius:8px;transform-origin:left}.check{position:absolute;width:58px;height:58px;color:#8ed9c7}.baseline{position:absolute;border:2px solid #446372;border-radius:50%;height:110px;opacity:.45}'''
blocks=[];js=[];aud=[];t=.3
SRC=['房貸與利率概念解說','CFPB 固定／機動利率；央行指數型房貸','央行政策傳遞與指數型房貸','假設試算，非銀行報價','本息平均攤還公式，四捨五入至元','請以承貸銀行合約條件為準','圖片為生成示意｜原旁白與片長保留']
def text(id,s,x,y,w,size=48,color='',align='left',weight=600):
 return f'<div id="{id}" class="label {color}" style="left:{x}px;top:{y}px;width:{w}px;font-size:{size}px;text-align:{align};font-weight:{weight}">{E(s)}</div>'
def panel(id,x,y,w,h):return f'<div id="{id}" class="panel" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px"></div>'
def enter(id,at,dx=0,dy=30,scale=1):
 js.append(f'tl.fromTo("#{id}",{{autoAlpha:0,x:{dx},y:{dy},scale:{scale}}},{{autoAlpha:1,x:0,y:0,scale:1,duration:.5,ease:"power3.out"}},{at:.3f});')
def art(id,name,x,y,w,h,at,bob=True):
 enter(id,at,dy=38,scale=.91)
 if bob:js.append(f'tl.to("#{id}-float",{{y:-12,duration:2.2,ease:"sine.inOut",repeat:40,yoyo:true}},{at+.5:.3f});')
 return f'<div id="{id}" style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px"><img id="{id}-float" class="art" src="assets/{name}.png" style="inset:0;width:100%;height:100%" alt="" /></div>'
def arrow(id,x,y,at):
 js.append(f'tl.fromTo("#{id}-path",{{strokeDashoffset:180}},{{strokeDashoffset:0,duration:.65,ease:"power2.out"}},{at:.3f});')
 js.append(f'tl.fromTo("#{id}-head",{{autoAlpha:0}},{{autoAlpha:1,duration:.2}},{at+.5:.3f});')
 js.append(f'tl.fromTo("#{id}-dot",{{x:0,autoAlpha:0}},{{x:130,autoAlpha:1,duration:1.0,ease:"none",repeat:18,repeatDelay:.55}},{at+.8:.3f});')
 return (f'<svg style="position:absolute;left:{x}px;top:{y}px;width:155px;height:70px;color:#8ed9c7" viewBox="0 0 155 70"><path id="{id}-path" d="M6 35 H135" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" style="stroke-dasharray:180"/><path id="{id}-head" d="M116 17 L138 35 L116 53" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/></svg><div id="{id}-dot" class="dot" style="left:{x+6}px;top:{y+28}px"></div>')
for i,(r,d) in enumerate(zip(rows,durations)):
 start=t;end=start+d+.22;sid=f's{i}';b=[]
 enter(sid+'-head',start,dy=18)
 if i==0:
  b += [f'<div class="halo" style="left:1040px;top:150px;width:800px;height:700px"></div>',text(sid+'-ey','1 分鐘帶你看世界金融大小事',96,146,1100,33,'mint'),text(sid+'-head','美國升息\n房貸就會跟著漲？',96,225,1100,102,weight=800)]
  b.append(art(sid+'-house','house',1210,180,575,650,start+.25))
  b += [panel(sid+'-p',96,575,980,124),text(sid+'-a','政策利率 ≠ 你的房貸利率',126,602,920,54,'gold'),text(sid+'-b','先看自己的貸款合約',96,755,1000,39,'muted')]
  enter(sid+'-p',start+.65);enter(sid+'-a',start+.8);enter(sid+'-b',start+1.0)
  b.append(f'<div id="{sid}-q" class="badge" style="left:1160px;top:200px;width:118px;height:118px;font-size:82px;line-height:115px">?</div>');enter(sid+'-q',start+.5,dy=15,scale=.75)
 elif i==1:
  b += [text(sid+'-ey','房貸：先打開合約',96,146,1100,33,'mint'),text(sid+'-head','先看：固定還是機動？',96,220,1130,86,weight=800)]
  b.append(art(sid+'-contract','contract',1230,215,540,610,start+.2))
  for j,(title,desc) in enumerate([('固定利率','約定期間依合約'),('機動利率','指標＋加碼＋調整日')]):
   x=96+j*510;bid=f'{sid}-c{j}'
   b += [panel(bid,x,450,476,250),text(bid+'-title',title,x+22,490,432,60,'mint' if j==0 else 'gold',align='center',weight=800),text(bid+'-sub',desc,x+18,600,440,35,'muted',align='center')]
   enter(bid,start+.5+j*.65);enter(bid+'-title',start+.65+j*.65);enter(bid+'-sub',start+.8+j*.65)
  b.append(text(sid+'-b','先看計息方式，再看利率新聞',96,760,1100,37,'muted'));enter(sid+'-b',start+1.5)
 elif i==2:
  b += [text(sid+'-ey','影響怎麼傳到你的帳單？',96,146,1600,33,'mint'),text(sid+'-head','政策利率，不是每筆房貸利率',96,219,1750,87,weight=800)]
  for j,(name,x,label) in enumerate([('bank',110,'銀行資金成本'),('contract',740,'銀行定價與條件'),('house',1370,'你的房貸合約')]):
   b.append(art(f'{sid}-art{j}',name,x,345,420,340,start+.3+j*.6))
   b += [panel(f'{sid}-lab{j}',x-25,712,470,85),text(f'{sid}-txt{j}',label,x-10,729,440,42,align='center')]
   enter(f'{sid}-lab{j}',start+.6+j*.6);enter(f'{sid}-txt{j}',start+.75+j*.6)
  b.append(arrow(sid+'-a1',555,490,start+1.2));b.append(arrow(sid+'-a2',1180,490,start+2.0))
 elif i==3:
  b += [text(sid+'-ey','以下是假設試算，非銀行報價',96,146,1200,33,'mint'),text(sid+'-head','把利率，換成月付金',96,220,1200,94,weight=800)]
  b.append(art(sid+'-house','house',1250,205,515,630,start+.25))
  b += [panel(sid+'-p',96,425,1040,280),text(sid+'-money','1,000 萬元',130,455,965,118,'gold',weight=800),text(sid+'-term','貸款本金',138,615,330,37,'muted'),text(sid+'-years','30 年',700,606,360,56,'mint',align='right',weight=800),text(sid+'-b','本息平均攤還｜本金加利息，每月同額',96,756,1120,37,'muted')]
  for j,key in enumerate(['p','money','term','years','b']):enter(sid+'-'+key,start+.3+j*.3)
 elif i==4:
  b += [text(sid+'-ey','假設試算｜本息平均攤還',96,146,1400,33,'mint'),text(sid+'-head','同一筆房貸，月付金差多少？',96,215,1720,88,weight=800)]
  b.append(art(sid+'-house','house',1505,355,300,330,start+.3,bob=False))
  for j,(rate,value,x,color) in enumerate([('2.0%',36962,96,'mint'),('2.5%',39512,798,'gold')]):
   bid=f'{sid}-c{j}';b+=[panel(bid,x,412,630,288),text(bid+'-rate',rate,x+28,432,574,53,color),f'<div id="{bid}-num" class="label {color}" style="left:{x+28}px;top:505px;width:574px;font-size:107px;font-weight:800;text-align:center">{value:,}</div>',text(bid+'-unit','元／月',x+28,630,574,30,'muted',align='center')]
   ratio=value/39512
   b.append(f'<div class="bartrack" style="left:{x+35}px;top:675px;width:560px"><div id="{bid}-bar" class="barfill" style="background:{"#8ed9c7" if j==0 else "#f1c778"};width:{ratio*100:.4f}%"></div></div>')
   enter(bid,start+.2+j*.5);enter(bid+'-rate',start+.35+j*.5);enter(bid+'-unit',start+.4+j*.5)
   js.append(f'tl.fromTo("#{bid}-bar",{{scaleX:0}},{{scaleX:1,duration:1.2,ease:"power2.out"}},{start+.5+j*.5:.3f});')
   js.append(f'const counter{i}_{j}={{v:0}};tl.fromTo(counter{i}_{j},{{v:0}},{{v:{value},duration:1.4,ease:"power2.out",onUpdate:()=>{{document.getElementById("{bid}-num").textContent=Math.round(counter{i}_{j}.v).toLocaleString("en-US");}}}},{start+.5+j*.5:.3f});')
  b += [panel(sid+'-delta',96,742,1332,83),text(sid+'-delta-text','每月多約 2,550 元',120,751,1284,53,'gold',align='center',weight=800),text(sid+'-note','本金 1,000 萬\n30 年｜不含費用',1480,734,350,30,'muted',align='center')]
  enter(sid+'-delta',start+1.8);enter(sid+'-delta-text',start+2.0);enter(sid+'-note',start+.9)
 elif i==5:
  b += [text(sid+'-ey','有房貸的人，先查這些',96,146,1300,33,'mint'),text(sid+'-head','查清楚合約裡的三件事',96,220,1250,89,weight=800)]
  b.append(art(sid+'-contract','contract',1245,225,530,580,start+.3))
  for j,(title,desc) in enumerate([('計息指標','利率怎麼算？'),('調整日期','什麼時候調整？'),('月付金','每月預算夠嗎？')]):
   y=408+j*132;bid=f'{sid}-row{j}';b += [panel(bid,96,y,1045,108),text(bid+'-head',title,210,y+21,360,49,weight=800),text(bid+'-sub',desc,610,y+33,480,34,'muted')]
   b.append(f'<svg class="check" style="left:128px;top:{y+27}px" viewBox="0 0 60 60"><circle cx="30" cy="30" r="26" fill="#8ed9c719" stroke="#8ed9c755" stroke-width="2"/><path id="{bid}-tick" d="M17 30 L26 39 L43 21" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" style="stroke-dasharray:50"/></svg>')
   enter(bid,start+.2+j*.55,dx=-35,dy=0);enter(bid+'-head',start+.35+j*.55);enter(bid+'-sub',start+.45+j*.55)
   js.append(f'tl.fromTo("#{bid}-tick",{{strokeDashoffset:50}},{{strokeDashoffset:0,duration:.45}},{start+.6+j*.55:.3f});')
 else:
  b += [text(sid+'-ey','先看合約，再看新聞',96,160,1728,34,'mint',align='center'),text(sid+'-head','1 分鐘帶你看世界金融大小事',96,260,1728,92,align='center',weight=800),text(sid+'-sub','每支一分鐘，只講清楚一件事',96,410,1728,47,'gold',align='center')]
  for j,(name,x) in enumerate([('bank',525),('contract',830),('house',1135)]):b.append(art(f'{sid}-mini{j}',name,x,510,255,280,start+.2+j*.15,bob=False))
  enter(sid+'-ey',start);enter(sid+'-sub',start+.2)
 blocks.append(f'<section id="{sid}" class="clip" data-start="{start:.3f}" data-duration="{end-start:.3f}" data-track-index="{i+1}"><div id="{sid}-in" class="inside">'+''.join(b)+'</div></section>')
 js.append(f'tl.fromTo("#{sid}-in",{{autoAlpha:0}},{{autoAlpha:1,duration:.18}},{start:.3f});')
 parts=[x for x in re.split('(?<=[，。？！；])',r[3]) if x.strip()];chars=sum(len(x) for x in parts);elapsed=0
 for j,part in enumerate(parts):
  seg=d*len(part)/chars;blocks.append(f'<div id="sub-{i}-{j}" class="clip" data-start="{start+elapsed:.3f}" data-duration="{seg:.3f}" data-track-index="{len(rows)+2}"><div class="subtitle">{E(part)}</div></div>');elapsed+=seg
 blocks.append(f'<div id="foot-{i}" class="clip" data-start="{start:.3f}" data-duration="{end-start:.3f}" data-track-index="{len(rows)+3}"><div class="source">{E(SRC[i])}</div><div class="page">{i+1:02} / {len(rows):02}</div></div>')
 aud.append(f'<audio id="voice-{i}" src="audio/{i:02}.mp3" data-start="{start:.3f}" data-duration="{d:.3f}"></audio>');t=end
T=round(t+.7,3)
js.append(f'tl.fromTo(".progress",{{scaleX:0}},{{scaleX:1,duration:{T},ease:"none"}},0);')
page=f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=1920,height=1080"><title>美國升息，台灣房貸就會漲？｜圖片動畫版</title><style>{CSS}</style><script src="vendor/gsap.min.js"></script></head><body><div id="root" data-composition-id="moneyrich" data-start="0" data-duration="{T}" data-width="1920" data-height="1080" data-fps="24"><div id="bg" class="clip" data-start="0" data-duration="{T}" data-track-index="0" style="background:radial-gradient(at 85% 25%,#23454d,#101923 64%)"></div>{''.join(blocks)}<div id="chrome" class="clip" data-start="0" data-duration="{T}" data-track-index="{len(rows)+4}"><div class="brand">1 分鐘帶你看世界金融大小事</div><div class="date">資料截至 2026.10.19</div><div class="progress"></div></div>{''.join(aud)}</div><script>window.__timelines=window.__timelines||{{}};const tl=gsap.timeline({{paused:true}});{''.join(js)}window.__timelines.moneyrich=tl;</script></body></html>'''
(P/'index.html').write_text(page);(P/'vendor').mkdir(exist_ok=True);shutil.copy(REPO/'hyperframes_trial/vendor/gsap.min.js',P/'vendor/gsap.min.js');shutil.copy(REPO/'hyperframes_trial/coldchain-03/hyperframes.json',P/'hyperframes.json');(P/'meta.json').write_text(json.dumps({'id':P.name,'name':'美國升息，台灣房貸就會漲？｜圖片動畫版'},ensure_ascii=False))
print(f'時間軸 {T:.2f} 秒，輸出 60 秒；房屋、銀行、合約三張圖片動畫。',flush=True)
if '--build-only' not in __import__('sys').argv:
 subprocess.run(['npx','--yes','hyperframes@0.8.30','render'],cwd=P,check=True)
 f=max((P/'renders').glob('*.mp4'),key=lambda x:x.stat().st_mtime);out=R/'試做成品'/'mw-01-minute_圖片動畫版_60秒_美國升息台灣房貸就會漲.mp4'
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(f),'-filter_complex','[0:v]setpts=PTS/1.3[v];[0:a]atempo=1.3[a]','-map','[v]','-map','[a]','-r','24','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-t','60','-movflags','+faststart',str(out)],check=True);print('成品',out,flush=True)
