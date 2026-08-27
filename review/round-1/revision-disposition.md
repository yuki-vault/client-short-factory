# Round 1 revision disposition

## 採用

- 最初のproduct milestoneをcaption-only vertical sliceへ変更する。
- product code前にWindows上の動画再生・seek・保存・render起動・再接続をpreflightする。
- render開始時のcaption revision固定、approval/download時のlock内再照合、output単位のreviewを明記する。
- full playbackは初期版でcoverage unionを作らず、0秒開始・seek不可・表示tab・同一outputの連続再生へ縮退する。
- Windowsのtemp fileをtarget siblingへ固定し、置換失敗を保存成功にしない。
- deliveryの1行台帳と、承認後修正を含む2-pass pilotを追加する。
- W0、早期multi-cut、早期candidate UI、初期style presetを初期product scopeから外す。
- multi-source scratchを再開する場合は `run_id/source_id` でnamespaceする。
- 15人日予算は完了済み工数を削減額に数えず、未着手scopeだけを削る。

## 上位のユーザー指示・live evidenceに合わせて修正採用

- Phaseごとの承認は、元のimplementation promptが明示したgateなので削除しない。Phase数を圧縮して停止回数を減らす。
- rights記録はtext file 1枚を維持するが、今回 `transcript` と `public metadata` の許可が別々だったlive evidenceに合わせ、payload名はnotesへ残す。
- 180秒上限はYouTube Shorts対象と元promptの明示要件があるため維持し、根拠をDraft 1へ記載する。
- legacy jobをtest fixtureとして変更する案は採らない。legacyはread-onlyとし、synthetic fixtureまたは新規disposable jobを使う。
- source triage、multi-cut、styleはユーザーが明示した将来品質課題なので設計から消さず、初期product scope外の後続レーンとして残す。

## 未解決として継続

- Hermes実機player経路はpreflight未実施。
- paced editの価値はholdout未検証。
- editable cut recipeを一つのedit revisionへ束ねるか、新job固定にするか未決定。
- client style briefがないためstyle presetは未定義。
