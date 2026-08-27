# Client Short Factory

許可済みのYouTube動画またはローカル動画から、指定区間を字幕付き縦型MP4へ変換するローカルCLIと、`127.0.0.1`限定の候補探索・字幕確認・構成調整WebUIです。

最初のMVPは次の範囲に限定しています。

- 指定区間だけを取得・切り抜き
- `faster-whisper` による日本語文字起こし
- 1画面1〜2行、1行最大15文字を目安にした字幕整形
- SRT / ASS / 文字起こし原稿の出力
- 16:9全体を保持し、ぼかし背景付き1080×1920へ変換
- ASSフルテロップ焼き込み
- 音量正規化
- 工程別チェックポイントと再開
- ffprobe / デコード検査
- ドラッグ＆ドロップしたローカル動画から、ローカルAIで切り抜き候補を0〜5件提案
- 候補ごとの短いpreviewと、hook・着地・選定理由・確認riskの表示
- 保存済み候補履歴、元動画全体のseek、開始・終了の微調整、字幕編集jobへの移行

話者分離、話者別色、顔追跡、複数区間を組み直すpaced編集、無音部分の映像削除、自動投稿は対象外です。候補から作れるjobは、元動画内の1つの連続区間に限定します。

## 実行環境

このPCでは次の既存資産を自動検出します。

- yt-dlp（WinGet版）
- FFmpeg / ffprobe 8.1（libass / NVENC対応）
- Hermes側Python環境の `faster-whisper`
- キャッシュ済み `faster-whisper-small`

パスが異なる場合は環境変数で上書きできます。

```powershell
$env:SHORT_FACTORY_YTDLP = 'C:\path\to\yt-dlp.exe'
$env:SHORT_FACTORY_FFMPEG = 'C:\path\to\ffmpeg.exe'
$env:SHORT_FACTORY_FFPROBE = 'C:\path\to\ffprobe.exe'
```

## 実行例

プロジェクト直下で、`faster-whisper` が入っているPythonを使います。

```powershell
& 'C:\Users\higes\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe' -m short_factory run `
  --input 'https://www.youtube.com/watch?v=VIDEO_ID' `
  --start '01:23:40' `
  --end '01:24:30' `
  --job-id 'youtube_test_001' `
  --rights-confirmed `
  --authorization-note '権利者からローカル編集実験の許可取得済み'
```

同じコマンドを再実行すると、完了済み工程を飛ばして途中から再開します。新規jobはmanifest version 3で作成され、machine字幕をimmutableなrevision 1として一度だけ保存します。

version 3 jobでは `subtitles/captions.ass` を直接編集せず、次のWebUIを使います。

```powershell
python -m short_factory review-ui
```

起動時に表示されるtoken付きlocalhost URLを開きます。画面でできることは次だけです。

このPCではデスクトップの`Short Factory - 切り抜き候補`をダブルクリックしても起動できます。ランチャーはPython・WebUI・schema・設定・ランチャー自身のSHA-256ビルド指紋を保存し、ソースが変わっていれば古いShort Factory serverだけを安全に再起動して最新版を開きます。指紋が同じ既存serverは二重起動せず、そのtoken付きURLを再利用します。PC再起動後はserverを非表示で起動し、新しいtoken付きURLを既定ブラウザで開きます。別アプリが`127.0.0.1:18765`を使用中の場合は、そのprocessを終了せずエラー表示で停止します。実体は`tools/launch_short_factory.ps1`です。

### 切り抜き候補を探す

1. LM Studioを起動し、OpenAI互換serverを`127.0.0.1:1234`で有効にします。
2. `qwen3.5-9b-uncensored-hauhaucs-aggressive.gguf`を利用可能な状態にします。
3. WebUIの「候補を探す」へ動画をドラッグ＆ドロップします。
4. その動画の編集・分析許可と、PC内ローカル処理への同意を確認して開始します。
5. 完了後、最大5件のcardを選びます。元動画全体が候補時刻へseekするので、シークバーと±0.1秒/±1秒で実際の見どころまで前後を確認します。
6. 現在位置または時刻入力で15〜60秒の開始・終了を直し、「この範囲をショート編集へ」を押します。source SHA-256を再検証してから、文字起こし用version 3 jobと、同じsourceを固定したversion 4 Composition project／EditPlan Revision 1を作成し、「ショートを編集」へ移動します。

候補結果はブラウザ内だけでなく`<jobs-root>/.candidate-runs/`へ保存されます。「新しい動画を選ぶ」を押しても削除されず、画面上部の「保存済みの候補結果」から復帰できます。元動画全体のplayerは対話的な確認用にsize・path confinement・記録済みETagを検査してRange配信し、job作成時には記録済みSHA-256と実ファイルを全量照合します。

