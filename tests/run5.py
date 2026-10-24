import os
import threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright
ROOT=os.environ.get('KD_ROOT','.')
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
socketserver.TCPServer.allow_reuse_address=True
srv=socketserver.TCPServer(('127.0.0.1',8475),functools.partial(Q,directory=ROOT))
threading.Thread(target=srv.serve_forever,daemon=True).start()
ok=ng=0; errs=[]
def check(n,c,x=''):
    global ok,ng
    if c: ok+=1; print('  OK ',n)
    else: ng+=1; print('  NG ',n,x)
ANS="""### 次にやること

ここからが本格的なPhase 2です。

**次は `hub_handoff_v1` を実際に各アプリへ接続します。**

優先順位は、

1. `flow-hub → music-suite`
2. `flow-hub → flow-mind`
3. `flow-mind → flow-hub`

> **「音楽を作る」→ music-suite → 「flow-hubへ戻る」**

を一本通します。これが通れば、flow-hubが単なるランチャーではなく、**本当に各アプリをつなぐ個人OS**になり始めます。flow-hub と music-suite と flow-mind をつなぎます。"""
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2).new_page()
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',lambda d:d.accept())
    pg.goto('http://127.0.0.1:8475/index.html'); pg.wait_for_selector('#list')
    r=pg.evaluate("autoExtract(%r,'flow-hub 計画',6)"%ANS)
    print('   抽出:',r)
    tg=[t.lower() for t in r['tags']]
    check('主要な語を拾う', 'hub_handoff_v1' in tg and 'music-suite' in tg and 'flow-mind' in tg, tg)
    check('自分の見出し語は除く', 'flow-hub-計画' not in tg)
    check('ゴミ語を拾わない', not any(t in tg for t in ['次に','これ','ここ','こと','http']))
    check('個数は6以内', len(tg)<=6)
    # Q&A フォームで自動入力
    pg.click('#btnAdd'); pg.wait_for_selector('#shQA.open')
    pg.fill('#qQuestion','flow-hubの次の一手は？'); pg.fill('#qAnswer',ANS); pg.wait_for_timeout(1200)
    v=pg.input_value('#qTags')
    check('タグが自動で入る', 'music-suite' in v.lower() and 'flow-mind' in v.lower(), v)
    check('自動の説明が出る', pg.locator('#autoNote').is_visible())
    pg.click('#qTagsChips .qc.on >> nth=0'); pg.wait_for_timeout(300)
    n1=len(pg.input_value('#qTags').split())
    pg.fill('#qAnswer',ANS+'\nさらに追加の文章をたくさん書きます。Cookie と JWT。'); pg.wait_for_timeout(1200)
    check('手で外したあとは、自動で戻さない', len(pg.input_value('#qTags').split())==n1, pg.input_value('#qTags'))
    pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'15-auto.png'))
    pg.click('#qaSave'); pg.wait_for_timeout(600)
    e=pg.evaluate("entries[0]")
    check('保存でタグが入る', len(e['tags'])>=3, e['tags'])
    # 表示：Markdown
    pg.evaluate("openEntry(entries[0].id)"); pg.wait_for_timeout(400)
    html=pg.inner_html('#enBody')
    check('見出し・太字・コードが整形される', 'class="mdh"' in html and '<b>' in html and 'class="kc"' in html and '###' not in pg.inner_text('#enBody') and '**' not in pg.inner_text('#enBody'), pg.inner_text('#enBody')[:200])
    # 2件目：同じタグ → 関連に出る
    pg.evaluate("(async()=>{const n=Date.now();await writeEntries([{id:'z9',term:'音楽メモ',oneLine:'',tags:['music-suite'],related:[],note:'',kind:'term',understanding:'unknown',checkedAt:null,createdAt:n,updatedAt:n}]);})()"); pg.wait_for_timeout(300)
    pg.evaluate("openEntry(entries.find(e=>e.id!=='z9').id)"); pg.wait_for_timeout(300)
    check('タグでつながる項目が出る', '音楽メモ' in pg.inner_text('#enBody') and '共通のタグ' in pg.inner_text('#enBody'))
    pg.click('#enBody .card[data-open="z9"]'); pg.wait_for_timeout(300)
    check('押すと開く', '音楽メモ' in pg.inner_text('#enBody'))
    pg.click('#enClose'); pg.wait_for_timeout(300)
    # 一覧のタグを押すと絞り込み
    pg.click('#list .tag.lk >> nth=0'); pg.wait_for_timeout(300)
    check('一覧のタグを押すと検索になる', pg.input_value('#q')!='')
    # 一括
    pg.fill('#q',''); pg.evaluate("searchQuery='';renderList()")
    pg.evaluate("(async()=>{const n=Date.now();await writeEntries([{id:'y1',term:'素のメモ',oneLine:'',tags:[],related:[],note:'Cookie と Session管理 を学ぶ。Cookie の属性。',kind:'term',understanding:'unknown',checkedAt:null,createdAt:n,updatedAt:n}]);})()")
    pg.evaluate("bulkAutoTag()"); pg.wait_for_timeout(600)
    check('一括で自動タグ', pg.evaluate("entryById.get('y1').tags.length")>=1, pg.evaluate("entryById.get('y1').tags"))
    b.close()
print('結果: OK',ok,'/ NG',ng); print('JSエラー:',errs or 'なし')
