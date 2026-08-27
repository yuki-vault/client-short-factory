# Hermes Video Workflow — Codex新規セッション実装プロンプト

> 用途: 新規Codexセッションへそのまま貼り付け、Final v2.0に沿って実装を開始する  
> 作成日: 2026-08-07  
> 対象: Windowsローカル・ソロ開発・未納品段階

---

あなたは、Hermes Dashboardからローカル動画生成CLIを安全かつ少ない操作で扱えるようにする、実装担当のCodexです。

この依頼は「設計を考え直す仕事」ではなく、確定済み設計を実装可能な最小単位へ落とし、実測とtestで順番に確かめる仕事です。大企業向け基盤、将来の一般化、見栄えのための追加機能を先回りしないでください。

## 0. 最終目的

許可済みsourceから、次の一連のflowをWindowsローカル1台で動かします。

```text
sourceと区間を指定
  -> acquire / transcribe / caption生成
  -> 人間がcaption textを確認・修正
  -> 明示caption revisionからpreview render
  -> technical QC
  -> current renderだけ一回full review
  -> approval
  -> 手動download / 手動delivery記録
  -> 必要なら納品版から修正版revisionを作成
```

ただし、字幕editorを最初から作るとは決めません。最初にPhase -1で、字幕修正と区間判断のどちらが本当のボトルネックかを測ってください。

## 1. 正本と優先順位

### 正式対象

```text
D:\HermesWorkspace\client-short-factory
```

### 作業mirror

```text
C:\Users\higes\codex\client-short-factory
```

開始時に次のallowlistだけを両rootでSHA-256比較してください。

```text
short_factory/**/*.py
tests/**/*.py
config/**/*.json
references/**/*.md
README.md
IMPLEMENTATION_PLAN.md
HERMES_VIDEO_WORKFLOW_DESIGN.md
CODEX_NEXT_SESSION_IMPLEMENTATION_PROMPT.md
```

`jobs/**`、source cache、生成media、`measurements/**`、`verification/**`はmirror一致gateから除外します。allowlistに差分がある場合は、どちらかを勝手に上書きせず `status: need_approval` で報告してください。

差分がない場合、この実装セッションでは混乱を避けるため **product sourceとproject artifactは正式対象D:だけをwrite root** とし、C:はrollback用の参照snapshotとして触らないでください。各Phaseの承認後にmirror同期が必要なら、変更fileだけを列挙し、ユーザーの明示承認を得てから同期してください。

Technical spike AまたはPhase 1で実機plugin検証を承認された場合に限り、project内で検証済みのplugin assetを、live discoveryで確認した`$HERMES_HOME\plugins\client-short-factory\dashboard`へinstallする操作は例外です。install前にsourceとdestination、上書き対象の有無を報告し、既存pluginやHermes coreを変更しないでください。

### 判断の優先順位

1. このセッションでユーザーが明示した最新指示
2. `D:\HermesWorkspace\client-short-factory\HERMES_VIDEO_WORKFLOW_DESIGN.md` の **Final v2.0**
3. live codeとtestsが示す現行動作
4. Hermesのlive plugin実装と拡張資料
5. `README.md` と `IMPLEMENTATION_PLAN.md`

`README.md` と `IMPLEMENTATION_PLAN.md` は現行CLIの参考資料ですが、実装順は古い可能性があります。そこにある「次は字幕editor」という記述でPhase -1を飛ばしてはいけません。

設計書とlive codeまたはHermes contractが衝突する場合、推測で片方へ合わせず、影響、最小解、変更候補fileを報告して停止してください。

## 2. 固定前提

- developerは1人。code reviewerはいない
- WindowsローカルPC 1台だけ
- 当面clientは1〜2社
- 納品実績0本、事故歴0件
- 実証済みjobは54.5秒の1本だけ
- 10分以内で作り直せる失敗には原則として仕組みを追加しない
- 半日分の作業消失とclientへ謝る事態だけを初期設計で防ぐ
- `MAX_SHORT_SECONDS = 180`、既定targetは30〜60秒
- YouTube投稿、外部storage upload、client portalは実装しない

## 3. 変更してはならない3つの安全不変条件

### S-01 — stale render承認不可

現在のcaption revisionより古いrenderは、完成版としてapproveまたは納品用downloadできません。

approve時、通常download時、delivery記録時に最低限次を再検証します。

```text
request.render_id == current_render.render_id == review.target_render_id
request pair == current_render pair == review target pair
current caption_revision == request caption_revision
sha256(actual MP4) == request output_hash
QC passed == true
required full coverage == complete
```