通常の文字起こしは`faster-whisper small / CPU / int8`、候補選定は上記のLM Studioを使い、transcriptを外部サービスへ送信しません。素材に独立したhookと着地がなければ、候補0件を正常結果として返します。5件を水増しする仕様ではありません。

個別のsourceについてユーザーが明示的に外部AI利用を許可した場合だけ、run・source SHA-256・provider・model・payload scopeを`external-ai-authorization.json`へ不変記録し、Codex CLIを選定器にできます。現在の実装は`gpt-5.6-sol`、read-only sandbox、ephemeral session、timestamp付きtranscript本文のみを固定し、動画・音声・frameは送りません。許可artifactがない別runは自動的にCodexへ切り替わらず、従来どおりLM Studio経路です。ephemeralはローカルsessionを保存しない指定であり、provider側の保持条件を推測するものではありません。

ブラウザは元ファイルの絶対パスを取得できないため、動画bytesを8 MiBずつローカル作業領域へ転送します。転送済みchunkはhashで照合され、同じファイルを選び直せば中断後も再開できます。分析状態はdiskへ保存されるため、WebUI再起動後も復元できます。候補探索中のartifactは`<jobs-root>/.candidate-runs/`へ隔離され、通常のjob・字幕revision・renderには触れません。

長尺素材は即時処理ではありません。このPCで2時間22分35秒の許可済み素材を全文文字起こしした実測は約20分44秒で、その後に候補選定とpreview生成が加わります。短い素材でもモデル起動時間が必要です。現在のローカル9Bモデルは候補の見逃しやASR由来の意味誤認が残るため、候補cardの説明を正解扱いせずpreviewで必ず確認してください。

### ショートを編集する

上部の作業入口は「候補を探す」と「ショートを編集」の2つです。独立した「字幕を編集」は廃止し、1本のショートを完成させる同じEditPlan Revisionへ全操作を集約しています。

「ショートを編集」内には、今後編集機能を追加できるsection navigationがあります。現在は次の2sectionです。

- `構成・画面`: カット順、除外、尺、layout、crop、選択カットの字幕
- `字幕一覧`: ショート全体をカット単位で俯瞰し、本文、役割、開始／終了、追加、削除を調整

字幕の開始／終了はカット内秒数を直接入力するか、±0.1秒で微調整できます。「映像で確認」は該当カットを選び、ライブ編集previewを字幕開始位置へseekします。空本文、カット外、前後字幕との重なり、1frame未満の表示時間は保存前に検出し、「保存してProxy更新」を無効にします。

保存前の変更はbrowser draftだけにあり、既存Revisionとrenderを変更しません。追加／削除／本文／役割／時刻／構成をまとめて新しいimmutable EditPlan Revisionとして保存し、そのRevisionからProxyを生成します。入力のたびに通信やFFmpeg renderは行わず、Canvasライブpreviewへ即時反映します。ASSの最終改行、映像filter、音量、micro fade、公開可否は保存後のProxyで確認してください。

## C0 Composition Kernel

C0は、既存version 3字幕workflowを変更せず並行動作するversion 4構成kernelです。単一source内の複数場面、場面札、場面内layout切替、役割付き字幕、click防止micro fadeを、immutable EditPlanからrenderします。

手書きEditPlanに加え、review UIの「ショートを編集」から次の人間調整ができます。

- 再生順でのカット選択、同一story beat内の並べ替え、不要カットの除外
- カットごとのレイアウト変更（ゲーム＋顔、ゲーム寄せ、顔寄せ、全体）
- 開始・終了の±1秒／±0.1秒調整
- 選択カットまたは全字幕一覧から、字幕の追加／削除、本文、役割、開始／終了を修正
- ゲーム／顔の重要範囲をドラッグ・拡縮し、敵HPなどの見切れ禁止点を指定
- 元動画をdraftのカット順・IN/OUT・削除・字幕・layout・cropで再生するライブ編集preview
- 未保存変更の一括破棄、immutableな新Revisionとしての保存、その保存Revisionからのproxy自動更新

「確認対象」はライブ編集と保存済みProxy／Finalを分離します。ライブ編集は構成判断用の近似表示で、未保存変更を即時反映します。字幕の最終改行、映像filter、音量、micro fade、公開可否は保存後のProxyで確認してください。未保存中に保存済みrenderを選ぶと「未保存変更は未反映」と表示します。

UIを起動する場合は、通常jobとComposition projectのrootを明示します。

```powershell
python -m short_factory review-ui `
  --jobs-root 'D:\ShortFactory\jobs' `
  --composition-projects-root 'D:\ShortFactory\composition-projects'
```

保存前の操作はブラウザ内のdraftだけを変更します。保存すると新しいEditPlan revisionが作られ、既存revisionとrenderは変更されません。proxyは保存済みrevisionだけから明示実行します。現在もAI planner、Vision/OCR、BGM/SFX自動化、自由layer/keyframeは未接続です。

