# C0 EditPlan Kernel 実装報告

実施日: 2026-08-25  
対象: `D:\HermesWorkspace\client-short-factory`  
状態: C0 kernel＋人間調整WebUI実装・実Composition検証完了。C1自動化は未着手。

## 結果

既存version 3字幕workflowを変更せず、version 4のC0 Composition Kernelを並行実装した。

手書きEditPlanから、次を再現できる。

- 単一source内の複数keep range
- Story Beatと実clipの分離
- 同一clip内のlayout切替
- Generated Card／場面札
- 通常／コメント／引用／強調字幕
- Editorial Overlay
- hard cutと、output尺を変えないclick防止micro fade
- 1080×1920、30fps、H.264/AAC出力
- finalと同じgeometry／filter graphを使うproxy

AI planner、Vision/OCR、BGM/SFX自動化、自由layer/keyframeは実装していない。C0 EditPlanを人間が直すWebUIは追加した。

## 人間調整WebUI

review UIは「候補を探す」と「ショートを編集」の2入口へ整理した。旧「字幕を編集」は廃止し、Composition EditPlanを唯一の編集draftとする。「ショートを編集」内には拡張可能なsection navigationを置き、現在は「構成・画面」と「字幕一覧」を提供する。構成sectionはライブ編集previewを中央に保ち、左から再生順、中央で画角、右で選択カットを直す3領域構成である。保存済みProxy／Finalは別の確認対象として切り替える。

- 不要カットの除外と同一Story Beat内の並べ替え
- レイアウトpreset切替
- 開始／終了の±1秒、±0.1秒調整
- 選択カットと全字幕一覧の両方から、字幕の追加／削除、本文、役割、開始／終了を修正
- 空本文、カット外、字幕重複、1frame未満を保存前に検出
- ゲーム／顔の重要範囲をdrag／resize
- 敵HPなどの見切れ禁止点を指定し、zoom率を保ったまま枠を移動
- 元動画をdraftの順序・trim・削除・字幕・layout・cropで再生するCanvasライブpreview
- draftの一括破棄
- immutableなEditPlan revision保存
- 保存したrevisionを明示指定したproxy連続生成

操作は保存までbrowser draftに留め、入力ごとにFFmpegを起動しない。ライブpreviewは構成判断用の近似で、ASSの最終改行、filter、音量、micro fadeはProxyを正本とする。保存とrenderは既存global OS lockを使うworker commandを経由する。

## 追加した境界

### EditPlan

機械可読schema:

- `short_factory/schemas/editplan.v1.schema.json`

実行時validator:

- `short_factory/composition_schema.py`

主な不変条件:

- source videoは整数PTS
- source audioはstream開始からの整数sample index
- outputは整数frame／sample
- source clipは1つの半開連続区間
- joinは隣接Timeline Item間だけ
- Presentation Eventはsource clipをgapなく被覆
- Speech Captionは1つのclip内だけ
- trimで字幕anchorが失われた場合は`ORPHANED`としてpublish拒否
- 15〜60秒、最大12 Story Beats、最大24 Source Clips

### Immutable artifact

- `project.json`と`project-identity.json`
- `edits/revisions/<revision>/edit.json`
- `edits/revisions/<revision>/compiled-timeline.json`
- atomic `edits/current.json`
- recovery pointer
- explicit edit revision render
- source SHA-256再検査
- render-input、timeline、style、compiler、profile identity
- partial render directoryの非公開
- stale edit renderの識別

### Renderer

- clip／layout eventごとの決定論的segment作成
- Generated Card
- 4 layout presets
- role別ASS style
- proxy／final共通のcanvas、fps、font、改行、filter graph、sample rate
- proxyはencoder presetだけを軽量化
- ffprobe、frame count、duration、decode QC

## CLI

追加したcommand:

```text
composition-init
composition-publish-edit
composition-compile
composition-render --profile proxy|final
composition-save-worker
composition-render-worker
```

具体例は`README.md`の「C0 Composition Kernel」に記載した。

## Fixture

3つの構造fixture:

