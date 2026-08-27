# Shorts Composer 製品設計 V1

作成日: 2026-08-25  
状態: C0 kernel実装済み。C1は未承認・未着手。  
対象: `D:\HermesWorkspace\client-short-factory`

## 0. 結論

Short Factoryを、汎用動画編集ソフトではなく、次の製品へ進化させる。

> 長尺配信から見どころを探し、AIがShorts用の構成初稿を作り、人間が意味を壊さず局所修正して、固定プリセット付きの完成MP4まで出せるShorts専用Composer

中心に置くのは「30秒の区間」でも「AIが生成した完成動画」でもない。中心は、ストーリー構造、使用場面、字幕役割、画面の主役、カット境界を保存する、再現可能な編集仕様である。

初期対象はVTuber／ゲーム配信、desktop、単一素材、完成15〜60秒に限定する。ここで3種類の構成を再現できれば成功とする。

1. 会話をテンポよく見せる
2. ゲーム画面などの出来事に合わせて画面の主役を切り替える
3. 同じテーマの複数場面を並べる

ただし、これらは製品トップで選ばせる固定モードではない。同じ編集仕様を作るためのAIレシピとして扱う。

## 1. 4本の参考動画から採用する編集文法

4本から分かったのは「カット数が多いほど良い」ではない。

- 参考1: ほぼ固定構図でも、発言の意味ごとに字幕の役割と強さを変えれば見続けられる。
- 参考2: ゲーム内の出来事が話者へ働きかける瞬間だけ、顔からゲーム画面へ主役を切り替える。
- 参考3: 単体では弱い場面も、同じテーマの3場面として並べ、場面札を入れると企画になる。
- 参考4: コメント、本人、引用された第三者を、字幕の情報源として見分けられる。

したがって、製品が再現すべきなのは「派手なエフェクト」ではなく、次の判断である。

- どこからどこまで使うか
- 何を削るか
- どの順で見せるか
- その場面の役割は何か
- 今は人物と元画面のどちらを読ませるか
- 誰の言葉として字幕を見せるか
- どのカットに意味事故・音声事故の危険があるか

## 2. 成功の定義と、言わないこと

### C1時点で言える成功

対応範囲内のShortsについて、構成rough cut、固定レイアウト、役割付き字幕、安全確認済みの音声join、1080×1920 MP4出力までを外部NLEなしで行える。

これは今回の「実務製品レベルの構成を再現する」という成功条件を満たす。

### C1時点では言わないこと

- あらゆるShortsを公開品質へ自動変換できる
- PremiereやCapCutを全面的に置き換える
- 自動BGM／効果音／複雑な字幕アニメーションまで完成する
- 長尺からモンタージュ場面をAIが自動発見する
- 複数素材、B-roll、速度変更、自由レイヤーへ対応する

ブランド固有の仕上げが必要な案件では、外部NLEが残り得る。C1で外部NLE不要と言う範囲は、下記MVP制約内の構成作業に限る。

## 3. 製品原則

1. AIがなくても、人間が同じ編集仕様を組める。
2. AIは完成状態を何度もポン出しせず、1つの初稿と局所差分を提案する。
3. 人間の修正済み箇所をAIが勝手に戻さない。
4. 元動画の時間と完成動画の時間を混同させない。
5. 削った文脈は消去せず、原音付きでいつでも確認・復元できる。
6. Browser上の近似表示を最終品質として承認させない。
7. 技術QC、join確認、内容確認を別々に記録する。
8. 同じ編集revisionから、同じ編集判断を再現できる。
9. 対象外要求をNLE機能追加で吸収せず、対象外として明示する。
10. 「Shortにする価値がない」も正常な出力とする。

## 4. 中核データモデル

### 4.1 3層へ分ける

`ビート`、`場面`、`演出`を混ぜない。

```text
Story Beat（意味構造）
  つかみ / 前振り / 展開 / 反応 / オチ / 余韻
      └─ Timeline Item（実際に並ぶ場面）
           Source Clip: 元動画の連続した1区間
           Generated Card: 場面札などの生成画面
                └─ Presentation Event（場面内の見せ方変更）
                     人物優先 / 元画面優先 / 両方 / コメント
```