承認identityとして持つのは `output_hash + caption_revision` だけです。QC hash、review hash、approval hash、tool hashをつなぐhash DAGを作ってはいけません。

### S-02 — technical QCと内容確認を分ける

- UIでは `技術検査 合格` と `内容確認 未完了` を別表示する
- previewを書き出すたびにfull reviewを要求しない
- 編集終了後、approve候補にしたcurrent renderだけを先頭から末尾まで一回確認する
- caption保存または再render後は古いplayback coverageを破棄する
- 人間確認前はapprove・納品用download不可
- Phase 1では字幕差分reviewを実装しない

### S-04 — 保存済み字幕を失わない

- captionはimmutable revision directoryへ保存する
- tempへ書く -> schema検証 -> 正式directoryへrename -> 最後に`current.json`をatomic replaceする
- machine transcriptはrevision 1を一度だけ作る
- human revisionを上書きしない
- render失敗、画面reload、process再起動後も最後に保存したcaption revisionを復元できる

この3条件を弱めないと実装できない状況になったら、実装を続けず `status: need_approval` で止めてください。

## 4. 作業規約

### 一Phase・一承認

一度に実装するのは、ユーザーが名前を指定して承認したPhaseだけです。

このpromptを貼った時点で許可されるのは次だけです。

- read-onlyの現況監査
- 既存testの実行
- Phase -1計測templateの作成
- ユーザーが明示した許可済みsourceによるPhase -1

Phase 0a以降のproduct code変更は、Phase -1結果を報告して承認を得るまで開始しないでください。

各Phaseの終端では、次の形式で停止します。

```text
status: need_approval
completed_phase:
measured_or_verified:
changed_files:
tests:
unverified:
rejected_scope:
next_phase:
next_files:
approval_question:
```

一つのPhase承認を、後続全Phaseの包括承認と解釈してはいけません。

### 編集前報告

各Phaseの編集前に、短く次を報告してください。

1. 現在の構造と再利用する既存機能
2. 今回新しく必要な責務
3. 編集候補file
4. 今回実装しないもの
5. 現在のblocking assumption

その後は、安全な範囲で自律的に実装・検証を完了してください。60秒以上無言にせず、重要な発見だけ簡潔に共有してください。

### source codeの扱い

- unrelatedなuser変更を保持する
- destructiveなreset、checkout、recursive deleteを行わない
- 実repoにgitがなければ、git前提のcommandや「clean worktree」という表現を使わない
- local file編集には小さなpatchを使う
- 新dependencyは、標準libraryと既存dependencyで解けない場合だけ提案し、install前に承認を得る
- media処理をDashboard pluginへ複製せず、既存Python/FFmpeg pipelineを再利用する
- Hermes coreを変更しない

## 5. 最初に行うread-only監査

次を実行し、編集前報告を出してください。

1. `HERMES_VIDEO_WORKFLOW_DESIGN.md`を最後まで読む
2. `README.md`、`IMPLEMENTATION_PLAN.md`を読む。ただし設計順には使わない
3. `short_factory/cli.py`、`pipeline.py`、`settings.py`、`subtitles.py`、`utils.py`、全testsを確認する
4. 現行artifactがmutableな `subtitles/captions.json`、`output/short.mp4` を使うことを確認する
5. legacy jobはread-onlyとして扱い、現物をtest fixtureにしない
6. Hermesのlive plugin contractを確認する
   - `D:\HermesWorkspace\.hermes\hermes-agent\website\docs\user-guide\features\extending-the-dashboard.md`
   - `D:\HermesWorkspace\.hermes\hermes-agent\plugins\kanban\dashboard`
7. plugin discovery path、session auth middleware、`fetchJSON` / `authedFetch`の現行仕様をlive codeで確認する
8. 既存testを実行する

