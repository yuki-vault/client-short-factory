# Arbiter — Round 1

## プロセス健全性

| # | 判定 | 根拠 |
|---|---|---|
| P-1 | 非該当 | Agent 01 / 02 / 03 / 04 の重大判定は順に 4 / 1 / 4 / 5 件で、4体すべてに操作可能な指摘がある。 |
| P-2 | 非該当 | 同じ節に対する逆向きの結論を4軸で検出した。特に §9 W2 の current pointer / global OS lock は Agent 02 の削除案と Agent 03 の保持案が正面から対立する。 |
| P-3 | 非該当 | 重大判定14件の再現条件はすべて、作業者または開発者の操作順まで記載されている。 |
| P-4 | 非該当 | 正の追加提案は Agent 03 の1.0人日と Agent 04の0.75人日の計1.75人日で、Draft 0の Phase 0a 見積2〜3人日以下である。 |
| P-5 | 非該当 | finding-schema の無効条件に触れる finding は見当たらない。正の追加コストにはすべて交換削除があり、影響区分と再現操作も埋まっている。 |

→ **成立**

同一根本原因である「W5より前に二次目的を直列配置」は F-01-001 / F-02-001 / F-03-005 / F-04-01 / F-04-03 を一本化した。動画経路の未観測は F-01-004 / F-04-07、納品後修正は F-01-003 / F-04-05、W0削除は F-02-002 / F-04-06、style削除は F-01-005 / F-02-005 / F-04-05 として統合した。severity規則による機械的な降格対象はない。F-01-006 と F-03-006 は should_fix、F-04-07 は defer のままとし、動画経路を先に測る作業義務は同根の F-01-004 から採る。

## 対立と裁定

| # | 節 | A の立場 | B の立場 | 採用 | 受け入れたリスク | 影響区分 |
|---|---|---|---|---|---|---|
| 1 | §3.2 / §4.4〜§4.5 / §7.1 / W1 / W4 | Agent 01・04: core後にspikeを残し、計測またはholdoutで判断する | Agent 02・03: 現行設計からmulti-cut枝を削る | **Agent 02・03**。記載0.5〜1日を超えて実質1.5〜3日かかる見積を採り、W1/W4を現行設計から削る | slow-talkの自動テンポ改善を初版では行えず、必要時は外部編集または後日の手作業になる | 半日 |
| 2 | §4.2〜§4.3 / §5 / W3 | Agent 01・04: core後の独立改善として残す | Agent 02: 初回scopeから削る | **Agent 02**。source triage / candidate生成を現行設計から削る | 長時間sourceの候補探索は当面手作業になり、候補探索時間の改善を先送りする | 半日 |
| 3 | §9 W2 | Agent 02: current pointer と global OS lock を削る | Agent 03: pointerを保持し、lock内で承認・納品用downloadを再照合して書き込む | **Agent 03**。S-01へ直結するため pointer と global OS lock を残す。180秒制約だけは F-01-006 に従って外す | 単一PCでもpointer更新とlock処理の実装・確認が残る | 謝罪 |
| 4 | §7.2 / W7 | Agent 02: 独立pilotを削り、縮退版W5の受け入れへ統合する | Agent 01・04: 納品版台帳を残し、承認後修正を含む独立2回pilotにする | **Agent 01・04**。過去納品版を修正起点として識別する操作列を独立して通す | 1回確認より0.5人日増え、core完成後にもう一つ完了境界が残る | 謝罪 |

## 着手順（この順で実装する）

| 順 | 作業 | 由来 finding | 人日 | 完了判定 |
|---:|---|---|---:|---|
| 1 | Draft 1で当面の目的を caption-only vertical slice に戻し、W0/W1/W3/W4/W6を初期列から外す。product code着手前とvertical slice受け入れの2 gateだけを残す | F-01-001, F-02-001〜005, F-03-005, F-04-01, F-04-03, F-04-06 | 0 | Phaseの先頭から読んで、別sourceなしで `plain caption save → explicit render → technical/content別表示 → currentだけ承認` に到達し、二次目的が途中停止点にならない |
| 2 | product codeを変えないWindows preflightで、既存MP4再生・seek、字幕scratch保存、既存render入口、app再起動後の再接続を測る | F-01-004, F-04-07 | 0.25 | 4項目を1枚のlogへ記録する。1項目でも不成立ならUI実装を止め、既存CLI＋file運用へ縮退する |
| 3 | Phase 0aの安全境界を実装する。render開始時のcaption revision固定、immutable render、current pointer、global OS lock、承認・納品用downloadのlock内再照合、3境界fault testを一体で閉じる | F-03-001, F-03-002, F-03-006, F-04-02 | 4.5〜6.5 | `S01_render_input_snapshot_while_caption_changes` と `S01_two_tabs_approval_compare_and_commit` が旧renderを拒否する。置換失敗時は旧revision/renderとdirty内容を保持し、保存済み表示・render・approvalへ進まない |
| 4 | Phase 1のcaption-only UIを実装する。current video、plain caption edit、explicit render、technical/content別表示、output単位の全編再生証跡、current-only approvalに限定する | F-01-001, F-02-001, F-03-003, F-03-004, F-04-01 | 1.5〜2.5 | legacy job `pJFBzCQq7M8_mvp_final` でASSを直接編集せず1語修正する。review状態は `output_hash + caption_revision` に結び、終端seek・非表示tab・途中source差替えでは全編再生済みにならず、0秒から同一outputを連続再生した場合だけ承認へ進む |
| 5 | 納品版の1行台帳と独立2回pilotを実施する | F-01-003, F-04-05 | 1.5〜2.5 | `client / delivered_at / output_hash / caption_revision` でR1を記録し、R2をcurrentにした後、台帳のR1を起点にR3を作る。再起動後も3版を保持し、R3だけをcurrentとして再承認できる |
| 6 | 各作業境界で `actual burn + 残作業の上側見積` を更新し、15人日を越える作業を開始しない | F-04-02 | 0 | 未着手作業だけが削減候補として表示され、完了済み工数を削減額へ数えない |

