# Hermes Video Workflow 実装設計書

> 文書状態: Final v2.0 — ソロ開発・未納品段階へ前提修正  
> 正式対象: `D:\HermesWorkspace\client-short-factory`  
> 作業ミラー: `C:\Users\higes\codex\client-short-factory`  
> 更新日: 2026-08-07  
> 注意: 本書は実装計画であり、外部レビューや実運用実績による保証ではない

## 1. 経営判断

前版は、チーム開発、監査、複数顧客、事故後の賠償リスクを先回りしすぎていた。実際の前提は次のとおりである。

- 開発者は1人、コードレビュアーはいない
- WindowsローカルPC 1台で動かす
- 当面のクライアントは1〜2社
- 納品実績は0本、事故歴も0件
- 現行実証は54.5秒の動画1本だけ

したがって、最初に作るべきものを設計書だけで断定しない。製品コードを書く前に **Phase -1** を実施し、既存CLIを使った1〜2本の手作業から、区間判断と字幕修正のどちらが本当のボトルネックかを測る。

実装順は次のように変更する。

1. Phase -1で人間の実作業時間を測る
2. Phase 0aで、半日分の作業消失と誤った完成版だけを防ぐ
3. 計測結果に応じて「字幕エディタ優先」または「候補提示優先」へ分岐する
4. 1本を内部pilotとして完走する
5. 実データで必要になった仕組みだけをPhase 0bまたは後続phaseへ昇格する

コア方針は「10分で戻せる失敗には設計を足さない」である。

### 1.1 主な用語

- `render`: 動画を書き出す処理、またはその出力
- `revision`: 字幕などの版番号
- `current`: 現在作業対象として選ばれている版
- `immutable`: 作成後に同じfileを上書きしないこと
- `atomic`: 途中状態を見せず、一度に切り替わる更新
- `active time`: 人が実際に操作・判断・視聴している時間
- `QC`: Quality Control。機械的な品質検査
- `stale render`: 現在の字幕revisionより古い動画
- `cue`: 一つの字幕表示区間
- `hash`: file内容から作る識別値
- `control plane / data plane`: 操作層 / 実処理層
- `spike`: 不確実性だけを短時間で確かめる小規模実証
- `pilot`: 本運用前の試行
- `hard gate / warning / outcome`: 必須条件 / 注意表示 / 公開後の結果
- `backlog`: 条件成立まで後回しにする項目
- `review receipt`: 人間がどの動画を確認したかを残す確認記録

## 2. 実務レベルの定義

### 2.1 事故コストによる判断

| 失敗時の影響 | 判断 |
|---|---|
| 10分以内で作り直せ、クライアントへ影響しない | 設計で防がない。手順書で戻す |
| 10分を超えるが半日未満 | 一度記録し、同種が短期間に再発したら昇格を判断 |
| 半日分の作業が消える | 最初から防ぐ |
| 誤納品など、クライアントへ謝る事態になる | 絶対に防ぐ |

### 2.2 残す安全不変条件

不変条件は次の3つだけとする。番号は前版との比較のため維持する。

| ID | 不変条件 | 最小判定 |
|---|---|---|
| S-01 | stale render（現在の字幕より古い動画）を完成版として承認・納品用取得できない | `caption_revision` がcurrentと一致し、MP4の `output_hash` がrender記録と一致する場合だけ承認・納品用取得可能 |
| S-02 | 技術QC（機械検査）と内容確認を混同しない | `技術検査 合格 / 内容確認 未完了` を別表示し、人間確認前は完成扱いしない |
| S-04 | 失敗しても保存済み字幕を失わない | revision（版番号）保存後は、画面更新・render失敗・再起動後も復元できる |

S-03、S-05〜S-10は削除せず、§25のbacklog（後回し一覧）へ移す。

## 3. 目的と非目的

### 3.1 達成すること

- 許可済みのローカル動画または既存CLIの対応入力から縦型Shortsを作る
- 区間判断、字幕修正、最終確認の実時間を測る
- 保存済み字幕revisionを明示指定して再renderする
- 最新字幕と一致する動画だけを完成版として扱う
- 技術QCと人間の内容確認を分ける
- 納品後の修正依頼を、元の納品版から新revisionへ派生させる

### 3.2 初期に実装しないもの

- DB、Redis、分散queue、WebSocket、SSE
- 複数PC、複数operator、同時編集
- 複数jobの同時render
- 汎用NLE、scene並べ替え、字幕timing編集、話者分離、顔追跡
- 自動投稿、client portal、請求、通知
- 自動cache削除
- 全commit境界のcrash test
- 汎用legacy migration
- immutable attestation store
- 全artifactを結ぶhash DAG
- 常設chat、総合AI品質score

## 4. 確認済みbaselineと未検証の仮説

### 4.1 確認済み

現行 `client-short-factory` は次を実装済みである。

