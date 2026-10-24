import os
import json, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright
ROOT=os.environ.get('KD_ROOT','.')
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
socketserver.TCPServer.allow_reuse_address=True
srv=socketserver.TCPServer(('127.0.0.1',8491),functools.partial(Q,directory=ROOT))
threading.Thread(target=srv.serve_forever,daemon=True).start()
store={'data':None}
CORS={'access-control-allow-origin':'*','access-control-allow-headers':'*','access-control-allow-methods':'*'}
def handle(route):
    r=route.request
    if r.method=='OPTIONS': return route.fulfill(status=204,headers=CORS)
    if r.method=='PUT': store['data']=r.post_data_json['data']; return route.fulfill(status=200,headers=CORS,body='{}')
    if store['data'] is None: return route.fulfill(status=404,headers=CORS,body='')
    return route.fulfill(status=200,content_type='application/json',headers=CORS,body=json.dumps({'data':store['data']}))
ok=ng=0
def check(n,c,x=''):
    global ok,ng
    if c: ok+=1; print('  OK ',n)
    else: ng+=1; print('  NG ',n,x)
with sync_playwright() as p:
    b=p.chromium.launch()
    def mk():
        pg=b.new_context().new_page(); pg.on('dialog',lambda d:d.accept()); pg.route('https://mock.example.test/sync/knowledge-dictionary',handle)
        pg.goto('http://127.0.0.1:8491/index.html'); pg.wait_for_selector('#list'); pg.evaluate("lsSet('kd_endpoint','https://mock.example.test');lsSet('kd_token','tok_abc123')"); return pg
    A=mk(); B=mk()
    A.evaluate("(async()=>{const n=Date.now();await writeEntries([{id:'a',term:'JWT',oneLine:'',tags:[],related:[],note:'',kind:'term',understanding:'unknown',checkedAt:null,createdAt:n,updatedAt:n},{id:'b',term:'JWT認証',oneLine:'',tags:[],related:[],note:'',kind:'term',understanding:'unknown',checkedAt:null,createdAt:n,updatedAt:n}]);await writeQAs([{id:'q',entryId:'a',question:'Q',answer:'A',judgment:'',sourceType:'other',sourceUrl:'',createdAt:n,updatedAt:n}]);})()")
    A.evaluate("kdSync(false)"); A.wait_for_timeout(700); B.evaluate("kdSync(false)"); B.wait_for_timeout(700)
    check('Bに2項目届く', B.evaluate("entries.length")==2)
    A.evaluate("mergeEntries('b','a')"); A.wait_for_timeout(3500)
    B.evaluate("kdSync(false)"); B.wait_for_timeout(900)
    check('統合がBに届く（片方が消え、別名が付く）', B.evaluate("entries.length")==1 and B.evaluate("entries[0].aliases.includes('JWT')"), B.evaluate("entries.map(e=>e.term)"))
    check('Q&AがBでも移っている', B.evaluate("qas.length==1 && qas[0].entryId==='b'"))
    A.evaluate("kdSync(false)"); A.wait_for_timeout(700)
    check('消えた項目が復活しない', A.evaluate("entries.length")==1 and B.evaluate("entries.length")==1)
    b.close()
print('結果: OK',ok,'/ NG',ng)
