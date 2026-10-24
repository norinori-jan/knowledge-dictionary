import os
import json, time, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright
ROOT=os.environ.get('KD_ROOT','.')
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
socketserver.TCPServer.allow_reuse_address=True
srv=socketserver.TCPServer(('127.0.0.1',8481),functools.partial(Q,directory=ROOT))
threading.Thread(target=srv.serve_forever,daemon=True).start()
ok=ng=0; errs=[]
def check(n,c,x=''):
    global ok,ng
    if c: ok+=1; print('  OK ',n)
    else: ng+=1; print('  NG ',n,x)
prompts=[]
CORS={'access-control-allow-origin':'*','access-control-allow-headers':'*','access-control-allow-methods':'*'}
QR={'data':{'items':[
 {'id':'m1','type':'ai_qa','title':'クラウド経由A','tags':['AI Q&A','テスト'],'createdAt':1,'updatedAt':2,'qa':{'question':'Q1','answer':'A1','judgment':'','summary':'要約','sourceType':'chatgpt','sourceUrl':''}},
 {'id':'m2','type':'ai_qa','title':'秘密メモ','sensitive':True,'qa':{'question':'Q','answer':'A'}},
 {'id':'m3','type':'note','title':'ふつうのメモ'}]}}
def reply(p):
    if '関係しそうな語を' in p: return '{"terms":["認証基盤"],"keywords":["ログイン","本人確認"]}'
    if '個人辞書だけを根拠' in p: return '認証基盤を使うと決めました。'
    return 'x'
def handle(route):
    r=route.request
    if r.method=='OPTIONS': return route.fulfill(status=204,headers=CORS)
    p=r.post_data_json['prompt']; prompts.append(p)
    route.fulfill(status=200,content_type='application/json',headers=CORS,body=json.dumps({'text':reply(p)}))