- `acquire -> audio -> transcribe -> subtitles -> render -> qc`
- 指定区間取得と、失敗時の検証付き全編cache
- ローカル `faster-whisper` による日本語文字起こし
- 辞書補正、字幕分割、SRT/ASS/JSON生成
- 1080 x 1920、H.264/AAC、字幕焼き込み
- `--rerun-from` による工程再開
- ffprobe、全編decode、字幕ruleの技術QC

現行実証は54.5秒、字幕23cue、技術QC合格である。一方、`semantic_transcript_accuracy_checked=false`、`human_caption_review_required=true` で、「アマースクーム」「チートミトル」など明白な誤認識が残る。

### 4.2 未検証

「主要な人間ボトルネックは字幕レビューである」は仮説であり、事実ではない。根拠は実証1本だけで、区間選定に要した時間も比較計測されていない。

次のどちらもあり得る。

- Whisper精度が十分低く、字幕修正が最大コスト
- 字幕修正より、長時間素材から使う区間を決める方が高コスト

この不確実性は設計議論ではなくPhase -1の実測で解く。

## 5. Phase -1 — ボトルネック計測

### 5.1 期間と方法

- 想定: **0.5日**
- 製品コードは書かない
- 現行CLIと現行の手修正手順で、許可済み素材1〜2本を最初から最後まで完走する
- 既存54.5秒jobは参考にできるが、時間記録なしの過去作業を測定値へ混ぜない

成果物:

```text
measurements/phase-minus-1.csv
measurements/phase-minus-1-notes.md
```

CSV列:

| 列 | 定義 |
|---|---|
| `job_id` | 計測job |
| `source_duration_min` | 確認対象になった元素材の尺 |
| `short_duration_sec` | 完成尺 |
| `range_active_min` | 素材を探し、開始・終了を判断・入力したactive time（人が操作・判断した時間） |
| `caption_active_min` | 原音確認、誤字探索、字幕修正のactive time |
| `final_review_active_min` | 最終内容確認のactive time |
| `acquire_wait_min` | 取得待ち。人の時間と分ける |
| `transcribe_wait_min` | 文字起こし待ち |
| `render_wait_min` | render待ち |
| `recovery_active_min` | error復旧の人間操作 |
| `caption_edits` | 修正cue数 |
| `range_alternatives` | 比較した候補区間数 |
| `notes` | 迷い、例外、外部editor退避 |

30秒を超える放置時間はactive timeへ含めない。動画を聞きながら確認している時間はactive timeに含める。

### 5.2 数値分岐

各job `i` の字幕時間を `C_i`、区間判断時間を `R_i` とする。1〜2本しかない段階で平均値一つに賭けない。

| job単位の判定 | 条件 |
|---|---|
| 字幕優勢 | `C_i >= 10分` かつ `C_i >= 1.5 × R_i` |
| 区間判断優勢 | `R_i >= 10分` かつ `R_i >= 1.5 × C_i` |
| 小差・両方軽い | 上記以外 |

branch（実装分岐）は次で決める。

| 分岐 | 条件 | 次に作るもの |
|---|---|---|
| 字幕エディタ優先 | 2本とも「字幕優勢」 | Phase 1A |
| 候補提示を検証 | 2本とも「区間判断優勢」 | Phase 1B0のoffline spike |
| 未確定 | 1本しか測れない、2本の判定が割れる、または小差を含む | Phase 1Mだけを作り、累計3本で再判定 |

累計3本での再判定は、`C = median(C_i)`、`R = median(R_i)` とし、`C >= 10分 && C >= 1.5R` ならPhase 1A、`R >= 10分 && R >= 1.5C` ならPhase 1B0、それ以外はPhase 1Mを維持する。

完成尺や元素材尺が大きく違う場合の誤読を避けるため、`caption_active_min × 60 / short_duration_sec` と `range_active_min × 60 / source_duration_min` もnotesへ併記する。ただし、機能が実際に削るのは1jobあたりの総active timeなので、branch gateは上表の実時間を使う。累計5本でも平均ではなくmedian（中央値）で再評価する。

## 6. システム境界

Hermes Dashboard pluginをcontrol plane（操作層）、現行CLIをdata plane（実処理層）とする原則は維持する。

```text
Hermes Dashboard
  -> thin plugin
       -> fixed API request
            -> existing/local Python CLI
                 -> acquire / transcribe / subtitle / render / QC

job files
  -> caption revision
  -> immutable render
  -> review / approval record
```

境界:

- Hermes coreは変更しない
- media処理をpluginへ複製しない
- pluginは固定argvを `shell=False` で起動する
- 初期版は1操作だけ。queueを作らない
- 外部Whisper fallbackと自動投稿は行わない

## 7. 最小file契約

