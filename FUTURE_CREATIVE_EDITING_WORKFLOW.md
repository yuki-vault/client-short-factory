# 高品質Shorts制作・開発ワークフロー — Final

更新日: 2026-08-11  
状態: 2周の独立批判レビューと最終裁定を反映済み。product code実装は未承認・未着手。

## 0. 結論

今回のテストは、**長時間動画からAIが候補を出し、字幕付きShortsを作る基礎workflowとしては成功**だった。一方、売り物としての品質は字幕精度だけで決まらず、次の3点が支配的だと分かった。

1. そもそもsourceが切り抜き向きか。
2. 連続区間のまま抜くべきか、間や反復を詰めるべきか。
3. font・演出・テンポをclientごとにどう決めるか。

したがって、今後は次の2本を混ぜない。

- **制作運用**: AIにsource判定と候補抽出を任せ、人間は短いpreview、意味が変わるcut、字幕の細部、最終確認へ集中する。
- **product開発**: まず字幕修正と誤納品防止だけを安全にする。AI候補UI、multi-cut、style editorは、別sourceで価値が実証されるまで作らない。

「候補0件」または「このsourceは見送り」を正常な成果として扱う。無理に1本作ることを成功条件にしない。

## 1. 今回わかった事実と限界

### 観測済み

- 許可済みの約8,555秒sourceを、無人約21分18秒で全編文字起こしできた。
- AIは候補を絞り、選択した50.21秒区間を字幕付き縦動画とtechnical QCまで処理できた。
- 人間の字幕確認active timeは5分だった。
- ユーザー評価では字幕表示の約90%が良好で、細部だけ直したくなる品質だった。
- 対象sourceではYouTubeの公開Most Replayed情報を取得できなかった。heatmapを必須入力にはできない。
- ユーザーの目視では、より良い箇所を長時間動画から人力で探すと約2時間かかりそうで、このslow-talk source自体も切り抜き適性が低かった。
- 連続区間をそのまま抜く方式では、0.1秒単位の間、反復、false startなどが残り、テンポ品質に上限がある。

### 未確定

- Phase -1の正式CSVは、元の12手順を完了していないため分岐判定には使わない。
- AIが「真に一番よい箇所」を候補へ含める率は測れていない。
- paced multi-cutが別sourceでも品質と作業時間を改善するかは測れていない。
- 再利用可能なfont・演出presetは、client briefがないため決められない。

## 2. 実際のShorts制作workflow

これは新しいproduct codeがなくても使う運用である。

### Gate R — 権利と利用範囲

`RIGHTS_AND_USAGE.md`へ、source、編集許可、取得方法、external AI利用、確認日を記録する。transcript、audio、frames、public metadataで許可範囲が違う場合はpayload別にnotesへ残す。未記録payloadは開かない。

停止条件:

- 編集許可または必要payloadの許可がない。
- 許可の対象をsourceへ一意に結び付けられない。

### Step A — AIによるsource適性判定

許可済みtranscriptを主入力とし、取得できる場合だけpublic metadata、許可がある場合だけframesを補助入力にする。AIはnumeric scoreだけで決めず、次のいずれかを理由付きで返す。

- **straight cut**: hook、展開、着地が短い連続区間で閉じ、間も許容範囲。
- **paced edit**: 話は強いが、silence、filler、反復、言い直しを詰めないと弱い。
- **reject**: 文脈依存、着地不足、画面変化不足、または編集量に対して価値が低い。

`reject`ならそこで止め、別sourceへ移る。

### Step B — AI候補抽出

AIは候補を最大5件、または0件返す。各候補には少なくとも次を添える。

- sourceの開始・終了時刻
- 最初のhook
- setupとpayoff
- 前後文脈への依存
- ASR・固有名詞risk
- 推奨mode: straight / paced / reject

人間はまずpreviewだけで採否を決める。候補探索精度は未測定なので、「最大5件を見れば最良箇所を必ず発見できる」とは扱わない。

### Step C — 編集modeを決める

#### straight cut

候補区間を連続で抜き、冒頭と末尾の余白だけを調整する。会話の自然さが残るsource向け。

#### paced edit

keep rangeをsource時間順・non-overlapで並べ、場面順は変えない。初期に削除候補にできるのは次だけとする。

- 無音と不自然に長い間
- filler
- 同じ意味の反復
- false start

