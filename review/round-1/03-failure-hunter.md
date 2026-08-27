# Failure Hunter — Round 1

## 破壊試験

| # | 標的 | 操作列 | 結果 | 影響区分 |
|---|---|---|---|---|
| 1 | S-01 | 1. rev1でrender開始 2. ffmpeg実行中に字幕をrev2へ保存 3. 完了handlerが完了時点のcurrentを読み、rev1映像へrev2を記録 4. 一致gateを通して承認 | 破れた（F-03-001） | 謝罪 |
| 2 | S-01 | 1. Tab Aでrev1/render1を表示 2. Tab Bでrev2を保存 3. Tab Aを更新せず承認 4. 表示時に計算したgate値で承認を書込む | 破れた（F-03-002） | 謝罪 |
| 3 | S-01 | 1. Creative Spikeのpaced previewを作る 2. approvalまたは納品用downloadへ渡す | 破れなかった。§3.2と§9 W1が接続を明示的に禁止している | 謝罪 |
| 4 | S-02 | 1. render1を全編確認 2. 字幕をrev2へ修正 3. render2のtechnical QCを通す 4. job単位で残ったcontent/full-playback状態を使ってrender2を承認 | 破れた（F-03-003） | 謝罪 |
| 5 | S-02 | 1. current renderを開く 2. 終端直前へseek 3. 最後の1秒だけ再生して`ended`を発火 4. content確認を押して承認 | 破れた（F-03-004） | 謝罪 |
| 6 | S-02 | 1. technical QCだけ成功させる 2. content reviewを未実施のままdownloadする | 破れなかった。§7.2は両状態を別gateにし、欠落時のdownloadを禁止している | 謝罪 |
| 7 | S-01 / S-04 | 1. rev1のffmpegを開始 2. Hermesだけ終了して子processを残す 3. 再起動後にrev2/render2を完了 4. 遅れて終わる旧invocationを完了順でcurrentにする | 破れた。旧invocationのcommit権限を失効させる規定がない（F-03-001、F-03-002） | 謝罪 |
| 8 | S-04 | 1. jobsをD:または同期folderへ置く 2. C:の一時fileからpointerを置換、または同期clientがpointerをlock 3. 保存成功扱いでeditorを閉じる 4. 再度開く | 操作上失われた（F-03-006）。旧revisionと旧renderは残るため手復旧可能 | 10分 |
| 9 | S-04 | 1. 最後の正常MP4をplayerで開いたままにする 2. 新renderを失敗させる 3. current成果物を再度開く | 破れなかった。immutable renderを文字どおり別fileとして実装すれば旧MP4へ書込まない | 半日 |

## Windows固有確認

| 項目 | 確認操作 | 設計上の判定 |
|---|---|---|
| file lock | `current_caption` pointerを削除共有なしで開いた状態を作り、保存時の置換を実行する | Windowsのsharing violation時に「保存成功」にしない契約がないため未合格。F-03-006で初期対応を縮退する |
| `os.replace` | `%TEMP%`がC:、jobsがD:の状態で一時fileからpointerへ置換する | cross-volume置換を許す書き方で未合格。同じdirectoryに一時fileを作る制約が必要 |
| 残存子process | rev1のffmpeg中にHermesを終了し、再起動後のrev2完了より遅くrev1を完了させる | immutable file自体は守れるが、旧invocationのpointer commitを拒否できず未合格。F-03-001/002のcommit時照合で塞ぐ |
| OneDrive / Dropbox | jobsを同期対象に置き、同期中にcaption saveとpointer swapを行う | 初期版の対応範囲が未定義で未合格。同期folderを非対応として起動時に止めるのが最小 |

## 総括（3行以内）

S-01/S-02は状態名こそ分かれているが、どのrevision/hashへ結び付くかとcommit時点が未定義で、普通の二タブ操作だけで破れる。
S-04はimmutable成果物により旧file自体は守れる一方、Windowsの置換失敗を保存成功に見せない条件がない。
また、核心の字幕修正UIを別素材のCreative Spikeより後ろへ置く順序は、1人開発で途中停止すると成果ゼロになる。

## findings

### [F-03-001] renderの字幕版を開始時に固定しないと、古い映像をcurrent字幕のrenderとして偽装できる

