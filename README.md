# VTK画像出力マニュアル

[main.py](./main.py) は、ParaViewのPython APIを使用して、VTKファイルを1ファイルにつき1枚のPNGに変換します。面・節点・保存された積分点の表示、変形図、カラーコンター、カメラの指定に対応しています。

**基本の使い方は、[config.json](./config.json) を編集し、[run.sh](./run.sh) で実行する方法です。** CLIによる個別指定は、一時的な設定上書きのための補助機能として扱います。

## ファイル構成と実行場所

```text
visualize_vtk_by_pvpython/
├── README.md
├── main.py
├── config.json
├── run.sh
└── sample/
    ├── inputs/    # サンプルVTK
    └── images/    # サンプル設定のPNG保存先
```

- [main.py](./main.py)：可視化プログラム本体（旧名 `visualize_vtk_by_paraview.py`）。
- [config.json](./config.json)：実行設定（旧名 `visualize_vtk.json`）。
- [run.sh](./run.sh)：実行コマンドを記録したシェルスクリプト。
- [sample/inputs](./sample/inputs)：付属の入力データ。
- [sample/images](./sample/images)：付属設定による出力先。既存の同名PNGは上書きされます。

以降のコマンド例は、すべてこのREADMEが置かれた `visualize_vtk_by_pvpython` ディレクトリをカレントディレクトリとして実行します。親ディレクトリから始める場合は、最初に移動してください。

```bash
cd visualize_vtk_by_pvpython
```

## 1. condaによる環境構築

### 1.1 前提

- Linux上でcondaが使用できること。未導入の場合は、組織の運用ルールに従ってMiniforgeなどをユーザー領域に導入してください。
- conda-forgeからパッケージを取得できるネットワーク接続があること。
- 作業用の環境は `base` と分離します。通常、ユーザー領域へのconda環境作成に管理者権限は不要です。

```bash
conda --version
conda create -n paraview --override-channels -c conda-forge paraview
conda activate paraview
```

ParaView本体と対応するPythonモジュールを含む環境を使用します。一般のPython環境に `vtk` だけをインストールしても、このスクリプトは実行できません。

### 1.2 インストール確認

```bash
command -v pvpython
pvpython --version
pvpython -c 'from paraview import simple; print("ParaView Python: OK")'
```

`pvpython` が有効化したconda環境内を指していることを確認してください。ParaViewのバージョンや提供ビルドは、OS・アーキテクチャ・パッケージの配布状況に依存します。

スクリプトが置かれたディレクトリで、ヘルプを確認します。

```bash
pvpython main.py --help
```

新しいシェルでも実行前に `conda activate paraview` が必要です。環境を有効化せずに実行する場合は、次の形式も使えます。

```bash
conda run -n paraview pvpython main.py --config config.json
```

### 1.3 環境情報の保存

動作確認後、使用環境を記録すると再構築時に役立ちます。

```bash
conda env export -n paraview --no-builds > environment-paraview.yml
```

別の場所で再構築する場合：

```bash
conda env create -f environment-paraview.yml
conda activate paraview
```

このエクスポートはパッケージのバージョンを記録しますが、異なるOSや将来の配布状況に対する完全な再現を保証するものではありません。

## 2. 最初の実行

### 2.1 JSON設定を編集して実行

付属の [config.json](./config.json) を編集して実行できます。

```bash
conda activate paraview
bash run.sh
```

[run.sh](./run.sh) に記録されているコマンドは次のとおりです。

```bash
pvpython main.py --config config.json
```

`run.sh` はconda環境の有効化や、自身が置かれたディレクトリへの移動を行いません。実行前に環境を有効化し、このREADMEのディレクトリへ移動してください。`bash /path/to/run.sh` と絶対パスで呼んでも、カレントディレクトリは変わりません。

現在の `run.sh` は追加引数を転送しません。設定をCLIで上書きする場合は、`bash run.sh --point-size 10` ではなく、`pvpython main.py --config config.json --point-size 10` のように直接実行してください。

