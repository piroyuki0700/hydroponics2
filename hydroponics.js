//
// hydroponics javascript
//

// グローバル変数
let pump_active = false;

let timerIdPump = 0;
let timerIdCamera = 0;
let timerIdReconnect = 0;

let webSocket = null;
let connectRetry = true;
let master = {};  // masterデータ保持用連想配列

const server_uri = 'ws://' + location.hostname + ':10700/'

//
// 初期化処理 jQueryの書き方
//
$(function(){
  // バージョン
  $('#version').text('Ver.2024.4.29');

  // 最初は非表示にするもの
  $('#setting').hide();	// 設定ページ
  $('#picture_save_buttons').hide();	// カメラ保存ボタン
  $('#pump_working').hide();	// ポンプ動作表示

  // 時計の表示
  setTimeout(UpdateClock, 500);

  // websocket-serverと接続
  websocketConnect();
});

//
// 再接続ボタン
//
function reconnectButtonClick()
{
  if (webSocket == null) {
    websocketConnect();
    connectRetry = true;
  } else {
    printDebugMessage("websocket is already connected.")
  }
}

//
// 切断ボタン
//
function disconnectButtonClick()
{
  if (webSocket == null) {
    printDebugMessage("websocket is not connected.")
  } else {
    connectRetry = false;
    webSocket.close();
  }
}

//
// メインページへ移動
//
function goMain()
{
  $('#setting').hide();
  $('#main').show();
}

//
// 設定ページへ移動
//
function goSetting()
{
  $('#setting').show();
  $('#main').hide();
}

//
// websocket-serverと接続
//
function websocketConnect()
{
  if (timerIdReconnect != 0)
  {
    clearTimeout(timerIdReconnect);
    timerIdReconnect = 0;
  }

  if (webSocket != null)
  {
    printDebugMessage("already connected.");
    return;
  }

  // WebSocket の初期化
  webSocket = new WebSocket(server_uri);

  // イベントハンドラの設定
  webSocket.onopen = websocket_open;
  webSocket.onclose = websocket_close;
  webSocket.onerror = websocket_error;
  webSocket.onmessage = websocket_message;
}

function websocket_open(event)
{
  printDebugMessage("websocket opened.");
  $('#reconnectButton').hide();
  $('#confirmModal').modal('hide');
}
function websocket_close(event)
{
  printDebugMessage("websocket closed.");
  webSocket = null;
  $('#reconnectButton').show();
  setValuePumpStatus({'pump_status': 'manual_stop', 'seconds': 0});
  setValueRefillUpdate({ 'refill_switch': false})

  // 1分後に１回だけ自動再接続を試みる
  if (connectRetry == true) {
    connectRetry = false;
    printDebugMessage("reconnect timer start")
    timerIdReconnect = setTimeout(websocketConnect, 60 * 1000);
  }
}
function websocket_error(event)
{
  if (timerIdReconnect != 0){
    clearTimeout(timerIdReconnect)
    timerIdReconnect = 0;
  } else {
    printDebugMessage("websocket error occured.");
    const now = new Date();
    const nowstr = now.getFullYear() + "/" + (now.getMonth() + 1) + "/" + now.getDate()
      + " " + now.getHours() + ":" + now.getMinutes() + ":" + now.getSeconds();
    showModalResult({'result': 'error', 'message': 'websocket error.', 'datetime': nowstr});
  }
};