これにより、ストーリー上は1つの出来事でも途中だけゲーム画面を大きくする構成と、複数場面を束ねるモンタージュの両方を扱える。

### 4.2 MVP上限

- source: 1本
- 完成尺: 15〜60秒
- Story Beat: 1〜12
- Source Clip: 1〜24
- Presentation Event: 最大24
- Caption: 最大80
- speed: 1.0固定
- video transition: hard cutのみ
- layout: 固定4プリセット
- output: 1080×1920 H.264/AAC 1種類

上限を超えた要求は、初期版では対象外とする。

### 4.3 Edit revisionの正本

renderへ影響する状態は、1つのimmutable `edit revision`へまとめる。

```text
edit.json
├─ source identity
├─ story_beats[]
├─ timeline_items[]
├─ presentation_events[]
├─ speech_captions[]
├─ editorial_overlays[]
├─ join_edges[]
├─ source_regions
└─ preset references
```

字幕だけを直した場合も新しいedit revisionになる。`caption revision`と`edit revision`の2つのcurrent headは作らない。

一方、renderへ影響しない情報は分離する。

- `proposal.json`: AIの提案、根拠、risk、planner情報
- `review.json`: join確認、内容確認、確認者
- `render-input.json`: 正規化済みrender snapshot
- `compiled-timeline.json`: compilerが導出した映像／音声／字幕対応

`human override`は全fieldへフラグを埋めず、proposalと採用済みedit revisionの差分として導出する。

### 4.4 場面の不変条件

1つのSource Clipは、必ず1つの連続した半開区間 `[in, out)` とする。1場面の中へ複数rangeを押し込まない。

複数場面を意味的にまとめる場合は、複数のTimeline Itemを1つのStory Beatへ所属させる。

Joinは前後どちらかの場面ではなく、2つのTimeline Item間の`Join Edge`へ所属させる。

### 4.5 時刻モデル

float秒を正本にしない。

- source video: 宣言されたtime base上の整数PTS
- source audio: 整数sample index
- output video: 整数frame index
- output audio: 整数sample index
- UI表示: `MM:SS.cc`へ変換した値だけ

取込時に非ゼロstart PTSを正規化し、元streamとの対応を保持する。区間の終端はすべてexclusiveとする。

compilerはEditPlanから次を導出する。

```text
CompiledTimeline
├─ video segments: output frame ↔ source PTS
├─ audio segments: output sample ↔ source sample
├─ caption spans: output frame ↔ source anchor
└─ presentation spans: output frame ↔ item event
```

映像と音声のmapは分ける。EditPlanへoutput時刻を保存しない。

### 4.6 字幕と文字演出

発話字幕と後付け文字を別オブジェクトにする。

#### Speech Caption

- immutable ASR token IDとsource spanへanchorする
- 1つのSource Clipをまたがない
- tokenを含む場面が消えた場合、隣へ自動移動しない
- trimで一部が外れた場合は`NEEDS_REVIEW`
- anchorが失われた場合は`ORPHANED`となり保存を拒否する

役割は、通常／コメント／引用／強調の4種を初期値とする。

#### Editorial Overlay

- 場面札、後付け状況説明、コメントカードに使う
- Timeline Item内のlocal frame rangeへanchorする
- モンタージュの順番を変えても、その場面と一緒に移動する

### 4.7 構図

Story Beatを分割せず、Presentation Eventで場面内の構図を変える。

初期プリセット:

1. 人物を見せる
2. 元画面を見せる
3. 両方を見せる
4. コメントを見せる

source取込後に一度だけ、人物、元画面、コメント、保護領域を矩形で指定する。未設定の対象を使うプリセットは無効化し、理由と設定導線を表示する。

保護領域には人物の顔、ゲーム内テキスト、HUDを指定できる。Shortsの右側UIと下部説明欄のsafe areaは常時ガイド表示する。

## 5. Candidateを「30秒の塊」から変える

現行の30〜60秒候補をそのまま完成区間にする思想は廃止する。候補selectorは次を返す。

```text
core_span
  面白さの核となるevent / reaction / payoff

context_span
  人間とplannerが前後関係を確認する90〜180秒の範囲

suggested_final_duration
  参考値。完成範囲ではない
```

`core_span`に30秒の下限を置かない。plannerまたは人間がcontextから複数場面を組み、完成15〜60秒へする。