付属設定は編集可能な利用例であり、スクリプトのデフォルト設定そのものではありません。現在の主な設定は次のとおりです。

| 項目 | 付属設定 |
|---|---|
| 入力 | `sample/inputs/prvw*.vtk` に一致するファイル |
| 出力先 | `sample/images` |
| コンター | `DISPLACEMENT` の大きさ、`POINTS`、`Viridis`、レンジ自動 |
| 表示 | `surface`、エッジあり、変形倍率 `1.0` |
| カメラ | 位置・注視点は自動、上方向 `y`、Roll `0` |
| 点サイズ | `50.0`（`surface` 表示では使用しない） |
| 画像サイズ | 1600×1200ピクセル |

たとえばスクリプト自体の配色は `Turbo`、変形表示は無効ですが、この設定では `Viridis`、変形表示は有効です。

### 2.2 単一ファイルから始める

最初は [config.json](./config.json) を次の内容にして実行すると、単一ファイルの未変形形状に変位の大きさを色付けできます。

```json
{
  "vtkfile": ["sample/inputs/prvw0001.vtk"],
  "output-dir": "./sample/images",
  "field": "DISPLACEMENT",
  "association": "POINTS",
  "representation": "surface",
  "deform": false,
  "view": "xy",
  "range": null,
  "colormap": "Turbo",
  "edges": true,
  "width": 1600,
  "height": 1200
}
```

保存後、`bash run.sh` を実行します。出力は `sample/images/prvw0001.png` です。

- 変形図にするには `"deform": true` に変更します。
- `range` が `null` の場合は、ファイルごとにレンジを自動調整します。
- 単色表示にする場合は `field` と `colormap` を削除してください。固定の `range` も指定しないでください。
- 不要な設定が残らないよう、この例を使う場合は該当キーだけの変更ではなく、JSON全体を置き換えてください。

## 3. 入出力ファイル

### 対応形式

- `.vtk`：Legacy VTK形式
- `.vtu`：XML Unstructured Grid形式

拡張子の大文字・小文字は区別しません。他の形式（`.pvtu`、`.pvd` など）は対象外です。旧キー `vtkdir` は使用せず、`vtkfile` を使用してください。

### 複数指定とワイルドカード

以下は `vtkfile` の設定例です。用途に合った1つをJSONに設定してください。

```json
{
  "vtkfile": ["sample/inputs/prvw0001.vtk", "sample/inputs/prvw0002.vtk"]
}
```

```json
{
  "vtkfile": ["sample/inputs/*.vtk"]
}
```

明示パスとパターンの混在：

```json
{
  "vtkfile": ["sample/inputs/prvw0001.vtk", "sample/inputs/prvw001*.vtk"]
}
```

サブディレクトリも検索：

```json
{
  "vtkfile": ["results/**/*.vtu"]
}
```

`*`、`?`、`[abc]`、再帰検索用の `**` に対応します。JSON内のパターンはスクリプトが展開します。補助的にCLIを使う場合は、パターンを引用符で囲むとシェルではなくスクリプト側で展開されます。

- 指定したパス・パターンの順に処理し、各パターンの一致結果はパスの辞書順に並べます。数値順ではありません。
- 同じファイルへの重複指定は除去します。
- 1つでも一致しないパターンがあるとエラーになります。
- ディレクトリそのものや、対応外のファイルを選択するとエラーになります。

### 保存先

`output-dir` 指定時は、すべての画像をそのディレクトリに保存します。省略時は各入力ファイルの親ディレクトリ内の `images` に保存します。

```text
sample/inputs/prvw0001.vtk → sample/inputs/images/prvw0001.png
```

保存先は自動作成されます。既存の同名PNGは上書きします。異なる入力が同じ出力パスになる場合（共通出力先に対する別ディレクトリの同名ファイルなど）は、描画開始前にエラーにします。

## 4. JSONの書式と優先順位

付属の [config.json](./config.json) に対応する設定例：

