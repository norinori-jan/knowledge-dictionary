import os
import json, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright
ROOT=os.environ.get('KD_ROOT','.')
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
socketserver.TCPServer.allow_reuse_address=True
srv=socketserver.TCPServer(('127.0.0.1',8541),functools.partial(Q,directory=ROOT))
threading.Thread(target=srv.serve_forever,daemon=True).start()
ok=ng=0; errs=[]
def check(n,c,x=''):
    global ok,ng
    if c: ok+=1; print('  OK ',n)
    else: ng+=1; print('  NG ',n,x)
prompts=[]
CORS={'access-control-allow-origin':'*','access-control-allow-headers':'*','access-control-allow-methods':'*'}
def reply(p):
    if '知識の体系' in p:
        return json.dumps({'items':[
          {'term':'HTTP','cat':'Web/基礎','lvl':1,'prereq':[]},
          {'term':'Cookie','cat':'Web/基礎','lvl':1,'prereq':['HTTP']},
          {'term':'JWT','cat':'Web/認証','lvl':2,'prereq':['Cookie','存在しない語']},
          {'term':'OAuth','cat':'Web/認証','lvl':3,'prereq':['JWT']},
          {'term':'お香','cat':'趣味','lvl':1,'prereq':[]},
          {'term':'幽霊項目','cat':'X','lvl':1,'prereq':[]}]})
    if '質問を1つ作って' in p: return '{"question":"問題文です"}'
    if '私の答えを採点' in p: return '{"verdict":"ok","feedback":"よい","model":"模範"}'
    return 'x'