これが「自動検出できた話題」と「実際に面白いShorts」の間を埋める最初の変更である。

## 6. 生成パイプライン

```text
既存の全編ASR
  ↓
core / context候補探索
  ↓
選択候補周辺だけ精密解析
  word timestamp / 無音 / filler / 反復 / scene change
  ↓
EditPlan proposalを1案生成
  ↓
決定論validator
  ↓
人間が差分を採用・修正
  ↓
immutable edit revision
  ↓
同じCompiledTimelineで部分proxy
  ↓
final render / technical QC / join review / content review
```

C2では文字起こし中心の会話構成だけをAI支援する。OCRと映像意味理解はC3、同一テーマ場面の探索はC4で扱う。

全編へ高密度Vision／OCRをかけない。C3でもcandidate周辺の少数frameだけを分析し、画面の出来事を観測していない場合は断定せず`visual evidence未確認`とする。

## 7. AIガチャを防ぐ契約

C2初期は代案を出さない。

1. 生成前に「自然さ優先」など方針を1つ選ぶ。
2. 主案を1つだけ生成する。
3. proposalはcurrent EditPlanを直接変更しない。
4. 人間は差分を見て採用／却下する。
5. 再提案は選択中の未lock箇所だけへ出す。
6. lock済み場面を変えるpatchはvalidatorが拒否する。
7. 却下済み提案と人間修正を、次のproposalのconstraintへ渡す。

AIの自己申告confidenceは表示しない。代わりに次を見せる。

- 使用した文字起こし
- 削る原文と秒数
- 無音・scene changeなどの観測根拠
- 影響する字幕
- 発話途中、否定語付近、大きなsource gapなどのrisk
- 視覚証拠がなく判断できない箇所

AIを再現するのではなく、生成されたproposalとevidenceをfreezeすることで再現性を確保する。

## 8. UI設計

### 8.1 トップフロー

```text
素材 → 候補 → 構成 → 確認
```

候補一覧で常時見せるのは、要約、位置、想定尺、最大riskだけ。Hook、setup、payoff、選定理由は選択中候補で展開する。

### 8.2 構成画面

4ペインを常設しない。1440×900を基準に2カラムへ固定する。

```text
┌────────────────────────────────────────────────────┐
│ 素材 > 候補 > 構成 > 確認   保存状態   構成v7       │
├──────────────────┬─────────────────────────────────┤
│ Viewer 400〜440px│ Story Strip                     │
│ [完成 / 元動画]  │ [つかみ][前振り][反応][オチ]    │
│                  │   3.2秒省略   場面転換           │
│ 完成 00:12.30    ├─────────────────────────────────┤
│ または           │ 選択中の場面                    │
│ 元動画 02:14:37  │ trim / 字幕 / 画面主役 / risk   │
│                  │                                 │
│ 更新前 badge     │ [保存してプレビュー更新]        │
└──────────────────┴─────────────────────────────────┘
```

Viewerは完成と元動画を明示切替する。同じ画面へ2つのrulerを重ねない。元文脈の文字起こしと波形はdrawerで開く。

### 8.3 ユーザーが使う言葉

内部語の`split / merge / role`を主要ラベルにしない。

1. `＋ 元動画から場面を追加`
2. `場面を短くする`
3. `ここで場面を分ける`
4. `字幕を直す`
5. `何を大きく見せるか`

常時見せるのは、再生、選択、trim handle、Undo／Redoだけ。残りは選択中場面のcontextual actionとして出す。

`隣とまとめる`は、同一sourceの連続・隣接場面にだけ詳細メニューで出す。Story roleの変更も詳細へ置き、普段はAIが付けた`つかみ／前振り／反応／オチ`を読むだけにする。

### 8.4 削った範囲

2時間素材のgapを時間比例表示しない。

```text
[場面1]  [3.2秒省略]  [場面2]
[場面2]  [32分14秒を省略]  [場面3]
```

省略chipを押すと、境界前後の原文、波形、原音を確認できる。復元は元文脈drawer内で行う。

### 8.5 即時確認と正確な確認

Browser draftの役割を限定する。

- 選択場面の字幕、crop、trim候補の即時確認に使う
- テンポ、join、衝突、内容承認には使わない

