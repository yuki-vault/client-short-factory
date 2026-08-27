# Agent 03 — Failure Hunter — Round 2

## 総括（3行以内）

S-01は、approval/downloadだけがlockを取り、`current.json`と`current_render.json`の更新側が同じlockへ参加しないため破れる。
S-02は、mute/音量0がfull-playback無効化条件に含まれず、音声未確認でもcontent reviewを完了できるため破れる。
S-04は、Windowsのpointer置換失敗後にHermesを再起動すると、publish済みrevisionがcurrentから孤立する経路が残る。

## 破壊試験

| # | 標的 | 操作列 | 結果 | 影響区分 |
|---|---|---|---|---|
| 1 | S-01 | 1. Tab AでR1/C1のapprovalを開始 2. handlerがpointerを読みMP4 hash計算へ進む 3. Tab BでC2をsaveし`current.json`を置換 4. Tab Aがキャッシュ済みR1/C1でapprovalを書込む | 破れた | 謝罪 |
| 2 | S-01 | 1. R1/C1をfull review済みにする 2. Tab Aでapprovalを開始 3. 残存render子プロセスの完了側がR2/C1を`current_render.json`へpublish 4. Tab AがR1/C1を承認する | 破れた | 謝罪 |
| 3 | S-02 | 1. QC成功したR1を開く 2. playerをmuteまたは音量0にする 3. 表示tabで0秒から終端まで再生 4. full-playback/content review completeとしてapprovalする | 破れた | 謝罪 |
| 4 | S-04 | 1. `current.json`をWindowsのDELETE共有なしhandleで保持 2. captionをsave 3. revision publish後のpointer replaceをsharing violationで失敗させる 4. Hermesを再起動する | 破れた（publish済みrevisionがcurrentから孤立） | 10分 |
| 5 | S-04 | 1. 最後の正常MP4をWindows playerまたはExplorer previewで開いたままにする 2. 新renderを実行 3. 新しいimmutable directoryへpublishする | 破れなかった（旧MP4を上書きしない） | 10分 |
| 6 | S-04 | 1. jobsをD:、`%TEMP%`をC:に置く 2. caption saveを実行 3. same-directory tempから`current.json`をreplaceする | 破れなかった（caption pointerは同一volume） | 10分 |
| 7 | S-01 / S-04 | 1. ffmpeg実行中にrenderをcancel 2. 子プロセスを残存させる 3. 別renderを完了 4. 残存側を後から完了させる | S-04は破れなかったが、pointer publisherがlock外なのでS-01は試験2の経路で破れた | 謝罪 |
| 8 | S-04 | 1. OneDrive配下をjobs directoryに指定 2. preflightを通過 3. 同期中にcaption save 4. pointer replace失敗後に再起動 | 破れた（「非対応」の記述だけでは指定を拒否しない） | 10分 |

## findings

### [F-03-01] current pointerの更新側が同じOS lockへ参加せず、承認時snapshotを分裂させられる

- **対象**: §4.3・§4.4・§4.6 / 「approvalと納品用download handlerはglobal OS lock内でcurrent caption、current render、actual MP4 hash、QC、content reviewを再読込する」
- **主張**: lock対象として明記されているのはapproval/download handlerだけで、`current.json`と`current_render.json`のpublisherはlock外である。大きなMP4のhash計算中に別tabのcaption saveまたは遅延render完了がpointerを更新すると、handlerは旧pointer群だけで照合を終え、既にcurrentでないrenderを承認・納品用取得できる。
- **再現条件**: 1. R1/C1をreview済みにする 2. Tab Aでapprovalを開始し、R1のhash計算まで進める 3. 計算中にTab BでC2をsaveして`current.json`を置換する 4. Tab Aが先に読んだC1、R1、QC、content reviewで照合を終えてapprovalを書き込む
- **反証条件**: caption/renderのpointer publishもapproval/downloadと同じOS lockを取得し、pointerの読取りからapproval確定またはdownload開始までwriterが進めないなら、この操作列は成立しない。
- **影響区分**: 謝罪
- **severity**: must_fix
- **最小修正案**: 新しいlockを増やさず、既存のglobal OS lockの対象を`current.json`と`current_render.json`のpublishにも広げる。render処理全体ではなく、pointer commitの短い区間だけをlockする。
- **検証方法**: `test_pointer_publish_serializes_with_approval_and_delivery` — approvalをhash計算直前で停止し、別tabのcaption saveとrender pointer publishを投入して、両writerが待機すること、writer完了後の旧identity downloadが拒否されることを確認する。
- **追加コスト**: 0 人日
- **交換に削除する項目**: なし

### [F-03-02] mute再生がfull-playbackを満たし、音声未確認のcontent reviewを承認へ渡せる

- **対象**: §4.5 / 「tab非表示、source変更、再renderで試行を無効化する」
- **主張**: 無効化条件にplayerのmute、音量0、再生途中の音量変更がなく、content reviewをcompleteへ遷移させる別の明示確認も定義されていない。字幕と原音を照合していない連続再生がcontent reviewとして保存され、technical QC以外の実質的な内容確認なしでapproval条件を満たす。
- **再現条件**: 1. QC成功したR1を開く 2. 再生前にplayerをmuteまたは音量0にする 3. seekせず表示tabで0秒から終端まで再生する 4. full-playback completeをcontent review completeとして保存しapprovalする
- **反証条件**: mute・音量0・再生中の消音が試行を無効化し、full playback後の明示的な「内容確認済み」操作だけがR1のcontent reviewをcompleteにするなら、この主張は誤りである。
- **影響区分**: 謝罪
- **severity**: must_fix
- **最小修正案**: coverage計算は追加せず、gate中はplayer muteと音量変更を無効化し、開始時に音量0ならgateを開始しない。`ended`だけでcontent reviewへ昇格させず、同じ画面の明示確認を1回だけ要求する。
- **検証方法**: `test_muted_playback_never_completes_content_review` — `muted=true`、`volume=0`、途中muteの3ケースで終端まで進め、content reviewが未完了のままapproval/downloadが拒否されることを確認する。
- **追加コスト**: 0 人日
- **交換に削除する項目**: なし

