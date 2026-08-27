# Agent 02 — Scope Assassin — Round 2

## 総括（3行以内）

S-01 / S-02 / S-04を弱めず、初期P0 + P1は6.25〜9.25人日から4.50〜7.50人日へ縮退できる。
主な余剰は、P1と重複するP2、まだ作らないcreative laneの詳細設計、内容確認を機械で強制する再生状態機械である。
条件付き将来作業を含む削減合計は4.25人日で、現時点の中核はcaption revision、server-side identity照合、明示的な内容確認だけで足りる。

## findings

### [F-02-01] P1と同じ事故列をもう一度通すP2を独立Phaseから削除する

- **対象**: §5 / `### Phase P2 — Two-stage internal pilot（1.5〜2.5日）`
- **主張**: P2の新規job、再起動、R1からR2への修正、旧版保持、再承認は、P1完了条件の1語修正、再起動復元、stale render拒否、revision保持を実データでもう一巡する工程である。納品実績0本の段階で別Phaseにすると、同じ安全性を二度証明するために最短1.5日を消費する。
- **再現条件**: 開発者がP1の完了条件を全て通す → 新たな許可済みjobを用意する → rightsからR1承認まで実行する → appを再起動する → 固有名詞を直してR2をrender・全編review・再承認する → P2終了まで初回運用を止める。
- **反証条件**: P1がsynthetic fixtureでは通るが許可済み実sourceでは既存render入口まで到達できないとP0で実測された場合。
- **影響区分**: 半日
- **severity**: reject
- **最小修正案**: P2を削除し、同じdisposable jobでR1→R2を1回通す手順をP1の手動smoke testへ統合する。新規sourceでのrights-to-delivery確認は最初の実案件で行い、既存CLI＋file reviewをfallbackにする。
- **検証方法**: P1-E2E-REVISION — 同一fixtureでR1承認後に1語直してR2を承認し、R1が残りR2だけがcurrentであることを確認する。
- **追加コスト**: -1.5 人日
- **交換に削除する項目**: §5 / Phase P2全体

### [F-02-02] evidence待ちのcreative laneを詳細設計した§6〜§8とP3を現行文書から削除する

- **対象**: §5 / `### Phase P3 — Creative-quality offline spike（§8成立時だけ、1〜2日timebox）`
- **主張**: §1.2で効果不明、§2.2で後続とした機能に、source assessment、candidate schema、paced recipe、holdout、成功閾値まで先に固定している。しかも§8条件3は本文中で既に成立済みと宣言されているため、evidence gateではなく、承認さえあれば直ちに1〜2日を使える入口になっている。
- **再現条件**: 開発者がP1を終える → §8の「今回の所感は3に該当」を読む → holdout sourceの許可を得る → P3を開始する → 未計測のcandidate形式と閾値に沿ってpreview一式を作る → 初回納品前に1〜2日を消費する。
- **反証条件**: 支払い予定のclientがpaced editを受注条件として明示し、許可済みholdout sourceも同時に提供した場合。
- **影響区分**: 半日
- **severity**: reject
- **最小修正案**: Phase P3と§6〜§8を削除し、§11へ「paid clientの明示要件、または納品済みjobでpacing手修正10分超を観測した時だけ別設計を作る」というbacklog 1行だけを残す。
- **検証方法**: SCOPE-DOC-01 — P0/P1の実装一覧にcandidate、recipe、holdout、style presetのartifact・schema・testが一件も含まれないことを確認する。
- **追加コスト**: -1.0 人日
- **交換に削除する項目**: §5 / Phase P3、§6、§7、§8

### [F-02-03] 内容確認の分離は残し、連続再生を証明するbrowser状態機械を削除する