proxyは低解像度の別実装にしない。finalと同じCompiledTimeline、canvas、fps、font、改行、filter graph、audio sample rateを使い、encoder presetと部分cacheだけを軽くする。

構成変更後の古いproxyには`更新前`を明示する。主要CTAは`保存してプレビュー更新`の1つにし、保存revisionを固定してからproxyを作る。

## 9. 音声join

BGM／効果音の自動選曲は後回しにするが、元音声のjoin確認はC0から必要である。

C0〜C2で許可するのは次だけ。

- hard cut
- output尺を変えないclick防止用micro fade-out / fade-in

creative crossfade、J/L cut、room tone生成は後回しにする。重ねるcrossfadeはsource/output対応を多対一にするため、専用のaudio map設計後に追加する。

全joinで境界前後300〜500msをloop auditionできるようにし、次を警告する。

- 発話中のcut
- 語頭・語尾に近すぎるcut
- 大きなlevel差
- 原音BGMが継続している箇所
- 音声handle不足
- 否定語・接続語付近
- 大きなsource gapまたは順番変更

flagがないことは安全保証ではない。全joinを人間が確認しない限り、最終内容確認へ進めない。

## 10. Revision・render安全性

既存caption workflowの、immutable directory、current pointer、atomic publish、stale render拒否、technical/content review分離を設計パターンとして再利用する。

ただしv4のschemaは新規に作る。

- v1/v2 job: 従来どおりread-only
- v3 job: 現在の字幕editorを維持
- v3から構成編集へ進む場合: 元jobを変えず、新しいv4 projectを作る
- 自動migration: しない

render identityへ含めるもの:

- normalized render-input hash
- source hash
- style presetの内容hash
- 使用media asset hash
- compiler version
- render profile version

AI理由、analysis revision、review状態はrender bytesへ影響しないためrender identityへ含めない。reviewは対象render identityへ紐付ける。

同じPlanから同じMP4 bytesになることは保証しない。保証するのは、同じnormalized Planとcompilerから同じCompiledTimeline、frame/sample mapping、filter graph、caption layoutが得られることである。実MP4のoutput hashは別途記録する。

## 11. 段階実装

### C0: EditPlan kernel

UIもAIも作らない。まず編集表現とrenderを成立させる。

成果物:

- EditPlan schema / validator
- source clock normalization
- video/audio timeline compiler
- Speech Caption / Editorial Overlayの投影
- 4つのlayout preset renderer
- Join Edgeとmicro fade
- render-input snapshot
- compiled-timeline artifact
- immutable edit artifact publish
- 明示revisionからrenderするCLI

手書きPlanで再現する3ケース:

1. 連続会話＋意味字幕
2. 同じ場面内の画面主役切替
3. 非連続3場面＋場面札

C1へ進むgate:

- 3ケースを外部NLEなしでrenderできる
- 同じnormalized Planから同じCompiledTimeline hashを100回得る
- orphan caption、未解決anchor、無所属joinがあればcompile拒否する
- proxyとfinalでcut、字幕、layout eventが同じoutput frameになる
- stale revisionをcurrentとして表示しない
- 2時間級sourceでRange seekと60秒proxy生成時間を実測する
- v3 jobの既存bytesを変更しない

### C1: Manual Story Composer

既存candidateから新規v4 projectを作り、人間が構成を完成できるUIを作る。

必要機能:

- `元動画から場面を追加`
- trim、分割、除外、復元、Undo／Redo
- manual montage reorder
- Story Beat表示
- Speech Caption編集
- Editorial Overlay／場面札
- source region／protected region設定
- 4 layout presets
- join auditionとjoin review
- same-geometry proxy
- immutable revision比較
- final renderとtechnical/content review

候補採用時にcandidate周辺のword timestamp ASRを行う。C1ではVision/OCRを使わず、コメント文字とsource regionsは人間が入力する。

C1完了gate:

- 主要操作がすべてUndo可能
- revision保存失敗とproxy失敗から正常に復帰できる
- 全join確認とfull content reviewを別々に記録できる
- 対応範囲内で、時刻手入力や外部NLEなしに3構造を組める
- 同一作業を外部NLEと比較し、median active timeを30%以上短縮する
- content review後の意味事故を増やさない

