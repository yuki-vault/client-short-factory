# 高品質Shorts制作ワークフロー — Draft 1

## §0. 位置付けと優先順位

この文書はRound 1の敵対レビューを反映した将来ワークフロー案であり、product code変更の承認ではない。

判断の優先順位は次とする。

1. ユーザーの明示指示と `CODEX_NEXT_SESSION_IMPLEMENTATION_PROMPT.md`
2. live repo・実機観測・今回のPhase -1定性テスト
3. Round 1の批判と裁定

開発者1人、Windowsローカル1台、当面のclient 1〜2社という前提は維持する。

## §1. 今回の結論

### §1.1 観測済み

- 約8,555秒の許可済みsourceを無人約21分18秒で全編文字起こしし、0〜5候補を作れた。
- 選択した50.21秒の連続区間は、字幕付き1080x1920 MP4とtechnical QCまで完走した。
- 人間の字幕確認active timeは5分で、ユーザーは字幕の約90%を良好と評価した。
- ユーザーはsystem workflowを概ね成功と評価した一方、slow-talk sourceを連続区間のまま抜く方式には品質上限があり、source適性、細かな間、multi-cut、font・演出が次の課題だと判断した。
- public heatmapは対象sourceで取得できず、候補探索の必須入力にはできない。

### §1.2 今回だけでは決められないこと

- paced multi-cutが別sourceでも品質とactive timeを改善するか。
- source rejectをAIが十分な精度で判断できるか。
- style presetがclient要件として再利用できるか。

これらは初期product実装へ混ぜず、§8の再開条件を満たした時にoffline spikeから再検証する。

## §2. 二段階の目的

### §2.1 最初のproduct milestone

ASSを直接編集せずにcaptionを保存し、そのcaptionから明示renderし、technical QCと内容確認を分け、current renderだけを承認できること。

このmilestoneはS-01 / S-02 / S-04を一つの縦切りで満たす。

### §2.2 後続のcreative-quality milestone

人間が長時間sourceを通して見ず、AIが最大5件のpreviewまたは0件を提示し、候補ごとに次を選べること。

- 連続切り抜き
- source順を保ったテンポ編集
- 見送り

後続milestoneは§8のevidence gateを満たすまでproduct scopeへ入れない。

## §3. 保持する安全条件

- **S-01**: current captionより古いrenderを承認・納品用取得できない。
- **S-02**: technical QC successを内容確認済みとして表示しない。
- **S-04**: 保存済みcaptionと最後の正常renderを失わない。

approval identityは元promptどおり `output_hash + caption_revision` とする。full hash DAGは作らない。

## §4. 初期product workflow

### §4.1 Gate R — sourceと権利

`RIGHTS_AND_USAGE.md` 1枚へ、少なくとも次を記録する。

- source識別子
- `edit_permission_checked`
- `acquisition_method`
- external AI利用許可
- 確認日

payloadごとの差がある場合は、providerと `transcript`、`audio`、`frames`、`public metadata` の対象名をnotesへ残す。これは今回、transcriptとpublic metadataが別々に許可された実例があるためである。未記録payloadは開かない。

### §4.2 Preflight — product code変更前

Windows実機で次の4項目をread-onlyまたはscratchで確認する。

1. current MP4をHermes review surfaceで開ける。
2. 先頭・中間・末尾へseekできる。
3. scratch caption saveと既存render入口を呼べる。
4. app再起動後に同じjobとcurrent MP4へ再接続できる。

4項目のどれかが成立しなければUI実装を始めず、既存CLI＋file reviewへ縮退する。実機pluginのbackendはstartup時mountであるため、install後のHermes再起動をpreflight手順へ含める。

### §4.3 Caption save

1. userがcurrent videoとplain caption textを開く。
2. saveは新しいimmutable `caption_revision` を作る。
3. revision本体を検証・publishした後だけ、同じdirectoryのtempから`current.json`をatomic replaceする。
4. replace失敗時は旧currentとeditorのdirty内容を保持し、保存済み表示、render、approvalへ進まない。
5. jobs directoryは初期版でOneDrive / Dropboxなどの同期folderを非対応とする。

