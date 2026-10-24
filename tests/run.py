import os
import json, sys, threading, http.server, socketserver, functools, os, time
from playwright.sync_api import sync_playwright
ROOT=os.environ.get('KD_ROOT','.')
H=functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
H=functools.partial(Q, directory=ROOT)
socketserver.TCPServer.allow_reuse_address=True
srv=socketserver.TCPServer(('127.0.0.1',8477),H)
threading.Thread(target=srv.serve_forever,daemon=True).start()
URL='http://127.0.0.1:8477/index.html'
errs=[]; ok=0; ng=0
def check(name,cond,extra=''):
    global ok,ng
    if cond: ok+=1; print('  OK ',name)
    else: ng+=1; print('  NG ',name,extra)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome') if os.path.exists('/opt/pw-browsers/chromium-1194/chrome-linux/chrome') else p.chromium.launch()
    ctx=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,permissions=['clipboard-read','clipboard-write'],accept_downloads=True)
    pg=ctx.new_page()
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.on('console',lambda m: errs.append('console:'+m.text) if m.type=='error' else None)
    pg.on('dialog',lambda d:d.accept())
    pg.goto(URL); pg.wait_for_selector('#list')
    check('空の画面が出る', 'まだ何もありません' in pg.inner_text('#list'))
    pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'01-empty.png'))

    def add(q,a,term='',one='',tags='',rel='',judg=''):
        pg.click('#btnAdd'); pg.wait_for_selector('#shQA.open')
        pg.fill('#qQuestion',q); pg.fill('#qAnswer',a)
        if term: pg.fill('#qTerm',term); pg.dispatch_event('#qTerm','change')
        if one: pg.fill('#qOne',one)
        if tags: pg.fill('#qTags',tags)
        if rel: pg.fill('#qRel',rel)
        if judg: pg.fill('#qJudgment',judg)
        pg.click('#qaSave'); pg.wait_for_timeout(250)
    add('JWTとは何ですか？','JSON Web Tokenを使った認証トークン形式です。署名で改ざんを検知します。',term='JWT',one='APIの認証に使うトークン形式',tags='認証 API Web',rel='OAuth Cookie',judg='今回はJWTを採用する')
    check('1件保存して一覧に出る', 'JWT' in pg.inner_text('#list') and '1項目' in pg.inner_text('#count'))
    add('JWTの有効期限はどう決める？','短くしてリフレッシュトークンを併用します。',term='jwt')   # 大文字小文字違いでも同じ項目
    check('同じ見出し語は1項目にまとまる', '1項目' in pg.inner_text('#count'))
    add('Cookieとは？','ブラウザに保存される小さなデータです。',term='Cookie',one='ブラウザ側の小さな保存データ',tags='Web')
    check('2項目になる', '2項目' in pg.inner_text('#count'))
    pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'02-list.png'))

    # 検索
    pg.fill('#q','認証'); check('タグ検索でJWT', 'JWT' in pg.inner_text('#list') and 'Cookie' not in pg.inner_text('#list'))
    pg.fill('#q','jwt 有効期限'); check('AND検索（回答側の語）', 'JWT' in pg.inner_text('#list') and '1件ヒット' in pg.inner_text('#count'))
    pg.fill('#q','jwt zzz'); check('AND検索：片方なしで0件', '見つかりませんでした' in pg.inner_text('#list'))
    pg.fill('#q','ＪＷＴ'); check('全角でも当たる', 'JWT' in pg.inner_text('#list'))
    pg.fill('#q','Cookie'); first=pg.inner_text('.c-term'); check('見出し語一致が先頭', first.strip()=='Cookie')
    pg.fill('#q','')

    # 保存前検索
    pg.click('#btnAdd'); pg.wait_for_selector('#shQA.open')
    pg.fill('#qQuestion','JWTとOAuthの違いは？'); pg.wait_for_timeout(400)
    sim=pg.inner_text('#simBox'); check('保存前検索：JWTが出る', 'JWT' in sim and '似ている項目' in sim)
    pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'03-form-sim.png'))
    pg.click('[data-simuse]'); check('「ここに足す」で見出し語が入る', pg.input_value('#qTerm')=='JWT')
    check('既存項目の値が入る', '認証' in pg.input_value('#qTags') and 'OAuth' in pg.input_value('#qRel'))
    check('既存項目の注記', '既存の項目' in pg.inner_text('#termNote'))
    pg.click('#qaCancel'); pg.wait_for_timeout(300)

    # AI整理（モック）
    pg.click('#btnSettings'); pg.wait_for_selector('#shSet.open')
    pg.fill('#sEndpoint','https://mock.example.test'); pg.fill('#sToken','tok_abcdef123456'); pg.click('#btnSaveAI'); pg.click('#stClose'); pg.wait_for_timeout(300)
    reqs=[]
    def handle(route):
        reqs.append(route.request.post_data_json)
        route.fulfill(status=200,content_type='application/json',headers={'access-control-allow-origin':'*'},body=json.dumps({'text':'```json\n{"term":"OAuth","oneLine":"認可の標準的な仕組み","tags":["認証","OAuth","API"],"related":["JWT","Session"]}\n```'}))
    pg.route('https://mock.example.test/ai',lambda r: handle(r) if r.request.method=='POST' else r.fulfill(status=204,headers={'access-control-allow-origin':'*','access-control-allow-headers':'*','access-control-allow-methods':'*'}))
    pg.click('#btnAdd'); pg.wait_for_selector('#shQA.open')
    pg.fill('#qQuestion','OAuthとは？'); pg.fill('#qAnswer','認可の仕組み。\napi_key = sk-abcdefghijklmnopqrstuvwxyz123456\nアクセストークンを使う。')
    pg.fill('#qJudgment','これは送られない秘密のメモ')
    pg.click('#btnAI'); pg.wait_for_selector('[data-ai="all"]',timeout=8000)
    check('AIに送った本文に秘密行が無い', reqs and 'sk-abcdef' not in reqs[0]['prompt'])
    check('自分の判断は送らない', reqs and '秘密のメモ' not in reqs[0]['prompt'])
    check('provider/modelが付く', reqs and reqs[0]['provider']=='gemini' and reqs[0]['model']=='gemini-3.5-flash-lite')
    pg.wait_for_timeout(450); pg.evaluate("document.getElementById('shQA').scrollTo(0,document.getElementById('btnAI').offsetTop-80)"); pg.wait_for_timeout(200); pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'04-ai.png'))
    pg.click('[data-ai="all"]')
    check('すべて採用：見出し語', pg.input_value('#qTerm')=='OAuth')
    check('すべて採用：タグ/関連', '認証' in pg.input_value('#qTags') and 'JWT' in pg.input_value('#qRel'))
    pg.click('#qaSave'); pg.wait_for_timeout(300)
    if pg.evaluate("document.getElementById('shSecret').classList.contains('open')"): pg.click('#scAsIs'); pg.wait_for_timeout(300)
    check('3項目になる', '3項目' in pg.inner_text('#count'))

    # 項目画面
    pg.fill('#q','JWT'); pg.click('.card'); pg.wait_for_selector('#shEntry.open')
    body=pg.inner_text('#enBody'); check('項目画面：Q&A2件', 'Q&A（2件）' in body, body[:200])
    check('関連用語に📖（OAuthは項目あり）', '📖 OAuth' in body)
    pg.wait_for_timeout(450); pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'05-entry.png'))
    pg.click('[data-und="known"]'); pg.wait_for_timeout(200)
    check('理解度を変えられる', 'on' in pg.get_attribute('[data-und="known"]','class'))
    pg.click('#enEdit'); pg.fill('#eeNote','自分の言葉：署名つきの身分証みたいなもの'); pg.click('#eeSave'); pg.wait_for_timeout(250)
    check('自分の理解が表示される', '署名つきの身分証' in pg.inner_text('#enBody'))
    pg.click('summary >> nth=0'); pg.click('[data-copy="ask"] >> nth=0'); pg.wait_for_timeout(200)
    clip=pg.evaluate('navigator.clipboard.readText()'); check('再質問用コピーに内容が入る', '以前の質問' in clip and '自分の理解' in clip and '今回の質問' in clip)
    pg.click('#enClose'); pg.wait_for_timeout(300)
    pg.click('[data-f="known"]'); check('理解済フィルタ', 'JWT' in pg.inner_text('#list') and 'Cookie' not in pg.inner_text('#list'))
    pg.click('[data-f="all"]')

    # quick-ref 取り込み
    pg.click('#btnSettings'); pg.wait_for_selector('#shSet.open')
    pg.set_input_files('#fileQR',os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'qr-export.json')); pg.wait_for_timeout(500)
    t=pg.inner_text('#toast'); check('取り込みの通知', '取り込み 2件' in t and '対象外 2件' in t, t)
    pg.set_input_files('#fileQR',os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'qr-export.json')); pg.wait_for_timeout(500)
    t=pg.inner_text('#toast'); check('再取り込みは重複しない', 'すでにあった 2件' in t and '取り込み 0件' in t, t)
    pg.click('#stClose'); pg.wait_for_timeout(300)
    pg.fill('#q','OAuth'); pg.wait_for_timeout(100)
    names=pg.locator('.c-term').all_inner_texts(); check('OAuthの項目は1つにまとまり先頭', names[0].strip()=='OAuth' and names.count('OAuth')==1, str(names))
    pg.fill('#q','')

    # 書き出し・読み込み・再読込
    pg.click('#btnSettings'); pg.wait_for_selector('#shSet.open')
    with pg.expect_download() as dl: pg.click('#btnExport')
    path=dl.value.path(); data=json.load(open(path,encoding='utf-8'))
    check('書き出しの中身', data['app']=='knowledge-dictionary' and len(data['entries'])>=3 and len(data['qas'])>=5, str((len(data['entries']),len(data['qas']))))
    n_e,n_q=len(data['entries']),len(data['qas'])
    pg.click('#stClose')
    pg.reload(); pg.wait_for_selector('#list'); pg.wait_for_timeout(300)
    check('再読込しても残っている', f'{n_e}項目' in pg.inner_text('#count'))
    check('バックアップ警告は消える', 'バックアップ' not in pg.inner_text('#warnBox'))
    # 別の空のコンテキストに読み込み
    ctx2=b.new_context(viewport={'width':390,'height':844}); p2=ctx2.new_page(); p2.on('dialog',lambda d:d.accept()); p2.goto(URL); p2.wait_for_selector('#list')
    check('新しい端末は空＋バックアップ警告なし(0件)', 'まだ何もありません' in p2.inner_text('#list'))
    p2.click('#btnSettings'); p2.set_input_files('#fileOwn',path); p2.wait_for_timeout(500)
    p2.click('#stClose'); p2.wait_for_timeout(300)
    check('書き出しを別端末に読み込める', f'{n_e}項目' in p2.inner_text('#count'), p2.inner_text('#count'))
    # SW登録
    p2.wait_for_timeout(800)
    check('Service Worker 登録', p2.evaluate('navigator.serviceWorker.getRegistrations().then(r=>r.length)')>=1)
    b.close()
print('\n結果: OK',ok,'/ NG',ng)
print('JSエラー:',errs if errs else 'なし')