function websocket_message(event)
{
//  printDebugMessage(event.data);
  const data = JSON.parse(event.data);

  switch(data['command'])
  {
    case 'initial_data':
    //  setValueReport(data);
      setValuePicture(data);
      setValueBasic(data);
      setValueSchedule(data);
      setValueSensorLimit(data);
      setValuePumpStatus(data);
      setValueRefillUpdate(data);
      break;

    case 'report':
      setValueReport(data);
      break;

    case 'picture':
      setValuePicture(data);
      break;

    case 'setting_basic':
      setValueBasic(data);
      break;

    case 'setting_schedule':
      setValueSchedule(data);
      break;

    case 'setting_sensor_limit':
      setValueSensorLimit(data);
      break;

    case 'pump_status':
      setValuePumpStatus(data)
      break;

    case 'tmp_picture':
      setValueTmpPicture(data);
      break;

    case 'refill_update':
      setValueRefillUpdate(data);
      break;

    case 'result':
      printDebugMessage(data['datetime'] + ': ' + data['result'] + ' - ' + data['message']);
      if (data['show_popup'])
        showModalResult(data);
      break;

    default:
      printDebugMessage('unknown command [' + data['command'] + '] is received via websocket');
      break;
  }

  /* コマンドは除いてすべてマージしてマスターに集める */
  delete data['command'];
  Object.assign(master, data);
};

//
// websocketサーバーへデータ送信
//
function websocket_send(data)
{
  webSocket.send(JSON.stringify(data));
}

//
// メイン：定時撮影写真の反映
//
function setValuePicture(data)
{
  if ('picture_path' in data) {
    $('#picture_frame').css('background-image', 'url(' + data['picture_path'] + ')');
    $('#picture_timestamp').text(data['picture_taken']);
  }
}

//
// メイン：測定データの反映
//
function setValueReport(data)
{
  const sensors = new Array('air_temp', 'humidity', 'water_temp', 'water_level', 'tds_level', 'brightness');
  const decimal = new Array(1,1,1,0,2,0);

  for (let i = 0; i < sensors.length; i++) {
    const name = '#' + sensors[i];
    let value = 'XX.X';
    const item = '#sensor_' + sensors[i];
    let color_name = 'bg-secondary';

    if (sensors[i] in data) {
      value = data[sensors[i]].toFixed(decimal[i]);
      const status = data[sensors[i] + '_status'];
      if (status == 'danger') {
        color_name = 'bg-danger';
      } else if (status == 'warning') {
        color_name = 'bg-warning';
      } else if (status == 'success') {
        color_name = 'bg-success';
      }   
    }

    // センサー値の更新
    $(name).text(value);
    // センサー値エリアの色変更
    $(item).removeClass("bg-success").removeClass("bg-warning").removeClass("bg-danger").removeClass("bg-secondary");
    $(item).addClass(color_name);
  }

  // タイトル部分の色変更
  let value = "unknown";
  let status = "secondary"
  if ('total_status' in data) {
    status = data['total_status'];
    value = (status == 'success')?'all OK':status
  }
  // ステータスエリア全体の色変更
  $('#status_color').removeClass("alert-success").removeClass("alert-warning").removeClass("alert-danger").removeClass("alert-secondary");
  $('#status_color').addClass("alert-" + status)
  // バッジの色と文字列変更
  $('#status_badge').removeClass("badge-success").removeClass("badge-warning").removeClass("badge-danger").removeClass("badge-secondary");
  $('#status_badge').addClass("badge-" + status)
  $('#status_badge').text(value);
}

//
// 設定：基本情報の反映
//
function setValueBasic(data)
{
  $('#titlename').text(data['myname']);
  $('#myid').text(data['myid']);
  $('#myname').text(data['myname']);
  $('#memo').text(data['memo']);

  if (data['started'] != null)
  {
    $('#started').text(data['started']);
  }
  if (data['finished'] != null)
  {
    $('#finished').text(data['finished']);
  }
}

