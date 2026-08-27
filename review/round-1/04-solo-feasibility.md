# Agent 04 — Solo Feasibility — Round 1

## 総括（3行以内）

現行順では限定的な判断価値はW1後に残るが、主目的の「ASSを手編集せず字幕を直し、最新版を承認する」はW5まで現れず、そこまでの実質所要はW4なしでも11.75〜18.5人日、W4ありで13.75〜22.5人日である。
W2の安全kernelとW5のcaption-only部分を5〜8人日の最初のvertical sliceへまとめ、W1・W3・W4を後置しない限り、中断時にproduct価値が残らない。
全Phaseの実質見積はW4込み15.25〜25.5人日であり、現行の15人日上限には収まらないため、総合判定は「分割必須」とする。

## 完走判定

| Phase | 記載人日 | 実質人日 | 単独で価値があるか | 中断耐性 | 判定 |
|---|---:|---:|---|---|---|
| W0 | 0.25日 | 0.25〜0.5日 | いいえ。文書上の判断だけで実作業は変わらない | 高。文書だけなので再開位置は明瞭 | 独立Phaseを削除し、必要な記録だけ後続gateへ統合 |
| W1 | 0.5〜1日 | 1.5〜3日 | 限定的にはい。A/B結果は残るが、字幕修正・承認は改善しない | 低。第2sourceの準備状態とsource別checkpointがない | core完成後へ後置し、入力ready時だけ開始 |
| W2 | 2〜3日 | 4〜6日 | いいえ。UIなしでは安全機構を運用者が使えない | 低。6つの実装項目と3境界testに内部完了点がない | W5のcaption-only部分と一体化 |
| W3 | 1〜2日 | 2〜3日 | 条件付きではい。JSON候補を既存CLIへ渡せる場合は長時間視聴を減らせる | 中。JSONは残るが、3jobの進捗台帳がない | core完成後の独立改善として実施 |
| W4 | 1〜2日 | 2〜4日 | いいえ。W5前には操作入口と承認経路が記載されていない | 低。revision方式選択とrenderer統合が同じ箱に入る | W1採用かつ予算残ありの場合だけ後置 |
| W5 | 2〜3日 | 4〜6日 | はい。ここで初めて主目的を端から端まで達成する | 低。caption、candidate、cut、QC、approvalが一括で、途中成果の完了条件がない | caption-only coreとcandidate/multi-cut拡張へ分割 |
| W6 | 0.5〜1日 | 0.5〜1日 | はい。固定presetにより毎回のstyle指定が減る | 高。file 1個で完了点が明瞭 | 初回pilot後へbacklog化可能 |
| W7 | 1日 | 1〜2日 | はい。実運用可能性と計測値が残る | 中。1回完走は残るが、承認後の修正再開を検証しない | 2-pass pilotへ変更 |

- 最初の体感価値までの人日: 1.75〜3.5人日（W1の判断価値）。主目的の操作価値まではW4なし11.75〜18.5人日、W4あり13.75〜22.5人日
- 最長の無価値区間: Phase W2 の4〜6人日
- 総合判定: 分割必須
- 実質人日の合計: W4込み15.25〜25.5人日、W4なし13.25〜21.5人日

実質見積には、各Phaseに明記された実装、自己レビュー、Windowsローカルでのbuild・install/sync・再起動往復、fixture/source準備、記載されたtestと手動確認を含めた。無人のtranscription/render待ちは含めていない。特にW1は第2source準備とA/B生成、W2はrevision/pointer/lockと3境界fault test、W5は再生・保存・render・状態分離・full review・approvalの結線が記載見積からはみ出す。

## 各Phaseの単独価値

- **W0**: 測定語彙は整理されるが、停止した時点ではASS手編集も承認方法も従来のままである。独立Phaseではなく、W1/W7の結果欄へ統合すべきである。
- **W1**: 2素材のA/Bとmulti-cut採否という意思決定資産は残る。ただし第2sourceがreadyである場合に限られ、主目的の字幕修正には届かない。
- **W2**: S-01/S-02/S-04の土台として必要だが、UIまたは明記されたCLI操作がないため、このPhaseだけでは作業を楽にできない。
- **W3**: timestamp候補JSONを既存CLIへ直接渡せるなら、長時間sourceを探す作業を減らす単独価値がある。渡せない場合は単なる中間artifactなので、開始条件にCLI受け渡し確認を置く。
- **W4**: renderer内部には価値があるが、W5前に人がrecipeを確認・実行・承認する経路がない。停止するとscratch運用との差を回収できない。
- **W5**: current video、plain caption edit、明示render、technical/content分離、full playback、current-only approvalが揃い、初めて主目的を満たす。candidate採否とcut join previewはこのcoreの後へ分けられる。
- **W6**: core完成後なら固定preset自体が単独価値を持つが、初回pilotより前の必須作業ではない。
- **W7**: 完走記録とactive timeは残るため単独価値がある。ただし「前に送ったやつを直して」を含まない1-passでは、日常運用の再開性を証明しない。