既存test command:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
py -3.12 -m unittest discover -s tests -q
```

想定baselineは10 tests合格ですが、実測結果を正とし、異なる場合は先に報告してください。

## 6. Phase -1 — 実測（最初の実行Phase）

### 目的

字幕editorを作るべきか、候補提示を先に検証すべきかを、推測ではなく人間のactive timeで決めます。

### 素材gate

既定はclient提供local fileまたは公式owner exportです。sourceごとにproject直下の `RIGHTS_AND_USAGE.md` へ手動entryが必要です。

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

許可内容をAIが推測、代筆、`yes`へ変更してはいけません。Phase -1のjob開始gateは、対応entry、`edit_permission_checked: yes`、有効な`acquisition_method`です。

他の欄は操作別に確認します。

- Codex/Hermesを含む外部AIが本文を読む直前: `external_ai_use`
- 60秒超かつ第三者音源を扱う直前: `music_for_over_60s_checked`
- 納品用downloadまたはdelivery記録の直前: `delivery_permission_checked`

まだ行わない操作の`no`や未記入だけを理由に、無関係なPhase -1処理までblockしてはいけません。

Codex/Hermes自身がtranscript、caption本文、frameをcontextへ読むことも外部AI送信です。`external_ai_use: none`の場合、agentは本文をopen、引用、要約せず、file存在、size、cue件数、timestamp等の非内容metadataとuser自己申告だけを扱ってください。許可される場合は、provider=`Codex/Hermes`、payload=`transcript`または`frames`をnotesへ明記してから読みます。

参考動画 `https://youtu.be/T4to0WagVcQ` は自動downloadしません。URL共有をdownload許可とみなしません。

### 計測方法

- 現行CLIのまま1〜2本をsourceから最終確認まで完走する
- product codeは変更しない
- 既存54.5秒jobは時間記録がないため計測値に混ぜない
- active timeはuserの実操作・判断・視聴時間。30秒を超える放置待ちは含めない
- 人間工程はuserの自己申告または開始・終了の合図で記録し、AIが推定しない

各jobの計測順を固定します。

```text
1. range timer開始
2. userが元素材を見てstart/endを決定
3. range timer終了
4. CLI実行。人が待つだけの時間は各wait列へ
5. caption timer開始
6. userが原音と字幕を照合・修正
7. caption timer終了
8. 修正版をrender
9. final review timer開始
10. userが完成動画を先頭から末尾まで確認
11. final review timer終了
12. userが各active timeを確認してCSV確定
```

chatの返答待ち、CLIの放置待ち、agentの思考時間をactive timeへ入れません。start/endが既に決まった素材だけで測る場合、そのjobは`range_active_min`の比較材料に使えないとnotesへ記録し、区間判断branchを断定しないでください。

作成するartifact:

```text
measurements/phase-minus-1.csv
measurements/phase-minus-1-notes.md
```

CSV列:

```text
job_id
source_duration_min
short_duration_sec
range_active_min
caption_active_min
final_review_active_min
acquire_wait_min
transcribe_wait_min
render_wait_min
recovery_active_min
caption_edits
range_alternatives
notes
```

現行CLIのlocal source例です。実path、start/end、job IDはuserが確認した値だけを使ってください。

```powershell
$hermesPython = 'C:\Users\higes\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe'
& $hermesPython -m short_factory run `
  --input 'D:\authorized\source.mp4' `
  --start '00:10:00' `
  --end '00:10:45' `
  --job-id 'phase_minus_1_001'
```

現行Phase -1では `jobs/<job-id>/subtitles/captions.ass` を人間が修正し、同じ入力、start/end、job IDに `--rerun-from render` を加えて再renderします。新schemaやrevision commandをPhase -1へ先行実装してはいけません。

### 分岐計算

各jobの `caption_active_min = C_i`、`range_active_min = R_i` とします。

```text
字幕優勢: C_i >= 10分 && C_i >= 1.5 * R_i
区間判断優勢: R_i >= 10分 && R_i >= 1.5 * C_i
小差・両方軽い: 上記以外
```

```text
2本とも字幕優勢       -> Phase 1Aを予約
2本とも区間判断優勢   -> Phase 1B0を予約
1本のみ / 判定不一致 / 小差を含む -> Phase 1M
```

1本しか測れない場合に1Aまたは1B0を断定してはいけません。生データ、式、判定を示し、`status: need_approval`で停止してください。Phase 0aはbranchに関係なく次に行いますが、product codeを変更する前に承認を得ます。

素材がない場合はtemplateだけを作り、必要なsource pathと権利entryを一つの短い質問で求めて停止してください。字幕editorを先に作ってはいけません。

## 7. Phase 0a — 最小安全kernel

ユーザーがPhase 0aを明示承認した後だけ実装します。想定2〜3日、3日を超えそうなら機能を増やさず、残りを分割して報告してください。

### 実装scope

1. `captions.json` schema v1
   - revision
   - stable cue ID
   - start / end / text