### §4.4 Explicit render

1. render commandは開始時にimmutable `caption_revision` を必須引数として固定する。
2. render完了時にcurrent captionを読み直して入力identityを付け替えない。
3. temp render directory内でMP4、QC、render metadataを検証する。
4. 完成directoryをpublishした後だけ`current_render.json`をatomic replaceする。
5. captionがrender中に変更された場合、完成renderは履歴として保持するがcurrent承認対象にはしない。

### §4.5 Technical QCとcontent review

- technical QC stateとcontent review stateを別表示する。
- review対象は `output_hash + caption_revision` に結び、別outputへ継承しない。
- 初期のfull-playback gateはcoverage unionを作らない。
- gate獲得中は0秒から開始し、seekと速度変更を無効化する。
- tab非表示、source変更、再renderで試行を無効化する。
- 同一outputを表示tabで終端まで連続再生した場合だけfull playback completeにする。

### §4.6 Approvalとdownload

1. UIの表示済み判定を信用しない。
2. approvalと納品用download handlerはglobal OS lock内でcurrent caption、current render、actual MP4 hash、QC、content reviewを再読込する。
3. `output_hash + caption_revision`が一致しないrequestを拒否する。
4. approval書込みは同じcritical sectionでatomic publishする。
5. review用videoと納品用download endpointを分ける。

### §4.7 Deliveryと修正版

実送付した後だけ、text ledgerへ次の1行を追記する。

```text
client | delivered_at | output_hash | caption_revision
```

「前に送った版を直して」という依頼はcurrentから始めず、ledgerの該当caption revisionを新working revisionへcopyする。旧caption、旧render、旧deliveryを上書きしない。

## §5. product Phase

各Phaseは明示承認後だけ開始し、終了時に停止する。これは元implementation promptの一Phase・一承認gateを維持するためである。

### Phase P0 — Windows review preflight（0.25日）

- §4.2の4項目を実測する。
- product code変更なし。
- 失敗時の縮退先を確定して停止する。

### Phase P1 — Safe caption vertical slice（6.0〜9.0日）

内部実装順:

1. immutable caption revisionとcurrent pointer
2. revision固定renderとimmutable render
3. global OS lock、approval/download時の再照合
4. plain caption edit UI
5. technical/content別表示
6. output単位のfull playbackとapproval
7. 3境界fault test

完了条件:

- 新規disposable jobまたはsynthetic fixtureで、ASSを直接編集せず1語修正できる。
- render中caption変更、二つのtab、review後caption変更でstale renderを承認できない。
- pointer置換失敗時も旧revision/renderとdirty内容が残る。
- app再起動後もcurrent captionとcurrent renderを復元できる。
- 180秒jobを受理し、180秒超を拒否する。

180秒は `CODEX_NEXT_SESSION_IMPLEMENTATION_PROMPT.md` Phase 0aの明示要件であり、YouTube Shortsを最大3分とする同project設計の公式Help根拠に従う。対象配信先が変わる場合だけ別gateで見直す。

legacy jobはread-onlyであり、fixtureとして変更しない。

### Phase P2 — Two-pass internal pilot（1.5〜2.5日）

1. 新規許可済みjobでrightsからapprovalまで完走する。
2. deliveryは実送付せず、test ledgerへR1を記録する。
3. app再起動後、R1を起点に固有名詞を1件修正してR2を作る。
4. R1を履歴として保持し、R2だけをcurrentとしてfull review・再承認する。
5. recovery active timeとtotal active timeを記録する。

### Phase P3 — Creative-quality offline spike（§8成立時だけ、1〜2日timebox）