## findings

### [F-04-01] 主目的の最初のvertical sliceがW5まで遅れ、W2〜W4で中断するとproduct価値が残らない

- **対象**: §9 / 「Phase W2 — Phase 0a 最小安全kernel」「Phase W5 — 最小review UI」
- **主張**: W2は安全上必要だがUIがなく、W3とW4は主目的に対して二次的である。記載順を守ると、字幕を手編集せず最新版を承認できる最初の成果が、W4なしでも実質11.75〜18.5人日後になる。
- **再現条件**: 1人の開発者がW0を閉じる → W1を実行する → W2のkernelを作る → W3を作る → W4採用時はW4も作る → W5開始前に別案件で中断する → 現場ではplain caption editとcurrent-only approvalを使えずASS手編集へ戻る。
- **反証条件**: W2完了時点で、既存jobの動画を開き、字幕を保存し、明示renderし、旧renderを拒否してcurrent renderだけを承認できる操作列が既に通る場合。
- **影響区分**: 半日
- **severity**: must_fix
- **最小修正案**: W2とW5のうち `current video再生 / plain caption text edit / explicit render / technical・content別表示 / full review / current-only approval` だけを5〜8人日の最初のvertical sliceへ統合する。candidate採否、cut join preview、W1、W3、W4はその完走後へ移し、S-01/S-02/S-04はslice内で全て通す。
- **検証方法**: `core_caption_vertical_slice` — legacy jobで1語をASS非編集で直す → render → QC表示とcontent表示を別々に確認 → 旧renderの承認を拒否 → current renderを全編再生して承認 → app再起動後も成果物と字幕を確認する。
- **追加コスト**: 0 人日
- **交換に削除する項目**: なし

### [F-04-02] 15人日停止規則が、すでに実装済みのW4を削減候補にしており、超過時に時間を回収できない

- **対象**: §10 / 「15人日を超える見込みになったら、最初にW6、次にW5のcut preview UI、次にW4のproduct統合を落とし」
- **主張**: Phase順ではW4がW5・W6より先なので、W5中に超過が判明してW4を落としても、W4へ費やした2〜4人日は戻らない。現行タスクを自己検証込みで積むと、W4込みの下限だけで15.25人日となり、停止規則は開始前から成立していない。
- **再現条件**: 開発者がW0からW4まで順に実行する → 実績が0.5 + 3 + 6 + 3 + 4 = 16.5人日になる → §10の削減順を適用する → 未着手のW6を落とした後、実装済みW4もscope外にする → W4の統合を外す整理と再確認にさらに半日を使う。
- **反証条件**: W4着手前に全残作業の再見積を行い、15人日内に収まらなければW4を開始しないgateがPhase定義にある場合。
- **影響区分**: 半日
- **severity**: must_fix
- **最小修正案**: 各Phase終了時に `actual burn + 残Phaseの上側見積` を更新し、W4はcaption-only coreの後へ移す。W4開始条件を「W1採用済み、かつW4とpilotの上側見積を足して15人日以内」とし、完了済みPhaseを削減額へ数えない。
- **検証方法**: `budget_gate_sunk_cost_simulation` — 表の実質上限を順に入力し、15人日を越える前にW4/W6が未着手のまま停止されること、完了済み工数が削減として表示されないことを確認する。
- **追加コスト**: 0 人日
- **交換に削除する項目**: なし

### [F-04-03] W1は存在が確認されていない第2sourceを必須入力にし、core実装より前の停止点になっている

- **対象**: §9 / 「current slow-talk候補と、別の許可済み高密度source 1本を使う。」
- **主張**: §1で観測済みなのは今回のsourceだけであり、第2の許可済み高密度sourceがreadyとは記録されていない。W1を直列gateにすると、素材探索・権利確認だけで止まり、字幕修正の成果へ進めない。
- **再現条件**: W0を承認する → W1開始時に高密度sourceのpathとpayload許可を探す → 利用可能な第2sourceが見つからない → §11の「権利entryまたは対象payload許可が不足」に従い停止する → W2へ進まず、半日使っても操作可能な成果が残らない。
- **反証条件**: W1開始前に、第2sourceのpath、edit permission、利用payload、timestamp transcriptが全てreadyとして記録済みの場合。
- **影響区分**: 半日
- **severity**: must_fix
- **最小修正案**: W1をcaption-only coreの非blockingな後続Phaseへ移す。開始前に4項目のready確認だけを行い、1項目でも欠けたら `not_ready` を記録してW1をskipし、coreへ進める。
- **検証方法**: `w1_missing_second_source_does_not_block_core` — 第2sourceなしで手順を開始し、W1が `not_ready` で閉じ、core caption sliceの作業へ進めることを確認する。
- **追加コスト**: 0 人日
- **交換に削除する項目**: なし

