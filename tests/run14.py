import os
import json, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright
ROOT=os.environ.get('KD_ROOT','.')
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
socketserver.TCPServer.allow_reuse_address=True
srv=socketserver.TCPServer(('127.0.0.1',8614),functools.partial(Q,directory=ROOT))
threading.Thread(target=srv.serve_forever,daemon=True).start()
ok=ng=0; errs=[]
def check(n,c,x=''):
    global ok,ng
    if c: ok+=1; print('  OK ',n)
    else: ng+=1; print('  NG ',n,x)
prompts=[]; mode={'v':'gen'}
CORS={'access-control-allow-origin':'*','access-control-allow-headers':'*','access-control-allow-methods':'*'}
GOOD="```js\nconst a=[1,2,3];\na.splice(1,1);\nconsole.log(a);\n```\n\n使った部品：Array.splice\n注意：配列が直接変わります。"
BAD="```js\nconst a = [1,2,\n```\n使った部品：なし"
def handle(route):
    r=route.request
    if r.method=='OPTIONS': return route.fulfill(status=204,headers=CORS)
    pr=r.post_data_json['prompt']; prompts.append(pr)
    if '必要な部品だけを' in pr: txt=json.dumps({'use':['js:Array.splice','js:Array.push'],'missing':['再描画の方法']},ensure_ascii=False)
    else: txt={'gen':GOOD,'bad':BAD}[mode['v']]
    route.fulfill(status=200,content_type='application/json',headers=CORS,body=json.dumps({'text':txt}))
T=1792747635567
def E(id,term,lang,kind,summary,**k):
    d={'id':id,'term':term,'lang':lang,'kind':kind,'summary':summary,'form':'','parts':[],'example':'','mistakes':[],'related':[],'tags':[],'confidence':'high','verified':False,'updatedAt':T,'sources':[]}
    d.update(k); return d