- product code、DB、API、UIを作らない。
- `scratch/<run_id>/<source_id>/` へsource assessment、0〜5 candidates、baseline preview、paced preview、source map、resultを上書き禁止で保存する。
- 1つの開発用sourceで閾値を固定し、その閾値作成に使っていない許可済みsource 1本をholdoutにする。
- 結果を報告して停止する。

P0〜P2の再見積は7.75〜11.75日。P3を含めても15人日以内を上限とし、実績burnと未着手上側見積が15日を超える場合はP3を開始しない。

## §6. Creative-quality workflow（P3以降だけ）

### §6.1 Source assessment

許可されたtranscript、任意のpublic metadata、frames許可時だけscene変化を使い、次を文章で返す。

- `straight_cut_likely`
- `pace_edit_likely`
- `reject_likely`

public heatmap欠落はwarningであり停止条件にしない。numeric AI scoreだけで採否を決めない。

### §6.2 Candidate

AIは0〜5件を返す。0件は正常結果である。各候補はsource start/end、hook、setup、payoff、context依存、ASR risk、推奨modeを持つ。

### §6.3 Paced recipe

- keep rangesはsource時間順、非overlap、候補span内に限定する。
- sceneを並べ替えない。
- silence、filler、repetition、false startだけを削除候補にする。
- 否定、主語、対象、結論を変えるjoinを自動確定しない。
- 0.1秒cut数を品質指標にしない。
- editable recipeをproduct化する場合は、captionとrecipeを一つのimmutable edit revisionへまとめるか、recipe固定の新jobにするかを一つだけ選ぶ。

### §6.4 Human review

人間は長時間sourceではなくpreviewだけを確認し、candidate採否、意味が変わるjoin、字幕の細部、最後の全編再生を担当する。

### §6.5 Style

clientまたはユーザーの具体的briefが得られた後だけ、1つの固定file presetを作る。font、color、outline、shadow、punch-inの有無を含めるが、style editorは作らない。cut timingのA/Bとstyle比較を同時に行わない。

## §7. P3の事前成功条件

holdout実行前に次を固定する。

- userが見るpreviewは最大5件。
- candidate reviewとpacing correctionの合計active timeは10分以内を目標とする。
- paced版がbaselineより良いとuserが選ぶ。
- human-discovered semantic cut errorは0件。1件あれば修正後に再確認し、初回結果は未達とする。
- holdoutで未達ならmulti-cut product化を行わない。
- offline candidate UI化は、累計3job中2job以上で採用されるまで行わない。

開発用sourceの結果を、同じsourceの肯定gateとして再利用しない。

## §8. Creative-quality laneの再開条件

次のいずれかをユーザーが確認した場合、P3を提案できる。

1. 実案件でsource探索またはpacing手修正が1job 10分以上を占めた。
2. clientがpaced editを明示要件にした。
3. ユーザーが現在の連続切り抜き品質では案件化できないと判断した。

今回のユーザー所感は3に該当するが、P3開始には別の許可済みholdout sourceと明示承認が必要である。P3はP1/P2のblocking gateにはしない。

## §9. 初期scope外

- generic NLE timeline
- scene並べ替え
- B-roll自動生成・挿入
- face / speaker tracking
- DB、queue、複数worker
- 自動投稿・自動delivery
- client portal
- style editor
- AI scoreによる自動承認

## §10. 停止条件

- rights entryまたは必要payload許可がない。
- P0の4項目のどれかが成立せず、縮退先を決められない。
- S-01 / S-02 / S-04を弱める必要がある。
- legacy jobを変更しないと検証できない。
- actual burnと未着手上側見積が15人日を超える。
- P3のholdout sourceがない。
- paced editが意味を変えるが、人間確認で解消できない。
- 現Phaseの明示承認がない。

## §11. 未解決のまま進む項目

- Hermes実機playerとbackend roundtripはP0未実施。
- P1の6〜9日はRound 1の実質見積であり、P0結果で再見積する。
- paced editのproduct revision方式はP3結果が出るまで決めない。
- candidateの見逃し率は未測定である。
- client style briefは未入手である。
