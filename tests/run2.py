import os
import json, threading, http.server, socketserver, functools, os
from playwright.sync_api import sync_playwright
ROOT=os.environ.get('KD_ROOT','.')
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
socketserver.TCPServer.allow_reuse_address=True
srv=socketserver.TCPServer(('127.0.0.1',8471),functools.partial(Q,directory=ROOT))
threading.Thread(target=srv.serve_forever,daemon=True).start()
URL='http://127.0.0.1:8471/index.html'
errs=[]; ok=0; ng=0
def check(name,cond,extra=''):
    global ok,ng
    if cond: ok+=1; print('  OK ',name)
    else: ng+=1; print('  NG ',name,extra)
with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2,permissions=['clipboard-read','clipboard-write'])
    pg=ctx.new_page()
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.on('console',lambda m: errs.append('console:'+m.text) if m.type=='error' else None)
    dialogs=[]
    pg.on('dialog',lambda d:(dialogs.append(d.message),d.accept()))
    pg.goto(URL); pg.wait_for_selector('#list')

    # --- AIに聞く：接続未設定 ---
    pg.click('#btnAsk'); pg.wait_for_selector('#shAsk.open'); pg.wait_for_timeout(300)
    check('未設定のとき警告が出る', '未設定' in pg.inner_text('#aMeta'))
    pg.fill('#aQ','JWTとは何ですか？'); pg.click('#btnAskGo'); pg.wait_for_timeout(300)
    check('未設定で聞くとエラー表示', '未設定' in pg.inner_text('#aOut'), pg.inner_text('#aOut'))
    pg.click('#askClose'); pg.wait_for_timeout(300)

    # 接続設定＋モック
    pg.click('#btnSettings'); pg.wait_for_selector('#shSet.open')
    pg.fill('#sEndpoint','https://mock.example.test'); pg.fill('#sToken','tok_abcdef123456'); pg.fill('#sLimit','2'); pg.fill('#sSys','テスト指示：短く答えて'); pg.click('#btnSaveAI'); pg.click('#stClose'); pg.wait_for_timeout(300)
    reqs=[]
    ANS={'n':0}
    def handle(route):
        reqs.append(route.request.post_data_json); ANS['n']+=1
        route.fulfill(status=200,content_type='application/json',headers={'access-control-allow-origin':'*'},body=json.dumps({'text':'JWTは署名つきのトークンです。[[Cookie]] と組み合わせて使います。（回答%d）'%ANS['n']}))
    pg.route('https://mock.example.test/ai',lambda r: handle(r) if r.request.method=='POST' else r.fulfill(status=204,headers={'access-control-allow-origin':'*','access-control-allow-headers':'*','access-control-allow-methods':'*'}))

    pg.click('#btnAsk'); pg.wait_for_selector('#shAsk.open'); pg.wait_for_timeout(300)
    pg.fill('#aQ','JWTとは何ですか？\napi_key = sk-abcdefghijklmnopqrstuvwxyz123456')
    pg.click('#btnAskGo'); pg.wait_for_selector('[data-ask="save"]',timeout=8000)
    check('秘密行の除外を確認するダイアログ', any('秘密らしい行' in d for d in dialogs))
    check('送った本文に秘密が無い', 'sk-abcdef' not in reqs[0]['prompt'])
    check('回答の指示が先頭に付く', reqs[0]['prompt'].startswith('テスト指示：短く答えて'))
    check('質問が含まれる', 'JWTとは何ですか' in reqs[0]['prompt'])
    check('回答が表示される', 'JWTは署名つき' in pg.inner_text('#aOut'))
    check('使用量が増える', '今日：1回' in pg.inner_text('#aMeta') and '上限 2回' in pg.inner_text('#aMeta'), pg.inner_text('#aMeta'))
    pg.wait_for_timeout(450); pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'10-ask.png'))
    pg.click('[data-ask="save"]'); pg.wait_for_selector('#shEntry.open'); pg.wait_for_timeout(400)
    body=pg.inner_text('#enBody')
    check('そのまま保存：項目ができる', 'JWTとは何ですか？' in body and 'アプリから質問' in body, body[:200])
    check('回答内の[[Cookie]]が未作成リンクになる', pg.locator('#enBody .wl.unres[data-wl="Cookie"]').count()>=1)
    pg.click('#enClose'); pg.wait_for_timeout(300)
    d=pg.evaluate("JSON.parse(localStorage.getItem('kd_usage'))"); check('使用量が保存される', d['calls']==1 and d['inC']>0 and d['outC']>0, str(d))

    # --- 過去の項目を材料にして聞く ---
    pg.click('#btnAsk'); pg.wait_for_selector('#shAsk.open')
    pg.fill('#aQ','JWTとは何ですか？有効期限は？'); pg.wait_for_selector('[data-ctx]',timeout=3000)
    check('過去の項目が材料候補に出る', 'JWTとは何ですか' in pg.inner_text('#aCtx'))
    pg.check('[data-ctx]'); pg.click('#btnAskGo'); pg.wait_for_selector('[data-ask="save"]',timeout=8000)
    check('材料が送られる', '【参考：以前の自分の整理】' in reqs[1]['prompt'])
    check('1件チェックなら、その項目に足す案内', 'に足します' in pg.inner_text('#aOut'))
    pg.click('[data-ask="save"]'); pg.wait_for_selector('#shEntry.open'); pg.wait_for_timeout(400)
    check('同じ項目にQ&Aが2件', 'Q&A（2件）' in pg.inner_text('#enBody'))
    pg.click('#enClose'); pg.wait_for_timeout(300)

    # --- 上限（2回で到達→3回目は確認ダイアログ） ---
    n0=len(dialogs)
    pg.click('#btnAsk'); pg.wait_for_selector('#shAsk.open'); pg.fill('#aQ','3回目の質問'); pg.click('#btnAskGo'); pg.wait_for_selector('[data-ask="save"]',timeout=8000)
    check('上限を超えると確認が出る', any('上限' in d for d in dialogs[n0:]), str(dialogs[n0:]))
    # 「整理して保存」→ フォームに引き継ぐ
    pg.click('[data-ask="form"]'); pg.wait_for_selector('#shQA.open'); pg.wait_for_timeout(300)
    check('整理して保存：質問と回答が入る', pg.input_value('#qQuestion')=='3回目の質問' and '回答' in pg.input_value('#qAnswer'))
    check('ソースがAIの種類になる', pg.input_value('#qSource')=='gemini')
    pg.fill('#qTerm','テスト用語'); pg.click('#qaSave'); pg.wait_for_timeout(300)

    # --- [[リンク]]・被リンク・種類・つながり ---
    pg.click('#btnAdd'); pg.wait_for_selector('#shQA.open')
    pg.fill('#qQuestion','Cookieとは？'); pg.fill('#qAnswer','ブラウザに保存される小さなデータ。'); pg.fill('#qTerm','Cookie'); pg.click('#qaSave'); pg.wait_for_timeout(300)
    # 手順の項目を作る：種類=手順、自分の理解にリンク
    pg.click('#btnAdd'); pg.wait_for_selector('#shQA.open')
    pg.fill('#qQuestion','ログインの作り方は？'); pg.fill('#qAnswer','認証してトークンを返す。'); pg.fill('#qTerm','ログイン実装の手順'); pg.select_option('#qKind','howto'); pg.click('#qaSave'); pg.wait_for_timeout(300)
    pg.fill('#q','ログイン実装'); pg.click('.card'); pg.wait_for_selector('#shEntry.open'); pg.wait_for_timeout(350)
    check('手順のバッジ', '手順' in pg.inner_text('#enBody'))
    pg.click('#enEdit'); pg.wait_for_selector('#shEntryEdit.open'); pg.wait_for_timeout(300)
    pg.fill('#eeNote','1. [[JWT]] を発行する\n2. [[Cookie]] に入れる\n3. [[Session管理]] を決める')
    # リンク挿入ピッカー
    pg.click('[data-linkpick="eeNote"]'); pg.wait_for_selector('#shPick.open'); pg.wait_for_timeout(300)
    pg.fill('#pkQ','cook'); pg.wait_for_timeout(200)
    check('ピッカーにCookieが出る', 'Cookie' in pg.inner_text('#pkList'))
    pg.click('[data-pk="Cookie"]'); pg.wait_for_timeout(250)
    check('リンクが挿入される', pg.input_value('#eeNote').count('[[Cookie]]')>=2, pg.input_value('#eeNote'))
    pg.click('#eeSave'); pg.wait_for_timeout(350)
    body=pg.inner_text('#enBody')
    check('自分の理解：項目があるリンクは青、ないリンクは点線', pg.locator('#enBody .wl[data-wl="Cookie"]:not(.unres)').count()>=1 and pg.locator('#enBody .wl.unres[data-wl="JWT"]').count()>=1 and pg.locator('#enBody .wl.unres[data-wl="Session管理"]').count()>=1)
    check('未作成リンクの一覧', 'まだ項目がないリンク' in body)
    pg.wait_for_timeout(400); pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'11-howto.png'))
    # 未作成リンクから項目を作る
    pg.click('#enBody .wl.unres[data-wl="Session管理"] >> nth=0'); pg.wait_for_timeout(500)
    check('リンクから項目が作られ開く', 'Session管理' in pg.inner_text('#enBody') and any('まだありません' in d for d in dialogs))
    pg.click('#enClose'); pg.wait_for_timeout(300)
    # 被リンク：Cookie の項目に、手順からの被リンクが出る
    pg.fill('#q','Cookie'); pg.locator('.card').first.click(); pg.wait_for_selector('#shEntry.open'); pg.wait_for_timeout(350)
    b2=pg.inner_text('#enBody'); check('被リンクに手順が出る', 'この項目にリンクしている項目' in b2 and 'ログイン実装の手順' in b2, b2[-300:])
    # つながり図（この周辺）
    pg.click('[data-graph]'); pg.wait_for_selector('#shGraph.open'); pg.wait_for_timeout(500)
    check('つながり図にSVGの丸が出る', pg.locator('#gsvg circle').count()>=3, str(pg.locator('#gsvg circle').count()))
    pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'12-graph.png'))
    pg.click('#grClose'); pg.click('#enClose'); pg.wait_for_timeout(350)
    # 全体のつながり図
    pg.fill('#q',''); pg.click('#btnGraph'); pg.wait_for_selector('#shGraph.open'); pg.wait_for_timeout(500)
    check('全体のつながり図', pg.locator('#gsvg circle').count()>=3)
    # 丸を押すと項目が開く（グラフの上に重なる）
    pg.locator('#gsvg g[data-gn]').first.click(); pg.wait_for_selector('#shEntry.open'); pg.wait_for_timeout(350)
    vis=pg.evaluate("(()=>{const a=document.getElementById('shEntry'),g=document.getElementById('shGraph');return (+a.style.zIndex)>(+g.style.zIndex)})()")
    check('グラフから開いた項目が前面に出る', vis)
    pg.click('#enClose'); pg.click('#grClose'); pg.wait_for_timeout(300)

    # 種類フィルタ
    pg.click('[data-k="howto"]'); pg.wait_for_timeout(150)
    names=pg.locator('#list .c-term').all_inner_texts(); check('手順フィルタ', len(names)==1 and 'ログイン実装の手順' in names[0], str(names))
    pg.click('[data-k="all"]'); pg.click('[data-f="known"]'); pg.wait_for_timeout(100)
    check('理解度と種類のチップが干渉しない', pg.locator('#kchips .fchip.on').count()==1 and pg.locator('#fchips .fchip.on').count()==1)
    pg.click('[data-f="all"]')

    # 設定の保存・使用量表示
    pg.click('#btnSettings'); pg.wait_for_selector('#shSet.open'); pg.wait_for_timeout(300)
    check('設定に使用量が出る', '今日：' in pg.inner_text('#usageStat'))
    check('上限・指示が保存されている', pg.input_value('#sLimit')=='2' and pg.input_value('#sSys').startswith('テスト指示'))
    # 書き出しにkind/viaAppが残る
    data=pg.evaluate("new Promise(r=>{const q=indexedDB.open('knowledge-dictionary');q.onsuccess=()=>{const t=q.result.transaction(['entries','qas']);const a=t.objectStore('entries').getAll(),b=t.objectStore('qas').getAll();t.oncomplete=()=>r({e:a.result,q:b.result})}})")
    check('kindが保存される', any(e.get('kind')=='howto' for e in data['e']))
    check('viaApp/modelが保存される', any(q.get('viaApp') and q.get('model') for q in data['q']))
    b.close()
print('\n結果: OK',ok,'/ NG',ng); print('JSエラー:',errs if errs else 'なし')
