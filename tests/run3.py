import os
import json, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright
ROOT=os.environ.get('KD_ROOT','.')
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
socketserver.TCPServer.allow_reuse_address=True
srv=socketserver.TCPServer(('127.0.0.1',8441),functools.partial(Q,directory=ROOT))
threading.Thread(target=srv.serve_forever,daemon=True).start()
URL='http://127.0.0.1:8441/index.html'
ok=ng=0; errs=[]
def check(n,c,x=''):
    global ok,ng
    if c: ok+=1; print('  OK ',n)
    else: ng+=1; print('  NG ',n,x)
store={'data':None,'puts':0,'auth':[]}
CORS={'access-control-allow-origin':'*','access-control-allow-headers':'*','access-control-allow-methods':'*'}
def handle(route):
    r=route.request
    if r.method=='OPTIONS': return route.fulfill(status=204,headers=CORS)
    store['auth'].append(r.headers.get('authorization'))
    if r.headers.get('authorization')!='Bearer tok_abc123': return route.fulfill(status=401,headers=CORS,body='no')
    if r.method=='PUT': store['data']=r.post_data_json['data']; store['puts']+=1; return route.fulfill(status=200,headers=CORS,body='{}')
    if store['data'] is None: return route.fulfill(status=404,headers=CORS,body='')
    return route.fulfill(status=200,content_type='application/json',headers=CORS,body=json.dumps({'data':store['data']}))
with sync_playwright() as p:
    b=p.chromium.launch()
    def mk():
        c=b.new_context(viewport={'width':390,'height':844}); pg=c.new_page()
        pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',lambda d:d.accept())
        pg.route('https://mock.example.test/sync/knowledge-dictionary',handle)
        pg.goto(URL); pg.wait_for_selector('#list')
        pg.evaluate("lsSet('kd_endpoint','https://mock.example.test');lsSet('kd_token','tok_abc123')")
        return pg
    A=mk(); B=mk()
    mkE="(async()=>{const n=Date.now();await writeEntries([{id:'%s',term:'%s',oneLine:'',tags:[],related:[],note:'%s',understanding:'unknown',checkedAt:null,createdAt:n,updatedAt:n}]);})()"
    A.evaluate(mkE%('a1','JWT','メモA'))
    A.evaluate("writeQAs([{id:'qa1',entryId:'a1',question:'Q',answer:'A',judgment:'',sourceType:'other',sourceUrl:'',createdAt:Date.now(),updatedAt:Date.now()}])")
    check('未同期の間は送られない', store['puts']==0)
    A.evaluate("kdSync(true)"); A.wait_for_timeout(800)
    check('A→クラウド（初回PUT）', store['puts']==1 and len(store['data']['entries'])==1 and len(store['data']['qas'])==1)
    B.evaluate("kdSync(true)"); B.wait_for_timeout(800)
    check('B が受信', B.evaluate("entries.length")==1 and B.evaluate("qas.length")==1)
    check('B の画面に出る', 'JWT' in B.inner_text('#list'))
    check('自動同期がオンになる', B.evaluate("lsGet('kd_sync')")=='1')
    # B で編集→自動同期→A
    B.evaluate("writeEntries([Object.assign({},entries[0],{note:'メモB更新',updatedAt:Date.now()+5})])"); B.wait_for_timeout(3500)
    A.evaluate("kdSync(false)"); A.wait_for_timeout(800)
    check('編集が反映（自動同期）', A.evaluate("entries[0].note")=='メモB更新')
    # 同じ見出し語を別々に作る
    A.evaluate(mkE%('x1','Cookie','A側')); B.evaluate(mkE%('y1','cookie','B側'))
    A.evaluate("kdSync(false)"); A.wait_for_timeout(800); B.evaluate("kdSync(false)"); B.wait_for_timeout(800); A.evaluate("kdSync(false)"); A.wait_for_timeout(800)
    na=A.evaluate("entries.filter(e=>norm(e.term)==='cookie').length"); nb=B.evaluate("entries.filter(e=>norm(e.term)==='cookie').length")
    check('同じ見出し語は1つにまとまる', na==1 and nb==1, (na,nb))
    check('メモが両方残る', all(t in A.evaluate("entries.find(e=>norm(e.term)==='cookie').note") for t in ['A側','B側']))
    # 削除の反映
    A.evaluate("(async()=>{qas=qas.filter(q=>q.id!=='qa1');rebuild();addTomb(['qa1']);await idbDel('qas',['qa1']);})()"); A.wait_for_timeout(3500)
    B.evaluate("kdSync(false)"); B.wait_for_timeout(800)
    check('削除が相手に反映', B.evaluate("qas.some(q=>q.id==='qa1')")==False)
    B.evaluate("kdSync(false)"); B.wait_for_timeout(800)
    check('削除したものが復活しない', A.evaluate("qas.some(q=>q.id==='qa1')")==False and B.evaluate("qas.some(q=>q.id==='qa1')")==False)
    # 空の端末が上書きしない
    C=mk(); C.evaluate("kdSync(false)"); C.wait_for_timeout(800)
    check('空の端末が受信してもクラウドは減らない', len(store['data']['entries'])>=2 and C.evaluate("entries.length")>=2)
    # 保存した内容がDBにも入る
    check('IndexedDBに入る', C.evaluate("idbAll('entries').then(a=>a.length)")>=2)
    # トークン違い
    D=mk(); D.evaluate("lsSet('kd_token','bad')"); D.evaluate("kdSync(true)"); D.wait_for_timeout(600)
    check('トークン違いで失敗表示', 'トークン' in D.inner_text('#syncStat') or D.evaluate("syncMsg").find('トークン')>=0, D.evaluate("syncMsg"))
    check('失敗してもデータは壊れない', D.evaluate("entries.length")==0)
    # 設定画面
    A.click('#btnSettings'); A.wait_for_timeout(300)
    check('設定に同期欄', '自動同期：オン' in A.inner_text('#syncStat'), A.inner_text('#syncStat'))
    A.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'13-sync.png'))
    b.close()
print('結果: OK',ok,'/ NG',ng); print('JSエラー:',errs or 'なし')
