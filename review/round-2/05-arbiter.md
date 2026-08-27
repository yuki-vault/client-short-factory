# Arbiter — Round 2

## 裁定要約

- 原 finding 22件を根本原因9群へ統合した。
- 最優先は、P0を単なるHermes UI可否確認から、CLI＋file経路との実走比較を含む0.5日の最短経路選択へ置き換えることである。
- 現行実装範囲はP0＋P1へ縮退し、独立P2、P3と§6〜§8、180秒hard gate、`current_render.json`を外す。
- 暫定再見積はP0 0.50人日、統合pilot込みP1 6.10〜9.10人日、合計6.60〜9.60人日である。P0で得るWBS計測値を確定値とする。
- Round 2終了時点で未解決のまま進む項目は5件である。

## プロセス健全性

| # | 判定 | 根拠 |
|---|---|---|
| P-1 | 継続 | 重大指摘はAgent 01が4件、Agent 02は該当なし、Agent 03が2件、Agent 04が4件で、4体すべてが空ではない。 |
| P-2 | 継続 | 同じ節へ逆向きとなる立場を6件検出し、下表で片側を選んだ。 |
| P-3 | 継続 | must_fix 10件の全件に、主体・順序・失敗結果を含む操作列がある。操作列率は10/10、100%である。 |
| P-4 | 継続 | rawの正の追加コストは0.85人日、重複排除後に採る追加は0.60人日。Draft 1の初期実装本体P1（工程契約上のPhase 0a相当）の下限6.0人日を超えない。 |
| P-5 | 継続 | schema-invalidは0件。影響区分欠落、10分事故のmust_fix化、正の追加と交換削除なし、推測だけの操作列はいずれもない。 |

**工程判定: 成立。** 統合と着手順の確定へ進む。

## finding別 disposition

この表の `reject` はcriticの提案を採らないという意味であり、設計書から消す記述は後段の専用表にまとめる。

| finding | 統合先 | disposition | 裁定理由 |
|---|---|---|---|
| F-01-001 | D-01 P0最短経路 | adopt | 0人日で6〜9人日の誤選択を開始前に止められる。 |
| F-01-002 | D-01 P0最短経路 | modify | F-04-08と統合し、7項目の再利用分類に実機往復・fixture・fault testの計時も加える。 |
| F-01-003 | D-08 P3削除 | defer | 現行文書からP3を外すため、candidate recallの計測は将来の別設計まで保留する。 |
| F-01-004 | D-05 delivery ledger | modify | F-04-03と統合し、一意性と送付窓を一つのledger変更で扱う。 |
| F-01-005 | D-04 content review | reject | F-03-02の謝罪に至る操作列を優先し、初期版では再生監視を残す。 |
| F-01-006 | D-08 P3削除 | adopt | 単発10分を投資再開条件にしない。該当条件は現行文書から消す。 |
| F-02-01 | D-07 P2縮退 | modify | 独立Phaseは消すが、実jobのR1→R2確認0.5人日はP1最終release checkへ残す。 |
| F-02-02 | D-08 P3削除 | modify | P3と§6〜§8を消し、再開条件だけを§11のbacklog 1行へ縮退する。 |
| F-02-03 | D-04 content review | reject | identity-bound checkboxだけでは、mute再生を内容確認として通すF-03-02の操作列を閉じない。 |
| F-02-04 | D-03 pointer/lock | adopt | `current_render.json`を消し、actual hashとcaption revisionの照合を正本にする。 |
| F-02-05 | D-09 duration | adopt | 180秒受理・超過拒否をP1完了条件から消す。 |
| F-03-01 | D-03 pointer/lock | modify | render pointerは削除するため、同じOS lockへのwriter参加は残る`current.json`へ適用する。 |
| F-03-02 | D-04 content review | adopt | full-playback中のmute・音量0・音量変更を無効化し、終端後の明示確認も同一identityへbindする。 |
| F-03-03 | D-06 orphan recovery | modify | caption本文の二重保存ではなく、F-04-07の小さなrecovery pointerでpublish済みrevisionを復帰させる。 |
| F-04-01 | D-02 P1累積slice | modify | P1a/P1bを採り、Hermes UIのP1cはP0が必要と判定した場合だけ行う。 |
| F-04-02 | D-01 P0最短経路 | modify | 0.5日と各check 30分上限を採り、最短経路比較と同じdecision tableへ統合する。 |
| F-04-03 | D-05 delivery ledger | modify | F-01-004のjob/name一意性を加えた二段階ledgerへする。 |
| F-04-04 | D-02 P1累積slice | adopt | 1枚の`phase-progress.md`を各sliceの再開点として使う。 |
| F-04-05 | D-04 content review | reject | 再生監視を消す側は、F-03-02の謝罪操作列より優先できない。 |
| F-04-06 | D-07 P2縮退 | adopt | 独立P2を消し、0.5日の実job release checkだけをP1へ移す。 |
| F-04-07 | D-06 orphan recovery | adopt | pointer replace失敗後に、publish済みrevisionを再指定できる最小経路を作る。 |
| F-04-08 | D-01 P0最短経路 | adopt | P0で実機往復時間と7項目WBSを測り、それ以前の6〜9日をcommitmentに使わない。 |