//
// 設定：定時処理の設定の反映
//
function setValueSchedule(data)
{
  // 時刻指定なしにしたいとき（マイナス値は無効）
  const items = ["time_spot1", "time_spot2", "time_spot3", 
    "camera1", "camera2", "camera3", "camera4", "camera5"];

  for (const item of items) {
    if (data[item] < 0)
      data[item] = "";
  }

  $('input[name="schedule_active"]').bootstrapToggle(data['schedule_active']?'on':'off');
  $('input[name="time_morning"]').val(data['time_morning']);
  $('input[name="time_noon"]').val(data['time_noon']);
  $('input[name="time_evening"]').val(data['time_evening']);
  $('input[name="time_night"]').val(data['time_night']);
  $('input[name="morning_on"]').val(data['morning_on']);
  $('input[name="morning_off"]').val(data['morning_off']);
  $('input[name="noon_on"]').val(data['noon_on']);
  $('input[name="noon_off"]').val(data['noon_off']);
  $('input[name="evening_on"]').val(data['evening_on']);
  $('input[name="evening_off"]').val(data['evening_off']);
  $('input[name="nightly_active"]').bootstrapToggle(data['nightly_active']?'on':'off');
  $('input[name="time_spot1"]').val(data['time_spot1']);
  $('input[name="time_spot2"]').val(data['time_spot2']);
  $('input[name="time_spot3"]').val(data['time_spot3']);
  $('input[name="spot_on"]').val(data['spot_on']);
  $('input[name="refill_trigger"]').val([data['refill_trigger']]);
  $('input[name="refill_min"]').val(data['refill_min']);
  $('input[name="refill_max"]').val(data['refill_max']);
  $('input[name="camera1"]').val(data['camera1']);
  $('input[name="camera2"]').val(data['camera2']);
  $('input[name="camera3"]').val(data['camera3']);
  $('input[name="camera4"]').val(data['camera4']);
  $('input[name="camera5"]').val(data['camera5']);
  $('input[name="notify_active"]').bootstrapToggle(data['notify_active']?'on':'off');
  $('input[name="notify_time"]').val(data['notify_time']);
  $('input[name="emergency_active"]').bootstrapToggle(data['emergency_active']?'on':'off');
}

//
// 設定：センサー閾値の反映
//
function setValueSensorLimit(data)
{
  $('input[name="air_temp_vlow"]').val(data['air_temp_vlow']);
  $('input[name="air_temp_low"]').val(data['air_temp_low']);
  $('input[name="air_temp_high"]').val(data['air_temp_high']);
  $('input[name="air_temp_vhigh"]').val(data['air_temp_vhigh']);
  $('input[name="humidity_vlow"]').val(data['humidity_vlow']);
  $('input[name="humidity_low"]').val(data['humidity_low']);
  $('input[name="water_temp_vlow"]').val(data['water_temp_vlow']);
  $('input[name="water_temp_low"]').val(data['water_temp_low']);
  $('input[name="water_temp_high"]').val(data['water_temp_high']);
  $('input[name="water_temp_vhigh"]').val(data['water_temp_vhigh']);
  $('input[name="water_level_vlow"]').val(data['water_level_vlow']);
  $('input[name="water_level_low"]').val(data['water_level_low']);
  $('input[name="tds_level_vlow"]').val(data['tds_level_vlow']);
  $('input[name="tds_level_low"]').val(data['tds_level_low']);
  $('input[name="tds_level_high"]').val(data['tds_level_high']);
  $('input[name="tds_level_vhigh"]').val(data['tds_level_vhigh']);
}

//
// メイン／設定：ポンプ状態の反映
//
function setValuePumpStatus(data)
{
  switch (data['pump_status'])
  {
    case 'auto_start':
      // 時間がわからないのでカウントダウン更新はしない
      return;

    case 'auto_stop':
      $('#pump_info').text('')
      $('#cycle_icon').removeClass('fa-spin');
      pump_active = false;
      break;

    case 'cycle_start':
      $('#pump_info').text('オート動作中')
      $('#cycle_icon').addClass('fa-spin');
      pump_active = true;
      break;

    case 'cycle_stop':
      $('#pump_info').text('オート動作中')
      $('#cycle_icon').removeClass('fa-spin');
      pump_active = false;
      break;

    case 'manual_start':
      $('#pump_info').text('マニュアル動作中')
      $('#cycle_icon').addClass('fa-spin');
      pump_active = true;
      break;

    case 'manual_stop':
    default:
      $('#pump_info').text('')
      $('#cycle_icon').removeClass('fa-spin');
      pump_active = false;
      break;
  }

  pumpStatusUpdate(data['seconds']);
}

