import os
import json, threading, http.server, socketserver, functools
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
prompts=[]
CORS={'access-control-allow-origin':'*','access-control-allow-headers':'*','access-control-allow-methods':'*'}
def reply(p):
    items=[]
    for t in ['JWT','Cookie','CORS','Session']:
        if '■'+t in p: items.append({'term':t,'question':t+'を何のために調べたか','conclusion':t+'は〇〇と結論した','steps':['最初に概要を調べた','次に実装を比べた','最後に採用を決めた'],'open':['期限切れの扱い'],'plain':t+'は、身分証のようなものです。'})
    return json.dumps({'items':items})
def handle(route):
    r=route.request
    if r.method=='OPTIONS': return route.fulfill(status=204,headers=CORS)
    pr=r.post_data_json['prompt']; prompts.append(pr)
    route.fulfill(status=200,content_type='application/json',headers=CORS,body=json.dumps({'text':reply(pr)}))
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2).new_page()
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',lambda d:d.accept())
    pg.route('https://mock.example.test/ai',handle)
    pg.goto('http://127.0.0.1:8611/index.html'); pg.wait_for_selector('#list')
    pg.evaluate("lsSet('kd_endpoint','https://mock.example.test');lsSet('kd_token','tok_abc123');lsSet('kd_limit','0')")
    E=lambda id,term,extra='':"{id:'%s',term:'%s',oneLine:'',tags:['認証'],related:[],note:'',kind:'term',understanding:'unknown',checkedAt:null,createdAt:n,updatedAt:n%s}"%(id,term,extra)
    pg.evaluate("(async()=>{const n=Date.now();await writeEntries([%s]);})()"%",".join([E('a','JWT'),E('b','Cookie'),E('c','CORS'),E('d','Session'),E('e','空の項目')]))
    pg.evaluate("""(async()=>{const d=86400000,n=Date.now();await writeQAs([
      {id:'q1',entryId:'a',question:'JWTとは何ですか？\\n詳しく',answer:'JWTは署名つきトークンです。サーバーに状態を持たせずに認証できます。つまり、セッションを持たない認証方式として使えるということです。',judgment:'',sourceType:'gemini',sourceUrl:'',createdAt:n-5*d,updatedAt:n-5*d},
      {id:'q2',entryId:'a',question:'JWTの保存先はどこがいい？',answer:'Cookieに入れるのが無難です。',judgment:'httpOnlyのCookieに入れる。localStorageは使わない。',sourceType:'gemini',sourceUrl:'',createdAt:n-2*d,updatedAt:n-2*d},
      {id:'q3',entryId:'b',question:'Cookieの属性は？',answer:'### 属性\\n\\n**Secure** と HttpOnly を付けます。SameSiteも大事です。',judgment:'',sourceType:'gemini',sourceUrl:'',createdAt:n-1*d,updatedAt:n-1*d},
      {id:'q4',entryId:'c',question:'CORSとは？',answer:'ブラウザが別のオリジンへのアクセスを制限する仕組みです。',judgment:'',sourceType:'gemini',sourceUrl:'',createdAt:n,updatedAt:n},
      {id:'q5',entryId:'d',question:'Sessionとは？',answer:'サーバー側で状態を持つ方式です。',judgment:'',sourceType:'gemini',sourceUrl:'',createdAt:n,updatedAt:n}]);})()""")
    pg.evaluate("renderList()"); pg.wait_for_timeout(300)
    txt=pg.inner_text('#list')
    check('一覧に「何を調べたか（問い）」が出る', '❓ JWTとは何ですか？' in txt, txt[:300])
    check('自分の判断があれば結論はそれ（出所つき）', '🎯 httpOnlyのCookieに入れる' in txt and '自分の判断' in txt)
    check('判断がなければ回答から結論を自動抜粋', '🎯' in txt and 'Secure と HttpOnly' in txt.replace('\n',' ') and '自動抜粋' in txt, txt)
    check('Markdown記号が結論に出ない', '###' not in txt and '**' not in txt)
    check('空の項目は結論なしでも壊れない', '空の項目' in txt)
    pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'22-list-card.png'))
    # 結論一覧モード
    pg.click('#vchips [data-v="concl"]'); pg.wait_for_timeout(300)
    check('結論一覧に切り替わる', pg.locator('#list .crow').count()==5 and '🎯' in pg.inner_text('#list'))
    pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'23-list-concl.png'))
    check('表示形式を覚える', pg.evaluate("lsGet('kd_view')")=='concl')
    pg.click('#vchips [data-v="card"]'); pg.wait_for_timeout(200)
    # 項目画面
    pg.evaluate("openEntry('a')"); pg.wait_for_timeout(300)
    en=pg.inner_text('#enBody')
    check('項目画面に「何を調べていたか」', '何を調べていたか' in en and 'JWTとは何ですか？' in en)
    check('項目画面に結論', '結論' in en and 'httpOnlyのCookie' in en)
    check('経過が古い順に並ぶ', '経過' in en and en.index('JWTとは何ですか')<en.index('JWTの保存先'), en)
    check('経過に各回の要点', '判断：httpOnly' in en)
    pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'24-digest.png'))
    # AIでまとめる（1件）
    pg.click('[data-dg="ai"]'); pg.wait_for_timeout(1200)
    en=pg.inner_text('#enBody')
    check('AIのまとめが入る（問い・結論・経過・未解決・やさしい説明）', 'JWTを何のために調べたか' in en and 'JWTは〇〇と結論した' in en and '最後に採用を決めた' in en and '期限切れの扱い' in en and '身分証のようなもの' in en, en[:300])
    check('材料に自分の判断が渡る', any('httpOnlyのCookieに入れる' in x for x in prompts))
    # 自分の理解に入れる
    pg.click('[data-dg="tonote"]'); pg.wait_for_timeout(600)
    check('やさしい説明を自分の理解に入れられる', '身分証' in pg.evaluate("entryById.get('a').note"))
    # 自分の結論が最優先
    pg.evaluate("openEntry('a');openEntryEdit()"); pg.wait_for_timeout(300)
    pg.fill('#eeConcl','自分の結論：Cookieで決まり'); pg.click('#eeSave'); pg.wait_for_timeout(500)
    check('自分で書いた結論が最優先', pg.evaluate("conclusionOf(entryById.get('a'))")['text']=='自分の結論：Cookieで決まり')
    check('一覧にも反映', '自分の結論：Cookieで決まり' in pg.inner_text('#list'))
    # 古くなる
    pg.evaluate("writeEntries([Object.assign({},entryById.get('a'),{conclusion:''})])"); pg.wait_for_timeout(200)
    check('AIまとめは新しいうちは判断より優先', pg.evaluate("conclusionOf(entryById.get('a'))")['src']=='AIのまとめ')
    pg.evaluate("writeQAs([{id:'q9',entryId:'a',question:'追加の質問',answer:'追加の回答です。',judgment:'',sourceType:'gemini',sourceUrl:'',createdAt:Date.now(),updatedAt:Date.now()+5}])"); pg.wait_for_timeout(200)
    check('Q&Aが増えるとAIまとめは「古い」扱い', pg.evaluate("digestFresh(entryById.get('a'))")==False and pg.evaluate("conclusionOf(entryById.get('a'))")['src']=='自分の判断')
    # 一括（体系・学習の ③）
    pg.evaluate("openSys()"); pg.wait_for_timeout(300)
    check('サイクルに「結論をまとめる」', '③ 結論をまとめる' in pg.inner_text('#sysSteps'))
    n0=len(prompts)
    pg.click('[data-sys="digest"]'); pg.wait_for_timeout(2500)
    print('DBG',[ (x[x.find('---')-0:][:0], [t for t in ['JWT','Cookie','CORS','Session'] if '■'+t in x]) for x in prompts[n0:]],pg.evaluate("digestTargets().map(e=>e.term)"),pg.evaluate("[...entryById.values()].map(e=>e.term+':'+!!e.digest)"),len(prompts)-n0)
    check('まとめていない項目だけをまとめる', pg.evaluate("['b','c','d'].every(i=>!!entryById.get(i).digest)") and pg.evaluate("!!entryById.get('e').digest")==False, pg.evaluate("Object.keys(entryById.get('c'))"))
    check('3件ずつ（1回で足りる件数）', len(prompts)-n0>=1 and len(prompts)-n0<=2, len(prompts)-n0)
    # 検索で結論も引ける
    pg.evaluate("closeSheet('shSys')"); pg.fill('#q','身分証'); pg.evaluate("searchQuery='身分証';renderList()"); pg.wait_for_timeout(200)
    # 書庫でも結論
    pg.evaluate("document.querySelector('#q').value='';searchQuery='';renderList();openLib()"); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelectorAll('#libBody details.cat').forEach(d=>d.open=true)"); pg.click('#libBody details.shelf > summary'); pg.wait_for_timeout(300)
    check('書庫の棚でも結論が見える', '🎯' in pg.inner_text('#libBody'))
    b.close()
print('結果: OK',ok,'/ NG',ng); print('JSエラー:',errs or 'なし')
