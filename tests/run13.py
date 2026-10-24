import os
import json, threading, http.server, socketserver, functools, time
from playwright.sync_api import sync_playwright
ROOT=os.environ.get('KD_ROOT','.')
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
socketserver.TCPServer.allow_reuse_address=True
srv=socketserver.TCPServer(('127.0.0.1',8613),functools.partial(Q,directory=ROOT))
threading.Thread(target=srv.serve_forever,daemon=True).start()
ok=ng=0; errs=[]
def check(n,c,x=''):
    global ok,ng
    if c: ok+=1; print('  OK ',n)
    else: ng+=1; print('  NG ',n,x)
T=1792747635567
def E(id,term,lang,kind,summary,**k):
    d={'id':id,'term':term,'lang':lang,'kind':kind,'summary':summary,'form':'','parts':[],'example':'','mistakes':[],'related':[],'tags':[],'confidence':'high','verified':False,'updatedAt':T,'sources':[]}
    d.update(k); return d
entries=[
 E('js:Array.splice','Array.splice（途中を消す・差し替える・差し込む）','js','api','配列の途中を変える。元の配列を直接変え、消した要素を返す。',form='配列.splice(開始位置, 消す個数, 入れる値)',parts=[['開始位置','0から数える'],['消す個数','0なら差し込むだけ']],example='const a=[1,2,3];\na.splice(1,1);',mistakes=['slice と取り違える','ループの途中で splice すると要素を飛ばす'],related=['js:Array.slice','js:nothing-here'],tags=['JavaScript','配列','破壊的'],verified=True),
 E('js:Array.slice','Array.slice（一部を取り出す）','js','api','元を変えずに、一部を新しい配列として取り出す。',form='配列.slice(開始, 終わり)',tags=['JavaScript','配列','非破壊'],verified=True,related=['js:Array.splice']),
 E('js:Array.push','Array.push / pop（配列の端に足す・取る）','js','api','配列の後ろに足す／取る。',tags=['JavaScript','配列'],verified=True),
 E('ps:Unblock-File','Unblock-File','ps','command','ネットから落としたファイルに付くブロックの印を外す。',form='Unblock-File -Path パス',example='Get-ChildItem "$env:USERPROFILE\\Downloads" -Recurse -File | Unblock-File',mistakes=['全部に使わない'],tags=['ダウンロード','解凍'],confidence='low'),
 E('ai:llm','LLM（大規模言語モデル）','ai','concept','大量の文章から学習し、次に来る語を予測して文章を作るモデル。',tags=['AI','基礎'],related=['ai:rag']),
 E('ai:rag','RAG（検索して資料を渡して答えさせる）','ai','concept','質問に関係する資料を先に検索し、その内容を AI に渡して答えさせる方法。',tags=['AI','設計','変わりやすい']),
 E('css:flexbox','Flexbox（1方向に並べる）','css','syntax','横または縦に並べて、余白・間隔・折り返しを決める。',form='display: flex;',tags=['CSS','レイアウト']),
]
PACK={'app':'dict-pack','version':1,'builtAt':1792749790390,'entries':entries+[{'id':'bad'},{'term':'x'}]}
open(os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'pack.json'),'w',encoding='utf-8').write(json.dumps(PACK,ensure_ascii=False))
prompts=[]
CORS={'access-control-allow-origin':'*','access-control-allow-headers':'*','access-control-allow-methods':'*'}
def handle(route):
    r=route.request
    if r.method=='OPTIONS': return route.fulfill(status=204,headers=CORS)
    prompts.append(r.post_data_json['prompt'])
    route.fulfill(status=200,content_type='application/json',headers=CORS,body=json.dumps({'text':'答えです [[JWT]]'}))
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2); pg=ctx.new_page()
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',lambda d:d.accept())
    pg.route('https://mock.example.test/ai',handle)
    # --- 旧DB(v1)からの更新で、データが消えない
    pg.goto('http://127.0.0.1:8613/sw.js')
    pg.evaluate("""()=>new Promise((res,rej)=>{const r=indexedDB.open('knowledge-dictionary',1);r.onupgradeneeded=()=>{const d=r.result;d.createObjectStore('entries',{keyPath:'id'});d.createObjectStore('qas',{keyPath:'id'}).createIndex('entryId','entryId')};r.onsuccess=()=>{const t=r.result.transaction('entries','readwrite');t.objectStore('entries').put({id:'old1',term:'JWT',oneLine:'旧データ',tags:['認証'],related:[],note:'',kind:'term',understanding:'unknown',checkedAt:null,createdAt:1,updatedAt:1});t.oncomplete=()=>{r.result.close();res()}}})""")
    pg.goto('http://127.0.0.1:8613/index.html'); pg.wait_for_selector('#list'); pg.wait_for_timeout(500)
    check('旧版(v1)のデータが残ったまま更新される', pg.evaluate("entries.length")==1 and pg.evaluate("entries[0].oneLine")=='旧データ')
    check('パック未導入のときは、パックの案内を出さない', '辞書パック' not in pg.inner_text('#packBar') and 'コードを作る' in pg.inner_text('#packBar'))
    pg.evaluate("lsSet('kd_endpoint','https://mock.example.test');lsSet('kd_token','tok_abc123')")
    # --- 読み込み
    pg.evaluate("renderSettings();openSheet('shSet')"); pg.wait_for_timeout(200)
    check('設定に未導入の案内', '入っていません' in pg.inner_text('#pkStat'))
    pg.set_input_files('#filePack',os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'pack.json')); pg.wait_for_timeout(800)
    check('7件が入り、壊れた2件は飛ばす', pg.evaluate("pack.length")==7, pg.evaluate("pack.length"))
    check('設定に件数・確認済み・言語別', '7' in pg.inner_text('#pkStat') and '確認済み 3' in pg.inner_text('#pkStat') and 'JavaScript 3' in pg.inner_text('#pkStat'), pg.inner_text('#pkStat'))
    # 同じファイルを再度 → 変更なし
    pg.set_input_files('#filePack',os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'pack.json')); pg.wait_for_timeout(600)
    check('同じファイルの再読込で重複しない', pg.evaluate("pack.length")==7)
    # 新しい updatedAt が勝つ／古いのは負ける
    P2=json.loads(json.dumps(PACK)); P2['entries'][0]['summary']='新しい説明'; P2['entries'][0]['updatedAt']=T+1000
    P2['entries'][1]['summary']='古い説明'; P2['entries'][1]['updatedAt']=T-1000
    open(os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'pack2.json'),'w',encoding='utf-8').write(json.dumps(P2,ensure_ascii=False))
    pg.set_input_files('#filePack',os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'pack2.json')); pg.wait_for_timeout(600)
    check('新しい項目は入れ替わる', pg.evaluate("packById.get('js:Array.splice').summary")=='新しい説明')
    check('古い項目では上書きしない', 'から' not in pg.evaluate("packById.get('js:Array.slice').summary") or pg.evaluate("packById.get('js:Array.slice').summary")!='古い説明')
    open(os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'notpack.json'),'w').write('{"app":"x"}')
    pg.set_input_files('#filePack',os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'notpack.json')); pg.wait_for_timeout(300)
    check('違うファイルは受け付けない', pg.evaluate("pack.length")==7)
    # 再読込しても残る
    pg.reload(); pg.wait_for_selector('#list'); pg.wait_for_timeout(500)
    check('再起動しても残る', pg.evaluate("pack.length")==7)
    check('一覧に案内バー', '辞書パック' in pg.inner_text('#packBar') and '7' in pg.inner_text('#packBar'))
    # --- 引く
    pg.evaluate("openPack('')"); pg.wait_for_timeout(400)
    check('引く画面：言語チップ', 'JavaScript 3' in pg.inner_text('#pkLang'))
    pg.fill('#pxQ','splice'); pg.wait_for_timeout(300)
    t=pg.inner_text('#pxList'); check('英語名で引ける', 'Array.splice' in t and 'Array.slice' not in t, t[:100])
    pg.fill('#pxQ','配列 差し替え'); pg.wait_for_timeout(300)
    t=pg.inner_text('#pxList'); check('日本語の説明文でも当たる（AND）', 'Array.splice' in t.split('\n')[0] or 'Array.splice' in t[:60], t[:120])
    pg.fill('#pxQ','powershell'); pg.wait_for_timeout(300)
    check('言語名で絞れる', 'Unblock-File' in pg.inner_text('#pxList') and 'splice' not in pg.inner_text('#pxList'))
    pg.fill('#pxQ','配列 ブロック'); pg.wait_for_timeout(300)
    t=pg.inner_text('#pxList'); check('一部だけ当たるものも、ゆるく出す', '一部だけ一致' in pg.inner_text('#pkCount') and 'Unblock-File' in t, pg.inner_text('#pkCount'))
    pg.fill('#pxQ',''); pg.click('#pkFlag [data-fl="low"]'); pg.wait_for_timeout(300)
    check('⚠要確認で絞れる', 'Unblock-File' in pg.inner_text('#pxList') and 'splice' not in pg.inner_text('#pxList'))
    pg.click('#pkFlag [data-fl="ver"]'); pg.wait_for_timeout(300)
    check('✅確認済みで絞れる', 'splice' in pg.inner_text('#pxList') and 'Unblock' not in pg.inner_text('#pxList'))
    pg.click('#pkFlag [data-fl="vol"]'); pg.wait_for_timeout(300)
    check('⏳変わりやすいで絞れる', 'RAG' in pg.inner_text('#pxList') and 'splice' not in pg.inner_text('#pxList'))
    pg.click('#pkFlag [data-fl=""]'); pg.click('#pkLang [data-lg="css"]'); pg.wait_for_timeout(300)
    check('言語チップで絞れる', 'Flexbox' in pg.inner_text('#pxList') and 'splice' not in pg.inner_text('#pxList'))
    pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'26-pack-find.png'))
    # --- 項目の画面
    pg.click('#pkLang [data-lg=""]'); pg.fill('#pxQ','splice'); pg.wait_for_timeout(200); pg.click('#pxList [data-pk]'); pg.wait_for_timeout(500)
    d=pg.inner_text('#pdBody')
    check('形・部品・例・よくある間違いの順', all(x in d for x in ['形','部品の意味','例','よくある間違い']) and d.index('形')<d.index('部品の意味')<d.index('例')<d.index('よくある間違い'))
    check('確認済みの印', '確認済み' in d)
    check('存在しない関連はリンクにしない', pg.locator('#pdBody [data-pk="js:nothing-here"]').count()==0 and 'nothing-here' in d)
    check('存在する関連はリンク', pg.locator('#pdBody [data-pk="js:Array.slice"]').count()==1)
    pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'27-pack-entry.png'))
    pg.click('#pdBody [data-pk="js:Array.slice"]'); pg.wait_for_timeout(400)
    check('関連へ移れて「戻る」が出る', 'Array.slice' in pg.inner_text('#pdBody') and pg.evaluate("document.getElementById('pdBack').style.visibility")=='visible')
    pg.click('#pdBack'); pg.wait_for_timeout(300)
    check('戻れる', 'Array.splice' in pg.inner_text('#pdBody'))
    # コピー
    ctx.grant_permissions(['clipboard-read','clipboard-write'],origin='http://127.0.0.1:8613')
    pg.click('[data-pkcopy="example"]'); pg.wait_for_timeout(300)
    check('例をコピーできる', 'a.splice(1,1)' in pg.evaluate("navigator.clipboard.readText()"))
    # 要確認バナー
    pg.evaluate("openPackEntry('ps:Unblock-File')"); pg.wait_for_timeout(300)
    check('低確信は警告が出る', '確信が低い' in pg.inner_text('#pdBody'))
    pg.evaluate("openPackEntry('ai:rag')"); pg.wait_for_timeout(300)
    check('変わりやすいは警告が出る', '変わりやすい' in pg.inner_text('#pdBody'))
    # 取り込み
    pg.evaluate("openPackEntry('js:Array.splice')"); pg.wait_for_timeout(300)
    pg.click('[data-pkadopt]'); pg.wait_for_timeout(800)
    e=pg.evaluate("findEntryByTerm('Array.splice')")
    check('自分の辞書に取り込める（Q&Aつき）', e and pg.evaluate("(qasByEntry.get(findEntryByTerm('Array.splice').id)||[]).length")==1 and '【形】' in pg.evaluate("qasByEntry.get(findEntryByTerm('Array.splice').id)[0].answer"))
    pg.evaluate("openPackEntry('js:Array.splice')"); pg.click('[data-pkadopt]'); pg.wait_for_timeout(500)
    check('二重に取り込まない', pg.evaluate("(qasByEntry.get(findEntryByTerm('Array.splice').id)||[]).length")==1)
    # --- 一覧との統合
    pg.evaluate("closeSheet('shEntry');closeSheet('shPackEntry');closeSheet('shPack');closeSheet('shSet')")
    pg.fill('#q','配列'); pg.evaluate("searchQuery='配列';renderList()"); pg.wait_for_timeout(300)
    check('メイン検索の下にパックの結果も出る', '辞書パックでも見つかりました' in pg.inner_text('#packBox') and 'Array.slice' in pg.inner_text('#packBox'), pg.inner_text('#packBox')[:200])
    pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'28-main-pack.png'))
    pg.evaluate("searchQuery='';renderList()")
    # 自分の項目に、関連するパック
    pg.evaluate("writeEntries([{id:'my2',term:'Array.slice',oneLine:'',tags:[],related:[],note:'',kind:'term',understanding:'unknown',checkedAt:null,createdAt:1,updatedAt:1}])"); pg.wait_for_timeout(300)
    pg.evaluate("openEntry('my2')"); pg.wait_for_timeout(300)
    check('自分の項目の画面に、関係するパックが出る', '辞書パックにも載っています' in pg.inner_text('#enBody') and 'slice' in pg.inner_text('#enBody'))
    pg.evaluate("closeSheet('shEntry')")
    # --- AI（辞書に聞く）にパックを渡す
    pg.evaluate("openBrain()"); pg.fill('#bQ','配列の途中を消して差し替えるには？'); pg.click('#btnBrainAsk'); pg.wait_for_timeout(1500)
    pr=prompts[-1] if prompts else ''
    check('AIにパックの材料が渡る', '辞書パックの材料' in pr and 'Array.splice' in pr, pr[-300:])
    check('パックより自分を優先する指示', '自分の項目を優先' in pr)
    check('根拠にパックの項目が出る', pg.locator('#bOut [data-pk]').count()>=1)
    # 秘密行は送らない（従来どおり）
    # --- 復習
    pg.evaluate("closeSheet('shBrain');openPack('')"); pg.wait_for_timeout(300)
    pg.click('#pkStudy'); pg.wait_for_timeout(300)
    check('復習：入れていないと案内', '復習に入れた項目がありません' in pg.inner_text('#pkStudyBox'))
    pg.evaluate("openPackEntry('js:Array.slice')"); pg.click('[data-pkstar]'); pg.wait_for_timeout(300)
    pg.evaluate("closeSheet('shPackEntry')"); pg.click('#pkStudy') if pg.evaluate("document.getElementById('pkStudy').dataset.m")=='find' else None
    pg.evaluate("document.getElementById('pkStudy').click()") if pg.evaluate("document.getElementById('pkStudy').dataset.m")=='study' else None
    pg.wait_for_timeout(300)
    if 'Array.slice' not in pg.inner_text('#pkStudyBox'): pg.click('#pkStudy'); pg.wait_for_timeout(300)
    check('⭐を付けた項目が出る（答えは伏せてある）', 'Array.slice' in pg.inner_text('#pkStudyBox') and '元を変えずに' not in pg.inner_text('#pkStudyBox'), pg.inner_text('#pkStudyBox')[:100])
    pg.click('[data-pkst="show"]'); pg.wait_for_timeout(200)
    check('答えを見ると形・説明が出る', '元を変えずに' in pg.inner_text('#pkStudyBox'))
    pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'29-pack-study.png'))
    pg.click('[data-pkst="ok"]'); pg.wait_for_timeout(300)
    pr_=json.loads(pg.evaluate("lsGet('kd_pk')"))['js:Array.slice']
    check('分かった：3日後に回る', abs((pr_['n']-time.time()*1000)-3*86400000)<60000 and pr_['s']==1, pr_)
    check('今日の分が終わる', '終わりました' in pg.inner_text('#pkStudyBox'))
    check('復習の数は、次の日まで出ない', pg.evaluate("pkDueIds().length")==0)
    # 忘れた→すぐ戻る（同じ回では出ない）
    pg.evaluate("lsSet('kd_pk','{}')"); pg.evaluate("pkS={id:'',shown:false,done:0,skip:new Set(),rand:false};pkStudyDraw()"); pg.wait_for_timeout(200)
    pg.click('[data-pkst="show"]'); pg.click('[data-pkst="ng"]'); pg.wait_for_timeout(200)
    check('忘れた：今すぐ再出題の対象になる', pg.evaluate("pkDueIds().length")==1)
    pg.click('[data-pkst="rand"]') if pg.locator('[data-pkst="rand"]').count() else pg.evaluate("pkS.rand=true;pkStudyDraw()")
    pg.wait_for_timeout(200)
    check('ランダムに1つ引ける', pg.locator('[data-pkst="show"]').count()==1)
    # --- 同期・書き出しにパックが混ざらない
    pg.evaluate("closeSheet('shPack')")
    with pg.expect_download() as dl: pg.evaluate("exportData()")
    txt=open(dl.value.path(),encoding='utf-8').read()
    check('バックアップにパックは入らない', 'Array.splice（途中' not in txt and '"entries"' in txt)
    # --- 消す
    pg.evaluate("renderSettings();openSheet('shSet')"); pg.click('#btnPackClear'); pg.wait_for_timeout(500)
    check('パックを消しても自分のデータは残る', pg.evaluate("pack.length")==0 and pg.evaluate("entries.length")>=2)
    check('消すと案内バーのパック表示も消える', '辞書パック' not in pg.inner_text('#packBar'))
    b.close()
print('結果: OK',ok,'/ NG',ng); print('JSエラー:',errs or 'なし')