def qrh(route):
    r=route.request
    if r.method=='OPTIONS': return route.fulfill(status=204,headers=CORS)
    route.fulfill(status=200,content_type='application/json',headers=CORS,body=json.dumps(QR))
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2).new_page()
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',lambda d:d.accept())
    pg.route('https://mock.example.test/ai',handle); pg.route('https://mock.example.test/sync/quick-ref',qrh)
    pg.goto('http://127.0.0.1:8481/index.html'); pg.wait_for_selector('#list')
    pg.evaluate("lsSet('kd_endpoint','https://mock.example.test');lsSet('kd_token','tok_abc123')")
    mk="(async()=>{const n=Date.now();await writeEntries([%s]);})()"
    E=lambda id,term,one='',tags='[]',note='':"{id:'%s',term:'%s',oneLine:'%s',tags:%s,related:[],note:'%s',kind:'term',understanding:'unknown',checkedAt:null,createdAt:n,updatedAt:n}"%(id,term,one,tags,note)
    pg.evaluate(mk%(",".join([E('a','JWT','署名つきトークン',"['認証']"),E('b','JWT認証','JWTで認証する流れ',"['認証']"),E('c','認証基盤','ログインの仕組み全体',"['認証','基盤']",'[[JWT認証]] を採用'),E('d','お香','香料','[]','')])))
    pg.evaluate("writeQAs([{id:'q1',entryId:'a',question:'JWTとは',answer:'署名で改ざんを防ぐトークン',judgment:'',sourceType:'gemini',sourceUrl:'',createdAt:1,updatedAt:1},{id:'q2',entryId:'b',question:'JWT認証の流れ',answer:'ログイン→発行→検証',judgment:'採用',sourceType:'gemini',sourceUrl:'',createdAt:2,updatedAt:2}])")
    # 重複候補
    dp=pg.evaluate("dupPairs().map(x=>[x.a.term,x.b.term])")
    check('似た見出し語を見つける', any(set(x)=={'JWT','JWT認証'} for x in dp), dp)
    # 統合
    pg.evaluate("mergeEntries('b','a')"); pg.wait_for_timeout(500)
    check('相手の項目が消える', pg.evaluate("!entryById.get('a')"))
    check('Q&Aが移る', pg.evaluate("qasByEntry.get('b').length")==2)
    check('別名になる', 'JWT' in pg.evaluate("entryById.get('b').aliases"))
    check('別名で項目が引ける', pg.evaluate("findEntryByTerm('jwt').id")=='b')
    check('別名で検索できる', 'JWT認証' in (pg.evaluate("document.querySelector('#q').value='JWT';searchQuery='JWT';renderList();document.querySelector('#list').innerText")))
    check('別名の[[リンク]]が未解決にならない', pg.evaluate("rich('[[JWT]]').includes('unres')")==False)
    check('別名リンクが被リンクになる', pg.evaluate("openEntry('b');document.querySelector('#enBody').innerText").count('別名：JWT')==1)
    check('墓標が記録される', 'a' in json.loads(pg.evaluate("lsGet('kd_tomb')")))
    pg.evaluate("closeSheet('shEntry')")
    # UIから統合
    pg.evaluate("openEntry('c')"); pg.wait_for_timeout(300); pg.click('[data-merge="c"]'); pg.wait_for_selector('#shMerge.open'); pg.wait_for_timeout(300)
    check('統合画面に相手が並ぶ', pg.locator('#mgList [data-mg="d"]').count()==1)
    pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'18-merge.png'))
    pg.click('#mgList [data-mg="d"]'); pg.wait_for_timeout(600)
    check('画面から統合できる', pg.evaluate("!entryById.get('d')") and 'お香' in pg.evaluate("entryById.get('c').aliases"))
    pg.evaluate("closeSheet('shEntry')")
    # 言い換え検索
    pg.evaluate("lsSet('kd_limit','0')"); pg.evaluate("document.querySelector('#q').value='';searchQuery='';renderList()")
    r=pg.evaluate("retrieve('本人確認の方法は？',6).length"); check('局所検索では拾えない（前提）', r<3, r)
    pg.click('#btnBrain'); pg.wait_for_selector('#shBrain.open'); pg.wait_for_timeout(300)
    pg.fill('#bQ','本人確認の方法は？'); pg.click('#btnBrainAsk'); pg.wait_for_selector('#bOut .br-card',timeout=8000)
    check('言い換えで材料が見つかる', '言い換えで探しました' in pg.inner_text('#bOut') and '認証基盤' in pg.inner_text('#bOut'))
    check('語彙の中から選ばせている', any('辞書の語彙' in x and 'JWT認証' in x for x in prompts))
    check('材料つきで答えを聞く', any('個人辞書だけを根拠' in x and '認証基盤' in x for x in prompts))
    pg.click('#brClose')
    # クラウド経由の取り込み
    pg.evaluate("qrCloudImport(false)"); pg.wait_for_timeout(800)
    check('クラウドから取り込む', pg.evaluate("!!findEntryByTerm('クラウド経由A')"))
    check('秘密・ふつうのメモは入れない', pg.evaluate("!findEntryByTerm('秘密メモ') && !findEntryByTerm('ふつうのメモ')"))
    n=len(pg.evaluate("qas"))
    pg.evaluate("qrCloudImport(false)"); pg.wait_for_timeout(800)
    check('何度やっても重複しない', len(pg.evaluate("qas"))==n)
    # 大量データの速度
    pg.evaluate("""(async()=>{const L=[],Q=[];const n=Date.now();for(let i=0;i<600;i++){const id='bulk'+i;L.push({id,term:'項目'+i+'語'+(i%37),oneLine:'説明'+i,tags:['タグ'+(i%20)],related:[],note:'自分の理解'+i+' 認証 とトークンの話',kind:'term',understanding:'unknown',checkedAt:null,createdAt:n,updatedAt:n});for(let k=0;k<3;k++)Q.push({id:id+'q'+k,entryId:id,question:'質問'+i+'-'+k+' について',answer:'回答の本文です。'.repeat(30)+i,judgment:'',sourceType:'gemini',sourceUrl:'',createdAt:n,updatedAt:n});}
      entries=entries.concat(L);qas=qas.concat(Q);rebuild();})()""")
    t=time.time(); pg.evaluate("retrieve('認証とトークンについて自分が決めたことは',6)"); t1=time.time()-t
    t=time.time(); pg.evaluate("retrieve('認証とトークンについて自分が決めたことは',6)"); t2=time.time()-t
    t=time.time(); pg.evaluate("dupPairs()"); t3=time.time()-t
    t=time.time(); pg.evaluate("searchEntries('認証 トークン','all','all')"); t4=time.time()-t
    print('   速度(600項目/1800Q&A): 初回retrieve %.2fs / 2回目 %.2fs / 重複検出 %.2fs / 検索 %.2fs'%(t1,t2,t3,t4))
    check('大量でも実用的な速さ', t2<1.0 and t3<3.0 and t4<1.0)
    b.close()
print('結果: OK',ok,'/ NG',ng); print('JSエラー:',errs or 'なし')