### [F-03-03] pointer置換失敗後のdirty保持はHermes再起動をまたがず、publish済みcaptionが孤立する

- **対象**: §4.3 / 「replace失敗時は旧currentとeditorのdirty内容を保持し、保存済み表示、render、approvalへ進まない」
- **主張**: editor内のdirty保持だけではprocess再起動をまたげず、revision本体をpublishした後に`current.json`置換が失敗すると、そのrevisionへ戻る起動経路が定義されていない。Windows sharing violationへの自然な対処としてHermesを再起動すると旧currentだけが復元され、直前にpublishされたcaptionは通常workflowから見えなくなる。
- **再現条件**: 1. captionを修正する 2. Defender、同期client、または再現用のDELETE共有なしhandleで`current.json`を保持する 3. saveしてrevision本体のpublish後にpointer replaceを失敗させる 4. エラー後にHermesを再起動し、`current.json`からjobを再接続する
- **反証条件**: 失敗したsaveの本文がdurable draftとして再起動後に同じjobへ復元されるか、孤立revisionを起動時に回収する仕様があるなら、この主張は誤りである。
- **影響区分**: 10分
- **severity**: should_fix
- **最小修正案**: 自動昇格や履歴UIは作らず、pointer commit成功までeditor内容をjob単位のdurable draftへ保持し、次回起動時に一度だけ復元する。加えてOneDrive / Dropbox配下は「非対応」と表示するだけでなくpreflightでhard rejectする。
- **検証方法**: `test_caption_dirty_survives_pointer_replace_failure_and_restart` — `current.json`をDELETE共有なしでlockし、save失敗直後にappを再起動して修正文がeditorへ復元され、旧currentと最後の正常renderが不変であることを確認する。
- **追加コスト**: 0.25 人日
- **交換に削除する項目**: §4.1 Gate Rのpayload別provider・対象名notes記録を初期productから削除（0.25人日削減）

## 検査済み・問題なし

- **§4.4 / render中のcaption変更**: C1固定でrenderを開始してからC2をsaveする攻撃を試した。完成renderへC2 identityを付け替えず、approval/download側もcurrent captionを再読込するため、F-03-01の競合窓を閉じればR1/C1は拒否できる。
- **§4.4 / render失敗・cancel**: temp render directoryの途中MP4をcurrentにする攻撃を試した。MP4、QC、metadataを検証し、完成directory publish後だけpointerを替える順序なので、最後の正常renderは残る。
- **§4.3 / Windowsの同一volume条件**: `%TEMP%`がC:、jobsがD:の構成を試した。caption pointerはsame-directory tempを明記しており、`current.json`の`os.replace`がcross-volumeになる経路はない。
- **§4.4 / WindowsのMP4 file lock**: current MP4をplayerやExplorer previewで開いたまま新renderを作る攻撃を試した。render directoryがimmutableで別publishされるため、旧MP4を置換・削除せず、pointer失敗時も最後の正常renderを失わない。
- **§4.5 / seek・倍速・tab非表示**: keyboard seek、速度変更、tab非表示で再生時間を短縮する攻撃を試した。いずれも無効化または試行無効化が明記され、mute以外の列ではfull-playbackを偽装できない。
- **§4.6 / QCだけでのdownload**: technical QC success後、content reviewなしで納品用endpointを呼ぶ攻撃を試した。handlerがcontent reviewを再読込するため、QC表示と内容確認stateが混同されない実装なら拒否できる。
- **§4.7 / 過去納品の修正**: delivery後にcurrentを進めてから旧版修正を開始する攻撃を試した。ledgerの`output_hash + caption_revision`から新working revisionへcopyし、旧caption/render/deliveryを上書きしないため、履歴消失は起きない。
- **§5 P1 / legacy job**: 既存jobをfixtureとして書き換える攻撃を試した。legacy job read-onlyと明記され、新規disposable jobまたはsynthetic fixtureへ限定されているため破れない。

## 他エージェントと対立しうる立場

- **F-03-01**: atomic pointerとapproval側lockだけで十分とする削減側の立場と対立する。各fileのatomicityは複数pointerを同一時点のsnapshotにせず、writerも同じlockへ参加させる必要がある、という立場を取る。
- **F-03-02**: 字幕は画面だけでも確認でき、muteまで制約するのは過剰とするUX側の立場と対立する。今回のcontent reviewは原音に対する字幕修正の確認なので、無音の全編再生を完了扱いしない立場を取る。
- **F-03-03**: immutable revision本体がdiskに残る以上S-04は破れていないとする立場と対立しうる。物理fileを手探索すれば回収できるためmust_fixにはせず、通常workflowから消える10分事故としてshould_fixに留めた。
- §4.1のpayload別notesは権利事故防止側から維持要求が出うるが、S-03は降格済みであり、0.25人日をS-04の再起動回復へ交換する方を優先する。

## 集計

- must_fix: 2 件 / reject: 0 件 / 追加コスト合計: 0.25 人日 / 削減合計: 0.25 人日