```text
jobs/<job-id>/
  job.json                              # source、range、preset。Phase 1では作成後変更しない
  source/acquired.mp4
  transcript/raw.json
  subtitles/
    revisions/
      000001/captions.json
      000002/captions.json
    current.json                        # current caption_revision
  renders/
    <render-id>/
      short.mp4
      qc.json
      render.json                       # caption_revision, output_hash, qc_passed
  current_render.json                   # atomic pointer（一度に切り替わる参照file）
  approvals/
    <approval-id>.json                  # review receipt、approval、手動deliveryの記録
  logs/pipeline.log

RIGHTS_AND_USAGE.md                     # project全体で1枚の手動記録
scratch/candidate-runs/<run-id>/         # Phase 1B0だけ。選択後は通常jobへ移る
  transcript.json
  candidates.json
```

### 7.1 字幕

- `captions.json` はschema v1と `revision`、stableなcue ID、start/end/textを持つ
- revision directoryは作成後に上書きしない
- 新revisionを一時directoryへ書き、検証後にrenameし、最後に `current.json` をatomic replaceする
- machine transcriptはrevision 1を一度だけ作り、human revisionを上書きしない
- 納品後修正の依頼元、受領時刻、依頼文は新revisionの `change_request` metadataへ保存する
- SRT/ASSはrender時にcurrentではなく、明示されたcaption revisionから派生する

### 7.2 render

- `render-job --caption-revision <rev>` を追加する
- `renders/.tmp-<render-id>/` で生成・最低QCを完走した後だけ正式directoryへrenameする
- `current_render.json` は正式publish後だけ更新する
- render directoryは作成後に上書きしない
- 旧renderは少なくともjob完了・修正依頼終了まで残す

### 7.3 hashの縮退

承認判断に使うhashは `output_hash` だけで、版の判断は `caption_revision` だけとする。

```json
{
  "render_id": "render-003",
  "caption_revision": 4,
  "output_hash": "sha256:...",
  "qc_passed": true
}
```

QC hash、manifest hash、review hash、approval hash、tool/driver hashをつなぐDAGは作らない。tool versionは診断logへ残すだけで、承認gateにしない。

## 8. 状態、lock、復旧

### 8.1 UI状態

大きなworkflow state machineは作らず、次の事実から上から優先して表示を導出する。

| 条件 | 表示 | 主行動 |
|---|---|---|
| 処理中 | `<工程>を処理中` | 待つ |
| delivery済みrevisionより新しいrevisionがあり、そのrevisionのapprovalなし | 納品済み vN / 修正中 vN+1 | 編集を続ける |
| captionあり、renderなし | 字幕準備済み・preview未生成 | プレビューを書き出す |
| render.caption_revision != current | 前版・納品不可 | プレビューを書き出す |
| QC fail | 技術検査で停止 | 再実行 |
| QC pass、review未完了 | 技術検査 合格 / 内容確認 未完了 | 動画を確認する |
| review条件を満たし、approval未作成 | 完成版として確定可能 | 完成版として確定 |
| current approvalあり、deliveryなし | vN 納品可能 | 納品用動画を取得 |
| current approvalのdelivery記録あり | vN 納品済み | 修正版を作る |

### 8.2 global OS lock

- 新規にglobal OS lockを1個だけ実装する
- lockを取るのは最外周のPython mutation commandだけとする。plugin/APIはfileを書かず、そのcommandを起動する
- direct CLIもplugin経由も同じcommand入口を通り、内部helperはlockを再取得しない
- busyなら待ちqueueへ入れず、UIへ「別の処理中」と返す
- heartbeat、PID nonce、process tree管理、queueは作らない
- process crash時はOSがlockを解放し、ユーザーは最後の保存済みrevisionから再実行する

復旧が10分を超えた場合だけ、原因と所要時間をPhase 0b候補として記録する。

## 9. source取得と権利の最小運用

### 9.1 source

- Phase 1の既定はクライアント提供local fileまたは公式owner export
- URL取得は既存CLIのexpert経路として残すが、Dashboard既定にはしない
- source fileを上書き・自動削除しない
- job作成後はsource、range、preset、BGMを変更しない。変える場合は新jobにする

### 9.2 `RIGHTS_AND_USAGE.md`

immutable attestation storeは作らない。project直下のtext file 1枚へ、素材ごとに次だけを手で記録する。

```text
- date:
  job_id:
  client:
  source:
  source_owner:
  edit_permission_checked: yes/no
  acquisition_method: local / owner-export / authorized-url
  external_ai_use: none / transcript / frames
  music_for_over_60s_checked: yes/no/not-applicable
  delivery_permission_checked: yes/no
  notes:
```

このfileはmachine-readable schemaにせず、ソロ運用の手動hard gateとする。

- job処理開始前: 対応entryがあり、`edit_permission_checked: yes` と取得方法が埋まっている
- 外部AI送信前: `external_ai_use` に送信対象が書かれている
- 60秒超の案件: 第三者音源claimの有無を確認し、`music_for_over_60s_checked: yes` にする
- 通常download・delivery記録前: `delivery_permission_checked: yes` を目視確認する

未記入または `no` なら、その操作を進めない。API schema、attestation ID、hash、operator identityは持たない。二人目のoperator、契約上の監査要求、または自動外部送信が発生した時点で§25から昇格する。