```json
{
  "vtkfile": ["sample/inputs/prvw*.vtk"],
  "output-dir": "./sample/images",
  "field": "DISPLACEMENT",
  "association": "POINTS",
  "representation": "surface",
  "point-size": 50.0,
  "quadrature-offset": null,
  "deform": true,
  "deformation-field": "DISPLACEMENT",
  "deformation-scale": 1.0,
  "view": "iso",
  "camera-position": null,
  "camera-focal-point": null,
  "camera-view-up": "y",
  "camera-roll": 0.0,
  "range": null,
  "colormap": "Viridis",
  "edges": true,
  "width": 1600,
  "height": 1200
}
```

- キーはCLIの長いオプション名から `--` を除いた名前です。ハイフンはそのまま使用します。
- `vtkfile` は文字列または空でない文字列リストです。他の数値配列は所定の要素数が必要です。
- 真偽値は `true` / `false`、未指定を表す値は `null` です。数値や真偽値を引用符で囲まないでください。
- コメントや末尾の余分なカンマは使えません。不明なキー・不正な型はエラーになります。
- `config`、`no-edges`、`no-deform` はJSONのキーではありません。JSONでは `edges`、`deform` を真偽値で指定します。
- 相対パスは、JSONの所在ではなく**実行時のカレントディレクトリ**を基準に解釈します。
- 優先順位は **CLI指定 > JSON指定 > スクリプトのデフォルト** です。
- CLIの `--vtkfile` はJSONの対象リストを追加ではなく置き換えます。

```bash
pvpython main.py \
  --config config.json \
  --vtkfile sample/inputs/prvw0002.vtk \
  --representation points \
  --point-size 10 \
  --no-deform \
  --no-edges
```

このCLI例は一時的な上書き用です。通常は同じ項目をJSONで変更して `bash run.sh` を実行し、使用した設定を保存してください。

`range` やカメラ座標をJSONで固定している場合、自動調整に戻すにはJSONからキーを削除するか `null` にしてください。それらをCLIから `null` に戻すオプションはありません。

## 5. 全オプション一覧

以下のデフォルト値は、付属JSONではなくスクリプト自体の値です。
通常は各表の「JSONキー」を [config.json](./config.json) に指定します。「CLI」列は一時的な上書きや対応関係の確認用です。

### 入出力・画像

| CLI | JSONキー | 内容・デフォルト |
|---|---|---|
| `--help` / `-h` | なし | ヘルプを表示して終了 |
| `--config PATH` | なし | JSON設定ファイル。省略可能 |
| `--vtkfile PATH [PATH ...]` | `vtkfile` | 必須。単一パス、複数パス、パターン。JSONで指定してもよい |
| `--output-dir PATH` | `output-dir` | 共通出力先。省略時は各入力の親ディレクトリ内の `images` |
| `--width N` | `width` | 画像幅。正の整数、デフォルト `1600` |
| `--height N` | `height` | 画像高さ。正の整数、デフォルト `1200` |

### 表示・カラーコンター

| CLI | JSONキー | 内容・デフォルト |
|---|---|---|
| `--representation MODE` | `representation` | `surface`、`points`、`gauss`。デフォルト `surface` |
| `--point-size SIZE` | `point-size` | 点サイズ、ピクセル単位。有限の正数、デフォルト `5.0` |
| `--edges` / `--no-edges` | `edges` | 面表示の要素エッジ。デフォルト `false`。点表示では適用しない |
| `--field NAME` | `field` | 色付けする配列名。省略時は単色。ベクトルは大きさで色付け |
| `--association TYPE` | `association` | `POINTS` または `CELLS`。デフォルト `POINTS` |
| `--range MIN MAX` | `range` | 有限値かつ `MIN < MAX`。JSONは `[MIN, MAX]`。省略・`null` はファイルごとに自動調整。固定指定には `field` が必要 |
| `--colormap NAME` | `colormap` | ParaViewのプリセット名。省略・`null` は `Turbo`。明示指定には `field` が必要 |
| `--quadrature-offset NAME` | `quadrature-offset` | Gauss表示の積分点オフセット配列名。省略・`null` は候補が1つなら自動選択。明示指定は `gauss` のみ |

