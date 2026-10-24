import os
import json, threading, http.server, socketserver, functools, os
from playwright.sync_api import sync_playwright
ROOT=os.environ.get('KD_ROOT','.')
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
socketserver.TCPServer.allow_reuse_address=True
srv=socketserver.TCPServer(('127.0.0.1',8612),functools.partial(Q,directory=ROOT))
threading.Thread(target=srv.serve_forever,daemon=True).start()
ok=ng=0; errs=[]
def check(n,c,x=''):
    global ok,ng
    if c: ok+=1; print('  OK ',n)
    else: ng+=1; print('  NG ',n,x)
CORS={'access-control-allow-origin':'*','access-control-allow-headers':'*','access-control-allow-methods':'*'}
cloud={'body':None}; puts=[]
def worker(route):
    r=route.request
    if r.method=='OPTIONS': return route.fulfill(status=204,headers=CORS)
    if r.method=='PUT':
        cloud['body']=r.post_data; puts.append(r.post_data); return route.fulfill(status=200,content_type='application/json',headers=CORS,body='{}')
    if cloud['body'] is None: return route.fulfill(status=404,headers=CORS,body='{}')
    route.fulfill(status=200,content_type='application/json',headers=CORS,body=cloud['body'])
PASS='correct horse battery'
def dev(b):
    c=b.new_context(viewport={'width':390,'height':844}); pg=c.new_page()
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',lambda d:d.accept())
    pg.route('https://mock.example.test/**',worker)
    pg.goto('http://127.0.0.1:8612/index.html'); pg.wait_for_selector('#list')
    pg.evaluate("lsSet('kd_endpoint','https://mock.example.test');lsSet('kd_token','tok_abc123')")
    return pg