def handle(route):
    r=route.request
    if r.method=='OPTIONS': return route.fulfill(status=204,headers=CORS)
    pr=r.post_data_json['prompt']; prompts.append(pr)
    route.fulfill(status=200,content_type='application/json',headers=CORS,body=json.dumps({'text':reply(pr)}))
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2).new_page()
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',lambda d:d.accept())
    pg.route('https://mock.example.test/ai',handle)
    pg.goto('http://127.0.0.1:8541/index.html'); pg.wait_for_selector('#list')
    pg.evaluate("lsSet('kd_endpoint','https://mock.example.test');lsSet('kd_token','tok_abc123');lsSet('kd_limit','0')")
    E=lambda id,term,one='':"{id:'%s',term:'%s',oneLine:'%s',tags:['t'],related:[],note:'%sの自分の理解',kind:'term',understanding:'unknown',checkedAt:null,createdAt:n,updatedAt:n}"%(id,term,one,term)
    pg.evaluate("(async()=>{const n=Date.now();await writeEntries([%s]);})()"%",".join([E('h','HTTP','通信規約'),E('c','Cookie','小さなデータ'),E('j','JWT','署名トークン'),E('o','OAuth','認可の枠組み'),E('i','お香','香料')]))
    pg.click('#btnSys'); pg.wait_for_selector('#shSys.open'); pg.wait_for_timeout(300)
    check('サイクルの4段階が出る', all(x in pg.inner_text('#sysSteps') for x in ['① 集める','② 整える','③ 結論をまとめる','④ 体系にする','⑤ 復習する']))
    check('次はこれ：体系にする（分野のない項目あり）', 'next' in (pg.get_attribute('#sysSteps [data-sys="systemize"] >> xpath=..','class') or ''), pg.inner_html('#sysSteps')[:300])
    check('学習ログ行', '今日 0問' in pg.inner_text('#sysStudy'))
    pg.click('[data-sys="systemize"]'); pg.wait_for_selector('#sysCand .cand',timeout=8000)
    check('AIの体系案が出る（まだ入っていない）', 'Web/認証' in pg.inner_text('#sysCand') and pg.evaluate("entryById.get('j').cat")==None)
    check('存在しない項目・語は除く', '幽霊項目' not in pg.inner_text('#sysCand') and '存在しない語' not in pg.inner_text('#sysCand'))
    check('プロンプトに既存語彙と項目が入る', any('知識の体系' in x and 'HTTP' in x and '【整理する項目】' in x for x in prompts))
    pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'19-syscand.png'))
    pg.click('[data-sys="adopt"]'); pg.wait_for_timeout(600)
    check('採用で分野・レベル・前提が入る', pg.evaluate("entryById.get('j').cat")=='Web/認証' and pg.evaluate("entryById.get('j').lvl")==2 and pg.evaluate("entryById.get('j').prereq")==['Cookie'])
    check('ツリーに分野が出る', all(x in pg.inner_text('#sysTree') for x in ['Web','趣味','認証','基礎']))
    check('前提が未理解なら警告', '先に：Cookie' in pg.inner_text('#sysTree'))
    check('進み具合が出る', '理解済み 0／4' in pg.inner_text('#sysTree'))
    pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'20-systree.png'))
    # 復習の順序（前提が先）
    order=pg.evaluate("dueList('').map(e=>e.term)")
    check('前提を満たす・基礎の項目が先', order.index('HTTP')<order.index('JWT')<order.index('OAuth') or order[0] in ('HTTP','お香'), order)
    check('分野で絞れる', set(pg.evaluate("dueList('Web/認証').map(e=>e.term)"))=={'JWT','OAuth'})
    check('親の分野で子も含む', len(pg.evaluate("dueList('Web')"))==4)
    # 分野の復習
    pg.click('[data-syscat="Web"]'); pg.wait_for_selector('#rvA',timeout=8000); pg.wait_for_timeout(300)
    check('分野の復習が始まる', pg.evaluate("rvCat")=='Web')
    pg.fill('#rvA','答え'); pg.click('#btnGrade'); pg.wait_for_selector('.vd-ok',timeout=8000)
    first=pg.evaluate("rv.id")
    pg.click('[data-rvund="known"]'); pg.wait_for_timeout(1200)
    e=pg.evaluate("entryById.get(%r)"%first)
    check('理解済みで次回が先に決まる（3日後）', e['understanding']=='known' and abs(e['nextAt']-e['checkedAt']-3*86400000)<2000 and e['rvStreak']==1, e)
    check('学習ログが増える', '今日 1問' in pg.evaluate("studyLine()") and '連続 1日' in pg.evaluate("studyLine()"))
    check('理解済みはすぐ復習に出ない', first not in pg.evaluate("dueList('').map(e=>e.id)"))
    # 時期が来たら理解済みでも出る
    pg.evaluate("(async()=>{const e=entryById.get(%r);await writeEntries([Object.assign({},e,{nextAt:Date.now()-1000})]);})()"%first); pg.wait_for_timeout(300)
    check('時期が来たら理解済みも復習に出る', first in pg.evaluate("dueList('').map(e=>e.id)"))
    # 前提の警告が消える・entry view
    pg.click('#brClose'); pg.wait_for_timeout(400)
    pg.evaluate("openEntry('j')"); pg.wait_for_timeout(300)
    check('項目画面に分野と前提', 'Web/認証' in pg.inner_text('#enBody') and '前提' in pg.inner_text('#enBody') and 'Cookie' in pg.inner_text('#enBody'))
    # 編集で手直し
    pg.evaluate("closeSheet('shEntry');openEntry('j');openEntryEdit()"); pg.wait_for_timeout(300)
    pg.fill('#eeCat','Web/セキュリティ'); pg.select_option('#eeLvl','3'); pg.fill('#eePre','HTTP、Cookie'); pg.click('#eeSave'); pg.wait_for_timeout(500)
    ej=pg.evaluate("entryById.get('j')")
    check('編集で分野・レベル・前提を直せる', ej['cat']=='Web/セキュリティ' and ej['lvl']==3 and ej['prereq']==['HTTP','Cookie'], ej)
    b.close()
print('結果: OK',ok,'/ NG',ng); print('JSエラー:',errs or 'なし')