### C2: transcript中心のAI構成planner

C1をAIなしで成立させた後に追加する。

初期対象はdialogue stagingだけ。入力はword ASR、無音／filler／反復候補、候補のhook/setup/payoff、scene change時刻。主案1つをimmutable proposalとして返す。

C2完了gate:

- manual C1比でmedian active finishing time 50%削減を目標とする
- 25%も削減できなければC2昇格を止める
- lock違反patch 0件
- 却下済み提案の再導入 0件
- 意味変更join、語切れ、発言元誤認 0件
- needs_review未解消ではfinal content reviewへ進めない
- importから最初の編集可能Planまでのwall timeも別記録する

### C3: 局所Vision／OCR

候補周辺だけframeとOCRを使い、event reactionを支援する。

- ゲーム文字を読ませる瞬間の提案
- source region矩形の提案
- 字幕とprotected regionの衝突警告
- 人物／元画面／コメントの主役切替提案

自動追跡を品質保証しない。人間が1操作で修正できることを優先する。

### C4: Montage探索

同一テーマの弱い場面を複数探して束ねる。探索コストと誤判定が最も高いため最後に検証する。

## 12. 初見UIテスト

ready状態のprojectを渡し、説明書なしで次を行ってもらう。

1. 場面の終わりを再生位置まで短くする
2. 無駄な間の前後で分け、一方を外す
3. Undoで戻す
4. 誤字幕を直し、コメント表示へ変える
5. 画面主役を人物から元画面へ変える
6. 元動画の別位置から場面を追加する
7. 保存し、最新proxyを確認する
8. joinを試聴して確認済みにする

暫定合格:

- 主要5操作の4つ以上を外部説明なしで完了
- source時刻と完成時刻の取り違え 0件
- 保存版と未保存draftの取り違え 0件
- 素材や過去revisionを失う操作 0件
- raw時刻の手入力 0回

最初にユーザー本人の画面録画＋think-aloudを1回行う。可能なら、その後に初見3名で同じテストを行う。所要時間の目標値は、最初の実測後に固定する。

## 13. 評価素材の作り方

今は参考Shortsを大量収集しない。

4本は編集文法の観察資料として固定する。参考完成動画だけでは、元配信から何を削ったかという正解を検証できず、fixture権利も別問題だからである。

次に作るのは、権利確認済み素材による次の小さな評価セットである。

### 品質fixture

- 設計用3project: 3構造を1つずつ
- 完全未使用holdout 3project: 3構造を1つずつ

同じ長尺素材から別topicを取ってもよいが、project間で核となる場面は分離する。各projectにreference Planと、Planから独立したquality constraintsを持たせる。

Quality constraints:

- 必ず含めるevent／reaction／payoff
- 削除すると意味が変わる発言
- 発言元
- 守るべき顔・ゲームUI
- 許容できるcut範囲
- joinで切ってはいけない語
- 視聴後のcomprehension質問

gold Planとの完全一致は求めない。複数の正しい編集を許容する。

### 技術fixture

権利問題のない合成素材で次を作る。

- VFR＋非ゼロstart PTS
- audioがvideoより先行
- 発話途中の危険join
- 原音BGMが継続するjoin
- Generated Cardを含むoutput-only item
- token anchorがtrimでorphanになるケース

### 権利manifest

- 閲覧・分析許可
- ローカル編集再現許可
- fixtureとして反復利用する許可
- team／repoへ保存する許可
- 外部AIへ送れるpayload
- 出力を共有・配布できる範囲

長尺動画はrepoへ入れず、local manifestにpathとhashを持たせる。

6projectで商用品質一般化を証明することはできない。しかしMVPの停止判断には十分である。この結果が出るまで、参考Shortsを追加収集しない。

## 14. 比較評価

同じ素材から次を作る。

- A: 現行の連続切り抜き
- B: C1で人間が作った構成
- C: AI初稿を人間が仕上げた構成
- D: 必要な局面だけCapCut／Premiere等で同じ作業をした基準

見る指標:

- Hookからpayoffまで理解できるか
- 不要な間と反復
- cutで主語、否定、因果が変わっていないか
- その瞬間の視覚的主役
- 字幕の情報源と読みやすさ
- join音声の自然さ
- active editing time
- wall time
- AI案からの構造変更率
- Undo回数
- 外部NLEへ出た作業
- 視聴後comprehension