- `tests/fixtures/composition/dialogue.json`
- `tests/fixtures/composition/event-reaction.json`
- `tests/fixtures/composition/montage.json`

技術fixture／test:

- VFR metadata
- non-zero video PTS
- audio-leading source clock
- source/output frame/sample対応
- caption orphan
- presentation coverage gap
- missing／non-adjacent join
- source identity差し替え
- stale base revision
- pointer publish fault
- render publish fault
- proxy／finalの同一timeline・同一ASS

## 検証結果

### 自動test

最終実行command:

```powershell
py -3.12 -m unittest discover -s tests -q
```

実FFmpeg proxy／final smokeを含む136 testを44.539秒で実行し、すべてPASSした。

### 実Composition UI

`pokemon-hydro-80-v1` Revision 3をlocalhost UIへ読み込み、既存Revisionを保存変更せず次をbrowserで確認した。

- 51.3秒／6カット、10字幕、Revision 3 proxyと過去renderを表示
- 上部に「字幕を編集」がなく、「ショートを編集」内の「構成・画面／字幕一覧」を切替
- 字幕なしカットへ字幕を追加すると10→11件、Story要約と未保存ライブdraftへ即反映
- 本文修正と開始＋0.1秒を反映し、「映像で確認」で0:13.5へseek
- 追加字幕の削除で元planと一致し、未保存状態が自動解除
- 空本文では保存を無効化し、理由をalert表示
- 変更破棄でRevision 3、6カット、10字幕、未保存変更なしへ復元

### 100回決定性

同じnormalized EditPlanから、plan hashとCompiledTimeline hashが100回すべて一致した。

対象にしている決定性はMP4 byte一致ではなく、次の一致である。

- normalized EditPlan
- CompiledTimeline
- source frame／audio sample mapping
- caption／overlay frame
- layout event
- render filter graph identity

### 実FFmpeg smoke

14秒の合成sourceから、1秒の場面札＋3場面を組み、次をproxy／finalの両方でrenderした。

- 複数range
- source layout
- content layout
- split layout
- person layout
- role付き字幕
- Editorial Overlay
- micro fade
- 450 frames、1080×1920、30fps、H.264/AAC

proxyとfinalは同じCompiledTimeline hash、expected frame count、ASS bytesになった。

### 2時間source smoke

再現command:

```powershell
py -3.12 -m tools.c0_long_source_smoke
```

2026-08-25の実測:

```text
source duration: 7200秒
source size: 15,339,538 bytes
2時間source生成: 18.029秒
project init＋全量SHA-256: 0.100秒
EditPlan validate／compile／publish: 0.016秒
離れた6場面から60秒proxy render: 11.763秒
output size: 1,563,214 bytes
```

低複雑度の合成sourceであり、実配信のdecode負荷を代表する数値ではない。長尺sourceを先頭から全decodeせず、各場面へseekできることの技術確認として扱う。

## C0 gate判定

技術gate:

- PASS: 3構造を手書きPlanで表現・compileできる
- PASS: 同一PlanのCompiledTimeline hash 100回一致
- PASS: orphan／未解決join／coverage gapをcompile拒否
- PASS: proxy／finalのframe、subtitle、layout identity一致
- PASS: stale revisionを現行として扱わない
- PASS: 2時間sourceから60秒proxyを生成
- PASS: 既存version 3 workflowを回帰testで維持

品質gate:

- PENDING: 権利確認済み設計用3project
- PENDING: 完全未使用holdout 3project
- PENDING: 原音付き全joinの人間確認
- PENDING: comprehensionと意味事故の比較

参考Shorts 4本は観察資料のままとし、fixtureへ転用していない。

## 次の停止点

C1自動化は未承認・未着手である。

次はこのUIで実作品を1本仕上げ、人間の修正時間と修正箇所を記録する。自動化を増やす前に、レイアウトpresetで足りない表現と、繰り返し発生する人間修正を分離する。権利確認済み設計用projectと完全未使用holdout projectで同じUI操作が通ることを確認してから、頻出修正だけをplanner候補にする。
