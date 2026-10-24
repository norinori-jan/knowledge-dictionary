import os
import threading, http.server, socketserver, functools, time
from playwright.sync_api import sync_playwright
ROOT=os.environ.get('KD_ROOT','.')
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
socketserver.TCPServer.allow_reuse_address=True
srv=socketserver.TCPServer(('127.0.0.1',8611),functools.partial(Q,directory=ROOT))
threading.Thread(target=srv.serve_forever,daemon=True).start()
ok=ng=0; errs=[]
def check(n,c,x=''):
    global ok,ng
    if c: ok+=1; print('  OK ',n)
    else: ng+=1; print('  NG ',n,x)
prm={'v':None}
def dlg(d):
    if d.type=='prompt': d.accept(prm['v'] or '')
    else: d.accept()
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2).new_page()
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',dlg)
    pg.goto('http://127.0.0.1:8611/index.html'); pg.wait_for_selector('#list')
    def E(id,term,tags,und='unknown'): return "{id:'%s',term:'%s',oneLine:'%sの説明',tags:%s,related:[],note:'',kind:'term',understanding:'%s',checkedAt:null,createdAt:n,updatedAt:n+%d}"%(id,term,term,tags,und,len(id))
    L=[E('a','JWT',"['認証','Web']",'known'),E('b','Cookie',"['認証','Web']"),E('c','OAuth',"['認証','Web','API']"),E('d','CORS',"['Web']"),E('e','香料',"['お香','配合']"),E('f','沈香',"['お香','配合']"),E('g','配合比',"['お香']"),E('h','メモ',"['認証s','単発']"),E('i','無タグ',"[]")]
    pg.evaluate("(async()=>{const n=Date.now();await writeEntries([%s]);})()"%",".join(L))
    pg.click('#btnLib'); pg.wait_for_selector('#shLib.open'); pg.wait_for_timeout(300)
    check('棚と区画の件数が出る', '棚' in pg.inner_text('#libStat') and 'タグなし 1' in pg.inner_text('#libStat'), pg.inner_text('#libStat'))
    secs=pg.evaluate("(()=>{const r=libSections(tagIndex());return r.secs.map(s=>[s.name,s.shelves.map(x=>x.label).sort()])})()")
    print('   区画:',secs)
    check('よく一緒に付くタグは同じ区画に入る', any(set(['認証','Web'])<=set(sh) for _,sh in secs) and any(set(['お香','配合'])<=set(sh) for _,sh in secs))
    check('ひとつだけの棚は別にまとまる', pg.evaluate("libSections(tagIndex()).singles.map(o=>o.label)").count('単発')==1)
    check('タグなしの項目が見える', 'タグなし' in pg.inner_text('#libBody'))
    # 棚を開く（遅延表示）
    pg.click('#libBody details.shelf[data-shelf="認証"] > summary'); pg.wait_for_timeout(400)
    inner=pg.inner_text('#libBody details.shelf[data-shelf="認証"]')
    check('棚を開くと項目が並ぶ', all(x in inner for x in ['JWT','Cookie','OAuth']) and 'CORS' not in inner, inner[:200])
    check('棚に進み具合と未理解数', '未理解 2' in pg.inner_text('#libBody details.shelf[data-shelf="認証"] > summary'))
    pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'21-lib.png'))
    # 項目を開く
    pg.click('#libBody details.shelf[data-shelf="認証"] .card[data-open="a"]'); pg.wait_for_timeout(300)
    check('棚から項目が開く', pg.locator('#shEntry.open').count()==1); pg.evaluate("closeSheet('shEntry')")
    # 並び順
    pg.click('[data-lm="cnt"]'); pg.wait_for_timeout(300)
    first=pg.evaluate("document.querySelector('#libBody details.shelf').dataset.shelf")
    check('多い順（Web=4が先）', first=='web', first)
    pg.click('[data-lm="name"]'); pg.wait_for_timeout(200); pg.click('[data-lm="sec"]'); pg.wait_for_timeout(200)
    # しぼり込み
    pg.fill('#libQ','沈香'); pg.wait_for_timeout(300)
    check('項目名でも棚をしぼれる', pg.locator('#libBody details.shelf').count()>=1 and pg.locator('#libBody details.shelf[data-shelf="web"]').count()==0)
    pg.fill('#libQ',''); pg.wait_for_timeout(300)
    # おすすめ（認証 と 認証s）
    rec=pg.inner_text('#libRec'); check('似た棚の統合をすすめる', '認証' in rec and ('似て' in rec or '同じ' in rec), rec)
    # 名前変更
    pg.click('#libBody details.shelf[data-shelf="お香"] > summary'); pg.wait_for_timeout(300)
    prm['v']='香道'; pg.click('#libBody details.shelf[data-shelf="お香"] [data-ls="ren"]'); pg.wait_for_timeout(600)
    check('棚の名前を変えると全項目に反映', pg.evaluate("entryById.get('g').tags")==['香道'] and '香道' in pg.evaluate("entryById.get('e').tags"), pg.evaluate("entryById.get('e').tags"))
    # 統合（既存の棚名に）
    pg.click('#libBody details.shelf[data-shelf="香道"] > summary'); pg.wait_for_timeout(300)
    prm['v']='配合'; pg.click('#libBody details.shelf[data-shelf="香道"] [data-ls="mer"]'); pg.wait_for_timeout(600)
    check('別の棚に統合（重複なし）', pg.evaluate("entryById.get('e').tags")==['配合'] and pg.evaluate("entryById.get('g').tags")==['配合'], pg.evaluate("entryById.get('e').tags"))
    # 棚をなくす
    pg.evaluate("document.querySelectorAll('#libBody details.cat').forEach(d=>d.open=true)"); pg.wait_for_timeout(200)
    pg.click('#libBody details.shelf[data-shelf="単発"] > summary')
    pg.wait_for_timeout(300)
    pg.click('#libBody details.shelf[data-shelf="単発"] [data-ls="del"]'); pg.wait_for_timeout(600)
    check('棚をなくす（項目は残る）', pg.evaluate("entryById.get('h').tags")==['認証s'] and pg.evaluate("!!entryById.get('h')"))
    # おすすめの統合ボタン
    pg.wait_for_timeout(300)
    pg.click('[data-lrec="0"]'); pg.wait_for_timeout(600)
    check('おすすめから統合できる', pg.evaluate("entryById.get('h').tags")==['認証'], pg.evaluate("entryById.get('h').tags"))
    # 自動タグ
    pg.evaluate("writeEntries([Object.assign({},entryById.get('i'),{note:'Cookie と JWT と Cookie と JWT の話。Cookie JWT',updatedAt:Date.now()})])"); pg.wait_for_timeout(200)
    pg.evaluate("drawLib()"); pg.click('[data-ls="autotag"]'); pg.wait_for_timeout(800)
    check('タグなしに自動でタグが付く（AIなし）', len(pg.evaluate("entryById.get('i').tags"))>=1, pg.evaluate("entryById.get('i').tags"))
    # 棚の復習（AIが必要なので、対象の絞り込みだけ確認）
    check('棚で復習対象を絞れる', set(pg.evaluate("dueList('','web').map(e=>e.term)")) <= {'Cookie','OAuth','CORS','JWT'} and 'JWT' not in pg.evaluate("dueList('','web').map(e=>e.term)"))
    # 速度
    pg.evaluate("""(()=>{const L=[];const n=Date.now();for(let i=0;i<800;i++){L.push({id:'x'+i,term:'項目'+i,oneLine:'',tags:['タグ'+(i%40),'共通'+(i%7)],related:[],note:'',kind:'term',understanding:'unknown',checkedAt:null,createdAt:n,updatedAt:n});}entries=entries.concat(L);rebuild();})()""")
    t=time.time(); pg.evaluate("drawLib()"); d=time.time()-t
    print('   800項目・50棚の書庫描画 %.2fs'%d); check('大量でも実用的', d<2.0)
    b.close()
print('結果: OK',ok,'/ NG',ng); print('JSエラー:',errs or 'なし')