### 変形図

| CLI | JSONキー | 内容・デフォルト |
|---|---|---|
| `--deform` / `--no-deform` | `deform` | 変形表示。デフォルト `false` |
| `--deformation-field NAME` | `deformation-field` | 3成分の節点変位配列。デフォルト `DISPLACEMENT` |
| `--deformation-scale S` | `deformation-scale` | 変位倍率。有限数、デフォルト `1.0` |

### カメラ

| CLI | JSONキー | 内容・デフォルト |
|---|---|---|
| `--view MODE` | `view` | 基準視点 `iso`、`xy`、`xz`、`yz`。デフォルト `iso` |
| `--camera-position X Y Z` | `camera-position` | カメラのワールド座標。JSONは3要素配列。省略・`null` は自動 |
| `--camera-focal-point X Y Z` | `camera-focal-point` | 注視点のワールド座標。JSONは3要素配列。省略・`null` は自動 |
| `--camera-view-up AXIS` | `camera-view-up` | 上方向の軸。`x`、`y`、`z`、`-x`、`-y`、`-z`。省略・`null` は `view` の設定 |
| `--camera-roll DEGREES` | `camera-roll` | 視線軸まわりの回転角、度単位。有限数、デフォルト `0.0` |

## 6. 表示方法の使い分け

以下のJSON例は**変更する項目の抜粋**です。[config.json](./config.json) の対応するキーを更新し、記載のない設定は必要に応じて残してください。変更後の実行コマンドは共通して `bash run.sh` です。

### 6.1 面表示

```json
{
  "vtkfile": ["sample/inputs/*.vtk"],
  "representation": "surface",
  "field": "DISPLACEMENT",
  "association": "POINTS",
  "colormap": "Turbo",
  "range": [0, 100],
  "edges": true,
  "output-dir": "./sample/images"
}
```

複数時刻・複数ケースを比較するときは、色の意味を統一するため固定レンジを推奨します。自動レンジでは、同じ色がファイルごとに異なる値を表す場合があります。

セル単位の応力を表示する例：

```json
{
  "vtkfile": ["sample/inputs/prvw0001.vtk"],
  "field": "60031:SOLID_VON_MISES_STRESS",
  "association": "CELLS",
  "representation": "surface",
  "range": null
}
```

配列名は入力ファイルの実際の名前と一致させてください。VTKヘッダーの `VECTORS` や `SCALARS` は名前に含めません。確認した入力では `DISPLACEMENT` は `POINT_DATA`、応力などは `CELL_DATA` にあります。

### 6.2 節点表示

```json
{
  "vtkfile": ["sample/inputs/prvw0001.vtk"],
  "representation": "points",
  "point-size": 8,
  "field": "DISPLACEMENT",
  "association": "POINTS",
  "range": null
}
```

メッシュの節点を点で表示します。色付けには `POINTS` を使用してください。`CELLS` から `POINTS` への自動変換・補間は行いません。点サイズは画面上のピクセル単位であり、モデルの長さの単位ではありません。

### 6.3 Gauss点表示

**Gauss表示は、積分点情報が入力に保存されている場合だけ利用できます。**

必要な情報：

1. セルオフセット配列と、それに関連付けられたVTKの積分則辞書（quadrature scheme dictionary）。
2. 色付けする場合は、そのオフセット配列に関連付けられた積分点のフィールドデータ。

ParaViewの `QuadraturePointsGenerator` で積分点を生成し、対応する保存済みフィールドデータを出力の節点データに写して表示します。単に配列名を `Gauss` などにするだけでは利用できません。`.vtu` 形式でも必要なメタデータが必ず入っているわけではありません。

次は必要なメタデータを持つファイルに対する例です。ファイル名・配列名は実データに置き換えてください。

