import os
import json, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright
ROOT=os.environ.get('KD_ROOT','.')
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
socketserver.TCPServer.allow_reuse_address=True
srv=socketserver.TCPServer(('127.0.0.1',8501),functools.partial(Q,directory=ROOT))
threading.Thread(target=srv.serve_forever,daemon=True).start()
ok=ng=0; errs=[]
def check(n,c,x=''):
    global ok,ng
    if c: ok+=1; print('  OK ',n)
    else: ng+=1; print('  NG ',n,x)
prompts=[]
CORS={'access-control-allow-origin':'*','access-control-allow-headers':'*','access-control-allow-methods':'*'}
def reply(p):
    if '辞書だけを根拠' in p or '個人辞書だけを根拠' in p: return '認証は [[JWT]] を使うと決めました（自分の判断）。'
    if '質問を1つ作って' in p: return '{"question":"JWTとは何ですか？"}'
    if '私の答えを採点' in p: return '{"verdict":"partial","feedback":"署名の点が足りません","model":"署名つきのトークン"}'
    if 'つながりを提案' in p: return '{"links":[{"term":"Cookie","reason":"保存先"},{"term":"存在しない語","reason":"x"}],"gaps":[{"topic":"リフレッシュトークン","reason":"期限切れ対策"}]}'
    if '辞書の項目として整理' in p: return '{"term":"X","oneLine":"AIが付けた一言","tags":["認証","AI付与"],"related":["Cookie"],"kind":"idea"}'
    return 'その他'