function setValueTmpPicture(data) {
  if (data['tmp_picture_result']) {
	// 成功
    $('#tmp_picture_frame').css('background-image', 'url(' + data['tmp_picture_path'] + ')');
    $('#tmp_picture_timestamp').text(data['tmp_picture_taken']);

    $('#picture_save_buttons').show();
    $('#camera_countdown').text('');
  } else {
    // 失敗
    $('#picture_save_buttons').hide();
    $('#camera_countdown').text('error');
  }
}

function setValueRefillUpdate(data) {
  // サブポンプ動作状態
  if ('refill_switch' in data) {
    if (data['refill_switch']) {
      $('#subpump_working').addClass('text-primary').removeClass('text-secondary').addClass('fa-spin')
    } else {
      $('#subpump_working').removeClass('text-primary').addClass('text-secondary').removeClass('fa-spin')
    }
  }
  // メインタンク水位
  if ('refill_level' in data) {
    $('#refill_level').text(data['refill_level'])
  } else {
    $('#refill_level').text('ー')
  }

  // フロートスイッチ状態
  float_switchs = ['upper', 'lower', 'sub'];
  for (const float_switch of float_switchs) {
    if ('refill_float_' + float_switch in data) {
      if (data['refill_float_' + float_switch]) {
        $('#icon_float_' + float_switch).removeClass('fa-times-circle').removeClass('text-danger').addClass('fa-check-circle').addClass('text-success')
      } else {
        $('#icon_float_' + float_switch).removeClass('fa-check-circle').removeClass('text-success').addClass('fa-times-circle').addClass('text-danger')
      }
    }
  }
  // 水の補充記録、過去3回分
  if ('refill_record1' in data) {
    $('#refill_record1').text(data['refill_record1']);
  }
  if ('refill_record2' in data) {
    $('#refill_record2').text(data['refill_record2']);
  }
  if ('refill_record3' in data) {
    $('#refill_record3').text(data['refill_record3']);
  }
}
//
// メイン：ポンプボタン
//
function cycleButtonClick() {
  // オート動作の反転とする
  pump_active ^= 1;
  websocket_send({'command': pump_active?'pump_auto_start':'pump_auto_stop'});
}

//
// メイン：測定データ更新ボタン
// 　一時的なデータなので直接受け取る。websocketのbroadcastはしない。
//
function reloadButtonClick() {
  const sensors = new Array('air_temp', 'humidity', 'water_temp', 'water_level', 'tds_level', 'brightness');

  //一時的に無効の色に変える
  for (let i = 0; i < sensors.length; i++) {
    const item = '#sensor_' + sensors[i];
    $(item).removeClass("bg-success").removeClass("bg-warning").removeClass("bg-danger").addClass("bg-secondary");
  }

  websocket_send({'command': 'tmp_report'});
}

//
// 時計の更新
//
function UpdateClock()
{
  const now = new Date();

  let year = now.getFullYear();
  let month = now.getMonth() + 1;
  let day = now.getDate();

  let weekdays = new Array("日","月","火","水","木","金","土");
  let weekday = weekdays[now.getDay()];

  let hour = now.getHours();
  let minute = now.getMinutes();
  let second = now.getSeconds();

  let ampm = '午前';
  if (12 <= hour) {
    ampm = '午後';
    hour -= 12;
  }

  // 時計の更新
  $('#date_string').text(year + '年' + month + '月' + day + '日');
  $('#weekday_string').text(weekday + '曜日');
  $('#time_string').text(ampm + hour + '時' + minute + '分');

  // タイマー再設定
  ms = (59 - second) * 1000;
  if (ms < 300)
    ms = 300
  setTimeout(UpdateClock, ms);
}

function basicButtonClick(kind) {
  websocket_send({'command': 'post_basic', 'kind': kind});
}