- **対象**: §7.2 / `current caption revisionとrenderの一致`
- **主張**: 一致させる値をいつ取得するかが未定義である。完了handlerがその時点のcurrent revisionをmetadataへ書けば、rev1から作った映像へrev2の札が付き、S-01のgateが通る。
- **再現条件**: 1. 開発者がrender完了時にcurrent caption pointerを読んでmetadataを書く実装にする 2. 作業者がrev1でrenderを開始する 3. ffmpeg実行中に字幕をrev2へ保存する 4. render完了後に一致gateを通して承認する
- **反証条件**: render開始時にimmutableなcaption revision ID/pathを一度だけ捕捉し、出力metadataがその捕捉値からしか作られない場合。
- **影響区分**: 謝罪
- **severity**: must_fix
- **最小修正案**: W2へ「render commandは開始時の`caption_revision`を必須引数として固定し、完了時にcurrentを読まない」を1文追加する。暗黙current入力を禁止する。
- **検証方法**: `S01_render_input_snapshot_while_caption_changes` — rev1 render中にrev2を保存し、完成renderのmetadataがrev1のまま、承認不可であることを確認する。
- **追加コスト**: 0.25 人日
- **交換に削除する項目**: §9 Phase W5 / `candidate採否`

### [F-03-002] 承認の一致確認と書込みが一操作でなければ、二タブからstale renderを承認できる

- **対象**: §4.6 / `承認はcurrent inputと一致するrenderだけに行う。`
- **主張**: 「一致を見る」だけでは、表示から承認書込みまでの間にcurrentが変わる時差を塞げない。画面で計算済みの真偽値を信用する実装は本稿を満たして見えるが、S-01を破る。
- **再現条件**: 1. Tab Aでrev1/render1のgateを合格表示にする 2. Tab Bで字幕をrev2へ保存する 3. Tab Aをrefreshせず承認する 4. approval handlerがTab Aのrender IDと表示済みgateをそのまま記録する
- **反証条件**: approval/download handlerが既存global OS lock内でcurrent caption pointerと対象render metadataを再読込みし、一致確認とapproval書込みを同じcritical sectionで行う場合。
- **影響区分**: 謝罪
- **severity**: must_fix
- **最小修正案**: client側gateを根拠にせず、approvalと納品用downloadの各handlerで`output_hash + caption_revision`をlock内再照合する。旧renderは表示できても操作を拒否する。
- **検証方法**: `S01_two_tabs_approval_compare_and_commit` — Tab Bの保存後、Tab Aからのrev1承認と納品用downloadがともに409相当で拒否されることを確認する。
- **追加コスト**: 0.25 人日
- **交換に削除する項目**: §9 Phase W5 / `paced mode時だけcut joinの前後preview`

### [F-03-003] 内容確認と全編再生をoutput hashへ結び付けないと、新renderが未確認のまま合格表示になる

- **対象**: §7.2 / `human content review complete`
- **主張**: content reviewとfull playbackがjob単位booleanのままでも現記述を満たせる。字幕修正後の新renderへ旧renderの確認状態が持ち越され、technical QCしか見ていない新renderを内容確認済みとして承認できる。
- **再現条件**: 1. rev1/render1を全編再生してcontent reviewを完了する 2. 字幕をrev2へ保存してrender2を作る 3. render2のtechnical QCを成功させる 4. jobに残る旧content/full-playback値でrender2を承認する
- **反証条件**: 両状態が`output_hash + caption_revision`を対象として保存され、対象が1bitでも変わると未確認へ導出される場合。
- **影響区分**: 謝罪
- **severity**: must_fix
- **最小修正案**: 独立したreset処理を増やさず、review状態のkeyを`output_hash + caption_revision`にする。currentとのkey不一致は常にfalseとして表示する。
- **検証方法**: `S02_review_evidence_is_render_scoped` — render1確認後に字幕を1文字変えてrender2を作り、content/full-playbackが両方未完了へ戻ることを確認する。
- **追加コスト**: 0.25 人日
- **交換に削除する項目**: §9 Phase W6 / `style preset 1個`

### [F-03-004] `full playback complete`の成立条件がなく、終端へのseekだけで全編確認を偽装できる

- **対象**: §4.6 / `current renderを先頭から末尾まで一度だけ再生する。`
- **主張**: §7.2には状態名しかなく、seek、倍速、非表示tab、source差替え時の扱いがない。`ended` eventだけで完了にする最小実装では最後の1秒だけで内容確認済み表示になり、S-02を破る。
- **再現条件**: 1. 開発者がvideoの`ended` eventでfull playbackをtrueにする 2. 作業者がcurrent renderを開く 3. 終端直前へseekして最後の1秒を再生する 4. content確認を押して承認する
- **反証条件**: gate獲得用review modeが0秒からの連続再生だけを受け付け、seek・source変更・tab非表示でその試行を無効にする場合。
- **影響区分**: 謝罪
- **severity**: must_fix
- **最小修正案**: 初期版はcoverage unionを作らず、gate獲得中だけseekと再生速度変更を無効にし、0秒開始・表示tab・同一`output_hash`の`ended`だけを完了とする。
- **検証方法**: `S02_seek_hidden_tab_and_source_change_do_not_complete_review` — 終端seek、tab非表示、途中source差替えの3操作がすべて未完了のままで、通常の連続再生だけが完了することを確認する。
- **追加コスト**: 0.25 人日
- **交換に削除する項目**: §9 Phase W3 / `source-assessment.json`出力