- **対象**: §4.5 / `gate獲得中は0秒から開始し、seekと速度変更を無効化する。`
- **主張**: S-02が要求するのはtechnical QCと内容確認を同一表示にしないことであり、tab可視性、seek、速度、source変更、再renderを監視して連続再生を証明することではない。この状態機械は「見た時間」は証明しても「内容を確認した」ことは証明せず、browser event差分と中断復帰の実装・試験だけを増やす。
- **再現条件**: 開発者がQC状態とは別にplayback sessionを作る → visibility change、seek、速度変更、source変更、再renderでsessionを破棄する → 終端判定と再起動時状態を実装する → 各eventをWindows実機browserで試験する → 明示確認checkboxだけの場合より少なくとも半日余計に費やす。
- **反証条件**: client契約が「等速・無seek・連続全編再生の機械記録」を納品条件として要求した場合。
- **影響区分**: 半日
- **severity**: reject
- **最小修正案**: technical QCとcontent reviewの別表示、`output_hash + caption_revision`へのbind、caption/render変更時の確認解除だけを残し、ユーザーが押す「この版の内容を確認した」checkboxへ縮退する。
- **検証方法**: CONTENT-STATE-01 — QC成功直後は「内容未確認」、checkbox後だけ「内容確認済み」、caption変更後は再び「内容未確認」になり、旧outputの確認が継承されないことを確認する。
- **追加コスト**: -1.0 人日
- **交換に削除する項目**: §4.5 / full-playback gate、連続再生条件、tab・seek・速度の監視

### [F-02-04] S-01のserver-side照合を残し、二重管理になる`current_render.json`を削除する

- **対象**: §4.4 / `完成directoryをpublishした後だけcurrent_render.jsonをatomic replaceする。`
- **主張**: immutable render metadataが入力caption revisionを持ち、approval/download handlerがcurrent caption、actual hash、QC、content reviewをlock内で再照合するなら、別のcurrent render pointerはS-01を追加では守らない。pointerのpublish失敗、render directoryとの不一致、再起動復元という新しい状態だけが増える。
- **再現条件**: 開発者がrender directoryをpublishする → pointerをatomic replaceする → caption変更中renderではpointerを更新しない分岐を作る → pointer欠落・旧pointer・壊れたpointerからの復元を実装する → その後approval handlerでも同じcaption revisionとhashを再照合する。
- **反証条件**: 同じcaption revisionから複数renderを常時作り、そのうち一つを再起動後もcanonicalとして自動選択しなければ1案件を処理できない場合。
- **影響区分**: 半日
- **severity**: reject
- **最小修正案**: `current_render.json`を削除し、UIはpublish済みrenderのうちcurrent caption revisionに一致する最新の完成renderを表示する。approval/download時のglobal lock、actual hash、caption revision、QC、content review再照合はそのまま保持する。
- **検証方法**: STALE-RENDER-02 — R1をrender後にcaptionをR2へ変更し、R1のapproval/downloadが拒否され、R2の完成renderだけが承認できることを二つのtabとapp再起動後に確認する。
- **追加コスト**: -0.5 人日
- **交換に削除する項目**: §4.4 / `current_render.json`の作成・atomic replace・復元処理

### [F-02-05] 未観測の180秒境界をP1完了条件から削除する

- **対象**: §5 / `180秒jobを受理し、180秒超を拒否する。`
- **主張**: 観測済みoutputは50.21秒1本であり、目的はcaption修正と最新版承認である。配信先の上限をproductのhard rejectへ変換すると、180秒・181秒fixture、duration取得失敗、境界表示の実装と試験が増える一方、最初の1〜2社を回す根拠にはならない。
- **再現条件**: 開発者がduration validatorを追加する → 180秒と180秒超のfixtureを用意する → import、render、reviewの各入口で拒否を揃える → 50.21秒jobだけの現行運用を始める前に境界試験を完了する。
- **反証条件**: 最初のclient briefが180秒納品を要求し、既存render入口にduration制限が既に実装済みで追加作業が発生しない場合。
- **影響区分**: 10分
- **severity**: reject
- **最小修正案**: 180秒hard gateを削除し、初期版は観測済み50.21秒jobと同程度の短尺を手動で受ける。長尺依頼が来た時点で一度scratch実行し、失敗時は既存CLI＋file reviewへ縮退する。
- **検証方法**: P1-CURRENT-SIZE — 50.21秒のdisposable copyでcaption save、render、QC、content confirmation、approvalが完走することだけを確認する。
- **追加コスト**: -0.25 人日
- **交換に削除する項目**: §5 / P1完了条件の180秒受理・超過拒否