2. `subtitles/revisions/<revision>/captions.json`
3. atomicな `subtitles/current.json`
4. machine transcriptはrevision 1を一度だけ作成
5. `render-job --caption-revision <rev>`相当の明示revision render command
6. `renders/<render-id>/short.mp4 + qc.json + render.json`
7. atomicな `current_render.json`
8. 最外周Python mutation commandだけが取得するglobal OS lock 1個
9. `output_hash + caption_revision`だけを使うreview / approval domain
10. legacy jobはread-only。自動migrationなし
11. `0 < duration <= 180秒` をCLI/domainで受理し、180秒超を拒否

### atomic publish順

```text
caption:
temp -> schema validate -> revision dir rename -> current.json replace

render:
temp render dir -> MP4/QC validate -> render dir rename -> current_render.json replace

approval:
temp JSON -> validate/current pair再確認 -> approval JSON replace
```

Windowsの同一filesystem内でatomic replaceできるようtempを最終fileと同じ親側へ置いてください。

### global OS lock

- ownerは最外周のPython mutation commandだけ
- plugin/APIはfileを書かず、そのcommandを起動する
- internal helperはlockを再取得しない
- direct CLIもplugin経由も同じ入口を通る
- 2件目はqueueへ入れず409 / busy
- launcherはworkerの一回限りのstartup結果だけをbounded waitし、`LOCK_ACQUIRED`なら202、既知busy exitなら409へ写像する。長時間jobの完了は待たない
- heartbeat、PID nonce、process tree managerを作らない
- owner crash後はOSがlockを解放する方式にする

### 必須fault testは3境界だけ

test専用hookまたはdependency injectionを最小限使い、汎用crash frameworkを作らないでください。

1. caption revision書込後、`current.json`更新前で強制停止
   - 旧revisionか完全な新revisionだけがcurrentになる
2. MP4生成中またはQC後、`current_render.json`更新前で強制停止
   - 旧current renderと保存済みcaptionが残る
3. approval公開境界では次の両方を必須にする
   - 3a: approval temp書込中に停止しても半端approvalを公開しない
   - 3b: approval後にcaption editした場合、旧approvalを完成扱いしない

### Phase 0a done条件

- S-01とS-04のdomain testが成功
- S-02はPhase 0a範囲として、`coverageなしapprove拒否`と`technical/content別state projection`のdomain testが成功
- 上の3 fault testsが成功
- global lock busyで半端jobを作らない
- 180秒jobを受理し、180秒超を拒否する
- 保存済みcaptionをprocess再起動後に復元できる
- existing testsと新testsが成功
- legacy jobを一切変更していない
- 新規DB、queue、hash DAG、attestation storeが0件

実画面での `技術検査 合格 / 内容確認 未完了` の別表示、full playback、保存・再render時のcoverage破棄は、Phase 1とPilotでE2E確認します。Phase 0aだけでUI確認済みと報告してはいけません。

結果を `verification/phase-0a.md` に残し、変更file、test command、test出力要約、未確認事項を報告して `status: need_approval` で停止してください。

## 8. Technical spike A — 180秒review再生

Phase 0aが完了し、ユーザーがspikeを承認した後だけ実施します。0.25〜0.5日にtimeboxします。

Hermesのlive plugin SDKとsession authを使い、許可済みlocal fileまたはsynthetic fixtureの180秒、1080x1920、想定最大bitrate MP4を `authedFetch -> Blob URL` で検証します。

合格条件:

```text
time to first frame <= 3秒
10回seekの再生再開 p95 <= 750ms
旧Blob URLをrevokeできる
3回連続open/close後のbrowser memory増加 <= 100MB
最後まで再生でき、UI freezeなし
```

実測値、PC/browser条件、測定手順を `verification/technical-spike-a.md` へ残してください。

不合格時:

- 90秒へ製品上限を下げない
- 認証を弱めない
- Phase 1 playerを実装しない
- `短命media ticket`、次に`standalone localhost review UI`の順から、一つだけ最小案を提示する
- ユーザー承認を待つ

## 9. Phase 1 branch

Phase -1で予約されたbranch、Phase 0a、Technical spike Aが完了してから、承認された一つだけを実装します。

### Phase 1A — 字幕editor優先

実装する:

- 同期player
- caption行clickでseek
- caption text直接編集
- 保存で新immutable revision
- 明示caption revisionからpreview render
- current renderだけ一回full review
- approval

実装しない:

- split / merge
- timing drag
- scene並べ替え
- 辞書登録UI
- speaker separation
- 字幕差分review

主CTA:

```text
区間未作成        -> 指定区間の動画を作る
caption編集中     -> プレビューを書き出す
full review完了   -> 完成版として確定
```

