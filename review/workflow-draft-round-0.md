# 長時間動画から高品質Shortsを作る将来ワークフロー — Draft 0

## §0. 文書の位置付け

これは実装指示ではなく、今回のPhase -1定性テストから得た知見を次の制作工程へ変換するための設計初稿である。
この文書のレビュー中はPhase 0a以降のproduct codeを変更しない。

正式対象は `D:\HermesWorkspace\client-short-factory`、開発者は1人、実行環境はWindowsローカル1台、当面のクライアントは1〜2社とする。

## §1. 今回確認できた事実

### §1.1 観測済み

- 許可済みの約8,555秒のローカル動画を、低負荷設定で約21分18秒かけて全編文字起こしできた。これは無人待ち時間である。
- transcript-onlyで5候補を作り、50.21秒の候補を通常jobへ渡せた。
- 1080x1920のMP4、字幕、technical QCまで既存CLIで完走した。
- 人間の字幕確認active timeは5分だった。
- ユーザー評価は「字幕の約90%は良好で、細部は直したくなる」だった。
- 対象動画の公開Most Replayed heatmapは、複数の公開player clientで取得できなかった。heatmapは補助信号であり必須入力にできない。
- ユーザーは完成した連続区間を見て、システム面は概ね成功と評価した。

### §1.2 ユーザー自己申告であり、正式計測ではないもの

- 長時間動画を人間が通して見て区間を探すと約2時間かかりそうである。
- 今回の一人語り素材は、一定区間をそのまま抜く方式ではShortsとしてのテンポを作りにくい。
- 気持ちよい結果には、無音・言い直し・間を細かく詰める人間の編集判断が必要に感じられた。

### §1.3 今回から導く仮説

ボトルネックは字幕だけでも区間選定だけでもない。次の3つを分離しないと品質が頭打ちになる。

1. source自体が切り抜き向きか
2. 話として良い候補がどこか
3. 候補を連続区間のまま使うか、複数のkeep rangeへ圧縮するか

この仮説は2素材以上のA/B previewで検証するまでproduct要件として固定しない。

## §2. 目的と完了像

### §2.1 目的

ユーザーが長時間sourceを通して見ずに、AIが提示した最大5本の短いpreviewだけを見て、次のいずれかを決められる状態にする。

- そのまま切り抜く
- テンポ編集して切り抜く
- このsourceからは作らない

### §2.2 完了像

- AIは0〜5候補を返せる。0件は正常結果である。
- 各候補に `連続切り抜き`、`テンポ編集`、`見送り` の推奨modeと根拠がある。
- `テンポ編集` はsource順を変えない複数keep rangeとして表現し、削除箇所を追跡できる。
- 人間は候補採否、意味が変わるcut、字幕の細部、最後の全編再生だけを確認する。
- AIのnumeric scoreだけで完成扱いにしない。
- technical QCと内容確認を別の状態として保持する。

人間作業を何分まで減らせるかは未検証である。Creative Spikeでは候補確認、テンポ修正、字幕修正、最終確認を別々に測る。

## §3. 保持する安全条件

### §3.1 既存の3条件

- S-01: current字幕より古いrenderを完成版として承認・納品用取得できない。
- S-02: technical QCを内容確認済みとして表示しない。
- S-04: 保存済み字幕と最後の正常成果物を失わない。

### §3.2 multi-cutに伴う未解決点

editableなcut recipeをproductへ入れると、字幕だけでなくcut recipe変更後の旧renderもstaleになる。
現行の `output_hash + caption_revision` 契約だけで十分かは未検証である。

このためCreative Spikeのmulti-cutはscratch artifactとしてのみ作り、approval・download・deliveryへ接続しない。
product化する場合は、次のどちらか一つを別gateで選ぶ。

1. captionとcut recipeを一つのimmutable edit revisionへまとめる。
2. cut timing変更ごとに新jobを作り、job内ではrecipeを変更不可にする。

両方は実装しない。選択前にS-01 / S-04の操作列テストを書けない場合、multi-cutのproduct化を落とす。

## §4. 制作ワークフロー

### §4.1 Gate R — 権利と外部AI利用

1. source pathまたは許可済みURLを記録する。
2. `edit_permission_checked` と `acquisition_method` を確認する。
3. Codex/Hermesが扱うpayloadを `transcript`、`audio`、`frames`、`public metadata` ごとに記録する。
4. 未許可payloadは開かず、該当分析をskipする。

権利不足はsource不適合ではなく `rights_blocked` として終了する。

### §4.2 Stage A — source triage

機械側は、許可された範囲だけで次を集める。

- duration、音声有無、既存chapter、任意の公開heatmap
- timestamp付きtranscript
- speech density、長い無発話、フィラー、言い直しの分布
- frames許可時だけ、scene変化と画面情報の密度

出力は `source-assessment.json` とし、結論を次の3つから選ぶ。