否定、主語、対象、因果、結論が変わるjoinはAIが確定せず、人間確認へ送る。cut数や0.1秒単位の多さ自体を品質指標にしない。

#### reject

手を加えてもhookまたはpayoffが成立しない、もしくは編集時間に見合わない場合は作らない。

### Step D — 字幕と見た目

現行systemで字幕を生成し、人間は固有名詞、助詞、改行、表示タイミングだけを重点確認する。font、color、outline、shadow、punch-inは、clientまたはユーザーの具体的briefを受けた後に固定presetとして決める。cut timing比較とstyle比較を同時に行わない。

安全なcaption revision機能ができるまでは、既存jobを上書きせず、新規jobで作業し、ASS修正後は同じ条件で再renderする。technical QCは字幕本文の正しさを保証しないため、原音付きの最終確認を省略しない。

### Step E — 最終確認と納品

1. technical QCと内容確認を別々に記録する。
2. 対象videoを音声ありで先頭から最後まで確認する。
3. 実際に確認した`output_hash + caption_revision`を固定する。
4. 納品準備記録を残してからファイルを取り出す。
5. 実送付後に送付時刻を追記する。

## 3. Product開発workflow

各Phaseは、結果を報告して停止し、ユーザーの明示承認後だけ次へ進む。

### Phase P0 — 最短経路の実機比較（0.50人日、product code変更なし）

目的は「Hermes UIを作れるか」ではなく、同じ安全milestoneへ最短で届く経路を選ぶことである。

#### 実走する共通操作

scratch/disposable jobで次を通す。

1. 字幕を1語直す。
2. 修正した版を入力として固定してrenderする。
3. technical QCと内容確認を別記録にする。
4. current identityと一致する版だけを承認対象にする。

#### 比較する経路

- 既存CLI＋file review
- Hermes review surface＋既存render入口

Hermes側では、MP4 open、先頭・中間・末尾seek、caption save/render入口、app再起動後の再接続を確認する。各checkの調査上限は30分。P0では修復実装をしない。

#### P0で必ず測るもの

- Windows上のcold/warm build→install/sync→再起動→確認の1往復時間
- P1各項目を `実走済み / 再利用のみ / 新規` に分けたWBS
- fixture準備と3 fault境界の所要時間
- CLI/fileで止めるか、条件付きHermes UIへ進むか

P0終了時に暫定見積を捨て、実測WBSでP1上下幅を作り直す。CLI/fileでmilestoneを満たせるなら、UI実装をせず停止してよい。render入口が成立しない場合はP1を始めず、修復待ちとして停止する。

### Phase P1a — 字幕保存とpreview render

最初の体感価値を出す停止点。approval/downloadはまだ公開しない。

- plain captionからimmutable `caption_revision`を作る。
- revision本体を検証・publishした後だけ、same-directory tempから`current.json`をatomic replaceする。
- `current.json` replace失敗時は旧currentと最後の正常renderを維持する。
- publish済みrevision IDを最小のrecovery pointerへ残し、再起動後に旧current維持か再指定かを選べるようにする。
- jobs directoryがOneDrive / Dropbox等の同期folderなら初期版ではhard rejectする。
- render開始時にcaption revisionを固定する。完成時に新しいcurrent captionへidentityを付け替えない。
- immutable render directoryでMP4、QC、metadataを検証してからpublishする。
- `current_render.json`は作らない。

完了時には、ASSを直接触らず1語修正し、preview renderできる。ここで中断しても旧正常版を失わない。

### Phase P1b — 安全なreview・approval・delivery

- `current.json`のpublisher、approval、納品用downloadを同じglobal OS lockへ参加させる。
- handlerはlock内でcurrent caption、actual MP4 hash、QC、content reviewを再読込する。
- `output_hash + caption_revision`が一致しないrequestを拒否する。
- technical QCとcontent reviewを別表示にし、別identityへ確認を継承しない。
- full-playbackは0秒から開始し、seek・速度変更・mute・音量0・途中音量変更を許可しない。tab非表示、source変更、再renderで試行を無効化する。
- 終端到達だけでは内容確認済みにせず、同じidentityへの明示確認を要求する。
- review用videoと納品用downloadを分ける。
- approval artifactは同じcritical sectionでatomic publishする。

delivery ledgerはdownloadを露出する前に`prepared`行をatomic追記し、送付後に同じidentityへ`delivered`行を追記する。