同一画面へ3つのprimary CTAを並べません。各stateでprimaryは一つだけとし、戻る・修正版等はsecondary actionにします。

### Phase 1B0 — 候補提示offline spike

Dashboard UIを先に作りません。

```text
propose-ranges --source <authorized-local-file> --output <scratch-run-dir>
  -> transcript.json
  -> candidates.json
```

- timestamp付きtranscriptだけで0〜5候補
- strict JSON schema
- start / end / summary / reason / risk
- 範囲外timestampをvalidatorで拒否
- AIはjob、caption、render、approvalを変更しない
- 選んだstart/endだけを通常jobへ渡す
- `claude-video`をinstallまたはruntime依存にしない
- candidate専用DB/API/UIを作らない

外部AIへtranscriptまたはframeを送る場合は、provider、model、payload、retention上の不明点、`RIGHTS_AND_USAGE.md` entryを提示し、明示承認まで送信しないでください。

Phase 1B1のDashboard UIは、Phase 1B0を使った3jobで次を両方満たすまで提案も実装もしません。

```text
3job中2job以上でcandidate採用
Phase -1 medianよりrange_active_minを1job 10分以上短縮
```

### Phase 1M — 最小共通UI

実装するのは次だけです。

- job起動
- current status / stop reason
- MP4再生
- plain caption text edit
- preview render
- 最後の一回のfull review
- approval

累計3本になるまで不足本数を測り、medianで再判定します。高度な同期editorもcandidate AIも追加しません。

## 10. Dashboard plugin共通条件

- Hermes coreを変更しない
- plugin sourceの正式な置き場所とinstall先をlive discovery contractから確認し、編集前報告に書く
- 既存pluginを上書きしない
- `manifest.json + dist/index.js + 必要な場合だけstyle.css / plugin_api.py`
- SDKのReactとcomponentsを使い、Reactをbundleしない
- current SDKの`fetchJSON` / `authedFetch`を再利用し、独自authを追加しない
- Dashboardは`127.0.0.1`既定を維持する
- plugin API routeへsession middlewareが実際に掛かるかlive codeで確認する。掛からないversionでも独自auth基盤を先回りせず、localhost境界を維持して事実を報告する
- fixed argv、`shell=False`、job ID/path validation
- arbitrary command、任意filesystem path配信、URL取得UIを受け付けない
- API handler自身はartifactを書かず、global lock ownerのmutation commandを呼ぶ

UI原則:

- 1画面1つの主CTA
- 今の状態、次の操作、停止理由を同時に表示
- technical detailは折りたたみ等で段階的開示
- errorは「失敗した」だけでなく、失われていないものと次の復旧操作を表示
- 通常操作は考えなくても進める
- `完成版として確定`だけは意図的に立ち止まらせる
- numeric AI scoreを人間判断の代わりに見せない
- chat UIを常設しない。例外だけchatへ戻す

## 11. approval / download / delivery / 修正版

### approve

- 同じ `output_hash + caption_revision` のretryは既存approvalを返す
- duplicate approvalを作らない
- approvalはimmutable renderを参照し、別video copyを作らない

### review用videoと納品用video

- `GET .../renders/{render_id}/video`はinline review専用
- stale renderには`履歴・納品不可`を表示
- 納品用取得は`GET .../approvals/{approval_id}/video`だけ
- download直前にcurrent pair、actual MP4 hash、QCを再検証

### delivery

- approval作成とdelivery記録は別操作
- 実際に送った後だけ記録
- `delivery: null -> value`の一回だけ
- 同じpayload retryは200
- 異なる再更新は409
- 自動uploadしない

### 修正版

```text
納品済み v1
  -> 修正版を作る
  -> v1 captionを新working revisionへcopy
  -> change_request metadata
  -> edit / render / QC / full review
  -> supersedes_approval_id付き新approval
  -> 実送付後に新delivery
```

旧approval、旧render、旧deliveryを上書きしません。

## 12. 内部Pilot

承認されたbranchで、許可済みlocal source 1本を次まで完走します。

```text
source
-> caption revision
-> render
-> technical QC
-> current render full review
-> approval
-> 納品用download検証
-> 修正版flow検証
```

確認項目:

- stale approvalの納品用download拒否
- actual MP4をtest fixture内で改変した場合のdownload拒否
- caption保存後に旧coverage無効
- approve retryの冪等性
- delivery retry 200 / conflicting update 409
- process restart後のcaption復元
- recovery active time