### disposition集計

- adopt: 9件
- modify: 9件
- reject: 3件
- defer: 1件
- 合計: 22件

## 対立と裁定

| # | 節 | Aの立場 | Bの立場 | 採用 | 受け入れたリスク | 影響区分 |
|---|---|---|---|---|---|---|
| C-01 | §4.5 | F-01-005 / F-02-03 / F-04-05: 再生状態機械を削り、identity-bound明示確認だけにする | F-03-02: full-playbackを残し、mute系を封じたうえで明示確認する | **B**。謝罪までの操作列があるため、初期版は機械監視＋identity-bound明示確認とする | browser event実装約1人日相当と、修正版でも全編再生する負担を残す | 謝罪 |
| C-02 | §4.2 / §5 | F-01-001: CLI＋fileが同じmilestoneを満たせばUIへ進まない | F-04-01: P1cでHermes editorまで積む | **A**。P1cはP0で不足が示された場合だけ行う | 最初のmilestoneでHermes UIが提供されない場合がある | 半日 |
| C-03 | §4.4 / §4.6 | F-02-04: `current_render.json`を削除する | F-03-01をrender側へ適用: pointerを残してwriterをlockする | **A**。render pointer自体を消す。F-03-01は残るcaption pointerだけに限定する | 同一caption revisionに複数renderがある時、表示対象を手で選び直すことがある | 10分 |
| C-04 | §5 P2 | F-02-01: fixture smokeへ統合し、実job pilotは初回案件へ送る | F-04-06: 独立Phaseを消すが実job確認0.5人日はrelease checkへ残す | **B**。ledger起点のR1→R2だけを0.5日で残す | fixtureだけの案より初期到達が0.5日遅い | 半日 |
| C-05 | §5 P3 / §6〜§8 | F-01-003: P3をpaced比較へ縮退して残す | F-02-02: 現行文書からP3詳細を削除する | **B**。将来条件だけbacklogへ残す | creative品質の検証開始が後ろ倒しになる | 半日 |
| C-06 | §4.3 | F-03-03: durable draftを別保存する | F-04-07: publish済みrevision IDだけをrecovery pointerへ残す | **B**。既にdurableなrevision本文を重複保存しない | revision本体publish前の失敗は既存editor dirty保持に依存する | 10分 |

同一対立で両案を積み上げていない。C-03でF-03-01を`current.json`へ残すのは、削除する`current_render.json`と別の競合面である。

## 着手順（この順で実行する）

人日は、明記がない限り既存P1見積に対する差分である。