## 10. QCと人間確認

### 10.1 技術QC

最低限の自動QC:

- MP4 full decode
- video/audio stream存在
- duration、1080 x 1920、fps、H.264/AAC
- 字幕cueの範囲、重なり、2行上限、overflow
- preview生成成功

技術QCは意味、固有名詞、文脈、面白さを保証しない。

### 10.2 承認候補だけを全編確認

previewを書き出すたびに全編確認を要求しない。字幕を編集中のrenderは何回作ってもpreviewであり、承認対象ではない。ユーザーが編集を終えて `最終確認へ` を押した時点のcurrent renderだけを、先頭から末尾まで一回確認する。

UIは `技術検査 合格` と `内容確認 未完了` を別表示する。全編coverage（確認済み範囲）が揃った後だけ `完成版として確定` を押せる。確認後に字幕を保存または再renderした場合、そのcoverageは破棄し、新しいcurrent renderを一回確認する。

再生進捗は承認前のbrowser sessionだけに持ち、閉じて失っても再確認する。`完成版として確定` を押した時点で、全編を確認した対象pairとcoverageをapproval JSON内の `review` blockへ保存する。独立した `review.json` やreview hashは作らない。

### 10.3 字幕差分確認 — 初期不採用

字幕revision間の差分を取り、変更cueの前後±2秒だけ再確認する案は、Phase 1には入れない。理由は次のとおりである。

- 既定尺30〜60秒では、最終候補一回の全編確認は10分未満
- 180秒でも一回の全編確認は3分である
- 「5回renderしたら5回全編確認」ではなく、編集後の最後の一回だけ確認すればよい
- coverage継承にはcue差分だけでなく、未視聴区間のrender同一性検査も必要になり、現段階では削減時間より実装・testが重い

これが§21のactive time短縮との解決策である。S-02を弱めず、確認の開始時点を最後に寄せる。累計5jobで「最終確認開始後の修正により、全編確認をやり直した時間」のmedianが1jobあたり10分を超えた場合だけ、§25から差分確認を昇格させる。

## 11. UI設計

共通原則:

- 1画面1つの主CTA
- 状態、次の操作、停止理由を同時に見せる
- 技術詳細は段階的開示で隠す
- 最終確定だけは意図的に立ち止まらせる

### 11.1 Phase 1A — 字幕エディタ優先

画面:

1. job入力: source、start/end、preset
2. 字幕review: video左、caption右、行clickでseek、text直接編集
3. 最終確認: current renderを一回だけ全編確認し、技術/内容を分離

主CTA:

- `指定区間の動画を作る`
- `プレビューを書き出す`
- `完成版として確定`

初期はcaption text編集だけ。split、merge、timing drag、辞書登録は作らない。

### 11.2 Phase 1B — 候補提示優先

最初はDashboard画面を作らない。Phase 1B0として、local source全編を文字起こしし、timestamp付きtranscriptから0〜5候補をJSONへ出す一回限りのCLI spikeを作る。選択後に初めて通常jobを作り、Phase 1Mの画面へ渡す。これにより、range未確定sourceを既存job modelへ無理に入れない。

Phase 1B0を使った3jobで「2job以上で候補を採用」かつ「Phase -1 medianより区間判断を1jobあたり10分以上短縮」を満たした場合だけ、Phase 1B1として次のDashboard UIを作る。

- 全体timelineと候補marker
- 選択中のpreview一つ
- 開始/終了、要約、採用理由、確認risk
- `どれも使わない` とmanual range fallback
- numeric AI scoreは表示しない

主CTAは `選んだ候補を動画にする` 一つ。選択後は最小caption text編集と最終確認へ進む。

### 11.3 Phase 1M — 計測が小差の場合

job起動、状態表示、MP4再生、plainなcaption text areaだけを持つ。高度な同期editorも候補AIも作らず、累計3本になるまで不足本数だけを測る。

## 12. 最小API契約

```text
GET  /api/plugins/client-short-factory/jobs
POST /api/plugins/client-short-factory/jobs
GET  /api/plugins/client-short-factory/jobs/{job_id}
GET  /api/plugins/client-short-factory/jobs/{job_id}/captions/{revision}
PUT  /api/plugins/client-short-factory/jobs/{job_id}/captions
POST /api/plugins/client-short-factory/jobs/{job_id}/renders
GET  /api/plugins/client-short-factory/jobs/{job_id}/renders/{render_id}/video
POST /api/plugins/client-short-factory/jobs/{job_id}/approve
GET  /api/plugins/client-short-factory/jobs/{job_id}/approvals/{approval_id}/video
PUT  /api/plugins/client-short-factory/jobs/{job_id}/approvals/{approval_id}/delivery
```

契約:

- `POST /jobs` はjob metadataだけを作って止まらない。global lockを取る最外周workerを起動し、`job.json` のatomic作成から既存 `acquire -> ... -> qc` までを開始して `202 + job_id + status URL` を返す。lock busyは409で、半端なjobを作らない
- caption保存は `base_revision` 必須。競合は409
- renderは `caption_revision` 必須
- approveは `render_id`、`caption_revision`、`output_hash`、full coverage、`content_reviewed=true` が必須
- serverはapprove直前に次の一つのpredicate（判定式）を評価する

```text
request.render_id == current_render.render_id == review.target_render_id
request pair == current_render pair == review target pair
current caption_revision == request caption_revision
sha256(actual MP4) == request output_hash
QC passed == true
required full coverage == complete
```

`pair` は `output_hash + caption_revision` であり、`render_id` はfileを探すlocator（場所の識別子）にすぎない。別のhashやhash DAGは追加しない。
- `GET .../renders/{render_id}/video` はreview用inline再生だけで、stale renderには常に `履歴・納品不可` を表示する
- 納品用取得は `GET .../approvals/{approval_id}/video` だけを使い、取得直前にも上のcurrent pair、actual MP4 hash、QCを再検証する
- job尺は `0 < end - start <= MAX_SHORT_SECONDS`
- arbitrary command、任意pathのmedia配信、shell文字列を受けない

## 13. approval、delivery、納品後修正

### 13.1 approval record

`approvals/<approval-id>.json` は動画を複製せず、既存のimmutable renderを参照する。

```json
{
  "approval_id": "approval-002",
  "render_id": "render-005",
  "caption_revision": 6,
  "output_hash": "sha256:...",
  "approved_at": "2026-08-07T00:00:00Z",
  "review": {
    "target_render_id": "render-005",
    "target_caption_revision": 6,
    "target_output_hash": "sha256:...",
    "mode": "full",
    "checked_windows": [[0.0, 54.5]],
    "content_reviewed": true
  },
  "delivery": null,
  "supersedes_approval_id": null
}
```

approval作成とdelivery記録は別操作である。実際に送った後だけ `delivery` に `delivered_to / delivered_at / channel / note` をatomic updateする。自動uploadは行わない。deliveryから参照されたrenderは手動修正期間中に削除しない。

```json
"delivery": {
  "delivered_to": "client-name",
  "delivered_at": "2026-08-07T01:00:00Z",
  "channel": "manual",
  "note": "初稿"
}
```

approval JSONの作成・delivery追記は一時fileへ書いて検証後にatomic replaceする。UIの通常downloadは有効なcurrent approvalだけを対象とし、古いrenderは履歴表示から明示選択しない限り取得導線へ出さない。deliveryから参照されたrenderは、client関係または明示retention期間が終わるまでcleanup対象外とする。

`valid current approval` は、approval、current render、current caption revisionのpairが一致し、actual MP4のSHA-256が `output_hash` と一致し、QC passであることを指す。通常downloadとdelivery記録の直前にもこの判定を行う。

retry（再試行）は冪等にする。同じ `output_hash + caption_revision` のapprove再送は既存approvalを返す。deliveryは `null -> value` の一回だけで、同じpayloadの再送は200、異なる値への再更新は409とする。訂正が必要なら元recordを上書きせず、新approvalと新deliveryで表す。

### 13.2 修正依頼flow

1. `納品済み v1` からsecondary action `修正版を作る`
2. v1のcaption revisionを新working revisionへcopyし、依頼元、受領時刻、依頼内容を `change_request` metadataへ記録
3. v1のcaption revisionをbaseとして保持
4. 同じ字幕review画面で変更cueを強調
5. 新renderと技術QC
6. current renderを一回だけ全編確認
7. 新approvalへ `supersedes_approval_id` を記録
8. 実際に修正版を送った後、別操作でdeliveryを記録

表示状態は `納品済み v1 / 修正中 v2 / v2納品可能 / v2納品済み` の4つだけ。ticket管理、client portal、通知は作らない。

## 14. Securityと運用境界

- Dashboardは `127.0.0.1` のみ
- 現行Hermes session tokenを `fetchJSON` / `authedFetch` で使う
- 独自認証は追加しない
- fixed argv、`shell=False`、job ID/path validationを維持
- source、caption revision、render、delivery参照中fileを自動削除しない
- URL入力をDashboardへ出す場合はcanonical YouTube URLだけに限定する
- 外部AIへ送る場合は送信対象を画面表示し、`RIGHTS_AND_USAGE.md` の対応entryを確認してから送る

監査台帳、SSRF全provider対応、identity管理は現段階では作らない。

## 15. `claude-video` の扱い

参考対象:

- repository: `https://github.com/bradautomates/claude-video`
- inspected commit: `83da59fa78c3eee9e20f515fe75c438bb5166efd`
- license: MIT

直接installもruntime依存もしない。候補提示が本当のボトルネックと判明し、transcript-only候補が弱い場合だけ次を適応する。

- I-frameの疎なscan
- scene-change frame
- near-duplicate除去
- transcript timestampのpinned frame
- durationに応じたframe budget