### [F-04-04] 複数source・複数jobを同名scratch artifactで扱うため、上書きと中断後の再開不能が起きる

- **対象**: §6 / 「source-assessment.json」「candidates.json」「edit-recipe.json」「spike-result.md」
- **主張**: W1は2source、W3は3jobを扱うのに、artifact名はsource/jobでnamespaceされておらず、進捗台帳もない。2本目を同じscratchへ出すと1本目の比較根拠を失い、1〜2週間後にどこまで済んだか判別できない。
- **再現条件**: source Aをscratch rootへ実行して6 artifactを作る → source Bを同じrootへ実行する → 同名JSON・MP4・Markdownを上書きする → Bの途中で中断する → 2週間後に戻る → Aの採否とBの未完了工程を判別できずAから再実行する。
- **反証条件**: 実装契約が `run_id/source_id` ごとの上書き禁止directoryと、各sourceの最終完了stepを示す永続statusを既に必須としている場合。
- **影響区分**: 半日
- **severity**: must_fix
- **最小修正案**: artifact追加ではなく配置を `scratch/<run_id>/<source_id>/` へ変更し、各directoryの `spike-result.md` 先頭に `last_completed / next_step / command / input_hash` の4行を置く。同名root出力を禁止する。
- **検証方法**: `multi_source_resume_without_overwrite` — A完了後にBを開始し、Bのpreview生成前で停止 → 2週間後を模して再起動 → Aの全artifactが不変で、Bのnext stepだけを再開できることを確認する。
- **追加コスト**: 0 人日
- **交換に削除する項目**: なし

### [F-04-05] W7が初回完走だけで終わり、承認後の「前に送ったやつを直して」を完走条件にしていない

- **対象**: §9 / 「authorized source 1本でrightsからfinal reviewまで完走する。」
- **主張**: 1-pass pilotでは新規jobのhappy pathしか残らず、承認済みjobを再度編集する日常的な再開経路を証明できない。後日の修正依頼でjob複製やartifact探索が必要になると、1人で半日を失う。
- **再現条件**: pilotでcaption revision 1とrender R1を承認する → 翌日「前に送った動画の固有名詞を直して」と依頼された体で同じjobを開く → revision 2を保存してR2をrenderする → 設計された手順に再open・再承認・旧版扱いの完了条件がないため、手作業でjobまたはartifactを複製して対応を組み立てる。
- **反証条件**: W7の完了条件に、承認済みjobを再openして新revisionを作り、R1を保持したままR2だけをcurrentとして再承認する操作列が含まれている場合。
- **影響区分**: 半日
- **severity**: must_fix
- **最小修正案**: W7を2-passにし、1回目の承認直後に同じjobへ字幕修正を1件入れ、再起動を挟んでR2を作る。R1は回復用に保持するがcurrent納品用には出さず、R2だけを再承認する。追加時間と交換にW6を初期scopeから削除し、presetはpilot後のbacklogへ移す。
- **検証方法**: `pilot_reopen_after_approval` — R1承認 → app再起動 → revision 2保存 → R2 render → R1のcurrent approval/download拒否 → R2全編再生・承認 → 両revisionと最後の正常成果物の保持を確認する。
- **追加コスト**: 0.5 人日
- **交換に削除する項目**: §9 Phase W6 — style preset 1個 / 0.5人日（記載下限）

### [F-04-06] W0は単独価値のない承認停止Phaseなので削除すべきである

- **対象**: §9 / 「文書改訂をユーザー承認して停止する。」
- **主張**: W0だけ終えても字幕修正、候補選定、承認のどれも楽にならず、独立した停止点が中断機会を1つ増やす。必要な測定項目は実験・pilotの結果欄へ直接置けば足りる。
- **再現条件**: 開発者が測定protocolだけを改訂する → 承認待ちで停止する → 別案件が入り2週間空く → 再開時に実行artifactが一つもないまま設計書と承認内容を読み直す → 従来どおりASSを手編集する。
- **反証条件**: W0単独完了後に、現在の字幕修正または承認作業の操作数が減る場合。
- **影響区分**: 10分
- **severity**: reject
- **最小修正案**: Phase W0を削除し、「旧式を定性成功として閉じる」は§1末尾へ、「新しい5計測値」はW1とW7のresult templateへ移す。0.25日枠はF-04-07のpreflightへ転用する。
- **検証方法**: Phase一覧からW0を除いた後も、W1/W7の出力だけで旧式の終了理由と5つのactive timeを記録できることを文書walkthroughで確認する。
- **追加コスト**: -0.25 人日
- **交換に削除する項目**: §9 Phase W0 — 計測protocol改訂 / 自身の削除