| 順 | 作業 | 由来 finding | 人日 | 交換に削除する項目 | 完了判定 |
|---:|---|---|---:|---|---|
| 1 | P0を0.5日の最短経路gateへ置換し、CLI＋fileで1語修正→revision固定render→QC/content別記録→current identity照合を実走する。同時にHermes 4 checkを各30分で打ち切る | F-01-001, F-04-02 | 0.50（+0.25） | §4.4 `current_render.json`削除の0.5人日をD-06と分けて充当 | `P0-shortest-route-gate`と`P0-failure-routing`が経路を一意に返す |
| 2 | P0結果へP1の7項目を`実走済み / 再利用のみ / 新規`で記録し、cold/warm往復、fixture、3 fault境界を含むWBSで上下見積を再計算する | F-01-002, F-04-08 | 0.00 | なし | 第三者が同じlower/upperを再計算でき、15日判定を開始前に行える |
| 3 | P1をP1a（ASS不要の保存＋preview render）、P1b（安全なreview/approval/download）、条件付きP1c（Hermes UI）へ分け、`phase-progress.md`を各停止点で更新する | F-04-01, F-04-04 | +0.10 | 独立P2削除の最低1.0人日から充当 | 各slice終了後に停止し、15分以内に次testから再開できる |
| 4 | P1aへorphan revision recovery pointerを入れ、再起動後に旧current維持かpublish済みrevision再指定かを選べるようにする | F-03-03, F-04-07 | +0.25 | §4.4 `current_render.json`削除の残り0.25人日を充当 | `caption-pointer-failure-restart`で旧正常caption/renderを保ったまま復帰できる |
| 5 | `current_render.json`を使わず、`current.json`のpublish writerをapproval/downloadと同じOS lockへ参加させる。approvalはactual hash＋caption revisionを正本として再照合する | F-02-04, F-03-01 | -0.50 | なし | approval中はcaption writerが待ち、writer後の旧identity requestが拒否される |
| 6 | P1bのfull-playbackを維持し、mute・音量0・途中音量変更を無効化する。終端だけではcontent reviewを完了させず、同じ`output_hash + caption_revision`への明示確認を要求する | F-03-02 | 0.00 | なし | mute 3ケースは未確認のまま、正常再生＋明示確認だけが対象identityを確認済みにする |
| 7 | ledgerを`prepared`と`delivered`の二段階にし、`job_id`、clientが見る`delivery_name`、unique filename、hash、caption revisionを記録する | F-01-004, F-04-03 | 0.00 | なし | 同一clientのA/Bを自然言語名と送信済みfilenameから一意に選べ、送付直後の強制終了でもR1を復元できる |
| 8 | 独立P2を作らず、許可済み実jobのR1→R2、ledger起点、再起動、再承認をP1最終release checkとして0.5 active dayで行う | F-02-01, F-04-06 | 0.50（既存P2から移管） | §5 独立P2の残り1.0〜2.0人日を削除 | 0.5日内でR1保持、R2だけcurrent、再起動後再承認を確認し、欠陥はP1 burnへ戻す |
| 9 | P0がHermes UIを必要と判定した場合だけ、P1cとして同じbackendへeditorを被せ二tab試験を行う。CLI＋fileでmilestone達成ならここで停止する | F-01-001, F-04-01 | P0 WBSで確定 | P1c不要時は未着手UI全体 | `P1c-two-tabs`、またはP0記録にUI不要の停止根拠がある |

## 削除する記述（reject）

| § | 削除対象 | 削減人日 | 受け入れるリスク |
|---|---|---:|---|
| §4.4 | `current_render.json`の作成、atomic replace、復元処理 | 0.50 | 同じcaption revisionのrenderが複数ある時、表示対象の選び直しに10分以内を使う |
| §5 | 独立Phase P2の1.5〜2.5日枠。R1→R2実job確認0.5日だけはP1へ移す | 1.00〜2.00 | pilotで見つかった欠陥の修正余白を別Phaseに隠せず、P1 burnへ戻す必要がある |
| §5 P3 / §6 / §7 / §8 | creative-quality laneの現行詳細設計。§8.1の単発10分triggerも含む | 1.00 | paid案件のcreative要件が先に来た場合、別設計に半日以上を取り直す |
| §5 P1完了条件 | 180秒受理・180秒超拒否のhard gateと境界fixture | 0.25 | 初めて長尺依頼が来た時、その案件だけscratch確認またはCLI縮退が必要になる |

