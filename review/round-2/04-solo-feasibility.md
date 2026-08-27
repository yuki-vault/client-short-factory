# Agent 04 — Solo Feasibility — Round 2

## 総括（3行以内）

現状はP1完了まで8.5〜12.5人日の体感価値ゼロ区間が残り、1人開発の中断リスクを吸収できない。
P0の失敗分岐、送付直後の台帳窓、失敗保存後の再起動復帰も、Windows 1台運用ではその場の判断に依存する。
P1を累積価値のある3片へ分け、初期の再生監視を削り、検証を工程内へ戻せば追加0.6人日・削減2.0人日で完走圏へ入る。

## 完走判定

| Phase | 記載人日 | 実質人日 | 単独で価値があるか | 中断耐性 | 判定 |
|---|---:|---:|---|---|---|
| P0 | 0.25 | 0.5（現状記述のままでは失敗時上限なし） | いいえ。診断結果だけで作業自体はまだ楽にならない | 低。失敗時の縮退仕様と記録先がない | 失敗分岐と時間上限の固定が必要 |
| P1 | 6.0〜9.0 | 8.0〜12.0（P0実測前の暫定） | 完了時だけある。途中のitems 1〜3ではASS手編集が残る | 低。7項目に完了証跡と再開点がない | 3つの累積vertical sliceへ分割必須 |
| P2 | 1.5〜2.5 | 0.5〜1.0（P1完了条件が真なら） | ある。実jobで修正版復帰まで確認できる | 中。操作列はあるが独立予算が重複 | P1の最終pilotへ統合して縮退 |
| P3 | 1.0〜2.0 | 1.0〜2.5（許可済みholdout支給後） | ある。offline成果物と不採用判断が残る | 中〜高。run別保存と停止条件がある | 条件成立時だけ実行可能 |

- 最初の体感価値までの人日: 8.5〜12.5人日（現行P0＋P1を順に完了する場合）
- 最長の無価値区間: Phase P1の8.0〜12.0人日
- 総合判定: 分割必須

実質人日のP1幅は、7実装単位、3 fault境界、Windows plugin往復、fixture準備を含む暫定値であり、F-04-08の計測後に固定する。

## findings

### [F-04-01] P1は完了まで利用可能な字幕修正経路を出さないため、途中停止すると成果が残らない

- **対象**: §5 / 「Phase P1 — Safe caption vertical slice（6.0〜9.0日）」
- **主張**: 内部順1〜3を終えてもplain caption edit UIは4番目で、承認可能な完成経路は7番目まで閉じたままである。したがって中断時にはASS直接編集を続けるしかなく、数日分の実装が利用価値へ変換されない。
- **再現条件**: 1人の開発者がP1の1「caption revision」、2「revision固定render」、3「OS lock」を順に実装する → 別案件で2週間中断する → 現場で字幕修正が必要になる → plain captionの入口も検証済みapproval経路もないため従来のASS編集へ戻る → 復帰時に部分実装の整合性確認と再試験へ半日以上を使う。
- **反証条件**: P1途中に、ASSを触らず保存・renderできる公開済みのCLI＋file経路と、その時点で露出する操作に対するS-01 / S-02 / S-04試験が存在する場合。
- **影響区分**: 半日
- **severity**: must_fix
- **最小修正案**: P1を累積する3停止点へ置換する。P1aはplain caption fileのrevision保存とpreview renderまでを公開し、approval/downloadはまだ露出しない。P1bは明示content review、hash＋revision再照合、lock、approval/downloadと復旧試験を足してCLI＋fileだけで最初のmilestoneを完結させる。P1cは同じbackendへHermes editorを被せ、二tab試験を行う。各片の終了時に停止でき、P1aだけでもASS手編集が消え、P1bまでで3安全条件を満たす。
- **検証方法**: `P1a-stop-resume`で1語修正、preview render、app再起動、旧正常render保持を確認する。`P1b-safe-approval`でstale request拒否とQC成功だけではapproval不可を確認する。`P1c-two-tabs`で古いtabからのapproval/downloadを拒否する。
- **追加コスト**: 0.0 人日
- **交換に削除する項目**: なし

### [F-04-02] P0は失敗時の時間上限と縮退先の完成形がなく、0.25日で止まれない

