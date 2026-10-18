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
git commit -m "feat: 知識辞書 v0.1"
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

## できないこと（v0.1）

- **端末どうしの自動同期はありません。** 移すときは「書き出す」→「読み込む」を使います
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