def handle(route):
    r=route.request
    if r.method=='OPTIONS': return route.fulfill(status=204,headers=CORS)
    p=r.post_data_json['prompt']; prompts.append(p)
    route.fulfill(status=200,content_type='application/json',headers=CORS,body=json.dumps({'text':reply(p)}))
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2).new_page()
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',lambda d:d.accept())
    pg.route('https://mock.example.test/ai',handle)
    pg.goto('http://127.0.0.1:8501/index.html'); pg.wait_for_selector('#list')
    pg.evaluate("lsSet('kd_endpoint','https://mock.example.test');lsSet('kd_token','tok_abc123')")
    pg.evaluate("""(async()=>{const n=Date.now();
      await writeEntries([{id:'e1',term:'JWT',oneLine:'署名つきトークン',tags:['認証'],related:['Cookie'],note:'[[Cookie]] と組み合わせる。[[リフレッシュ]] は未整理',kind:'term',understanding:'unknown',checkedAt:null,createdAt:n,updatedAt:n},
      {id:'e2',term:'Cookie',oneLine:'ブラウザに保存する小さなデータ',tags:['認証','Web'],related:[],note:'',kind:'term',understanding:'unknown',checkedAt:null,createdAt:n,updatedAt:n},
      {id:'e3',term:'お香の配合',oneLine:'',tags:[],related:[],note:'',kind:'term',understanding:'known',checkedAt:null,createdAt:n,updatedAt:n}]);
      await writeQAs([{id:'q1',entryId:'e1',question:'認証はどうする？',answer:'JWTを使う。署名で改ざんを防ぐ。',judgment:'今回はJWTにする',sourceType:'gemini',sourceUrl:'',createdAt:n,updatedAt:n}]);})()""")
    # 取得
    r=pg.evaluate("retrieve('認証まわりで、自分はこれまで何を決めた？',6).map(e=>e.term)")
    check('関連項目を見つける', 'JWT' in r and 'お香の配合' not in r, r)
    r2=pg.evaluate("retrieve('今日の夕飯は何にする',6).map(e=>e.term)")
    check('無関係な質問では何も拾わない', r2==[], r2)
    # 辞書に聞く
    pg.click('#btnBrain'); pg.wait_for_selector('#shBrain.open'); pg.wait_for_timeout(300)
    pg.fill('#bQ','全然関係ない質問です'); pg.click('#btnBrainAsk'); pg.wait_for_timeout(400)
    check('関係なければ答えは聞かない（言い換えの探索だけ）', all('辞書だけを根拠' not in x for x in prompts) and '見つかりませんでした' in pg.inner_text('#bOut'))
    pg.fill('#bQ','認証まわりで、自分はこれまで何を決めた？'); pg.click('#btnBrainAsk'); pg.wait_for_selector('#bOut .br-card',timeout=8000)
    check('答えが出る', 'JWT' in pg.inner_text('#bOut'))
    pp=prompts[-1]
    check('辞書の材料と判断が送られる', '今回はJWTにする' in pp and '■[[JWT]]' in pp and 'お香の配合' not in pp)
    check('回答の[[JWT]]がリンクになる', pg.locator('#bOut .wl[data-wl="JWT"]').count()==1)
    check('根拠の項目が並ぶ', pg.locator('#bOut .br-src [data-open]').count()>=2)
    pg.click('#bOut .wl[data-wl="JWT"]'); pg.wait_for_timeout(400)
    check('リンクから項目が開く', pg.locator('#shEntry.open').count()==1)
    pg.click('#enClose'); pg.wait_for_timeout(300)
    pg.click('#bOut [data-br="save"]'); pg.wait_for_timeout(600)
    check('答えを項目として残せる', pg.evaluate("entries.some(e=>e.kind==='idea'&&e.term.startsWith('認証まわり'))"))
    pg.click('#enClose'); pg.wait_for_timeout(300)
    # 知識の穴
    pg.evaluate("drawGaps()"); pg.wait_for_timeout(200)
    check('穴：項目のない言葉', pg.locator('#gapBox .wl.unres[data-wl="リフレッシュ"]').count()==1, pg.inner_text('#gapBox'))
    check('穴：未理解なのに参照される', 'Cookie' in pg.inner_text('#gapBox'))
    check('穴：孤立項目', 'お香の配合' in pg.inner_text('#gapBox'))
    # 復習
    pg.click('#btnReview'); pg.wait_for_selector('#rvA',timeout=8000)
    check('問題が出る', 'JWTとは何ですか' in pg.inner_text('#rvBox'))
    pg.fill('#rvA','トークン'); pg.click('#btnGrade'); pg.wait_for_selector('.vd-partial',timeout=8000)
    check('採点が出る', '署名の点' in pg.inner_text('#rvBox'))
    check('採点の材料に自分の答えが入る', 'トークン' in prompts[-1] and 'JWTとは何ですか' in prompts[-1])
    pg.click('[data-rvund="learning"]'); pg.wait_for_timeout(1500)
    check('理解度が更新される', pg.evaluate("entryById.get('e1').understanding")=='learning' and pg.evaluate("entryById.get('e1').checkedAt")>0)
    check('次の問題が出る', pg.locator('#rvA').count()==1)
    pg.click('#brClose'); pg.wait_for_timeout(300)
    # AIでつながりを探す
    pg.evaluate("openEntry('e1')"); pg.wait_for_timeout(300)
    pg.click('[data-aiconn="e1"]'); pg.wait_for_selector('#enAiOut .cand',timeout=8000)
    check('提案が出る（存在しない語は除く）', 'Cookie' in pg.inner_text('#enAiOut') and '存在しない語' not in pg.inner_text('#enAiOut') and 'リフレッシュトークン' in pg.inner_text('#enAiOut'))
    pg.click('#enAiOut [data-cn="gap"]'); pg.wait_for_timeout(500)
    check('足りない知識から項目が作れる', pg.evaluate("!!findEntryByTerm('リフレッシュトークン')"))
    pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'16-aiconn.png'))
    pg.click('#enClose'); pg.wait_for_timeout(300)
    # 自動整理
    n0=len(prompts)
    pg.click('#btnSettings'); pg.wait_for_timeout(300); pg.check('#sAutoOrg'); pg.click('#btnSaveOrg'); pg.click('#stClose'); pg.wait_for_timeout(300)
    pg.click('#btnAdd'); pg.wait_for_selector('#shQA.open'); pg.fill('#qQuestion','手順について'); pg.fill('#qAnswer','まずAをして次にBをする。これが手順です。'); pg.fill('#qTerm','新しい手順'); pg.click('#qaSave'); pg.wait_for_timeout(1500)
    e=pg.evaluate("findEntryByTerm('新しい手順')")
    check('保存時に自動整理（空欄を埋める）', e and e['oneLine']=='AIが付けた一言' and e['kind']=='idea' and 'AI付与' in e['tags'], e)
    check('見出し語は変えない', e and e['term']=='新しい手順')
    n1=len(prompts)
    pg.click('#btnSettings'); pg.wait_for_timeout(300); pg.uncheck('#sAutoOrg'); pg.click('#btnSaveOrg'); pg.click('#stClose'); pg.wait_for_timeout(300)
    pg.click('#btnAdd'); pg.wait_for_selector('#shQA.open'); pg.fill('#qQuestion','別の質問'); pg.fill('#qAnswer','別の回答がここにあります。長めにします。'); pg.fill('#qTerm','オフ確認'); pg.click('#qaSave'); pg.wait_for_timeout(1000)
    check('オフなら自動整理しない', len(prompts)==n1)
    pg.evaluate("openBrain()"); pg.wait_for_timeout(400); pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'17-brain.png'))
    b.close()
print('結果: OK',ok,'/ NG',ng); print('JSエラー:',errs or 'なし')