- **対象**: §4.2 / 「4項目のどれかが成立しなければUI実装を始めず、既存CLI＋file reviewへ縮退する」
- **主張**: 成功時の4確認は書かれているが、どの失敗を何分で打ち切り、CLI＋file reviewのどの操作へ移るかがない。§10も「縮退先を決められない」時に停止するとしか定めず、ソロ開発者がP0内で設計判断と調査を始める構造になっている。
- **再現条件**: 開発者がP0の1でHermes playerを開く → seek後に末尾復帰が壊れる → plugin再install、sync、再起動を繰り返す → 直らないのでCLI＋file reviewを選ぼうとする → caption保存、content review、approval/downloadのどこまでをCLIにするか本文から決められず、半日を超えて分岐設計を続ける。
- **反証条件**: 各checkに打切り時刻、失敗分類、移行先、最初の実行コマンド、残す証跡を対応付けた実機確認済みdecision tableがある場合。
- **影響区分**: 半日
- **severity**: must_fix
- **最小修正案**: P0を0.5日へ固定し、4 checkそれぞれに30分の調査上限を置き、残りで結果を`Hermes UI`、`OS player＋CLI/file`、`既存render入口の修復待ち`の3分岐へ分類する。P0では修復実装をしない。player/seek/reconnect失敗はfile経路、既存render入口失敗はblocker、と機械的に決める。
- **検証方法**: `P0-failure-routing`として4 checkを1つずつ意図的に失敗扱いにし、開始から0.5日以内に分岐名、次の一手、保存した観測ログが一意に決まることを確認する。
- **追加コスト**: 0.25 人日
- **交換に削除する項目**: §4.5「full playback completeの自動判定」 / 1.0人日削減

### [F-04-03] delivery ledgerを送付後だけ記録すると、送付と追記の間の中断で修正元を特定できない

- **対象**: §4.7 / 「実送付した後だけ、text ledgerへ次の1行を追記する」
- **主張**: 外部送付とローカル追記は一つのatomic操作にできないため、必ず記録のない時間窓ができる。その窓で中断し、その後currentが進むと、「前に送った版」の起点を誤る。
- **再現条件**: R1をapproveしてdownloadする → R1をclientへ送る → ledger追記前にWindows更新またはapp終了が起きる → 後日R2をcurrentにする → clientが「前に送ったR1を直して」と依頼する → ledgerにR1がないためcurrentのR2をcopyして修正・再送し、送付版と異なる内容になる。
- **反証条件**: 送付に使ったファイル名または送付channelの記録から、client・output hash・caption revisionを必ず一意に復元できる場合。
- **影響区分**: 謝罪
- **severity**: must_fix
- **最小修正案**: 現行の送付後1行を置換し、downloadを露出する直前に`prepared | client | output_hash | caption_revision | unique_filename`をledgerへatomic追記する。送付後は同じidentityへ`delivered_at`行を追記する。未送付のprepared行は残してよく、clientから依頼が来た時は送信済みファイル名との照合だけを手作業にする。
- **検証方法**: `delivery-crash-window`でprepared追記後・送付後・delivered追記前に強制終了し、再起動後に送信済みファイル名からR1を一意に選び、新working revisionを作れることを確認する。
- **追加コスト**: 0.0 人日
- **交換に削除する項目**: なし

### [F-04-04] Phase内の完了証跡が最終条件にしかなく、1〜2週間後の再開点を判定できない

- **対象**: §5 / 「各Phaseは明示承認後だけ開始し、終了時に停止する」
- **主張**: Phase間の停止は定義されているが、最長12人日になり得るP1内部7項目にはdone証跡、最後に成功したtest、次の一手、既知のrollback点がない。中断後はコードと生成物から進捗を再推定する必要がある。
- **再現条件**: P1のitems 1〜3と一部fault testを実行する → 14日中断する → 同じ開発者が復帰する → どのpointer置換試験とlock試験を終えたか文書から判定できない → current pointer、render metadata、test出力を再調査し、items 1〜3を再試験して半日を使う。
- **反証条件**: P1の各内部itemに、完了証跡path、最後の成功test、次の一手、最後の正常artifactを記した単一の再開記録が残る場合。
- **影響区分**: 半日
- **severity**: must_fix
- **最小修正案**: 各Phase開始時に1枚だけ`phase-progress.md`を作り、`current item / done evidence / last green test / next action / last known-good caption and render`の5欄を更新する。新しい管理systemは作らず、Phase終了時の報告書を実行中も使う。
- **検証方法**: `P1-resume-drill`でitem 3直後に作業を閉じ、別日にコードを先に読まずprogress fileだけを開き、15分以内に次のtestを再開できることを確認する。
- **追加コスト**: 0.1 人日
- **交換に削除する項目**: §5「Phase P2を独立1.5〜2.5日で持つ」 / 最低1.0人日削減

### [F-04-05] 初期版の自動full-playback監視はS-02を越えた実装であり削除すべき

