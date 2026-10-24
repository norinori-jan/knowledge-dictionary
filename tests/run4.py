import os
import threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright
ROOT=os.environ.get('KD_ROOT','.')
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
socketserver.TCPServer.allow_reuse_address=True
srv=socketserver.TCPServer(('127.0.0.1',8473),functools.partial(Q,directory=ROOT))
threading.Thread(target=srv.serve_forever,daemon=True).start()
ok=ng=0; errs=[]
def check(n,c,x=''):
    global ok,ng
    if c: ok+=1; print('  OK ',n)
    else: ng+=1; print('  NG ',n,x)
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_context(viewport={'width':390,'height':844},device_scale_factor=2).new_page()
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',lambda d:d.accept())
    pg.goto('http://127.0.0.1:8473/index.html'); pg.wait_for_selector('#list')
    # 既存項目（タグ付き）
    pg.evaluate("writeEntries([{id:'e1',term:'OAuth',oneLine:'',tags:['認証','API'],related:[],note:'',kind:'term',understanding:'unknown',checkedAt:null,createdAt:1,updatedAt:1},{id:'e2',term:'Cookie',oneLine:'',tags:['認証','Web'],related:[],note:'',kind:'term',understanding:'unknown',checkedAt:null,createdAt:1,updatedAt:1}])")
    pg.click('#btnAdd'); pg.wait_for_selector('#shQA.open'); pg.wait_for_timeout(500)
    check('既存タグの候補が出る', pg.locator('#qTagsChips .qc[data-tg="認証"]').count()==1 and pg.locator('#qTagsChips .qc[data-tg="Web"]').count()==1)
    pg.click('#qTagsChips .qc[data-tg="認証"]')
    check('タグを押すと入る', pg.input_value('#qTags')=='認証')
    check('入ったタグは✓表示', pg.locator('#qTagsChips .qc.on[data-tg="認証"]').count()==1)
    pg.click('#qTagsChips .qc.on[data-tg="認証"]')
    check('もう一度押すと外れる', pg.input_value('#qTags')=='')
    pg.fill('#qTerm','JWT'); pg.fill('#qRel','OAuth Cookie 署名'); pg.wait_for_timeout(500)
    check('既存の関連語は📖', pg.locator('#qRelChips .qc.has').count()==2)
    check('無い関連語は作成ボタン', pg.locator('#qRelChips .qc.mk[data-mk="署名"]').count()==1)
    pg.click('#qRelChips .qc.mk[data-mk="署名"]'); pg.wait_for_timeout(400)
    check('その場で項目ができる', pg.evaluate("!!findEntryByTerm('署名')"))
    check('作成後は📖になる', pg.locator('#qRelChips .qc.mk').count()==0 and pg.locator('#qRelChips .qc.has').count()==3)
    check('入力途中の質問は消えない', pg.input_value('#qTerm')=='JWT')
    # 選ぶ
    pg.click('#shQA [data-relpick="qRel"]'); pg.wait_for_selector('#shPick.open'); pg.wait_for_timeout(300)
    pg.fill('#pkQ','セッション'); pg.wait_for_timeout(300)
    pg.click('#pkList [data-pk="セッション"]'); pg.wait_for_timeout(400)
    check('ピッカーから関連用語に足せる（[[ ]]なし）', 'セッション' in pg.input_value('#qRel') and '[[' not in pg.input_value('#qRel'), pg.input_value('#qRel'))
    check('足した語もすぐチップに出る', pg.locator('#qRelChips .qc.mk[data-mk="セッション"]').count()==1)
    pg.screenshot(path=os.path.join(os.environ.get('KD_OUT','/tmp/kd-out'),'14-chips.png'))
    # 保存して項目編集でも使える
    pg.fill('#qQuestion','JWTとは'); pg.fill('#qAnswer','署名つき'); pg.click('#qaSave'); pg.wait_for_timeout(600)
    e=pg.evaluate("findEntryByTerm('JWT')")
    check('保存されて関連が入る', e and '署名' in e['related'] and 'セッション' in e['related'])
    pg.evaluate("openEntry(findEntryByTerm('JWT').id)"); pg.wait_for_timeout(300)
    pg.click('#btnEntryEdit') if pg.locator('#btnEntryEdit').count() else pg.evaluate("openEntryEdit && openEntryEdit()")
    pg.wait_for_timeout(500)
    check('項目の編集画面にも同じ仕組み', pg.locator('#eeTagsChips').count()==1 and pg.locator('#eeRelChips .qc').count()>=3)
    b.close()
print('結果: OK',ok,'/ NG',ng); print('JSエラー:',errs or 'なし')