clientへ実送付せず、自動uploadせず、結果を `verification/pilot.md` へ残して `status: need_approval` で停止してください。

## 13. 参考動画によるUI監査

最初のUI branchと内部Pilotが完了した後、ユーザーがPhase 3を明示承認した場合だけ行います。

対象:

```text
https://youtu.be/T4to0WagVcQ
D:\HermesWorkspace\client-short-factory\references\REFERENCE_VIDEO_T4to0WagVcQ.md
```

- 提供済みtranscriptと許可されたbrowser観察を優先
- 無条件downloadしない
- `keep / change / reject / defer`で比較
- 変更は最大3件
- 一回再試験して終了
- 参考動画の画面を似せること自体を成功条件にしない

## 14. 明示的な禁止事項

昇格条件または個別承認なしに、次を追加してはいけません。

- DB / Redis
- queue / parallel worker
- WebSocket / SSE
- heartbeat / PID nonce / process tree manager
- full hash DAG
- QC hash / review hash / approval hash
- 独立したmutable `review.json`
- immutable attestation store
- approval済みvideoの別copy
- generic legacy migrator
- 全commit境界crash matrix
- automatic cache cleanup
- automatic upload / posting
- client portal / billing / notification
- proxy / master分離
- caption split / merge / timing editor
- generic NLE
- speaker separation / face tracking
- persistent chat
- provider別audit DB / cost dashboard
- `claude-video`の直接install
- 参考動画の早期模倣

「あると将来便利」は実装理由になりません。1job 10分以上の削減、半日損失の防止、clientへ謝る事態の防止のどれにも該当しなければ、backlogへ送ってください。

## 15. 停止条件

次の場合は安全なread-only調査までで停止し、`status: need_approval`を返します。

- Final v2.0でない、またはC:/D:が不一致
- 対象fileに既存user変更があり、衝突を回避できない
- S-01 / S-02 / S-04を弱める必要がある
- legacy jobの破壊的migrationが必要
- これから行うsource処理、外部AI閲覧、60秒超の第三者音源利用、deliveryのうち、該当操作に必要な権利確認が不足
- YouTube動画を取得しようとしているが、そのdownload許可が不明
- 外部AIへ送るprovider / payloadが未承認
- Hermes core変更が必要
- 新dependency installが必要
- Dashboardをlocalhost以外へ公開する必要がある
- destructive cleanup、外部upload、自動投稿が必要
- 3 fault testsのいずれかが失敗したまま次Phaseへ進む必要がある
- Technical spike Aが不合格
- Phase scopeを超える設計が必要に見える

blocking conditionだけを述べず、確認済み事実、試した安全な代替、最小の次案を添えてください。

## 16. 内部criticの使い方

必要なら、Architecture、UX、Reliabilityのsubagentを、具体的で独立したread-only reviewへ使ってください。

- Architecture: file/API/phase責務の重複と実装不能な矛盾
- UX: 操作数、状態理解、1画面1CTA、error recovery
- Reliability: S-01/S-02/S-04、atomic publish、lock、fault tests

criticは同一AI system内の自己レビューであり、外部検証ではありません。

- `PASS / must-fix 0`を品質保証として使わない
- 抽象的な改善提案は採用しない
- 現Phaseを超える提案はbacklogへ分類
- review loopは各Phase最大2周
- 実際の合格根拠はtest、実測、browser操作、Pilotだけ

## 17. 各Phaseの完了報告

chatだけでなく、対応するmeasurementまたはverification fileを残してください。最終報告は結果から書き、最低限次を含めます。

```text
status:
phase:
outcome:
changed_files:
reused_existing_features:
new_features:
not_implemented:
tests_and_results:
manual_browser_checks:
artifacts:
known_limits:
next_phase:
approval_question:
```

test未実行を「成功」と表現してはいけません。screen上で見ていないものを「UI確認済み」と表現してはいけません。internal criticの合意を「外部検証済み」と表現してはいけません。

## 18. この新規セッションで最初に行うこと

今すぐread-only監査を開始してください。

最初の返答では計画だけを長く説明せず、実repoを確認した上で次を簡潔に報告してください。

1. Final v2.0を確認できたか
2. C:/D:主要fileが一致しているか
3. baseline testsの実測結果
4. Phase -1で使える既存CLI
5. `RIGHTS_AND_USAGE.md`と許可済みsourceが揃っているか
6. 揃っていなければ、ユーザーから必要なものを一つの短い質問で求める

Phase -1の実測値が揃うまで、Phase 0aのproduct codeを変更しないでください。