//
// 定時処理の設定を「反映する」ボタン
//
function scheduleCommitClick() {
  const scheduleForm = document.querySelector('#schedule_form');
  const formData = new FormData(schedule_form);
  data = Object.fromEntries(formData);

  // トグルスイッチの値の追加
  data["schedule_active"] = $('input[name="schedule_active"]').prop("checked")?"1":"0";
  data["nightly_active"] = $('input[name="nightly_active"]').prop("checked")?"1":"0";
  data["notify_active"] = $('input[name="notify_active"]').prop("checked")?"1":"0";
  data["emergency_active"] = $('input[name="emergency_active"]').prop("checked")?"1":"0";

  // ラジオボタンの値の取得
  data["refill_trigger"] = $('input[name="refill_trigger"]:checked').val();
  printDebugMessage("trigger=" + $('input[name="refill_trigger"]:checked').val());

  // 時刻指定なしにしたいとき（マイナス値は無効）
  const items = ["time_spot1", "time_spot2", "time_spot3", 
    "camera1", "camera2", "camera3", "camera4", "camera5"];

  for (const item of items) {
    if (data[item] == "")
      data[item] = "-1";
  }

  data['command'] = 'post_schedule';
  websocket_send(data);
}

//
// 定時処理の設定を「元に戻す」ボタン
// （resetではなくデータベースから取得した値に戻す必要がある）
//
function scheduleCancelClick() {
  $('#schedule_form').prop('disabled', true);
  setValueSchedule(master);
}

//
// 設定：ポンプ動作ボタン
//
function pumpButtonClick(request, seconds=0) {
  // サーバーへポンプ動作秒数を設定
  websocket_send({'command': 'pump_' + request, 'seconds': seconds});
}

function pumpStatusUpdate(seconds)
{
  // いったん停止
  clearInterval(timerIdPump);

  if (pump_active) {
    $('#pump_working').show();
    $('#pump_stop').hide();
  } else {
    $('#pump_working').hide();
    $('#pump_stop').show();
  }

  // カウントダウン表示
  if (seconds < 0) {
    // 連続動作
    $('#pump_countdown').text("連続");
  }
  else if (seconds == 0) {
    // 停止
    $('#pump_countdown').text("停止");
  }
  else
  {
    // カウントダウン開始
    pumpCountdownStart(seconds);
  }
}

function pumpCountdownStart(seconds)
{
  if (seconds <= 0) {
    clearInterval(timerIdPump);
    $('#pump_countdown').text("");
  } else {
    // 最初の表示
    pumpCountdownPrint(seconds);

    // 終了時刻を現在時刻＋カウントダウンする秒数に設定
    let start = new Date();
    let end = new Date(start.getTime() + seconds * 1000);

    // タイマー設定
    timerIdPump = setInterval(function(){
      let now = new Date();
      let diff = (end.getTime() - now.getTime()) / 1000;
      if (diff <= 0) {
        clearInterval(timerIdPump);
        diff = 0
      }
      pumpCountdownPrint(diff);
    }, 500);
  }
}

function pumpCountdownPrint(seconds) {
  seconds += 0.9;
  let min = parseInt(seconds / 60);
  let sec = parseInt(seconds % 60);
  if (sec < 10) {
    sec = '0' + sec;
  }
  $('#pump_countdown').text(min + ":" + sec);
}

//
// カメラ撮影ボタン
//
function cameraButtonClick(seconds) {

  cameraCountdownStop();
  $('#picture_save_buttons').hide();

  if (seconds < 0) {
    //中止
    $('#camera_countdown').text("");
  } else if (seconds == 0) {
    //今すぐ
    $('#camera_countdown').text("");
    takePicture();
  } else {
    //タイマー撮影
    $('#camera_countdown').text(seconds);
    cameraCountdownStart(seconds);
  }
}