### [F-04-07] Windows上のvideo再生とUI→backend往復の成立を先に測るまで、W5見積は確定できない

- **対象**: §9 / 「Phase W5 — 最小review UI」「current video再生」
- **主張**: W5で初めてvideo再生、字幕保存、render起動を同じUIへ結線するが、そのlocal file/Blob経路とbackend API到達性の実測がPhase前半にない。W2〜W4より前に短いpreflightを通し、失敗時の手戻り幅を測る必要がある。
- **再現条件**: WindowsローカルでW2〜W4を完了する → W5でcurrent MP4 pathをUIへ渡す → local resource拒否またはbackend endpoint不達を観測する → 動画transportとsave/render呼出しを変更する → W2のstate結線とW5 UIを半日以上つなぎ直す。
- **反証条件**: 対象PCの実アプリで、180秒MP4の先頭frame表示、字幕scratch保存、既存render起動、app再起動後の再接続がすでに一続きで成功している場合。
- **影響区分**: 半日
- **severity**: defer
- **最小修正案**: 削除するW0の0.25日枠を、product codeを変えないpreflightへ置換する。`first_frame_seconds`、字幕save応答、render起動応答、再起動後の再接続を測り、4つ全て成功した場合だけcore sliceの見積を固定する。
- **検証方法**: `windows_review_roundtrip_preflight` — 180秒fixtureを開く → first frameまでを計測 → scratch字幕を1回保存 → 既存CLI/render入口を1回起動 → app再起動後に同じjobを再表示し、結果を1枚のlogへ残す。
- **追加コスト**: 0.25 人日
- **交換に削除する項目**: §9 Phase W0 — 計測protocol改訂 / 0.25人日

## 検査済み・問題なし

- **§1.2 / §1.3**: 「約2時間」を正式baselineとして固定する攻撃を試したが、自己申告と仮説を観測事実から分離し、2素材以上のA/Bまでproduct要件にしないため破れなかった。
- **§3.2**: multi-cutを先にapproval/downloadへ混入させる経路を探したが、Creative Spikeをscratch限定にし、revision方式を一つ選ぶまでproduct化しないため、S-01/S-04を維持している。
- **§4.6 / §7.2**: technical QCだけで承認へ進む操作を試したが、technicalとcontentを別状態にし、full playbackとcurrent input一致を要求しているため、S-01/S-02を破れなかった。
- **§7.1**: AIが候補数を埋めるため不適切な区間を出す圧力を検査したが、0候補とsource rejectを成功結果として認めるため、不要な制作を止められる。
- **§9末尾 / §11**: 一つの承認を後続Phaseの包括承認に読み替える経路を検査したが、各Phaseで停止し、後続承認と解釈しないと明記されているため破れなかった。
- **§12**: 1人実装を膨張させるgeneric timeline、DB、queue、client portal、style editorを復活させる必要性を検査したが、現在の1台・1〜2社条件では除外が妥当である。

## 他エージェントと対立しうる立場

- 安全性の観点からは「W2を純粋なkernelとしてUIより先に完成させるべき」という逆結論がありうる。本reviewは安全項目を減らさずcaption-only UIと同じvertical sliceへ入れるため、独立kernelの完了より中断時の操作価値を優先する。
- 候補品質の観点からは「W1でmulti-cut仮説を先に決めないとproduct方針が定まらない」という逆結論がありうる。本reviewは、主目的がcaption修正と最新版承認に固定されているため、W1をcoreのblocking gateにしない。
- 表現品質の観点からはW6の固定presetをpilot前に残す結論がありうる。本reviewはW7の承認後修正pilotと交換し、presetはcoreの実運用が一度成立した後に昇格させる。
- platform実装の観点から、対象PCですでにvideo playbackとUI→backend往復が証明済みならF-04-07は不要になる。その証拠が出た場合はpreflightを再実行せず、既存結果をW5の開始条件へ貼ればよい。

## 集計

- must_fix: 5 件 / reject: 1 件 / 追加コスト合計: 0.75 人日 / 削減合計: 0.75 人日
- should_fix: 0 件 / defer: 1 件 / backlog: 0 件 / 差引追加: 0 人日