AIのbeat採用率だけは使わない。巨大なbeatを作るだけで高くできるためである。

## 15. 停止条件

次の場合、次phaseへ進まず設計または製品方針を見直す。

- 手書きEditPlanで3構造の1つでも再現できない
- 同じPlanから異なるCompiledTimelineが生じる
- captionを無言で別clipへ再anchorする必要が生じる
- proxyとfinalでcut、字幕、layoutが1frame以上ずれる
- 未確認joinを含むfinalを内容確認可能にしてしまう
- C1主要操作にraw時刻入力または外部NLEが必要
- pilot要求の20%以上がMVP対象外機能を必要とする
- UI要求を解くためfree layer、keyframe、track追加が必要になる
- C1が外部NLEよりactive timeを30%以上短縮しない
- C2がmanual C1よりactive timeを25%以上短縮しない
- holdoutで意味変更、発言元誤認、語切れを公開前に捕捉できない
- 分析許可しかない素材をfixtureへ転用する必要が生じる

C1が時短できなければ、独立編集製品ではなく、NLE向けEditPlan／EDL出力への方向転換を検討する。

## 16. 現行実装の再利用と新規境界

### 再利用する

- local uploadと権利確認
- source hashとpath confinement
- 全編ASRとcandidate runの再開性
- Range配信と粗い候補seek
- immutable artifact、atomic current pointer
- 明示revisionからのrender
- stale render拒否
- technical QCとcontent reviewの分離
- render履歴とlast known-good保持
- 字幕の細かい±0.1秒調整

### 新規に分離する責務

- EditPlan schema / validator
- edit artifact publish
- source clock normalization
- timeline compiler
- composition renderer
- proposal/diff/lock validator
- same-geometry partial proxy
- Story Strip state
- source context viewer
- join review

既存の大きな`app.js`へ構成stateを直接積み増さない。framework全面移行はしないが、composition、preview、source context、API clientをES module等へ分割する。

想定する新規module名は、実装前の責務レビューで確定する。

```text
short_factory/
  editplan_schema.py
  editplan_artifacts.py
  editplan_compiler.py
  composition_rendering.py
  webui/
    composition.js
    composition-preview.js
    composition-source.js
    composition.css
tests/
  test_editplan_schema.py
  test_editplan_compiler.py
  test_editplan_artifacts.py
  test_composition_rendering.py
```

## 17. 2周レビューでの裁定

中立・対立レビューの両方から採用したもの:

- 既存の安全なrevision構造は再利用するが、v4 schemaは新設する
- 汎用NLEではなくStory Stripにする
- AIより先に、人間が直せるEditPlanとrendererを作る
- 全編Visionを避け、候補周辺だけ深掘りする
- source/output時刻とSpeech/Editorial文字を分離する
- preview fidelityとaudio joinを構成品質の一部として扱う
- referenceとholdoutを実装前に固定する

第2周で修正したもの:

- `1 beat = 複数range`を撤回し、意味・場面・演出の3層へ分離
- C2の代案2つを削除し、主案1つ＋局所patchへ限定
- 低解像度proxyをやめ、finalと同じgeometry／filter graphを使う
- C2からOCR／映像意味判断を外し、C3へ移動
- C1の「外部NLE不要」をMVP対応範囲内へ限定
- AI confidenceではなく観測根拠とriskを表示
- current caption revisionとcurrent edit revisionの二重管理を禁止

## 18. 次の承認点

次に実装するなら、承認対象はC0だけにする。

C0着手前に確定するもの:

1. MVP対象をVTuber／ゲーム配信へ限定すること
2. 完成尺15〜60秒、単一source、最大24 clipsで開始すること
3. C0ではBGM／SFX、自動Vision、AI planner、UIを作らないこと
4. 権利確認済みの設計用3projectとholdout 3projectを固定すること
5. C0の3構造再現とcompiler安全gateを通るまでC1へ進まないこと

この順なら、特定Shortの見た目へ過適合せず、「構成を保存・再現・修正できる器」が先に完成する。AIはその器の初稿作成者として後から交換・改善できる。
