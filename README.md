# 📖 知識辞書（knowledge-dictionary）

AIに聞いたことを貼り付けて残し、**キーワード1つで「あのとき何を聞いて、何が分かったか」を引き出す**ための、個人用の知識辞書です。

- スマホ（iPhone）のホーム画面に入れて使う PWA（インストール不要・サーバー不要・ビルド不要）
- データは、**この端末の中にだけ**保存されます（IndexedDB）
- ファイルは `index.html` ほか数ファイルだけ

## 何ができるか

| やりたいこと | どうする |
|---|---|
| AIに聞いたことを残す | 「＋ Q&Aを足す」に、質問と回答を貼る |
| 同じことを何度も聞かない | 質問を書くと「似ている項目があります」と出る |
| あとで一発で引く | 検索欄に語を入れる（空白で区切ると、すべて含むものに絞り込み） |
| 用語としてまとめる | 同じ**見出し語**のQ&Aは、1つの項目にまとまる |
| AIの回答と自分の理解を分ける | 「自分の判断」「自分の理解」の欄が別にある |
| 分からないことを見返す | 未理解／理解中／理解済で絞り込む |
| AIに続きを聞く | 「再質問用にコピー」で、過去のやり取りを材料にした文を作る |
| 整理を任せる（任意） | ✨AI整理で、見出し語・一言・タグ・関連用語の**候補**を出す |
| AIに直接聞いて、そのまま残す | 「🤖 AIに聞く」（APIトークンを使う。月額プランとは別枠。1日の上限と使用量を表示） |
| 手順・考え方をつなぐ | 本文に `[[見出し語]]` と書くと、項目どうしがリンク（被リンク・つながり図つき。Obsidian風） |
| 項目の種類 | 用語／手順／考え方 で分けて絞り込める |
| PC と iPhone で同じ辞書にする | 設定の「今すぐ同期」（Worker 経由。以後は自動。削除も反映） |
| quick-ref から移す | 設定から、quick-ref の書き出しJSONを取り込む |

詳しくは [docs/USAGE.md](docs/USAGE.md)、設計は [docs/DESIGN.md](docs/DESIGN.md)。

## 使い始める（公開後）

1. iPhone の Safari で `https://norinori-jan.github.io/knowledge-dictionary/` を開く
2. 共有ボタン → **ホーム画面に追加**
3. **ホーム画面のアイコンから開いて**、そこでデータを入れる
   - Safari のタブと、ホーム画面のアプリは、**保存領域が別**です。どちらか一方だけで使ってください（おすすめはホーム画面のアプリ）

## 公開のしかた（GitHub Pages）

```powershell
cd C:\Users\norin\knowledge-dictionary
git init -b main
git add .
git commit -m "feat: 知識辞書 v0.2"
gh repo create norinori-jan/knowledge-dictionary --public --source . --push
gh api -X POST repos/norinori-jan/knowledge-dictionary/pages -f "source[branch]=main" -f "source[path]=/"
```

`gh` が無いときは、GitHub のサイトで空のリポジトリ（Public）を作り、表示される手順で push して、
**Settings → Pages → Branch: main / (root)** を選びます。数分で公開されます。

> コードには、鍵・トークン・個人データは入っていません。公開しても安全です。データは各自の端末にだけあります。

## ローカルで試す

```powershell
cd C:\Users\norin\knowledge-dictionary
python -m http.server 8000
```

ブラウザで `http://localhost:8000/` を開きます。（`file://` で直接開くと、オフライン用の機能だけが動きません）

## 費用について（AIに聞く）

「AIに聞く」は、Worker 経由で **API のトークン**を使います。ChatGPT・Claude の月額プランとは別の、使った分だけの課金です。設定で1日の上限（初期30回）を決められ、超えると確認が出ます。Gemini が安価でおすすめです。

## 端末どうしの同期（v0.3）

1. 両方の端末の ⚙︎ →「AIの接続」に、同じ **エンドポイント** と **同期トークン**（Worker の AUTH_TOKEN）を入れる。
2. 片方で「🔄 今すぐ同期」→もう片方でも「今すぐ同期」。以後は保存のたびに自動で同期します。
3. 同じ見出し語を別々の端末で作った場合は、1つにまとめます（メモは両方残る）。
4. Worker が `/sync/knowledge-dictionary` を受け付けない場合は、「送信失敗（404/400）」と出ます。その場合は sync-worker に置き場を足してください。

## できないこと（v0.3）

- 同期は、sync-worker に `/sync/knowledge-dictionary` の置き場が必要です（下記）。同期できなくても、書き出し／読み込みで移せます
- **暗号化（保護）には未対応**です。秘密が混ざる回答は貼らないでください
- 意味検索（言い換えでも見つかる検索）は未対応です。文字の一致が中心です
- **バックアップは、ときどき自分で**取ってください（端末の都合で保存領域が消えることがあります）

## ファイル

```
index.html            アプリ本体（1ファイル）
sw.js                 オフライン用
manifest.webmanifest  ホーム画面に入れるための設定
icons/                アイコン
docs/USAGE.md         使い方
docs/DESIGN.md        設計・データ・検索のしくみ・今後
```