## 検査済み・問題なし

- **§3 `output_hash + caption_revision`**: full hash DAGへの再膨張を試したが、approval identityをこの2値に限定しており、S-01とS-02の照合に直接使うため削除しない。
- **§4.1 `RIGHTS_AND_USAGE.md`**: attestation store、hash、job bindへの膨張を探したが、実体はtext 1枚と手書きnotesである。payload差が実際に観測済みなので、この粒度は追加product実装なしで保持できる。
- **§4.3 caption revisionとatomic current pointer**: 二重安全装置として攻撃したが、保存済み字幕の保持、dirty内容の保持、送付済み版からの修正開始を同時に満たす最小構成であり、S-04を弱めずには削れない。
- **§4.6 handler内のglobal lockとactual hash再照合**: 1人運用を理由に削減できるか試したが、二つのtabという明記済み操作列でstale approval競合が成立する。`current_render.json`だけを削り、このcritical sectionは残す。
- **§4.7 delivery ledger**: 汎用履歴DBとして攻撃したが、1 delivery 1行だけであり、「前に送った版を直して」へ直接対応する。自動移行やschema versionもないため適正である。
- **§5 P1の3境界fault test**: 全境界testへの膨張を探したが既に3境界へ縮退済みで、pointer replace失敗時のcaption/render保持を検証するS-04直結分なので残す。
- **§9 初期scope外**: 文書冗長として削れるか確認したが、DB、queue、client portal、style editorなどへの膨張を短い一覧で止めており、実装項目を増やさないため残す。

## 他エージェントと対立しうる立場

- reliability観点はfull-playback gateを内容事故防止として残す可能性がある。本レビューは、連続再生eventが注意深い確認を証明しない以上、S-02はidentityにbindした明示checkboxで満たす立場を取る。
- concurrency観点は`current_render.json`をcanonical stateとして残す可能性がある。本レビューは、canonical pointerではなくapproval/download時のactual hashとcurrent caption revisionの再照合を唯一の安全判定にする立場を取る。
- creative-quality観点は、今回の連続切り抜き品質では案件化できないという所感からP3を早期実行すべきと判断しうる。本レビューは、字幕修正milestoneを先に完了し、paid client要件または実納品の計測が出てから別設計にする立場を取る。
- validation観点はP2を初回release gateとして必要と判断しうる。本レビューは、P1の同一fixture R1→R2 smoke testと初回案件のCLI fallbackで十分と判断する。

## 集計

- must_fix: 0 件 / reject: 5 件 / 追加コスト合計: -4.25 人日 / 削減合計: 4.25 人日

## 削減サマリ

| 型 | 対象 | 削減人日 | 受け入れるリスク | 影響区分 |
|---|---|---:|---|---|
| A / F | §5 Phase P2 | 1.5 | 最初の実sourceでだけ見つかる接続不良は初回案件中に露見する。既存CLI＋file reviewへ戻し、その日の半日を復旧に使う。 | 半日 |
| D / F | §5 Phase P3、§6〜§8 | 1.0 | 現行の連続切り抜き品質が売り物にならない場合、creative spikeの開始が後ろ倒しになり、別途1日を取り直す。 | 半日 |
| A / E | §4.5 full-playback gate | 1.0 | 操作者が全編を見ずに「内容を確認した」を押し、見落とした内容を送ればclientへの謝罪になる。このhuman declaration riskを明示的に受け入れる。 | 謝罪 |
| E | §4.4 `current_render.json` | 0.5 | 同一caption revisionのrenderが複数あると表示対象の選択に迷うが、review identityとapproval対象はhashで一致し、選び直しは10分以内で済む。 | 10分 |
| A / D | §5 180秒hard gate | 0.25 | 初めて長尺依頼が来た時に処理時間超過または失敗が判明し、その案件だけ手動で断るかCLIへ縮退する。 | 10分 |

- 削減人日 合計: 4.25
- 削減後の Phase 0a + Phase 1 見積: 4.50〜7.50 人日