```json
{
  "vtkfile": ["results/quadrature.vtu"],
  "representation": "gauss",
  "point-size": 8,
  "field": "GAUSS_STRESS",
  "association": "POINTS",
  "range": null,
  "quadrature-offset": null,
  "deform": false
}
```

積分則の候補が複数ある場合：

```json
{
  "quadrature-offset": "QuadratureOffsets"
}
```

- 要素タイプだけから積分則を推測しません。セル中心での代用もしません。
- セル単位の応力から積分点ごとの応力を復元しません。
- 節点データを積分点に自動補間して色付けする機能はありません。
- 確認した `sample/inputs/prvw0001.vtk` には必要な積分点情報がないため、`gauss` はエラーになります。節点を表示したい場合は `points` を選択してください。

## 7. 変形図

表示座標は次の式で計算します。

```text
表示座標 = 元の座標 + deformation-scale × 節点変位
```

次の項目をJSONで更新して、`bash run.sh` を実行します。

```json
{
  "vtkfile": ["sample/inputs/prvw0001.vtk"],
  "deform": true,
  "deformation-field": "DISPLACEMENT",
  "deformation-scale": 10,
  "field": "60031:SOLID_VON_MISES_STRESS",
  "association": "CELLS",
  "representation": "surface",
  "range": null
}
```

- 倍率 `1` は実変位、`10` は10倍の強調表示です。`0` や負の有限値も指定できます。
- 変位配列は3成分の `POINTS` データである必要があります。
- 変形に使う配列とコンターに使う配列は独立しています。上の例は変位で変形し、セルの応力で色付けします。
- 倍率は形状だけに適用され、コンターの値には掛かりません。
- `points` との併用では変形後の節点を表示します。`gauss` との併用では、メッシュを変形してから積分点座標を生成します。
- 元形状との重ね合わせ表示は行いません。

## 8. カメラの指定と適用順

### 基準視点

| `view` | モデルから見たカメラ側 | 基準の上方向 |
|---|---|---|
| `iso` | `(+X, +Y, +Z)` の斜め方向 | `+Z` |
| `xy` | `+Z` 側からXY平面を見る | `+Y` |
| `xz` | `-Y` 側からXZ平面を見る | `+Z` |
| `yz` | `+X` 側からYZ平面を見る | `+Z` |

カメラは平行投影です。

1. `view` に基づいて表示対象の形状を収める初期カメラと表示スケールを計算します。
2. 明示した `camera-position`、`camera-focal-point` を適用します。
3. `camera-view-up` を適用します。
4. 最後に `camera-roll` を適用します。

未指定項目の扱い：

- 位置・注視点とも未指定：形状に合わせて自動調整します。
- 位置のみ指定：注視点は自動調整で得た形状の中心です。
- 注視点のみ指定：初期の視線方向と距離を維持して、カメラ位置も平行移動します。
- 両方指定：指定座標をそのまま使用します。

自動調整は各ファイルで行います。変形表示時は変形後、Gauss表示時は生成した積分点を対象に調整します。

次の項目をJSONで更新して、`bash run.sh` を実行します。

```json
{
  "camera-position": [7000, 7000, 10000],
  "camera-focal-point": [3000, 3000, 0],
  "camera-view-up": "y",
  "camera-roll": 30
}
```

- 上方向の軸は画像平面へ投影されます。指定軸が最終的な視線方向と平行ならエラーです。
- 負の上方向はJSONでは `"camera-view-up": "-z"` と指定します。CLIで上書きする場合は `--camera-view-up=-z` のように `=` を使用してください。
- Rollの正方向は、カメラ位置から注視点へ向かう軸に対する右ねじ方向です。
- Rollは位置・注視点・表示スケールを変えません。
- 上方向が未指定で既定の上方向と視線がほぼ平行になる場合は、別の軸を自動選択します。
- 明示座標・上方向・Rollの適用後に、形状を収めるためのスケール再計算はしません。回転や注視点変更によって端が切れる場合は、設定や画像の縦横比を見直してください。平行投影なので、カメラの距離だけを変えても表示倍率は変わりません。