## 削除する記述（reject）

| § | 削除対象 | 削減人日 | 受け入れるリスク |
|---|---|---:|---|
| §3.2 / §4.4〜§4.5 / §6のedit recipe系 / §7.1 / W1 / W4 | multi-cutのscratch A/B、product revision二択、keep ranges、source map、product統合 | 1.5〜3.0 | slow-talkの自動テンポ改善を初版から失い、必要時は外部編集または手作業になる |
| §4.2〜§4.3 / §5 / §6のassessment・candidate系 / W3 | source triage、0〜5 candidate生成、mode判定 | 1.0〜2.0 | 長時間sourceから区間を探す作業は当面人間が行う |
| §4.7 / W6 / §13.5 | client別style preset | 0.5〜1.0 | 初回は現行caption styleを使い、client固有指定には要望受領後に対応する |
| W0 / §9末尾 | 独立した計測protocol Phaseと各Phaseごとの停止。product code着手前とvertical slice受け入れの2 gateへ縮退する | 0.25 | 中間artifact単位の確認機会が減る |
| §4.1 | payload別permission schema。`rights.txt` 1枚のsource識別子・編集許可・外部AI利用許可・確認日へ縮退する | 0.25 | payload単位の差が実案件で出た場合、依頼者へ再確認が必要になる |
| §8 | 5分割active timeと7 outcomeの必須台帳。任意の `total_active_min` だけ残す | 0.25 | 次の自動化判断で工程別時間が必要になれば測り直す |
| W2 | 根拠未提示の180秒制約 | 0〜0.1 | 長い入力を事前拒否せず、処理時間が延びる場合がある |

F-02-008のうち current pointer / global OS lock の削除、および F-02-009 の独立W7削除は採らない。保守的な削減下限は3.75人日、正の追加提案は1.75人日なので、差引は少なくとも2.0人日の削減になる。

## 未解決のまま進む項目

| 項目 | 理由 | 撤退条件（何が起きたら戻ってくるか） |
|---|---|---|
| Hermesの動画再生・UI→backend経路 | 現行PCでの実測がなく、F-01-004とF-04-07の判断が未確定 | preflightの再生・seek・保存・render起動・再接続のどれか1つでも成立しなければUI前提を撤回し、既存CLI＋file運用へ戻る |
| multi-cutの価値とrevision方式 | 2素材で閾値を後決めする方法では肯定判断を反証できず、実質spike費も1人日を超える | 閾値を先に固定し、その作成に使っていない実案件が閾値を満たし、かつclientがpaced編集を必要とした時だけ再審する。S-01/S-04の操作列テストを書けなければproduct化を再度落とす |
| source triage / candidate生成の価値 | 候補探索が字幕修正より大きいボトルネックか未計測 | 2本以上の実案件で候補探索が字幕修正より大きいactive timeを占め、自動候補なしでは依頼完了を妨げると確認された時だけW3相当を再審する |
| 複数source用scratchのnamespaceと再開情報 | W1/W3を削除するため今は実装対象がないが、F-04-04の上書き操作列は未検証のまま残る | multi-source spikeを再導入する時は、実行前に `scratch/<run_id>/<source_id>/` と `last_completed / next_step / command / input_hash` を必須化する |
| 同期folder対応 | 初期版はOneDrive / Dropbox配下を非対応に縮退し、同期clientとの置換競合を解かない | 実案件のjob保存先が同期folder必須になった時だけ、sharing violationを含む保存・再開試験へ戻る |
| 配信先ごとのduration上限 | 180秒を支えるclient要件と公式仕様が提示されていない | 対象clientと配信先が固定され、現行仕様の根拠が得られた時だけ、その配信先固有gateとして戻す |

## 再見積

- Phase 0a: **4.75〜6.75人日**（preflight 0.25 + W2実質4〜6 + render/approval安全条件0.5）
- Phase 1: **3.0〜5.0人日**（caption-only UI 1〜2 + review証跡条件0.5 + 2回pilot 1.5〜2.5）
- Phase 0a + Phase 1: **7.75〜11.75人日**
- 最初の体感価値まで: **6.25〜9.25人日**（2回pilot前、caption-only vertical slice完了時）
- 15人日までの余白: **3.25〜7.25人日**。ただし削除したW1/W3/W4/W6をこの余白だけで自動復活させない

## Round 2 の要否

**必要**。Draft 1へ上記の採用・削除・未解決条件を反映した後、同じ4観点で再レビューする。Round 2を最終ループとし、そこで残る非安全系の論点はbacklogまたは未解決として固定する。