ents=[
 E('js:Array.splice','Array.splice（途中を消す・差し替える・差し込む）','js','api','配列の途中を消す・差し替える。元の配列を直接変える。',form='配列.splice(開始位置, 消す個数)',example='const a=[1,2,3];\na.splice(1,1);',mistakes=['slice と取り違える'],tags=['JavaScript','配列'],verified=True),
 E('js:Array.push','Array.push（配列の後ろに足す）','js','api','配列の後ろに値を足す。',form='配列.push(値)',example='a.push(4);',tags=['JavaScript','配列'],verified=True),
 E('js:Array.map','Array.map（全部を変えて新しい配列に）','js','api','配列の各要素を変換して新しい配列を作る。',form='配列.map(x => 変換)',example='[1,2].map(x => x*2)',tags=['JavaScript','配列'],verified=True),
 E('ps:Unblock-File','Unblock-File','ps','command','ネットから落としたファイルのブロックの印を外す。',form='Unblock-File -Path パス',example='Get-ChildItem . | Unblock-File',tags=['ダウンロード']),
 E('css:flexbox','Flexbox（1方向に並べる）','css','syntax','横または縦に並べる。',form='display:flex;',example='.row{display:flex;gap:8px}',tags=['CSS']),
 E('html:dialog','dialog（確認画面）','html','syntax','モーダルを出す。',form='<dialog>…</dialog>',example='<dialog id="d">x</dialog>',tags=['HTML']),
]
PACK={'app':'dict-pack','version':1,'builtAt':1,'entries':ents}
open(os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'pack3.json'),'w',encoding='utf-8').write(json.dumps(PACK,ensure_ascii=False))
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2); pg=ctx.new_page()
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',lambda d:d.accept())
    pg.route('https://mock.example.test/ai',handle)
    pg.goto('http://127.0.0.1:8614/index.html'); pg.wait_for_selector('#packBar'); pg.wait_for_timeout(400)
    pg.evaluate("lsSet('kd_endpoint','https://mock.example.test');lsSet('kd_token','tok_abc123')")
    pg.evaluate("renderSettings();openSheet('shSet')"); pg.set_input_files('#filePack',os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'pack3.json')); pg.wait_for_timeout(700)
    pg.evaluate("closeSheet('shSet')")
    pg.evaluate("writeEntries([{id:'m1',term:'配列の削除',oneLine:'',tags:['JavaScript'],related:[],note:'',kind:'term',understanding:'unknown',checkedAt:null,createdAt:1,updatedAt:1,conclusion:'自分は splice を使うと決めた'}])"); pg.wait_for_timeout(300)
    check('一覧に「コードを作る」ボタン', 'コードを作る' in pg.inner_text('#packBar'))
    pg.click('[data-codeopen]'); pg.wait_for_timeout(400)
    check('シートが開く・ルールが入っている', pg.evaluate("document.getElementById('shCode').classList.contains('open')") and '単一ファイルHTML' in pg.input_value('#cdRules'))
    # 部品を絞る（AIなし）
    n0=len(prompts)
    pg.fill('#cdTask','配列の途中の1件を消して、結果を表示する'); pg.click('#cdFind'); pg.wait_for_timeout(400)
    check('AIを使わずに絞り込む', len(prompts)==n0)
    cand=pg.inner_text('#cdCand')
    check('関係する部品が候補に出る', 'Array.splice' in cand and 'Array.push' in cand, cand[:200])
    check('関係ない言語(PowerShell等)は出ない', 'Unblock-File' not in cand)
    check('自分の辞書の項目も候補に出る', '配列の削除' in cand and '自分の辞書' in cand)
    check('言語をおまかせで判断した', 'JavaScript' in pg.inner_text('#cdMeta'), pg.inner_text('#cdMeta'))
    pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'30-code-cand.png'))
    # チェックを外す
    pg.uncheck('input[data-cdc="pack:js:Array.push"]'); pg.wait_for_timeout(200)
    check('チェックを外せる（件数が変わる）', pg.evaluate("cdSt.cands.filter(c=>c.on).length")==pg.evaluate("cdSt.cands.filter(c=>c.on).length") and not pg.evaluate("cdSt.cands.find(c=>c.id==='js:Array.push').on"))
    # 足す
    pg.evaluate("cdSt.cands=cdSt.cands.filter(c=>c.id!=='js:Array.map');cdDrawCand()")
    pg.fill('#cdAddQ','map'); pg.wait_for_timeout(300)
    pg.click('#cdAddList [data-cdadd]'); pg.wait_for_timeout(300)
    check('探して足せる', pg.evaluate("cdSt.cands.some(c=>c.id==='js:Array.map'&&c.on)"))
    # AIに絞ってもらう
    pg.click('#cdNarrow'); pg.wait_for_timeout(800)
    check('AIに絞らせると、選ばれたものだけが✓になる', pg.evaluate("cdSt.cands.filter(c=>c.t==='pack'&&c.on).map(c=>c.id).sort().join()")=='js:Array.push,js:Array.splice', pg.evaluate("cdSt.cands.filter(c=>c.on).map(c=>c.id)"))
    check('足りない部品を教えてくれる', '再描画の方法' in pg.inner_text('#cdMeta'))
    check('AIには候補の一覧だけを送る（例の全文は送らない）', 'Array.splice' in prompts[-1] and 'const a=[1,2,3]' not in prompts[-1])
    # コード生成
    pg.click('#cdGen'); pg.wait_for_timeout(900)
    pr=prompts[-1]
    check('部品の形・例・間違いがプロンプトに入る', '配列.splice(開始位置, 消す個数)' in pr and 'slice と取り違える' in pr)
    check('私のルールが入る', '単一ファイルHTML' in pr and 'else を置かない' in pr)
    check('自分の判断が入り、パックより優先と書く', '自分は splice を使うと決めた' in pr and 'パックより優先' in pr)
    out=pg.inner_text('#cdOut')
    check('コードが表示される', 'a.splice(1,1)' in out and 'コードをコピー' in out)
    check('JSの構文を検査する', '構文は読めました' in out)
    ctx.grant_permissions(['clipboard-read','clipboard-write'],origin='http://127.0.0.1:8614')
    pg.click('[data-cdo="copy"]'); pg.wait_for_timeout(300)
    check('コードだけをコピーできる', pg.evaluate("navigator.clipboard.readText()").startswith('const a=[1,2,3];') and '使った部品' not in pg.evaluate("navigator.clipboard.readText()"))
    pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'31-code-out.png'))
    # 構文エラーの検出
    mode['v']='bad'; pg.click('#cdGen'); pg.wait_for_timeout(900)
    check('構文エラーを知らせる', '構文エラー' in pg.inner_text('#cdOut'))
    mode['v']='gen'; pg.click('#cdGen'); pg.wait_for_timeout(900)
    # 結果つきで辞書へ
    pg.click('[data-cdo="ng"]'); pg.fill('#cdMemo','表示は動いたが再描画はまだ'); pg.click('[data-cdo="save"]'); pg.wait_for_timeout(900)
    e=pg.evaluate("findEntryByTerm('配列の途中の1件を消して、結果を表示する')")
    check('辞書に「手順」として残る', e and e['kind']=='howto')
    q=pg.evaluate("qasByEntry.get(findEntryByTerm('配列の途中の1件を消して、結果を表示する').id)[0]")
    check('試した結果が自分の判断に入る', '動かなかった' in q['judgment'] and '再描画' in q['judgment'], q['judgment'])
    check('質問=作りたいこと、回答=コード', q['question'].startswith('配列の途中') and 'splice' in q['answer'])
    check('使った部品がタグ・関連になる', 'コード' in e['tags'] and any('Array.splice' in r for r in e['related']), e)
    # AIなしの下書き
    pg.evaluate("closeSheet('shEntry');openCode()"); pg.wait_for_timeout(300)
    n1=len(prompts); pg.click('#cdDraft'); pg.wait_for_timeout(300)
    check('AIなしで下書きできる', len(prompts)==n1 and 'a.splice(1,1)' in pg.inner_text('#cdOut') and '下書き' in pg.inner_text('#cdOut'))
    # 秘密行は送らない
    pg.fill('#cdTask','APIを呼ぶ\napi_key = sk-abcdefghijklmnopqrstuvwxyz123456\n配列を作る'); pg.click('#cdFind'); pg.wait_for_timeout(300); pg.click('#cdGen'); pg.wait_for_timeout(900)
    check('秘密らしい行はAIに送らない', 'sk-abcdef' not in prompts[-1] and '送っていません' in pg.inner_text('#cdMeta'))
    # ルールを書き換えると保存される
    pg.evaluate("document.querySelector('#shCode details').open=true"); pg.fill('#cdRules','・テスト用ルール'); pg.reload(); pg.wait_for_selector('#packBar'); pg.evaluate("openCode()")
    check('ルールを書き換えて覚える', pg.input_value('#cdRules')=='・テスト用ルール')
    # パックなし
    pg.evaluate("closeSheet('shCode');pack=[];pkRebuild();renderList()"); pg.wait_for_timeout(200)
    pg.evaluate("openCode()"); pg.fill('#cdTask','配列の削除'); pg.click('#cdFind'); pg.wait_for_timeout(300)
    check('パックが無くても自分の辞書から絞れる', '配列の削除' in pg.inner_text('#cdCand'))
    b.close()
print('結果: OK',ok,'/ NG',ng); print('JSエラー:',errs or 'なし')