function cameraCountdownStart(seconds) {

  if (seconds <= 0) {
    clearInterval(timerIdCamera);
    $('#camera_countdown').text("");
  } else {
    // 最初の表示
    cameraCountdownPrint(seconds);

    // 終了時刻を現在時刻＋カウントダウンする秒数に設定
    let start = new Date();
    let end = new Date(start.getTime() + seconds * 1000);

    // タイマー設定
    timerIdCamera = setInterval(function(){
      now = new Date();
      diff = (end.getTime() - now.getTime()) / 1000;

      cameraCountdownPrint(diff);

      if (diff <= 0) {
        cameraCountdownStop();
        takePicture();
      }
    }, 500);
  }
}

function cameraCountdownStop() {
  clearInterval(timerIdCamera);
}

function cameraCountdownPrint(seconds) {
  seconds += 0.9;
  let sec = parseInt(seconds % 60);
  if (60 < sec) {
    sec = 60;  /* 最大60秒 */
  }
  $('#camera_countdown').text(sec);
}

//
// カメラ撮影リクエスト
//
function takePicture()
{
  $('#camera_countdown').html('<i class="fa fa-spinner fa-spin "></i>');
  websocket_send({'command': 'tmp_picture'});
}

//
// 写真保存ボタン
//
function saveButtonClick(needed) {
  if (needed) {
    // 保存
    websocket_send({'command': 'save_picture', 'tmp_picture_name': master['tmp_picture_name'],
      'tmp_picture_path': master['tmp_picture_path'], 'tmp_picture_taken': master['tmp_picture_taken']});
  } else {
    // 破棄
    websocket_send({'command': 'delete_picture', 'tmp_picture_path': master['tmp_picture_path']});

    $('#tmp_picture_frame').css('background-image', '');
    $('#tmp_picture_timestamp').text('no data');
  }

  // ボタンは隠す
  $('#picture_save_buttons').hide();
}

//
// センサー閾値の設定を「反映する」ボタン
//
function limitCommitClick() {
  const sensorForm = document.querySelector('#sensor_limit_form');
  const formData = new FormData(sensorForm);
  data = Object.fromEntries(formData);

  data['command'] = 'post_sensor_limit';
  websocket_send(data);
}

//
// センサー閾値の設定を「元に戻す」ボタン
// （resetではなくデータベースから取得した値に戻す必要がある）
//
function limitCancelClick() {
  setValueSensorLimit(master);
}

//
// 結果ポップアップ表示
//
function showModalResult(data)
{
  $('#modal_result').text(data['result'])
  $('#modal_message').text(data['message'])
  $('#modal_datetime').text(data['datetime'])
  $('#confirmModal').modal()
}

//
// デバッグ：サーバーへリクエストを送ってLEDをON/OFFするテスト
//
function ledButtonClick(color) {
  websocket_send({'command': 'set_led', 'color': color});
}

//
// デバッグ：センサーひとつの値取得
//
function debugButtonMeasure(sensor_kind) {
  websocket_send({'command': 'measure_sensor', 'sensor_kind': sensor_kind});
}

//
// デバッグ：サブポンプ動作
//
function subPumpButtonClick(request, option="none") {
  data = {'command': 'subpump_' + request, 'option': option}
  data["level_active"] = $('input[name="level_active"]').prop("checked")?"1":"0";
  websocket_send(data);
}

//
// デバッグ：汎用動作テスト
//
function debugButtonExec(debug_request="debug_echo", option="none") {
  websocket_send({'command': debug_request, 'option': option});
}
//
// デバッグ：時間区分の変更
//
function debugTimeSpan() {
  data = {'command': 'debug_time_span',
    "minute_start": $('input[name="minute_start"]').val(),
    "minute_stop": $('input[name="minute_stop"]').val(),
    "minute_refill": $('input[name="minute_refill"]').val()
  }
  websocket_send(data);
}

//
// デバッグ：メッセージ表示
//
function printDebugMessage(message)
{
  $('#debug_message').val($('#debug_message').val() + message + '\n');
  $('#debug_message').scrollTop($('#debug_message')[0].scrollHeight);
}

//
// デバッグ：メッセージクリア
//
function clearMessageClick() {
  $('#debug_message').val('');
}