削減合計は最低2.75人日、最大3.75人日。正の追加0.60人日との差引は、現行文書全体で最低2.15人日、最大3.15人日の縮退となる。

## 交換削除の裁定

| 追加 | 追加人日 | 交換対象 | 裁定 |
|---|---:|---|---|
| P0の0.5日化 | +0.25 | `current_render.json`削除0.5のうち0.25 | 採用 |
| `phase-progress.md` | +0.10 | 独立P2削除1.00〜2.00のうち0.10 | 採用 |
| orphan recovery pointer | +0.25 | `current_render.json`削除0.5の残り0.25 | 採用 |

F-03-03が交換候補にした§4.1のpayload別notesは削除しない。今回観測済みの許可差を記録する既存text運用であり、上表の削除だけで予算中立を満たすためである。

## 未解決のまま進む項目

| 項目 | 理由 | 撤退条件（何が起きたら戻ってくるか） |
|---|---|---|
| Hermes UIとCLI＋fileのどちらが最短か、およびP1の確定上下幅 | P0実機計測前である | P0でCLI＋fileが4操作を満たせばUIを落として停止。render入口が失敗すればP1を始めず修復待ちへ分岐する |
| candidate discoveryの見逃し率 | P3と§6〜§8を現行scopeから削除し、F-01-003を保留した | paid clientの明示要件、案件化不能の判断、または確定jobの累積手作業時間が1〜2日のspike幅を上回った時、holdout付きの別設計として戻す |
| 外部送付と`delivered`追記の完全な一体化 | 外部channelとlocal text追記はatomicにできず、prepared行＋unique filenameで手動照合する | 送信済みfilenameから一意に戻れない事例が1件出たらdelivery手順を再設計する |
| 同一caption revisionに複数renderがある場合の自動canonical選択 | `current_render.json`を削除し、hash identityを優先した | 1案件で選び直しが10分を超えた時だけrender選択規則を再検討する |
| 観測済み短尺を超えるjobの受理範囲 | 180秒hard gateを削除し、現時点では50.21秒相当しか実走していない | 初回の長尺brief受領時にscratch実行し、失敗または半日超の復旧が出たらduration gateを再設計する |

## 再見積

### 算式

```text
P0: 0.25 + timebox拡張0.25 = 0.50
P1: 6.00〜9.00
    + progress 0.10
    + orphan recovery 0.25
    + P2から移すrelease check 0.50
    - current_render 0.50
    - 180秒gate 0.25
    = 6.10〜9.10
P0 + P1 = 6.60〜9.60
```

- Phase P0: **0.50人日**
- Phase P1（P1a/P1b、必要時P1c、統合release check込み）: **暫定6.10〜9.10人日**
- 現行実装scope合計: **暫定6.60〜9.60人日**
- 最初の体感価値まで: **P0 0.50人日＋P1a**。P1a単独値はP0のWBSで確定し、現時点の防御可能な上限は全体上限の9.60人日とする。
- P3: **現行見積から除外**

この数値は裁定差分を既存レンジへ反映した上限枠であり、commitmentはP0後の実機WBS値へ置き換える。P0でCLI＋fileがmilestoneを満たした場合はP1cを行わず、実績はこの枠より小さくなる。

## Round 3 の要否

**ループ上限到達（Round 2で打ち切り）。** 5件の未解決は、上表の条件で戻すか、機能を落としたまま実装へ進む。次ラウンドは要求しない。