## 9. ヘッドレスサーバーでの実行

`pvpython` でも画像生成にはOpenGLの描画環境が必要です。GUIを開かないことと、Xサーバーが不要なことは同じではありません。

- EGLまたはOSMesaに対応したParaViewビルドを使用する方法があります。
- Xディスプレイが必要なビルドでは、利用可能なら `xvfb-run` を使用します。

```bash
conda activate paraview
xvfb-run -a pvpython main.py --config config.json
```

`xvfb-run` はParaViewとは別のツールで、condaのParaView導入だけで利用可能になるとは限りません。未導入の場合は管理者に相談してください。適切な方法はサーバーのGPU・ドライバー・ParaViewビルドによって異なります。condaでインストールできたことだけでは、ヘッドレス描画の成功は保証されません。

## 10. よくあるエラー

| 症状・メッセージ | 確認・対処 |
|---|---|
| `pvpython: command not found` | `conda activate paraview` と `command -v pvpython` を確認。システムの自動インストールに頼らず、環境内の実行ファイルを使用 |
| `ParaView Python modules are unavailable` | 通常の `python` ではなく、対応するParaViewの `pvpython` で実行 |
| パッケージ導入時の認証失敗 | システムインストールの権限問題。ユーザー領域のconda環境を使用するか管理者に相談 |
| XディスプレイやOpenGLのエラー | ヘッドレス実行の節を確認。使用ビルド・ドライバーの要件を確認 |
| `No VTK files matched` | パス、カレントディレクトリ、パターンを確認。JSONからの相対パスも実行場所基準 |
| `duplicate PNG` | 共通保存先に同じstemの入力を集めていないか確認。入力を分けるか保存先を分離 |
| `field ... not found` | 配列名と `POINTS` / `CELLS` の区分を確認。エラーに表示される利用可能な配列名を参照 |
| `Point and Gauss coloring require ... POINTS` | 点表示では `association` を `POINTS` に変更。セル値の自動変換は行わない |
| `displacement field ... must have 3 components` | 変形には3成分の節点ベクトルを指定 |
| `Unknown or unavailable ParaView colormap` | プリセット名と使用バージョンを確認。Turboがない版では、利用可能な配色を明示するか環境を更新 |
| `no stored quadrature scheme dictionary/offset array` | Gauss点メタデータがない。適切な出力データを用意するか、節点表示には `points` を使用 |
| `Multiple quadrature schemes` | 表示された候補から `quadrature-offset` を指定 |
| `camera-view-up must not be parallel ...` | 視線と異なる上方向の軸を選択 |
| 引数の次の行が別コマンドになる | Bashの行継続用 `\` は行末の最後の文字にする。後ろに空白を置かない |

処理はエラー時点で中断します。途中まで保存された画像の削除やロールバックは行いません。

## 11. 検証状況

旧構成では、引数処理、JSON設定、ファイル選択、描画APIの呼び出し・適用順序などのモックによるユニットテストを実施しました。ただし、親ディレクトリに残るテストは旧モジュール名を参照しているため、現在のファイル配置ではそのまま実行できません。移動後のテスト実行にはimportとモック対象の更新が必要です。

現在の配置で引数・設定の読み込みだけを確認する場合は、このREADMEのディレクトリで次を実行できます。通常のPythonで実行でき、画像は生成しません。

```bash
python -c 'from main import parse_arguments, get_vtk_files; a = parse_arguments(["--config", "config.json"]); print(*get_vtk_files(a.vtkfile, a.output_dir), sep="\n")'
```

この確認では、実際のOpenGL描画、プリセットの存在、積分点メタデータを含む実ファイルの読み込み・積分点生成は検証できません。

付属の `sample/images` にはPNGがありますが、今回のマニュアル更新では描画を再実行していません。環境構築後、まず単一ファイルで実行してPNGを確認してから、一括処理してください。