```text
state | job_id | client | delivery_name | unique_filename | output_hash | caption_revision | delivered_at
```

「前に送った版を直して」はcurrentから始めず、clientが見たdelivery nameまたは送信済みfilenameから該当revisionを選び、新working revisionへcopyする。

### Phase P1c — Hermes UI（P0で必要と判断した場合だけ）

P1a/P1bのbackendへplain caption editorとreview UIを被せる。二つのtab、render中のcaption変更、review後のcaption変更、app再起動を実機試験する。

CLI＋file経路で同じmilestoneを十分に達成できるならP1cは実施しない。

### P1 release check — 0.5 active day

独立Phaseにはしない。新しい許可済み実jobで次を1回だけ通す。

1. R1を作り、内容確認・承認・`prepared`記録まで行う。
2. appを再起動する。
3. ledgerのR1を起点に固有名詞を1件修正し、R2を作る。
4. R1を保持し、R2だけをcurrentとして再確認・再承認する。
5. 0.5 active dayで終わらなければ欠陥をP1の該当項目へ戻す。

legacy jobはread-onlyとし、fixtureに使わない。

### 中断と再開

実装中は1枚の`phase-progress.md`だけを更新する。

```text
current item
done evidence
last green test
next action
last known-good caption and render
```

別日に再開する時は、この記録だけで15分以内に次のtestを始められることを目標にする。

## 4. 現在の実装scopeと見積

- P0: 0.50人日。
- P1（P1a/P1b、必要時P1c、release check込み）: 暫定6.10〜9.10人日。
- 合計: 暫定6.60〜9.60人日。

これは契約値ではない。P0の実機WBSで置き換え、actual burn＋未着手上側見積が15人日を超えるならP1開始前またはPhase境界で停止する。

初期scopeから外すもの:

- AI candidate UI
- product化したmulti-cut recipe
- generic NLE timeline
- style editor
- B-roll自動生成・挿入
- face / speaker tracking
- DB、queue、複数worker
- client portal
- 自動投稿・自動delivery
- 180秒hard gate
- AI scoreによる自動承認

## 5. Creative-quality開発を再開する条件

candidate探索、paced multi-cut、style機能は、現時点ではproduct Phaseを作らない。次のいずれかが実際に起きた時だけ、許可済みの別sourceを使う新しいoffline検証計画を改めて作り、ユーザー承認を取る。

- paid clientがpaced editを受注条件として明示した。
- ユーザーが現行品質では案件化できないと判断し、検証用sourceを別途許可した。
- 確定済み同種jobの累積手作業時間が、想定する1〜2日の検証costを上回った。

単発の10分、今回と同じsourceでの自己評価、未許可sourceは再開根拠にしない。次回計画ではcandidate discoveryとpaced品質を別々に評価し、candidate recall、semantic error、active time、style briefの不足を明示する。

## 6. 停止条件と承認gate

- rights entryまたは必要payload許可がない。
- P0の0.5日内に経路を一意に選べない。
- 既存render入口が成立しない。
- S-01（stale render拒否）、S-02（QCと内容確認の分離）、S-04（保存済みcaptionと最後の正常renderを失わない）を弱める必要がある。
- legacy jobを変更しないと検証できない。
- actual burn＋未着手上側見積が15人日を超える。
- 現Phaseの明示承認がない。

各Phase終了時は、実測値、変更ファイル、検証結果、残リスク、次Phase見積を報告して停止する。

## 7. 未解決のまま残す5点

1. Hermes UIとCLI＋fileのどちらが最短か、およびP1の確定見積。P0で決める。
2. AI candidate discoveryの見逃し率。creative機能を再設計するまで未検証とする。
3. 外部送付とlocal ledger追記の完全な一体化。prepared行とunique filenameで事故窓を縮める。
4. 同一caption revisionに複数renderがある場合の自動canonical選択。初期版ではhashを見て手で選ぶ。
5. 観測済み50.21秒相当を超えるjobの受理範囲。最初の長尺briefでscratch確認する。

## 8. 現在地と次のgate

- 2周の批判レビュー: 完了。
- 最終workflow文書: 完了。
- Phase -1正式CSV: 未確定のまま保持。
- Phase P0: 未実施。
- product code: 変更なし。

次に進む場合は、**Phase P0の0.50人日read-only/scratch実機比較だけ**を明示承認の対象とする。P0結果が出るまでP1のproduct codeは変更しない。