実際にcodeを移植するphaseで `THIRD_PARTY_NOTICES.md` を作る。Phase 0aでは作らない。

## 16. Candidate / evidence path

候補提示優先になった場合も、最初からfull evidence systemやcandidate APIを作らない。

1. Phase 1B0のoffline CLIでtranscript-only候補を0〜5件出す
2. JSONと既存playerで人間が選び、選んだrangeから通常jobを作る
3. 累計3jobで採用・時間短縮条件を満たした時だけPhase 1B1のUIを作る
4. 3job中2job以上で全候補却下、または候補rangeの手直しが平均5分以上ならvisual evidenceを限定spikeする
5. visual evidence追加後も改善しなければCandidateScorerを停止し、manual rangeへ戻す

candidate品質は次で測る。

- 最初の候補をそのまま採用した率
- 全件却下率
- 候補range修正時間
- 完成後に「区間選定ミス」で修正依頼された率

## 17. 参考動画による設計監査

対象:

- `https://youtu.be/T4to0WagVcQ`
- ユーザー提供済み文字起こし

最初のUI branchが動いた後に一度だけ比較する。

1. 提供済みtranscriptと許可されたbrowser観察から画面・操作・人間判断を記録
2. Hermes版との差を `keep / change / reject / defer` に分類
3. 変更は最大3件
4. 1回再試験して終了

参考動画を無条件でdownloadしない。frame抽出が必要なら許可されたlocal fileを使う。参考動画の見た目に似せること自体を成功条件にしない。

## 18. CandidateScorer

CandidateScorerはPhase -1で候補提示優先になった場合だけoffline spike（Dashboard外の小規模実証）する。

```text
propose-ranges --source <local-file> --output <scratch-run-dir>
  -> transcript.json
  -> candidates.json
```

最低限:

- strict JSON schema
- candidate 0〜5件
- start/end、summary、reason、risk
- 範囲外時刻をvalidatorが拒否
- AIはfile、render、approvalを変更しない
- provider/model、送るtranscript/frameを実行前に表示する
- 選択されたstart/endだけを新しい通常jobへ渡し、candidate run自体は正本にしない

provider別監査store、prompt version DAG、cost dashboardは作らない。

## 19. Test戦略

### 19.1 Phase 0aの必須fault test

三境界だけを強制終了試験する。

1. **字幕保存**: 新revision書込後、`current.json` 更新前で停止しても旧版か完全な新版だけが残る
2. **render公開**: MP4生成中またはQC後、`current_render.json` 更新前で停止しても旧currentと字幕が残る
3. **approval公開**: approval一時file作成中に停止、またはapproval後に字幕編集しても、古いapprovalを完成扱いしない

### 19.2 Unit / integration

- caption schema、base revision競合
- explicit revisionからSRT/ASS生成
- output hashとcaption revisionによるS-01判定
- technical pass / content pending表示
- approve対象、current render、人間review targetのpair一致
- approve retryの重複防止、deliveryの同一retry 200 / 異なる再更新409
- preview再renderではfull coverageを要求せず、最終確認開始時だけ要求
- 字幕保存・再render後に古いcoverageを無効化
- stale approvalの納品用取得拒否と、actual MP4改変時の取得拒否
- render失敗後に保存字幕が復元できる
- global lock busy
- 180秒jobのUI/API/worker受理と180秒超の拒否

### 19.3 今は行わないtest

- 全commit境界crash matrix
- PID reuse、heartbeat、Windows process tree残存
- disk full、AV file lockの全組合せ
- multi-user concurrency
- immutable attestation改ざん
- proxy/master混入

これらは§25の昇格条件発生後に追加する。

## 20. 成果物の質の指標

### 20.1 意図的なscope分離

Phase 0a/1の第一責務は「修正作業を消さず、古い動画を完成版にせず、内容未確認を明示する」ことである。面白いShortsを自動保証することは初期scope外である。

ただし品質を無視するのではなく、次の3層を別々に記録する。単一のAI品質scoreへ合成しない。

### 20.2 納品hard gate

- S-01、S-02、S-04を満たす
- technical QC pass
- `RIGHTS_AND_USAGE.md` の対応entryとdelivery許可を目視確認
- 未解決の固有名詞・明白な誤字0
- 冒頭/終端に意図しないcutがない
- current renderのfull review完了

### 20.3 編集品質check — warning扱い

- 最初の3秒で主題または意味のあるactionが始まるか
- 区間単体で文脈を理解できるか
- 意図しない長い無音や間延びがないか
- 終端で問い、主張、payoffが閉じているか
- 字幕が読める速度と量か

これらは案件・genre依存なので、初期は最終確認guideにhuman yes/noとtimecodeを記録し、cue別状態や総合点を増やして承認をblockしない。

### 20.4 公開後outcome

YouTube Studioで最初の10本を手集計する。