```powershell
python -m short_factory composition-init `
  --project-id local_composition_001 `
  --source 'D:\video\authorized-source.mp4' `
  --rights-confirmed `
  --authorization-note 'owner-provided local editing fixture'

python -m short_factory composition-publish-edit `
  --project-id local_composition_001 `
  --edit-file 'D:\plans\edit.json'

python -m short_factory composition-compile `
  --project-id local_composition_001 `
  --edit-revision 1

python -m short_factory composition-render `
  --project-id local_composition_001 `
  --edit-revision 1 `
  --profile proxy

python -m short_factory composition-render `
  --project-id local_composition_001 `
  --edit-revision 1 `
  --profile final
```

2回目以降のpublishでは、現在のrevisionを明示します。

```powershell
python -m short_factory composition-publish-edit `
  --project-id local_composition_001 `
  --edit-file 'D:\plans\edit-v2.json' `
  --base-revision 1
```

EditPlanの機械可読schemaは`short_factory/schemas/editplan.v1.schema.json`です。3構造の最小例は`tests/fixtures/composition/`にあります。

```text
composition-projects/<project-id>/
  project.json
  project-identity.json
  edits/current.json
  edits/recovery.json
  edits/revisions/000001/edit.json
  edits/revisions/000001/compiled-timeline.json
  renders/<render-id>/render-input.json
  renders/<render-id>/compiled-timeline.json
  renders/<render-id>/captions.ass
  renders/<render-id>/short.mp4
  renders/<render-id>/qc.json
  renders/<render-id>/render.json
```

EditPlanのsource video境界は整数PTS、source audio境界はstream開始からの整数sample indexです。完成側のframe/sample対応は`compiled-timeline.json`だけが導出し、EditPlanへ完成時刻を保存しません。発話字幕がtrimで場面外になった場合は別場面へ自動移動せず、`ORPHANED`としてpublishを拒否します。

proxyとfinalは同じcanvas、fps、font、改行、filter graph、audio sample rate、CompiledTimelineを使い、final encodeのpresetだけを変えます。renderは明示edit revision、source SHA-256、style preset内容、compiler version、render profileを`render-input.json`へ固定します。同じPlanで同じMP4 bytesになることではなく、同じCompiledTimelineとframe/sample mappingになることを再現性の対象にします。

manifest version 1・2の既存jobはread-onlyです。自動migrationもmutableな`--rerun-from`も行わず、新しいjob IDから開始してください。字幕保存後のpreviewは、必ず明示したcaption revisionを`render-job`またはWebUIから固定して作成します。

長時間ライブで直接の区間取得が止まる場合は、CLIが自動的に全編360pの共有キャッシュへ切り替えます。画質確認を優先する場合は `--acquire-mode full --fallback-height 720` を指定します。キャッシュは動画IDと画質上限ごとに分離し、映像・音声・尺・実解像度を検証してから、同じURLの別ジョブでも再利用します。

ローカル動画も同じ形式です。

```powershell
python -m short_factory run --input 'D:\video\source.mp4' --start 00:10:00 --end 00:10:45 --job-id local_test
```

## 成果物

`jobs/<job-id>/` にすべてローカル保存します。

```text
source/acquired.mp4
audio/speech_16k.wav
transcript/raw.json
transcript/transcript.txt
subtitles/captions.srt
subtitles/captions.ass
subtitles/current.json
subtitles/recovery.json
subtitles/revisions/000001/captions.json
subtitles/revisions/000002/captions.json
output/short.mp4
output/preview.jpg
renders/<render-id>/captions.ass
renders/<render-id>/captions.srt
renders/<render-id>/short.mp4
renders/<render-id>/qc.json
renders/<render-id>/render.json
logs/pipeline.log
logs/revision-render.log
state.json
job.json
qc.json
```

YouTubeへの投稿や外部ストレージへのアップロード処理は実装していません。

`output/short.mp4`は初回pipelineの互換用bootstrap出力で、WebUIのreview対象・正本・納品物ではありません。WebUIが配信するのは、明示caption revisionから作成して実hashを再照合できた`renders/<render-id>/short.mp4`だけです。

caption revisionは同じfilesystem上の一時directoryへ書き、検証後にimmutable directoryとして公開してから、最後に`current.json`をatomic replaceします。preview renderもMP4・QC・metadataを一時directoryで検証してからimmutable render directoryとして公開します。ローカル入力とBGMはパスだけでなくファイルサイズと更新時刻もジョブ署名へ含め、同じパスで素材が差し替わった場合の誤った再開を防ぎます。

`qc.json` の合格は、解像度・コーデック・尺・デコード・字幕行数などの技術検査だけを意味します。WebUIも内容確認を自動完了せず、このprototypeから承認・納品はできません。

同じcaption revisionに複数のpreview renderがある場合、WebUIはどれかを自動で正本扱いしません。render IDとhashを見て、表示するものを手動で選択します。