- `straight_cut_likely`
- `pace_edit_likely`
- `reject_likely`

公開heatmapが無いことはwarningであり、停止条件ではない。分類理由と反証条件を文章で残し、AI scoreだけを見せない。

### §4.3 Stage B — story candidate

AIはtimestamp付きtranscriptから0〜5件を返す。各候補は次を持つ。

- source start / end
- 想定output duration
- hook、setup、payoff
- 前提知識への依存
- ASR修正risk
- 推奨edit mode
- 0件にした場合の理由

候補はsource時間順の範囲内に収め、範囲外timestampをvalidatorで拒否する。

### §4.4 Stage C — edit recipe

#### 連続切り抜き

`keep_ranges` は1件だけ。意味が閉じ、間と発話密度がそのままでも成立する候補に使う。

#### テンポ編集

`keep_ranges` は2件以上で、次の制約を持つ。

- source時間順を維持し、並べ替えない。
- overlapせず、候補source span内に収める。
- 各削除に `silence`、`filler`、`repetition`、`false_start` の理由を付ける。
- 否定語、主語、対象、結論を変えるjoinは自動確定しない。
- word boundaryに不確実性があるcutはhuman review対象にする。
- 削除前後のsource timeをpreviewから確認できるようにする。

0.1秒単位のcutを数多く作ること自体を品質とみなさない。cut数ではなく、意味を保ったまま不要な待ち時間を減らせたかで判断する。

### §4.5 Stage D — rough preview

Creative Spike中だけ、同じ候補から次のA/Bを作る。

- A: 連続区間のbaseline
- B: source順を保ったテンポ編集版

両方に同じcaption styleと音量基準を使い、比較変数をcut timingに限定する。hard cutでclickが出ない最小audio crossfadeを使い、cut位置はsource mapへ残す。

通常運用へ移った後はA/Bを毎回作らず、選択されたmodeだけをrenderする。

### §4.6 Stage E — human review

人間は長時間sourceではなく、最大5候補のpreviewだけを見る。

1. candidateを採用、見送り、またはsource全体をrejectする。
2. テンポ編集の場合、意味が変わるjoinと不自然な間だけを確認する。
3. 字幕本文と固有名詞を修正する。
4. renderを明示実行する。
5. technical QCと内容確認を別々に見る。
6. current renderを先頭から末尾まで一度だけ再生する。
7. 承認はcurrent inputと一致するrenderだけに行う。

### §4.7 Stage F — style preset

初期はgeneric style editorを作らず、clientごとに1つの固定presetをfileで持つ。

- font
- 文字サイズ、縁、影
- 通常語と強調語の色
- cutを隠すための小さなpunch-in preset
- 効果音を使うかどうか

styleのA/BはCreative Spikeのcut timing検証と混ぜない。テンポ編集の効果を確認した後に、1つのpresetだけ作る。

## §5. mode判定

| mode | 必要条件 | 主な警告 | system action |
|---|---|---|---|
| 連続切り抜き | hookからpayoffまで意味が閉じ、長い無音や反復が少ない | 冒頭文脈依存、固有名詞 | single range preview |
| テンポ編集 | 話は成立するが、間・フィラー・言い直しで速度が落ちる | joinで意味が変わる、cut過多 | monotonic keep ranges preview |
| 見送り | 独立したhook/payoffがない、前提が区間外、編集しても価値が立たない | AIが無理に候補数を埋める | 0候補またはsource reject |

visual変化が少ないだけで自動rejectしない。強い話なら一人語りでも成立する。逆に、scene変化が多くても話が閉じなければ採用しない。

## §6. 最小artifact

Creative SpikeではDBやAPIを作らず、scratch内のJSONだけを使う。

```text
source-assessment.json
candidates.json
edit-recipe.json
preview-baseline.mp4
preview-paced.mp4
source-map.json
spike-result.md
```

`edit-recipe.json` の最小形:

```json
{
  "version": 1,
  "source_id": "...",
  "candidate_id": "...",
  "mode": "contiguous|paced",
  "source_span": {"start": 0.0, "end": 0.0},
  "keep_ranges": [
    {"start": 0.0, "end": 0.0, "reason": "story|silence|filler|repetition|false_start"}
  ],
  "semantic_risks": [],
  "human_review_required": true
}
```

## §7. 品質gate

### §7.1 Creative Spikeの採用条件

2つの許可済みsourceで確認する。少なくとも1つはゆったりした一人語り、もう1つは連続切り抜き向きと思われる高密度素材にする。

- ユーザーがslow-talk素材でpaced版をbaselineより良いと判断する。
- 意味が変わったjoinが0件である。1件でもあれば修正して再確認する。
- candidate reviewとpacing修正の合計active timeを記録する。
- 2素材のどちらでもpaced版が選ばれない場合、multi-cut自動化をproduct scopeから落とす。
- source rejectが妥当だった場合、0候補は成功結果として記録する。