- `Stayed to watch` — 視聴を続けた割合
- `Engaged views` — 冒頭を越えて視聴された回数
- `Average percentage viewed` — 平均視聴率
- audience retention — 離脱した時刻
- client correction rate

[YouTube公式の指標定義](https://support.google.com/youtube/answer/12220281)では、Shortsの単純なview数とは別にEngaged views、Stayed to watch、Average percentage viewedが提供される。2025年以降、単純なShorts viewは再生開始・再生し直しも数えるため、品質判断ではEngaged viewsと視聴維持を優先する。公開本数が5本未満の間は数値目標を置かず、各動画の所見だけ残す。5〜10本で同じchannel・近い尺のmedianをbaselineにする。

修正依頼は次に分ける。

- `our_error`: 誤字、誤区間、案件rule違反。目標0
- `client_preference`: 好み変更。失敗扱いしない
- `new_request`: 当初scope外。失敗扱いしない

## 21. 継続計測

Phase -1後も次をCSVへ追記する。

- `range_active_min`
- `caption_active_min`
- `final_review_active_min`
- `review_restart_active_min`
- `render_wait_min`
- `recovery_active_min`
- caption revision数
- 全件候補却下率
- deliveryから修正版deliveryまでの時間
- `our_error / client_preference / new_request`

機能追加は、1jobあたり10分以上を削る、半日損失を防ぐ、またはクライアント謝罪を防ぐ場合だけ認める。

## 22. 実装phaseとソロ開発日数

1 developer-dayは集中作業約6時間とする。見積もりには調査・実装・最小testを含むが、素材待ちとclient feedback待ちは含まない。

### Phase -1 — 計測

- **0.5日**
- 1〜2本を現行CLIで完走
- §5の数値でbranch決定

### Phase 0a — 最小安全kernel

- **2〜3日。3日で終わらなければ機能を追加せず切り分ける**
- caption schema v1、revision directory、`current.json`
- `render-job --caption-revision`
- immutable render directory、`current_render.json`
- global OS lock 1個
- `output_hash + caption_revision` review/approval
- 三境界fault test
- legacy jobはread-onlyで残し、必要なら一回限りの手動copy

### Technical spike A — 180秒review再生

- **0.25〜0.5日**
- §24を実施
- Phase 1のUI surfaceを確定

### Phase 1A — 字幕エディタ優先

- **2〜4日**
- 同期player、caption直接編集、explicit render、最後の一回のfull review、approval

### Phase 1B0 — 候補提示offline spike

- **1〜2日**
- local source全編の文字起こし、transcript-only candidate JSON、既存playerでの手動採否
- candidate専用DB/API/UIは作らず、選択rangeから通常jobを作る

### Phase 1B1 — 候補提示UI（数値条件成立時だけ）

- **2〜4日**
- 累計3jobで§11.2の採用・10分短縮条件を満たした場合だけ実施
- timeline、candidate preview、manual fallback。candidate source modelをこの時点で初めて設計する

### Phase 1M — 小差時の最小共通UI

- **1〜2日**
- job起動、状態、video、plain caption editだけ
- 累計3本になるまで不足本数だけを再計測し、§5.2で再判定

### Pilot — 内部1本

- **1日**
- sourceから完成版まで通す
- 実クライアントへ送る前にS-01/S-02/S-04と修正版flowを確認

### Phase 2 — 第二のボトルネックまたはvisual evidence

- **2〜4日、数値条件成立時だけ**
- Phase 1で作らなかった側、または`claude-video`由来の限定visual evidence

### Phase 3 — 参考動画監査

- **0.5〜1日**
- 最大3変更、一回再試験で停止

### Phase 0b — 後回し安全機構

- **固定日程なし。項目ごと0.5〜2日**
- §25の昇格条件が成立した項目だけ実施
- Phase 0aの直後に一括実施する工程ではなく、§25から個別に昇格させるdeferred pool（保留枠）である

必須のPhase -1、Phase 0a、Technical spike A、選択branch、内部Pilotを含む「内部pilot完了まで」の目安:

- 字幕優先: **5.75〜9営業日**
- 候補検証: **5.75〜9営業日**（Phase 1B0 + Phase 1M。候補UI化は実績3job後に別途2〜4日）
- 小差: **4.75〜7営業日**で最小UIと内部pilot、その後再計測

Technical spike AでBlob方式が不合格の場合だけ、§24.2の代替再生方式に **0.5〜1日**を追加する。client feedback待ち、実素材入手待ち、候補UI化までの3job運用期間は上記に含めない。

## 23. 内部自己レビューの位置付け

Architecture、UX、Reliabilityという3つのcritic personaは、同一AI system内の役割分担であり、独立した外部reviewerではない。

したがって次を禁止する。

- `PASS / must-fix 0` を品質保証として表示する
- critic同士の合意を外部検証と呼ぶ
- 自己レビュー完了を実装開始の証拠にする

内部criticは、重複責務、操作負荷、失敗経路を洗い出すchecklist生成にだけ使う。

実際の検証は次である。

1. Phase -1の手作業計測
2. §24の180秒再生spike
3. Phase 0aの三境界fault test
4. Phase 1 branchのtask test
5. 内部pilot 1本
6. 初回client feedbackと納品後修正の実時間

## 24. YouTube Shorts尺とreview再生spike

### 24.1 現行要件

2026-08-07確認時点で、[YouTube公式Help](https://support.google.com/youtube/answer/15424877)は縦型または正方形のShortsを最大3分としている。したがって旧版の `MAX_REVIEW_CLIP_SECONDS=90` は撤回する。

```text
MAX_SHORT_SECONDS = 180
DEFAULT_TARGET_SECONDS = 30〜60
```

180秒は案件・platform要件、再生方式は実装詳細であり、混同しない。

同じ公式Helpでは、1分を超えるShortsにactiveな第三者Content ID claimがある場合はYouTube上でblockされると案内されている。60秒超の案件では `RIGHTS_AND_USAGE.md` と納品前checkへ音源確認を残す。

### 24.2 Technical spike A

Hermes session認証付き `authedFetch -> Blob URL` で、180秒、1080 x 1920、想定最大bitrateのMP4を次の条件で確認する。

- time to first frame（最初のframe表示）: 3秒以内
- 10回seekの再生再開: p95（95パーセンタイル）750ms以内
- 再render後に旧Blob URLをrevokeできる
- 3回連続で開閉後のbrowser memory増加: 100MB以内
- 途中でUIが固まらず、最後まで再生できる

0.5日で全条件を満たせばBlob方式を採用する。満たさなければPhase 1のplayer実装を始めず、製品上限を90秒へ下げないまま、0.5〜1日の追加timeboxで次の順に一つだけ成立させる。

1. 認証付きRangeを扱える短命media ticket
2. standalone localhost review UI

認証を弱める方式は採用しない。

## 25. Backlogと昇格条件

| 項目 | 現在の扱い | 昇格条件 | 目安 |
|---|---|---|---|
| S-03 承認hashと別copyの一致 | S-01の `output_hash + caption_revision` で代用。video copyなし | 自動upload、自動cleanup、または通常download以外の外部handoffを導入する直前 | 1日 |
| S-05 独立した復旧/backup契約 | S-04へ吸収 | 自動cleanup、project storage移動、または複数deviceを導入する直前 | 1日 |
| S-06 proxyの納品混入防止 | proxy自体を作らない | visual proxyをproductionへ初導入する直前 | 0.5日 |
| S-07 外部AI egress監査 | `RIGHTS_AND_USAGE.md` 手動記録 | 自動送信、二人目operator、契約上の監査要求 | 1〜2日 |
| S-08 複数writer/queue | global OS lock 1個 | 同時2jobが必要、第二worker、複数PC | 1〜2日 |
| S-09 承認済みbytesの別保存 | deliveryが参照するimmutable renderを保持 | 自動cleanup、外部upload、またはclient契約で別copy保管が必要になる直前 | 1日 |
| S-10 platform取得許可台帳 | text file手動記録。local/owner export既定 | URL取得をclient workflowへ常設、監査要求 | 1日 |
| 汎用legacy migrator | 既存1jobはread-only、必要時手動copy | 移行対象が3jobを超える | 1〜2日 |
| 全commit境界crash matrix | 3境界だけtest | destructive cleanup、自動投稿、同系統破損2回 | 1〜2日 |
| cancel / timeout / heartbeat | 再実行で復旧 | 30分超hangが2回、またはTask Manager復旧が常態化 | 1〜2日 |
| Windows process tree test | 対象外 | orphan FFmpeg/yt-dlpが7日内に2回 | 0.5〜1日 |
| immutable attestation store | 作らない | 二人目operator、責任分離、監査条項 | 1〜2日 |
| full hash DAG | 作らない | artifactを自動移送・削除するsystemを入れる | 1〜2日 |
| 字幕差分確認 / coverage継承 | 最終候補だけ一回full review | 累計5jobで `review_restart_active_min` のmedianが1job 10分超 | 1〜2日 |
| Analytics dashboard | 最初の10本は手集計 | 公開10本以上かつ手集計が月30分超 | 1〜2日 |

昇格は「事故が起きるまで何もしない」ではない。自動upload、外部送信、並列化など、明らかにriskを増やす機能を入れる直前に必要項目だけ先回りする。

## 26. 参照

- 現行仕様: `README.md`
- 現行計画: `IMPLEMENTATION_PLAN.md`
- 現行engine: `short_factory/pipeline.py`
- 参考動画: `https://youtu.be/T4to0WagVcQ`
- 参考実装: `https://github.com/bradautomates/claude-video`
- YouTube Help — Three-minute Shorts: `https://support.google.com/youtube/answer/15424877`
- YouTube Help — Shorts Analytics: `https://support.google.com/youtube/answer/12220281`
- YouTube Help — Content tab analytics tips: `https://support.google.com/youtube/answer/12942217`