- **対象**: §4.5 / 「seekと速度変更を無効化する」「tab非表示、source変更、再renderで試行を無効化する」
- **主張**: S-02が要求するのはtechnical QC成功を内容確認済みと表示しないことであり、visibility、seek、速度、連続再生のstate machineまでは要求しない。この監視はbrowser/player固有eventと再起動復元の実装・試験を増やし、最初の価値を遅らせる。
- **再現条件**: 開発者がended、seeking、ratechange、visibilitychange、source change、再renderの各eventを実装する → Hermes install/sync/restartを挟んで各組合せを試験する → background化やplayer差の修正を行う → 明示content review actionだけなら不要な実装と再試験に半日以上を使う。
- **反証条件**: 初期clientが、内容確認者の連続等速再生を機械的に強制しなければ受領しないという明示要件を提示した場合。
- **影響区分**: 半日
- **severity**: reject
- **最小修正案**: coverageと再生監視の記述、およびP1 item 6の自動gateを削除する。代わりにQCとは別の明示`content reviewed`操作を`output_hash + caption_revision`へ結び、identity変更時だけ無効化する。「全編再生を自動確認した」とは表示しない。
- **検証方法**: `content-review-separation`でQC成功直後のapprovalを拒否し、明示content review後だけ許可し、captionまたはMP4変更後に再び拒否する。seek、速度、tab状態は判定入力にしない。
- **追加コスト**: -1.0 人日
- **交換に削除する項目**: §4.5 full-playback state machine＋§5 P1 item 6 / 1.0人日削減

### [F-04-06] P2の独立1.5〜2.5日枠はP1の未完了修正予算を二重計上しているため削除すべき

- **対象**: §5 / 「Phase P2（1.5〜2.5日）の二周internal pilot」
- **主張**: P2の再起動、revision保持、current限定、再reviewはP1完了条件と重なる。最大180秒の1 jobで新たに行う価値はdelivery ledger起点のR1→R2実地確認であり、これに1.5〜2.5日を置くと、見つかった不具合をP1ではなくpilot予算へ隠せる。
- **再現条件**: P1完了条件をすべて終了する → P2でrights記録、R1 render、再起動、固有名詞1件変更、R2 render、reviewを行う → 不具合がなければ0.5〜1.0日で操作が終わる → 残り日数を統合不具合修正に使うとP1完了判定と工数実績が混ざり、15日停止判定が1〜2日早まる。
- **反証条件**: P2にP1と重ならないclient delivery operationと、その操作だけで1.5日以上必要な内訳が追加された場合。
- **影響区分**: 半日
- **severity**: reject
- **最小修正案**: 独立Phase P2と1.5〜2.5日の枠を削除し、delivery ledgerからR1を選んでR2を作る実job pilotだけをP1最終release checkとして0.5日で行う。欠陥が出たらP1を再openし、pilot時間へ混ぜない。
- **検証方法**: `real-job-two-revision-release`を0.5 active dayでtimeboxし、R1保持、ledger起点、R2だけcurrent、再起動後の再承認を確認する。未達時はP1の該当itemとburnへ戻す。
- **追加コスト**: -1.0 人日
- **交換に削除する項目**: §5 Phase P2の独立枠 / 最低1.0人日削減

### [F-04-07] pointer置換失敗後に再起動すると、publish済みだがcurrentでないcaptionへ戻る手順がない

- **対象**: §4.3 / 「replace失敗時は旧currentとeditorのdirty内容を保持」
- **主張**: 同じ手順ではrevision本体を先にpublishするため内容はdisk上に残るが、dirty保持は起動中editorにしか約束されていない。Windowsでfile handleを解放するためHermesを再起動すると旧currentが開き、orphan revisionを選び直す入口がない。
- **再現条件**: 3分jobのcaptionを複数箇所直す → saveでrevision本体publish後にantivirusまたは別processのhandleで`current.json` replaceを失敗させる → handle解放のためHermesを再起動する → editorが旧currentを読む → publish済みrevisionをcurrentへ再指定できず同じ修正をやり直す。
- **反証条件**: 再起動時に未参照revisionを列挙して復旧候補として表示するか、失敗画面がrevision IDを永続保存し再point操作を提供する場合。
- **影響区分**: 10分
- **severity**: should_fix
- **最小修正案**: autosave機構は追加せず、replace失敗時に既にpublish済みのrevision IDを小さなrecovery pointerへ残し、次回起動時に「旧current維持」または「このrevisionをcurrentへ再試行」の二択だけを出す。
- **検証方法**: `caption-pointer-failure-restart`でreplaceを失敗させ、その場でappを閉じ、再起動後に公開済みrevisionを再指定できること、選択前は旧captionと旧renderがcurrentのままであることを確認する。
- **追加コスト**: 0.25 人日
- **交換に削除する項目**: §4.5 full-playback state machine / 1.0人日削減