時間短縮の合格値は初回2素材を測ってから決める。ユーザーの「約2時間かかりそう」は正式baselineとして計算に使わない。

### §7.2 product時のgate

- technical QC success
- current caption revisionとrenderの一致
- multi-cutをproduct化した場合だけ、current edit inputとの一致
- human content review complete
- full playback complete

どれかが欠ければ承認・納品用downloadを無効化する。

## §8. 計測するhuman active time

- `candidate_review_active_min`
- `pacing_correction_active_min`
- `caption_active_min`
- `final_review_active_min`
- `recovery_active_min`

併記するoutcome:

- source classification: straight / paced / reject
- candidate count
- adopted candidate
- adopted mode
- human-discovered semantic cut errors
- caption edit count
- final verdict: baseline / paced / neither

chat待ち、transcription、render、agent思考などの無人時間はactive timeへ含めない。

## §9. 実行順と承認gate

### Phase W0 — 計測protocol改訂（0.25日）

- 今回のPhase -1を「定性成功、元のrange-vs-caption式は未成立」と正式に閉じる。
- source suitability、candidate review、pacing correctionを新しい測定項目として追加する。
- product code変更なし。
- 文書改訂をユーザー承認して停止する。

### Phase W1 — Creative Spike B（0.5〜1日）

- scratchだけでbaseline / paced A/Bを作る。
- current slow-talk候補と、別の許可済み高密度source 1本を使う。
- approval、download、deliveryへ接続しない。
- 結果を報告し、multi-cut product化の採否で停止する。

### Phase W2 — Phase 0a 最小安全kernel（2〜3日）

- S-01 / S-02 / S-04の最小実装に限定する。
- caption revision、immutable render、current pointer、global OS lock、3境界fault test、180秒制約。
- W1でmulti-cutが採用されても、このPhaseへcut editorを混ぜない。

### Phase W3 — Offline candidate / source triage（1〜2日）

- timestamp transcriptから0〜5候補とsource assessmentをJSON出力する。
- DB、API、candidate専用UIを作らない。
- 3jobで2job以上candidate採用となるまでUI化しない。

### Phase W4 — multi-cut最小統合（1〜2日、W1採用時だけ）

- §3.2のrevision方式を一つだけ選ぶ。
- monotonic keep rangesとsource mapだけを実装する。
- generic timeline、並べ替え、B-roll、face trackingは作らない。

### Phase W5 — 最小review UI（2〜3日）

- current video再生
- candidate採否
- plain caption text edit
- paced mode時だけcut joinの前後preview
- explicit render、technical/content別表示、full review、approval

### Phase W6 — style preset 1個（0.5〜1日）

- 1つのfont / color / punch-in presetをfileで固定する。
- style editorは作らない。

### Phase W7 — internal pilot（1日）

- authorized source 1本でrightsからfinal reviewまで完走する。
- clientへ実送付せず、active timeと失敗復旧を記録する。

各Phaseは一承認で止め、後続の包括承認と解釈しない。

## §10. 見積と予算

| Phase | 見積 |
|---|---:|
| W0 | 0.25日 |
| W1 | 0.5〜1日 |
| W2 | 2〜3日 |
| W3 | 1〜2日 |
| W4 | 1〜2日（条件付き） |
| W5 | 2〜3日 |
| W6 | 0.5〜1日 |
| W7 | 1日 |

条件付きW4を含む合計は8.25〜13.25日。15人日を超える見込みになったら、最初にW6、次にW5のcut preview UI、次にW4のproduct統合を落とし、scratch運用へ戻す。S-01 / S-02 / S-04は落とさない。

## §11. 停止条件

- 権利entryまたは対象payload許可が不足している。
- sourceから意味の閉じたcandidateを作れない。
- paced cutが意味を変えるが、自動で反証できない。
- Creative Spikeでpaced版が採用されず、修正時間も減らない。
- multi-cut revision方式を一つに絞れない。
- Phase見積が上限を超え、削除対象を特定できない。
- Phase 0a以降のproduct codeについて明示承認がない。

## §12. 初期に実装しないもの

- generic NLE timeline
- sceneの並べ替え
- B-roll自動生成・自動挿入
- 顔追跡、話者追跡
- 自動投稿・自動delivery
- DB、queue、複数worker
- client portal
- style editor
- numeric AI quality scoreによる自動承認

## §13. 未解決のまま次のreviewへ渡す論点

1. 2素材のCreative Spikeだけでmulti-cut product化を判断してよいか。
2. editable cut recipeをcaptionと同じrevisionへ含めるか、新jobとして固定するか。
3. source triageが全文transcription前に有効なreject判断を出せるか。
4. W2がUIなしでも単独で価値を持つPhase境界になっているか。
5. 1つのstyle presetが品質差を測るのに十分か。