def setopen(pg): pg.evaluate("renderSettings();openSheet('shSet')"); pg.wait_for_timeout(200)
with sync_playwright() as p:
    b=p.chromium.launch()
    A=dev(b); B=dev(b)
    A.evaluate("(async()=>{const n=Date.now();await writeEntries([{id:'a',term:'公開メモ',oneLine:'',tags:[],related:[],note:'ひみつの内容XYZ',kind:'term',understanding:'unknown',checkedAt:null,createdAt:n,updatedAt:n}]);await writeQAs([{id:'q1',entryId:'a',question:'何？',answer:'ふつうの答え',judgment:'',sourceType:'other',sourceUrl:'',createdAt:n,updatedAt:n}]);refresh()})()")
    # 平文で同期（従来どおり）
    A.evaluate("kdSync(true)"); A.wait_for_timeout(800)
    check('暗号化前は従来どおり平文で同期', cloud['body'] and 'ひみつの内容XYZ' in cloud['body'])
    # A: 暗号化を始める
    A.evaluate("openSettings && 0") if False else None
    setopen(A); A.fill('#sEncPass',PASS); A.fill('#sEncPass2',PASS)
    A.click('#btnEncOn'); A.wait_for_timeout(4000)
    body=json.loads(cloud['body'])
    check('暗号化後のクラウドは平文を含まない', 'ひみつの内容XYZ' not in cloud['body'] and 'enc' in body['data'] and 'entries' not in body['data'], cloud['body'][:150])
    env=body['data']['enc']
    check('方式がAES-GCM/PBKDF2 60万回', env['alg']=='AES-256-GCM' and env['kdf']=='PBKDF2-SHA256' and env['iter']==600000 and len(env['salt'])>10 and len(env['iv'])>10)
    check('設定画面にオンと出る', '🔒' in A.inner_text('#encStat') and 'オン' in A.inner_text('#encStat'))
    # 2回目の同期でIVが変わる（同じIVを使い回さない）
    A.evaluate("writeEntries([Object.assign({},entryById.get('a'),{note:'更新1',updatedAt:Date.now()+10})])"); A.wait_for_timeout(300)
    A.evaluate("kdSync(false)"); A.wait_for_timeout(1500)
    iv2=json.loads(cloud['body'])['data']['enc']['iv']
    check('送るたびにIVが新しい', iv2!=env['iv'])
    # B: 鍵なしで同期 → 止まる・上書きしない
    before=cloud['body']; n0=len(puts)
    B.evaluate("kdSync(true)"); B.wait_for_timeout(1200)
    check('鍵のない端末は送信せず止まる', len(puts)==n0 and cloud['body']==before)
    check('分かる案内が出る', '暗号化されています' in B.evaluate("syncMsg"), B.evaluate("syncMsg"))
    check('Bには何も入っていない', B.evaluate("entries.length")==0)
    # 間違ったパスフレーズ
    setopen(B); B.fill('#sEncPass','wrong passphrase!!'); B.click('#btnEncEnter'); B.wait_for_timeout(4000)
    check('間違いは弾かれ鍵は保存されない', B.evaluate("lsGet('kd_ek')")=='' )
    # 正しいパスフレーズ
    B.fill('#sEncPass',PASS); B.click('#btnEncEnter'); B.wait_for_timeout(5000)
    check('正しいパスフレーズで鍵が入り同期できる', B.evaluate("entries.length")==1 and B.evaluate("entryById.get('a').note")=='更新1', B.evaluate("syncMsg"))
    # B→A 逆方向
    B.evaluate("writeEntries([Object.assign({},entryById.get('a'),{note:'Bで更新',updatedAt:Date.now()+20})])"); B.wait_for_timeout(300)
    B.evaluate("kdSync(false)"); B.wait_for_timeout(1500)
    A.evaluate("kdSync(false)"); A.wait_for_timeout(1500)
    check('暗号化したまま双方向に反映', A.evaluate("entryById.get('a').note")=='Bで更新' and 'Bで更新' not in cloud['body'])
    # パスフレーズ変更（Aで）→ Bは入れ直しが必要
    A.fill('#sEncPass','another long passphrase'); A.fill('#sEncPass2','another long passphrase'); A.click('#btnEncOn'); A.wait_for_timeout(4500)
    salt_new=json.loads(cloud['body'])['data']['enc']['salt']
    check('パスフレーズ変更でsaltが変わる', salt_new!=env['salt'])
    B.evaluate("kdSync(true)"); B.wait_for_timeout(1200)
    check('変更後の旧鍵はやさしく止まる', '変えられました' in B.evaluate("syncMsg"), B.evaluate("syncMsg"))
    # 暗号化バックアップ
    A.fill('#sBkPass','backup passphrase 1'); A.fill('#sBkPass2','backup passphrase 1')
    with A.expect_download() as dl: A.click('#btnExportEnc')
    path=dl.value.path(); txt=open(path,encoding='utf-8').read()
    check('暗号化バックアップは平文を含まない', 'Bで更新' not in txt and '"enc"' in txt and dl.value.suggested_filename.endswith('.暗号化.json'))
    A.fill('#sBkPass','x'*10); A.fill('#sBkPass2','y'*10)
    n=A.evaluate("0"); 
    # 読み込み：別端末C
    C=dev(b); setopen(C)
    C.fill('#sBkPass','wrong-pass-xxx')
    C.set_input_files('#fileOwn',path); C.wait_for_timeout(3500)
    check('誤ったパスフレーズでは読み込めない', C.evaluate("entries.length")==0)
    C.fill('#sBkPass','backup passphrase 1')
    C.set_input_files('#fileOwn',path); C.wait_for_timeout(3500)
    check('正しいパスフレーズで読み込める', C.evaluate("entries.length")==1 and C.evaluate("entryById.get('a').note")=='Bで更新')
    # 通常バックアップは従来どおり
    with C.expect_download() as dl2: C.click('#btnExport')
    check('通常の書き出しは従来どおり', '"entries"' in open(dl2.value.path(),encoding='utf-8').read())
    # ---- 秘密検出
    S=dev(b)
    def openqa(): S.evaluate("openQA && openQA()") 
    S.evaluate("document.getElementById('btnAdd')&&0")
    S.evaluate("openSheet('shQA')")
    S.fill('#qQuestion','APIの設定は？'); S.fill('#qAnswer','こう設定します\napi_key = sk-abcdefghijklmnopqrstuvwx123456\n以上です'); S.fill('#qTerm','設定')
    S.click('#qaSave'); S.wait_for_timeout(500)
    check('秘密らしき行があると確認が出て保存されない', S.evaluate("document.getElementById('shSecret').classList.contains('open')") and S.evaluate("qas.length")==0)
    check('確認画面は秘密そのものを表示しない', 'abcdefghijklmnop' not in S.inner_text('#scBody') and '1行' in S.inner_text('#scBody'), S.inner_text('#scBody'))
    S.click('#scMask'); S.wait_for_timeout(800)
    ans=S.evaluate("qas[0].answer")
    check('伏せ字にして保存', S.evaluate("qas.length")==1 and '〔伏せ字〕' in ans and 'sk-abcdef' not in ans and 'こう設定します' in ans and '以上です' in ans, ans)
    S.evaluate("openSheet('shQA')"); S.fill('#qQuestion','別の質問'); S.fill('#qAnswer','token: ghp_aaaaaaaaaaaaaaaaaaaaaaaaaa を使う'); S.fill('#qTerm','設定2')
    S.click('#qaSave'); S.wait_for_timeout(300); S.click('#scAsIs'); S.wait_for_timeout(800)
    check('「そのまま保存」もできる', S.evaluate("qas.length")==2 and 'ghp_aaaa' in S.evaluate("qas.find(q=>q.question==='別の質問').answer"))
    S.evaluate("openSheet('shQA')"); S.fill('#qQuestion','普通の質問'); S.fill('#qAnswer','ただの説明です。https://example.com/a'); S.fill('#qTerm','普通')
    S.click('#qaSave'); S.wait_for_timeout(600)
    check('普通の内容は確認なしで保存', S.evaluate("qas.length")==3 and not S.evaluate("document.getElementById('shSecret').classList.contains('open')"))
    # 既存データの検索
    S.click('#btnSecScan') if False else S.evaluate("secretScan()"); S.wait_for_timeout(300)
    check('既存データから見つかる（1件）', '1件' in S.inner_text('#scBody'), S.inner_text('#scBody'))
    S.click('#scMask'); S.wait_for_timeout(800)
    check('まとめて伏せ字', 'ghp_aaaa' not in S.evaluate("qas.find(q=>q.question==='別の質問').answer"))
    S.evaluate("secretScan()"); S.wait_for_timeout(600)
    check('再検索では見つからない', '見つかりませんでした' in S.inner_text('#scBody'))
    S.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'25-secret.png'))
    b.close()
print('結果: OK',ok,'/ NG',ng); print('JSエラー:',errs or 'なし')