### [F-04-08] P0が真偽だけを測るため、P1の6〜9日を再見積する材料が得られない

- **対象**: §11 / 「P1の6〜9日はRound 1の実質見積であり、P0結果で再見積する」
- **主張**: P0の出力はplayer、seek、save/render入口、再接続の成立可否だけで、build・install/sync・再起動の1往復時間、想定往復回数、fixture作成、3 fault境界の所要時間を採らない。したがってP0後も6〜9日の上下幅を計算で更新できない。
- **再現条件**: P0の4項目を成立・不成立だけで記録する → P1を6〜9日で承認する → backendまたはUI変更ごとにWindows build、install/sync、Hermes再起動、動作確認を繰り返す → 何往復分を見積へ含めたか比較できず、9日超過が実装遅延か当初漏れか判定できない。
- **反証条件**: P0報告にcold/warmのplugin往復時間と、P1各itemの実装・test・fixture・往復回数を掛けた上下見積式が残る場合。
- **影響区分**: 半日
- **severity**: defer
- **最小修正案**: F-04-02で0.5日にしたP0内で、既存packageのcold/warm各1回のbuild→install/sync→再起動→確認を計時する。P1承認前に7 itemsごとの本体、test、fixture、想定往復数を1行ずつ置き、計時値を掛けて実質人日を再計算する。計測完了までは6〜9日をcommitmentに使わない。
- **検証方法**: `P1-estimate-rebuild`としてP0観測値とWBSだけから第三者が同じlower/upperを再計算でき、3 fault境界と180秒fixture準備が独立行で含まれることを確認する。
- **追加コスト**: 0.0 人日
- **交換に削除する項目**: なし

## 検査済み・問題なし

- **§4.3 caption publish順序**: revision本体publish前、publish後かつpointer前、pointer後の3中断点を攻撃した。same-directory tempからのreplaceと旧current保持により、最後の正常captionを失う列は作れなかった。再起動時のorphan復帰だけはF-04-07へ分離した。
- **§4.4 render identity**: render開始後にcaptionを変更する列を攻撃した。開始時revision固定、完成時にidentityを付け替えない、current対象にしない、の3記述が揃いstale renderがcurrentへ昇格する列は作れなかった。
- **§4.6 approval/download再照合**: 二つのtabで古い表示からrequestする列を攻撃した。global OS lock内でcurrent caption、render、actual hash、QC、content reviewを再読込するため、表示状態だけで承認する経路はなかった。
- **§4.5 QCとcontentの分離**: QC終了直後に内容確認済みへ継承する列を攻撃した。stateを別表示しidentity単位で継承しないためS-02は保たれる。F-04-05の縮退後も明示content review actionは残す。
- **§4.7 修正版の起点**: ledgerに記録済みの過去版を直す列を攻撃した。該当caption revisionからnew working revisionへcopyし履歴を上書きしないため、記録後のrollback構造は保たれる。送付直後の未記録窓だけはF-04-03へ分離した。
- **§5 P3の非blocking化**: holdout欠如と15日超過の列を攻撃した。P3はP1/P2をblockせず、明示条件と停止条件があるため、creative探索が最初のproduct milestoneを飲み込む構造には戻っていない。
- **§9 初期scope外**: NLE、B-roll、tracking、DB、queue、portal、style editorを初期へ戻す依存を探した。§6〜§8にもproduct化のevidence gateがあり、初期実装へ暗黙復活する記述はなかった。

## 他エージェントと対立しうる立場

- F-04-05は、再生coverageを安全要件とみなすreviewerとは逆になる。本判定はS-02を「QC成功と内容確認済みを分離すること」までと読み、連続等速再生の機械強制は初期要件ではないという立場である。
- F-04-01の分割は、一括で安全機能を出したいreviewerから境界増加と見られ得る。P1aではapproval/downloadを露出せず、P1bで全identity再照合を揃えてから露出するため、不完全な安全経路を公開する提案ではない。
- F-04-06は、pilotを厚く取りたい検証観点とは対立し得る。実job二周の操作列は削らず、そこで見つかった修正をP1 burnへ正しく戻すための予算境界変更である。

## 集計

- must_fix: 4件 / reject: 2件 / should_fix: 1件 / defer: 1件 / backlog: 0件
- 追加コスト合計: 0.6人日 / 削減合計: 2.0人日 / 差引: 1.4人日削減