### [F-03-005] 第二素材のCreative Spikeを核心機能より先に置く実行順は削除すべきである

- **対象**: §9 / `Phase W1 — Creative Spike B（0.5〜1日）`
- **主張**: W1で第二の許可済みsourceが取れないと§11で停止し、W2の安全kernelにもW5の字幕editorにも到達しない。主目的と無関係な入力不足で、半日以上使った後も「ASSを触らず字幕修正・最新版承認」がゼロのままになる。
- **再現条件**: 1. 1人の開発者がW0を完了する 2. W1用の別の高密度sourceを探す 3. payload許可を用意できず§11の停止条件を適用する 4. 後続W2〜W5を開始せず作業を閉じる
- **反証条件**: 既存54.5秒jobだけでW2と字幕編集・render・review・approvalの最小UIを先に完走でき、W1以降がその完了条件から外れている場合。
- **影響区分**: 半日
- **severity**: reject
- **最小修正案**: 現行の直列順からW0/W1/W3/W4/W6を削除してbacklogへ移し、W2とW5の`current video / plain caption edit / explicit render / technical-content別表示 / full review / approval`だけを最初の1 milestoneにする。
- **検証方法**: `core_path_without_second_source` — legacy job 1件だけを入力に、新規source探索なしで保存済み字幕revisionと最新版承認まで完走する。
- **追加コスト**: -2.25 人日
- **交換に削除する項目**: なし

### [F-03-006] Windowsの置換失敗を保存失敗として扱う規定がなく、保存したつもりの字幕を失う

- **対象**: §9 / `caption revision、immutable render、current pointer、global OS lock、3境界fault test、180秒制約。`
- **主張**: global OS lockはDefender・同期client・別volumeを跨ぐ`os.replace`を成功させない。保存成功の成立点とeditorのdirty保持がないため、置換前に成功表示する実装では新しい字幕がcurrentから消える。
- **再現条件**: 1. jobsをD:またはOneDrive配下に置く 2. 保存時の一時fileをC:へ作る、または同期clientにpointerをlockさせる 3. revision書込み時点でUIを保存済みにしてからpointer置換を実行する 4. 置換失敗後にeditorを閉じて開き直す
- **反証条件**: jobsがlocal non-sync filesystemに限定され、一時fileがtargetと同じdirectoryに作られ、pointer置換成功後だけsave成功を返し、失敗時はdirty内容と旧pointerを両方保持する場合。
- **影響区分**: 10分
- **severity**: should_fix
- **最小修正案**: 初期版は同期folderを非対応として起動時に拒否し、tempをtarget siblingに固定する。置換例外時はdirtyのままrender/approvalを無効にする。
- **検証方法**: `S04_windows_replace_failure_keeps_old_and_dirty` — sharing violationとcross-volume相当を各1回注入し、旧revision/renderが読め、未保存editor内容が残り、render/approvalが無効であることを確認する。
- **追加コスト**: 0 人日
- **交換に削除する項目**: なし

## 検査済み・問題なし

- **§3.2 multi-cut scratch隔離**: scratch previewからapproval/downloadへ進む攻撃を試した。接続禁止が二箇所に明記されており、product化前のS-01/S-04経路は開かなかった。
- **§7.2 technical/content分離**: technical QC成功だけで納品用downloadする攻撃を試した。別gateと全欠落時無効化が明記され、単純な状態混同では破れなかった。F-03-003は別renderへの持越しだけを指す。
- **§9 W2 immutable render**: 開いたままの旧MP4へ新renderを重ねる攻撃を試した。immutableを別名fileとして守れば、Windows playerのlockで新renderが失敗しても最後の正常MP4は残る。
- **§10 削除順**: 見積超過時にS-01/S-02/S-04を先に落とす経路を探した。W6、cut preview、W4の順で落とし、3条件を落とさないと明記されている。
- **§11 product code承認gate**: review文書の包括承認をproduct code変更承認へ読み替える経路を試した。Phaseごとに停止し、明示承認なしを停止条件にしているため破れなかった。

## 他エージェントと対立しうる立場

- 削減側はfull playback gate自体を落とす結論を出しうる。私はS-02を守る最小手段として残し、複雑なcoverage unionではなく制限付き連続再生へ縮退すべきと判断する。
- UX側はcandidate採否、cut join preview、style presetを先に残すと主張しうる。私はそれらをF-03-001〜004の交換削除へ使い、字幕修正と最新版承認を先に閉じる立場である。
- Windows運用側はOneDrive/Dropboxも支援対象に含めると主張しうる。私はクライアント1〜2社・ローカル1台の初期版では同期folderを明示的に拒否する方がS-04と工数の両方に合うと判断する。

## 集計

- must_fix: 4 件 / reject: 1 件 / 追加コスト合計: 1.0 人日 / 削減合計: 2.25 人日
