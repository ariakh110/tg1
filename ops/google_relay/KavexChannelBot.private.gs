/**
 * Kavex Channel Bot v1.2.0 — private polling, owner DM and dedicated group
 * Generated from modular sources. Paste this entire file into Code.gs.
 */

/* ===== 00_Config.gs ===== */
/**
 * Kavex Channel Bot — configuration and constants.
 * Secrets are kept in Script Properties, never in spreadsheet cells.
 */

var KAVEX_CHANNEL_BOT_VERSION = '1.2.0-private-site-relay';

var KX = Object.freeze({
  SERVICE_NAME: 'kavex-channel-automation',
  TIMEZONE: 'Asia/Tehran',
  LOCK_TIMEOUT_MS: 20000,
  STATE_TTL_MINUTES: 30,
  MAX_TELEGRAM_TEXT: 3900,

  PROPS: Object.freeze({
    SPREADSHEET_ID: 'KX_SPREADSHEET_ID',
    BOT_TOKEN: 'KX_TELEGRAM_BOT_TOKEN',
    OWNER_ID: 'KX_OWNER_TELEGRAM_USER_ID',
    INBOX_CHAT_ID: 'KX_PRIVATE_INBOX_CHAT_ID',
    TELEGRAM_OFFSET: 'KX_TELEGRAM_OFFSET',
    LAST_POLL_AT: 'KX_LAST_POLL_AT',
    LAST_POLL_ERROR: 'KX_LAST_POLL_ERROR',
    STATE_PREFIX: 'KX_BOT_STATE_',
    DAILY_SEQUENCE_PREFIX: 'KX_DAILY_SEQ_'
  }),

  SHEETS: Object.freeze({
    SETTINGS: 'Settings',
    SUPPLIERS: 'Suppliers',
    INBOX: 'Inbox',
    INVENTORY: 'Inventory',
    CATALOG: 'Catalog',
    TEMPLATES: 'Templates',
    HOLIDAYS: 'Holidays',
    POSTS: 'Posts',
    EVENTS: 'Events',
    AUDIT: 'AuditLog',
    DICTIONARIES: 'Dictionaries'
  }),

  HEADERS: Object.freeze({
    Settings: ['key', 'value', 'description', 'updated_at'],
    Suppliers: [
      'supplier_id', 'display_name', 'source_type', 'telegram_chat_id',
      'telegram_username', 'aliases', 'default_location', 'active',
      'created_at', 'updated_at', 'private_notes'
    ],
    Inbox: [
      'inbox_id', 'telegram_update_id', 'received_at', 'sender_user_id',
      'sender_name', 'inbox_chat_id', 'inbox_chat_title', 'source_type',
      'source_chat_id', 'source_title', 'source_username', 'source_message_id',
      'supplier_id', 'raw_text', 'detected_category', 'parsed_text',
      'item_count', 'status', 'valid_until', 'public_ref',
      'target_message_ids', 'review_message_id', 'error_message', 'updated_at'
    ],
    Inventory: [
      'inventory_id', 'inbox_id', 'supplier_id', 'received_at', 'category',
      'product_title', 'specification', 'grade', 'thickness', 'width',
      'length', 'unit', 'location', 'public_line', 'status', 'valid_from',
      'valid_until', 'include_in_digest', 'public_ref', 'source_message_id',
      'published_at', 'channel_message_ids', 'updated_at'
    ],
    Catalog: [
      'item_id', 'category', 'title', 'specifications', 'display_order',
      'active', 'updated_at'
    ],
    Templates: [
      'template_key', 'title', 'body', 'enabled', 'send_time',
      'working_days', 'notes', 'updated_at'
    ],
    Holidays: ['jalali_date', 'title', 'active', 'notes', 'updated_at'],
    Posts: [
      'post_id', 'inbox_id', 'post_type', 'schedule_key', 'scheduled_at',
      'published_at', 'destination_chat_id', 'telegram_message_ids',
      'public_ref', 'status', 'text', 'error_message', 'created_at', 'updated_at'
    ],
    Events: ['event_key', 'received_at', 'status', 'result', 'error_message', 'updated_at'],
    AuditLog: ['log_id', 'created_at', 'actor', 'action', 'entity_type', 'entity_id', 'details'],
    Dictionaries: ['rule_id', 'rule_type', 'pattern', 'replacement', 'priority', 'active', 'notes']
  })
});

function kxProps_() {
  return PropertiesService.getScriptProperties();
}

function kxSpreadsheet_() {
  var id = kxProps_().getProperty(KX.PROPS.SPREADSHEET_ID);
  if (!id) throw new Error('ابتدا گزینه «۱) نصب ساختار شیت‌ها» را اجرا کنید.');
  return SpreadsheetApp.openById(id);
}

function kxSheet_(sheetName) {
  var sheet = kxSpreadsheet_().getSheetByName(sheetName);
  if (!sheet) throw new Error('شیت موردنیاز پیدا نشد: ' + sheetName);
  return sheet;
}


/* ===== 01_Utils.gs ===== */
/** General utilities, time handling and Jalali date conversion. */

function kxAssert_(condition, message) {
  if (!condition) throw new Error(message || 'عملیات نامعتبر است.');
}

function kxString_(value) {
  return value === null || value === undefined ? '' : String(value);
}

function kxJson_(value) {
  try { return JSON.stringify(value); } catch (err) { return '{}'; }
}

function kxParseJson_(value, fallback) {
  try { return JSON.parse(kxString_(value)); } catch (err) { return fallback; }
}

function kxNowIso_() {
  return new Date().toISOString();
}

function kxUuid_() {
  return Utilities.getUuid();
}

function kxShortId_(prefix) {
  var stamp = Utilities.formatDate(new Date(), KX.TIMEZONE, 'yyyyMMdd-HHmmss');
  return prefix + '-' + stamp + '-' + kxUuid_().slice(0, 4).toUpperCase();
}

// Nested repository helpers share the outer lock within one execution.
var kxScriptLockDepth_ = 0;

function kxWithLock_(callback) {
  if (kxScriptLockDepth_ > 0) return callback();
  var lock = LockService.getScriptLock();
  lock.waitLock(KX.LOCK_TIMEOUT_MS);
  kxScriptLockDepth_++;
  try { return callback(); } finally {
    kxScriptLockDepth_--;
    // Commit pending sheet writes before another execution enters.
    try { SpreadsheetApp.flush(); } finally { lock.releaseLock(); }
  }
}

function kxNormalizeDigits_(value) {
  var persian = '۰۱۲۳۴۵۶۷۸۹';
  var arabic = '٠١٢٣٤٥٦٧٨٩';
  return kxString_(value).replace(/[۰-۹]/g, function (d) {
    return String(persian.indexOf(d));
  }).replace(/[٠-٩]/g, function (d) {
    return String(arabic.indexOf(d));
  });
}

function kxPersianDigits_(value) {
  var persian = '۰۱۲۳۴۵۶۷۸۹';
  return kxString_(value).replace(/[0-9]/g, function (d) {
    return persian.charAt(Number(d));
  });
}

/**
 * Persian presentation digits while keeping standard steel grades readable.
 * Examples: "12 ST37" -> "۱۲ ST37" and "14 A3" -> "۱۴ A3".
 */
function kxTechnicalPersianDigits_(value) {
  var source = kxString_(value);
  var protectedGrades = [];
  source = source.replace(/\b(?:STW?\s*-?\s*\d+|W\s*-?\s*\d+|A\s*(?:36|[1234])|304|410)\b/gi, function (grade) {
    var normalized = grade.replace(/\s+/g, '').toUpperCase();
    var marker = 'KXGRADE' + protectedGrades.length + 'X';
    protectedGrades.push(normalized);
    return marker;
  });
  source = kxPersianDigits_(source);
  protectedGrades.forEach(function (grade, index) {
    source = source.replace('KXGRADE' + kxPersianDigits_(index) + 'X', grade);
  });
  return source;
}

function kxNormalizeText_(value) {
  return kxNormalizeDigits_(value)
    .replace(/\r\n?/g, '\n')
    .replace(/[يى]/g, 'ی')
    .replace(/ك/g, 'ک')
    .replace(/ة/g, 'ه')
    .replace(/ۀ/g, 'ه')
    .replace(/[\u200c\u200d\u200e\u200f\ufeff]/g, ' ')
    .replace(/[\t\u00a0]+/g, ' ')
    .replace(/ {2,}/g, ' ')
    .trim();
}

function kxCompactLine_(value) {
  return kxNormalizeText_(value)
    .replace(/^[\s\-–—_=*•▪▫]+/g, '')
    // Keep emoji handling Unicode-aware. A non-Unicode character class can
    // remove only half of 🤍/💙/🧡 because many emoji share surrogate units.
    .replace(/^(?:(?:🔹|🔸|🔶|🔷|🟢|🔴|✅|❇️?|⭐️?|🌼|🌳|🍂|😔|👑|💋)\s*)+/u, '')
    .replace(/[\s\-–—_=*]+$/g, '')
    .trim();
}

function kxUnique_(values) {
  var seen = {};
  return (values || []).filter(function (value) {
    var key = kxNormalizeText_(value).toLowerCase();
    if (!key || seen[key]) return false;
    seen[key] = true;
    return true;
  });
}

function kxTehranDateKey_(date) {
  return Utilities.formatDate(date || new Date(), KX.TIMEZONE, 'yyyy-MM-dd');
}

function kxTehranTime_(date) {
  return Utilities.formatDate(date || new Date(), KX.TIMEZONE, 'HH:mm');
}

/**
 * Google Sheets may return a cell formatted as Time as a Date object rather
 * than the literal text "09:00". Normalize both representations before the
 * scheduler compares them. This also accepts Persian digits and H:mm:ss.
 */
function kxNormalizeClockTime_(value) {
  if (Object.prototype.toString.call(value) === '[object Date]' && !isNaN(value.getTime())) {
    return Utilities.formatDate(value, KX.TIMEZONE, 'HH:mm');
  }

  var text = kxNormalizeDigits_(value).trim();
  var match = text.match(/(?:^|\s)([01]?\d|2[0-3]):([0-5]?\d)(?::[0-5]?\d)?(?:\s|$)/);
  if (!match) return text;
  return ('0' + Number(match[1])).slice(-2) + ':' + ('0' + Number(match[2])).slice(-2);
}

function kxTehranDayNumber_(date) {
  var parts = kxTehranDateKey_(date).split('-');
  var utc = new Date(Date.UTC(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2])));
  return utc.getUTCDay(); // Sunday=0 ... Saturday=6
}

function kxParseWorkingDays_(value) {
  var normalized = kxNormalizeDigits_(value)
    .replace(/[يى]/g, 'ی').replace(/ك/g, 'ک')
    .replace(/[\u200c\u200d\u200e\u200f]/g, ' ')
    .trim();
  var compact = normalized.replace(/[\s\-–—_]+/g, '');
  if (!compact || compact === 'روزهایکاری' || compact === 'شنبهتاپنجشنبه' || compact === 'کاری') {
    return [0, 1, 2, 3, 4, 6];
  }
  if (compact === 'همه' || compact === 'هرروز' || compact === 'روزانه' || compact.toLowerCase() === 'all') {
    return [0, 1, 2, 3, 4, 5, 6];
  }

  var names = {
    'یکشنبه': 0,
    'دوشنبه': 1,
    'سهشنبه': 2,
    'چهارشنبه': 3,
    'پنجشنبه': 4,
    'جمعه': 5,
    'شنبه': 6
  };
  var days = [];
  normalized.split(/[,،;؛|]+/).forEach(function (token) {
    var clean = token.trim().replace(/[\s\-–—_]+/g, '');
    var day;
    if (/^[0-6]$/.test(clean)) day = Number(clean);
    else if (Object.prototype.hasOwnProperty.call(names, clean)) day = names[clean];
    if (day !== undefined && days.indexOf(day) === -1) days.push(day);
  });
  return days.length ? days : [0, 1, 2, 3, 4, 6];
}

function kxIsWeekdayAllowed_(date, configuredDays) {
  return kxParseWorkingDays_(configuredDays).indexOf(kxTehranDayNumber_(date || new Date())) !== -1;
}

function kxIsWorkingDay_(date) {
  var target = date || new Date();
  // Friday is always blocked even if it is accidentally entered in Settings.
  if (kxTehranDayNumber_(target) === 5) return false;
  var configured = kxString_(kxGetSetting_('working_days', '0,1,2,3,4,6'));
  return kxIsWeekdayAllowed_(target, configured) && !kxIsRegisteredHoliday_(target);
}

function kxTimeToMinutes_(value) {
  var parts = kxNormalizeClockTime_(value || '00:00').split(':');
  return Math.max(0, Math.min(23, Number(parts[0]) || 0)) * 60 +
    Math.max(0, Math.min(59, Number(parts[1]) || 0));
}

function kxIsInTimeWindow_(now, scheduled, windowMinutes) {
  var current = kxTimeToMinutes_(kxTehranTime_(now));
  var target = kxTimeToMinutes_(scheduled);
  return current >= target && current <= target + Number(windowMinutes || 20);
}

function kxIsAfterThursdayCutoff_(date) {
  var target = date || new Date();
  if (kxTehranDayNumber_(target) !== 4) return false;
  var cutoff = kxGetSetting_('thursday_cutoff', '12:30');
  return kxTimeToMinutes_(kxTehranTime_(target)) > kxTimeToMinutes_(cutoff);
}

function kxAutoPublishingPolicy_(date) {
  var target = date || new Date();
  var day = kxTehranDayNumber_(target);
  if (day === 5) return { allowed: false, reason: 'friday' };
  var configured = kxString_(kxGetSetting_('working_days', '0,1,2,3,4,6'));
  if (!kxIsWeekdayAllowed_(target, configured)) return { allowed: false, reason: 'non_working_day' };
  var holiday = kxRegisteredHolidayInfo_(target);
  if (holiday) return { allowed: false, reason: 'holiday', holiday: holiday };
  if (kxIsAfterThursdayCutoff_(target)) return { allowed: false, reason: 'thursday_cutoff' };
  return { allowed: true, reason: 'working_time' };
}

function kxEndOfTehranDay_(date) {
  return new Date(kxTehranDateKey_(date || new Date()) + 'T23:59:59+03:30');
}

function kxGregorianToJalali_(gy, gm, gd) {
  var gdm = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
  var gy2 = gm > 2 ? gy + 1 : gy;
  var days = 355666 + (365 * gy) + Math.floor((gy2 + 3) / 4) -
    Math.floor((gy2 + 99) / 100) + Math.floor((gy2 + 399) / 400) + gd + gdm[gm - 1];
  var jy = -1595 + 33 * Math.floor(days / 12053);
  days %= 12053;
  jy += 4 * Math.floor(days / 1461);
  days %= 1461;
  if (days > 365) {
    jy += Math.floor((days - 1) / 365);
    days = (days - 1) % 365;
  }
  var jm;
  var jd;
  if (days < 186) {
    jm = 1 + Math.floor(days / 31);
    jd = 1 + (days % 31);
  } else {
    jm = 7 + Math.floor((days - 186) / 30);
    jd = 1 + ((days - 186) % 30);
  }
  return [jy, jm, jd];
}

function kxJalaliParts_(date) {
  var parts = kxTehranDateKey_(date || new Date()).split('-');
  return kxGregorianToJalali_(Number(parts[0]), Number(parts[1]), Number(parts[2]));
}

function kxJalaliDateKey_(date) {
  var j = kxJalaliParts_(date || new Date());
  return j[0] + '/' + ('0' + j[1]).slice(-2) + '/' + ('0' + j[2]).slice(-2);
}

function kxJalaliDate_(date) {
  return kxPersianDigits_(kxJalaliDateKey_(date || new Date()));
}

function kxJalaliLongDate_(date) {
  var months = [
    'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
    'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
  ];
  var j = kxJalaliParts_(date || new Date());
  return kxPersianDigits_(j[2]) + ' ' + months[j[1] - 1] + ' ' + kxPersianDigits_(j[0]);
}

function kxNormalizeJalaliDateKey_(value) {
  var raw = kxNormalizeDigits_(value).trim();
  var match = raw.match(/(\d{4})\s*[\/\.\-]\s*(\d{1,2})\s*[\/\.\-]\s*(\d{1,2})/);
  if (!match) {
    var compact = raw.replace(/\D/g, '');
    if (/^\d{8}$/.test(compact)) match = [compact, compact.slice(0, 4), compact.slice(4, 6), compact.slice(6, 8)];
  }
  if (!match) return '';
  var year = Number(match[1]);
  var month = Number(match[2]);
  var day = Number(match[3]);
  if (year < 1300 || year > 1600 || month < 1 || month > 12 || day < 1 || day > 31) return '';
  return year + '/' + ('0' + month).slice(-2) + '/' + ('0' + day).slice(-2);
}

function kxRegisteredHolidayInfo_(date) {
  var rows;
  try {
    rows = kxRows_(KX.SHEETS.HOLIDAYS);
  } catch (err) {
    return null; // Existing installations remain operational until step 1 is rerun.
  }
  var key = kxJalaliDateKey_(date || new Date());
  for (var i = 0; i < rows.length; i++) {
    var active = kxString_(rows[i].active).trim() === '' || kxIsTrue_(rows[i].active);
    if (active && kxNormalizeJalaliDateKey_(rows[i].jalali_date) === key) {
      return { date: key, title: kxString_(rows[i].title || 'تعطیل رسمی') };
    }
  }
  return null;
}

function kxIsRegisteredHoliday_(date) {
  return !!kxRegisteredHolidayInfo_(date || new Date());
}

function kxPersianWeekday_(date) {
  var names = ['یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه', 'شنبه'];
  return names[kxTehranDayNumber_(date || new Date())];
}

function kxJalaliCompact_(date) {
  var j = kxJalaliParts_(date || new Date());
  return String(j[0]) + ('0' + j[1]).slice(-2) + ('0' + j[2]).slice(-2);
}

function kxMakePublicRef_() {
  return kxWithLock_(function () {
    var key = KX.PROPS.DAILY_SEQUENCE_PREFIX + kxTehranDateKey_(new Date());
    var seq = Number(kxProps_().getProperty(key) || 0) + 1;
    kxProps_().setProperty(key, String(seq));
    return 'KX-' + kxJalaliCompact_(new Date()) + '-' + ('000' + seq).slice(-3);
  });
}

function kxSplitTelegramText_(text, maxLength) {
  var max = Number(maxLength || KX.MAX_TELEGRAM_TEXT);
  var lines = kxString_(text).split('\n');
  var chunks = [];
  var current = '';
  lines.forEach(function (line) {
    var candidate = current ? current + '\n' + line : line;
    if (candidate.length <= max) {
      current = candidate;
      return;
    }
    if (current) chunks.push(current);
    while (line.length > max) {
      chunks.push(line.slice(0, max));
      line = line.slice(max);
    }
    current = line;
  });
  if (current) chunks.push(current);
  return chunks.length ? chunks : [''];
}

function kxHtmlEscape_(value) {
  return kxString_(value)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}


/* ===== 02_Repository.gs ===== */
/** Spreadsheet schema, row repository and audit/event helpers. */

function kxHeadersFor_(sheetName) {
  var headers = KX.HEADERS[sheetName];
  kxAssert_(headers && headers.length, 'تعریف ستون‌های شیت پیدا نشد: ' + sheetName);
  return headers;
}

function kxEnsureSheet_(book, sheetName) {
  var headers = kxHeadersFor_(sheetName);
  var sheet = book.getSheetByName(sheetName) || book.insertSheet(sheetName);
  var existing = sheet.getLastColumn() ? sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0] : [];
  var mismatch = existing.length < headers.length || headers.some(function (h, i) { return existing[i] !== h; });
  if (mismatch) sheet.getRange(1, 1, 1, headers.length).setValues([headers]);

  sheet.setFrozenRows(1);
  sheet.getRange(1, 1, 1, headers.length)
    .setBackground('#123B55').setFontColor('#FFFFFF').setFontWeight('bold')
    .setHorizontalAlignment('center').setVerticalAlignment('middle');
  sheet.setRowHeight(1, 34);
  sheet.getRange(2, 1, Math.max(1, sheet.getMaxRows() - 1), headers.length)
    .setVerticalAlignment('middle');
  return sheet;
}

function kxInstallSchema_() {
  var active = SpreadsheetApp.getActiveSpreadsheet();
  kxProps_().setProperty(KX.PROPS.SPREADSHEET_ID, active.getId());
  Object.keys(KX.HEADERS).forEach(function (name) { kxEnsureSheet_(active, name); });
  kxApplySheetWidths_(active);
  kxSeedDefaults_();
  return { ok: true, spreadsheet_id: active.getId() };
}

function kxApplySheetWidths_(book) {
  var widths = {
    Settings: [190, 260, 420, 170],
    Suppliers: [140, 220, 120, 150, 180, 260, 170, 90, 170, 170, 260],
    Inbox: [180, 150, 170, 150, 180, 160, 220, 120, 160, 220, 170, 150, 150, 500, 160, 500, 90, 150, 170, 180, 260, 160, 260, 170],
    Inventory: [180, 180, 150, 170, 170, 220, 320, 110, 110, 110, 110, 90, 180, 320, 110, 170, 170, 110, 180, 150, 170, 260, 170],
    Catalog: [130, 170, 220, 380, 110, 90, 170],
    Templates: [150, 220, 560, 90, 110, 170, 320, 170],
    Holidays: [150, 260, 90, 360, 170],
    Posts: [180, 180, 130, 200, 170, 170, 180, 260, 180, 120, 560, 260, 170, 170],
    Events: [220, 170, 110, 320, 260, 170],
    AuditLog: [180, 170, 170, 160, 140, 180, 420],
    Dictionaries: [140, 140, 280, 280, 100, 90, 300]
  };
  Object.keys(widths).forEach(function (name) {
    var sheet = book.getSheetByName(name);
    if (!sheet) return;
    widths[name].forEach(function (width, i) { sheet.setColumnWidth(i + 1, width); });
    sheet.getDataRange().setWrap(true);
  });
}

function kxSheetHeaders_(sheet) {
  return sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0].map(kxString_);
}

/**
 * Escape formula-like strings without changing numbers, booleans, or Dates.
 */
function kxSafeSheetValue_(value) {
  if (value === undefined || value === null) return '';
  if (value instanceof Date || typeof value === 'number' || typeof value === 'boolean') return value;
  if (typeof value === 'object') value = kxJson_(value);
  var text = kxString_(value);
  return /^[\s]*[=+\-@]/.test(text) ? "'" + text : text;
}

function kxObjectToRow_(headers, object) {
  return headers.map(function (header) {
    var value = Object.prototype.hasOwnProperty.call(object, header) ? object[header] : '';
    return kxSafeSheetValue_(value);
  });
}

function kxAppend_(sheetName, object) {
  kxAppendMany_(sheetName, [object]);
  return object;
}

function kxAppendMany_(sheetName, objects) {
  objects = objects || [];
  if (!objects.length) return objects;
  var sheet = kxSheet_(sheetName);
  var headers = kxSheetHeaders_(sheet);
  var rows = objects.map(function (object) { return kxObjectToRow_(headers, object); });
  var targetRow = sheet.getLastRow() + 1;
  var requiredLastRow = targetRow + rows.length - 1;
  if (requiredLastRow > sheet.getMaxRows()) {
    sheet.insertRowsAfter(sheet.getMaxRows(), Math.max(100, requiredLastRow - sheet.getMaxRows()));
  }
  sheet.getRange(targetRow, 1, rows.length, headers.length).setValues(rows);
  return objects;
}

function kxRows_(sheetName) {
  var sheet = kxSheet_(sheetName);
  var lastRow = sheet.getLastRow();
  var lastCol = sheet.getLastColumn();
  if (lastRow < 2 || lastCol < 1) return [];
  var headers = kxSheetHeaders_(sheet);
  return sheet.getRange(2, 1, lastRow - 1, lastCol).getValues().map(function (values, index) {
    var object = { _row: index + 2 };
    headers.forEach(function (header, i) { object[header] = values[i]; });
    return object;
  });
}

function kxFind_(sheetName, key, value) {
  var expected = kxString_(value);
  var rows = kxRows_(sheetName);
  for (var i = 0; i < rows.length; i++) {
    if (kxString_(rows[i][key]) === expected) return rows[i];
  }
  return null;
}

function kxFilter_(sheetName, predicate) {
  return kxRows_(sheetName).filter(predicate);
}

function kxUpdateRow_(sheetName, rowNumber, patch) {
  var sheet = kxSheet_(sheetName);
  var headers = kxSheetHeaders_(sheet);
  var values = sheet.getRange(rowNumber, 1, 1, headers.length).getValues()[0];
  headers.forEach(function (header, i) {
    if (Object.prototype.hasOwnProperty.call(patch, header)) {
      var value = patch[header];
      values[i] = kxSafeSheetValue_(value);
    }
  });
  sheet.getRange(rowNumber, 1, 1, headers.length).setValues([values]);
  return patch;
}

function kxUpdateById_(sheetName, idField, idValue, patch) {
  var row = kxFind_(sheetName, idField, idValue);
  kxAssert_(row, 'رکورد پیدا نشد: ' + idValue);
  patch.updated_at = kxNowIso_();
  kxUpdateRow_(sheetName, row._row, patch);
  return Object.assign(row, patch);
}

function kxGetSetting_(key, fallback) {
  var row = kxFind_(KX.SHEETS.SETTINGS, 'key', key);
  return row && kxString_(row.value) !== '' ? row.value : fallback;
}

function kxSetSetting_(key, value, description) {
  var row = kxFind_(KX.SHEETS.SETTINGS, 'key', key);
  var record = { key: key, value: value, description: description || (row ? row.description : ''), updated_at: kxNowIso_() };
  if (row) kxUpdateRow_(KX.SHEETS.SETTINGS, row._row, record);
  else kxAppend_(KX.SHEETS.SETTINGS, record);
  return value;
}

function kxSeedDefaults_() {
  var defaults = [
    ['destination_channel', '@kavexir', 'کانال عمومی مقصد'],
    ['inbox_chat_id', '', 'با دستور /bind_inbox در گروه خصوصی ثبت می‌شود'],
    ['inbox_chat_title', '', 'نام گروه میانی'],
    ['owner_telegram_user_id', '', 'شناسه عددی مدیر ربات'],
    ['timezone', 'Asia/Tehran', 'منطقه زمانی'],
    ['working_days', '0,1,2,3,4,6', 'یکشنبه تا پنجشنبه و شنبه؛ جمعه=5 حذف شده'],
    ['morning_time', '08:00', 'زمان پیام صبحگاهی و توان تأمین'],
    ['inventory_time', '09:00', 'زمان گزارش موجودی روز'],
    ['thursday_cutoff', '12:30', 'پس از این ساعت در پنجشنبه پیام خودکار منتشر نمی‌شود'],
    ['phone', '09132751779', 'شماره تماس عمومی کاوکس'],
    ['website', 'https://kavex.ir/', 'وب‌سایت عمومی کاوکس'],
    ['default_validity', 'end_of_day', 'اعتبار پیش‌فرض موجودی'],
    ['show_price', 'false', 'نمایش قیمت در کانال؛ در این پروژه false'],
    ['show_supplier', 'false', 'نمایش نام تأمین‌کننده؛ در این پروژه false'],
    ['post_empty_inventory', 'false', 'اگر موجودی ثبت نشده باشد پست خالی منتشر نشود'],
    ['parser_mode', 'rules_v3', 'نسخه قواعد تشخیص کالا، رنگ و واحدها']
  ];
  defaults.forEach(function (item) {
    if (!kxFind_(KX.SHEETS.SETTINGS, 'key', item[0])) kxSetSetting_(item[0], item[1], item[2]);
  });

  var templates = [
    {
      template_key: 'MORNING', title: 'سلام صبحگاهی با تاریخ شمسی',
      body: 'بسم الله الرحمن الرحیم\n\nسلام صبح بخیر 🌹☀️\n\nامروز {{weekday}} {{jalali_long_date}}',
      enabled: true, send_time: '08:00', working_days: '0,1,2,3,4,6',
      notes: 'تاریخ و نام روز به‌صورت شمسی و خودکار جایگزین می‌شوند.', updated_at: kxNowIso_()
    },
    {
      template_key: 'INVENTORY_FOOTER', title: 'پاورقی موجودی',
      body: '━━━━━━━━━━━━━━━━━━━━━\n📌  {{location}}\n━━━━━━━━━━━━━━━━━━━━━\n☎️ {{phone}}\n\n🌐 {{category_url}}\n━━━━━━━━━━━━━━━━━━━━━',
      enabled: true, send_time: '09:00', working_days: '0,1,2,3,4,6',
      notes: 'قالب نسخه ۱.۰.۵؛ قیمت، نام تأمین‌کننده و کد داخلی فقط در شیت خصوصی می‌ماند.', updated_at: kxNowIso_()
    },
    {
      template_key: 'DAILY_SAMPLE', title: 'نمونه پیام تکراری — ابتدا متن را تغییر دهید',
      body: 'متن پیام تکراری را اینجا بنویسید.\n\n☎️ {{phone}}\n🌐 {{website}}',
      enabled: false, send_time: '10:00',
      working_days: 'شنبه,یکشنبه,دوشنبه,سه‌شنبه,چهارشنبه,پنجشنبه',
      notes: 'برای فعال‌سازی، متن و ساعت را تنظیم و enabled را TRUE کنید.', updated_at: kxNowIso_()
    }
  ];
  templates.forEach(function (record) {
    if (!kxFind_(KX.SHEETS.TEMPLATES, 'template_key', record.template_key)) kxAppend_(KX.SHEETS.TEMPLATES, record);
  });

  // One-time migration: update installations made before the requested
  // Jalali greeting, then preserve any later user edits on repeated installs.
  if (kxString_(kxGetSetting_('morning_template_version', '')) !== '2') {
    var morning = kxFind_(KX.SHEETS.TEMPLATES, 'template_key', 'MORNING');
    if (morning) {
      kxUpdateRow_(KX.SHEETS.TEMPLATES, morning._row, {
        title: 'سلام صبحگاهی با تاریخ شمسی',
        body: 'بسم الله الرحمن الرحیم\n\nسلام صبح بخیر 🌹☀️\n\nامروز {{weekday}} {{jalali_long_date}}',
        enabled: true,
        send_time: '08:00',
        working_days: '0,1,2,3,4,6',
        notes: 'تاریخ و نام روز به‌صورت شمسی و خودکار جایگزین می‌شوند.',
        updated_at: kxNowIso_()
      });
    }
    kxSetSetting_('morning_template_version', '2', 'نسخه قالب پیام صبحگاهی؛ ویرایش‌های بعدی کاربر حفظ می‌شوند');
  }

  var catalog = [
    ['CAT-001', 'ورق', 'ورق گرم و سیاه', 'ST37، ST52، رول و شیت، برش در ابعاد سفارشی', 10, true],
    ['CAT-002', 'ورق', 'ورق روغنی، گالوانیزه و رنگی', 'رول و شیت در ضخامت‌ها و عرض‌های متنوع', 20, true],
    ['CAT-003', 'ورق', 'ورق استیل', 'گریدهای 304 و 410، مات و خش‌دار', 30, true],
    ['CAT-004', 'مقاطع', 'میلگرد', 'سایزها و کارخانه‌های مختلف، بارگیری کارخانه و انبار', 40, true],
    ['CAT-005', 'مقاطع', 'تیرآهن', 'ذوب‌آهن و کارخانه‌های متفرقه در سایزهای مصرفی', 50, true],
    ['CAT-006', 'پروفیل', 'پروفیل صنعتی و ساختمانی', 'ST37 و ST52، ابعاد و ضخامت‌های متنوع', 60, true],
    ['CAT-007', 'پروفیل', 'پروفیل Z و مقاطع سفارشی', 'تولید Z، نبشی، ناودانی، ابرو و کلاهی', 70, true],
    ['CAT-008', 'مقاطع', 'تسمه فولادی', 'تسمه نوردی ST37 در عرض‌ها و ضخامت‌های متنوع', 80, true]
  ];
  catalog.forEach(function (row) {
    if (!kxFind_(KX.SHEETS.CATALOG, 'item_id', row[0])) {
      kxAppend_(KX.SHEETS.CATALOG, {
        item_id: row[0], category: row[1], title: row[2], specifications: row[3],
        display_order: row[4], active: row[5], updated_at: kxNowIso_()
      });
    }
  });
}

function kxIsTrue_(value) {
  return value === true || ['true', '1', 'yes', 'بله'].indexOf(kxString_(value).toLowerCase()) !== -1;
}

function kxAudit_(actor, action, entityType, entityId, details) {
  return kxAppend_(KX.SHEETS.AUDIT, {
    log_id: kxShortId_('LOG'), created_at: kxNowIso_(), actor: actor,
    action: action, entity_type: entityType, entity_id: entityId,
    details: typeof details === 'string' ? details : kxJson_(details || {})
  });
}

function kxReserveEvent_(eventKey) {
  return kxWithLock_(function () {
    if (kxFind_(KX.SHEETS.EVENTS, 'event_key', eventKey)) return false;
    kxAppend_(KX.SHEETS.EVENTS, {
      event_key: eventKey, received_at: kxNowIso_(), status: 'processing',
      result: '', error_message: '', updated_at: kxNowIso_()
    });
    return true;
  });
}

function kxFinishEvent_(eventKey, result) {
  var row = kxFind_(KX.SHEETS.EVENTS, 'event_key', eventKey);
  if (row) kxUpdateRow_(KX.SHEETS.EVENTS, row._row, {
    status: 'completed', result: kxJson_(result || { ok: true }), updated_at: kxNowIso_()
  });
}

function kxFailEvent_(eventKey, error) {
  var row = kxFind_(KX.SHEETS.EVENTS, 'event_key', eventKey);
  if (row) kxUpdateRow_(KX.SHEETS.EVENTS, row._row, {
    status: 'failed', error_message: kxString_(error && error.message ? error.message : error),
    updated_at: kxNowIso_()
  });
}


/* ===== 03_Parser.gs ===== */
/** Rule-based parser for steel inventory messages. */

function kxExtractSource_(message, rawText) {
  var origin = message && message.forward_origin ? message.forward_origin : null;
  var source = {
    source_type: 'manual', chat_id: '', title: 'ثبت دستی کاوکس',
    username: '', message_id: '', hidden: false
  };

  if (origin) {
    source.source_type = kxString_(origin.type || 'forward');
    if (origin.chat) {
      source.chat_id = kxString_(origin.chat.id);
      source.title = kxString_(origin.chat.title || origin.chat.first_name || 'منبع تلگرام');
      source.username = kxString_(origin.chat.username);
    } else if (origin.sender_chat) {
      source.chat_id = kxString_(origin.sender_chat.id);
      source.title = kxString_(origin.sender_chat.title || 'منبع تلگرام');
      source.username = kxString_(origin.sender_chat.username);
    } else if (origin.sender_user) {
      source.chat_id = kxString_(origin.sender_user.id);
      source.title = [origin.sender_user.first_name, origin.sender_user.last_name].filter(Boolean).join(' ') || 'کاربر تلگرام';
      source.username = kxString_(origin.sender_user.username);
    } else if (origin.sender_user_name) {
      source.title = kxString_(origin.sender_user_name);
      source.hidden = true;
    }
    source.message_id = kxString_(origin.message_id);
    return source;
  }

  // Compatibility with older Telegram message fields.
  if (message && message.forward_from_chat) {
    source.source_type = 'legacy_chat';
    source.chat_id = kxString_(message.forward_from_chat.id);
    source.title = kxString_(message.forward_from_chat.title || 'منبع تلگرام');
    source.username = kxString_(message.forward_from_chat.username);
    source.message_id = kxString_(message.forward_from_message_id);
    return source;
  }
  if (message && message.forward_from) {
    source.source_type = 'legacy_user';
    source.chat_id = kxString_(message.forward_from.id);
    source.title = [message.forward_from.first_name, message.forward_from.last_name].filter(Boolean).join(' ') || 'کاربر تلگرام';
    source.username = kxString_(message.forward_from.username);
    return source;
  }
  if (message && message.forward_sender_name) {
    source.source_type = 'hidden_user';
    source.title = kxString_(message.forward_sender_name);
    source.hidden = true;
    return source;
  }

  // Fallback: find a source handle in the original text. It stays private.
  var normalized = kxNormalizeText_(rawText);
  var handles = [];
  var match;
  var urlRegex = /(?:t\.me|telegram\.me)\/([A-Za-z0-9_]{4,})/gi;
  while ((match = urlRegex.exec(normalized)) !== null) handles.push(match[1]);
  var handleRegex = /(?:^|\s)@([A-Za-z0-9_]{4,})/g;
  while ((match = handleRegex.exec(normalized)) !== null) handles.push(match[1]);
  handles = kxUnique_(handles).filter(function (h) { return h.toLowerCase() !== 'kavexir'; });
  if (handles.length) {
    source.source_type = 'text_handle';
    source.username = handles[handles.length - 1];
    source.title = '@' + source.username;
  }
  return source;
}

function kxUpsertSupplier_(source) {
  var rows = kxRows_(KX.SHEETS.SUPPLIERS);
  var chatId = kxString_(source.chat_id);
  var username = kxString_(source.username).replace(/^@/, '').toLowerCase();
  var title = kxNormalizeText_(source.title);
  var existing = null;

  rows.some(function (row) {
    var sameChat = chatId && kxString_(row.telegram_chat_id) === chatId;
    var sameUsername = username && kxString_(row.telegram_username).replace(/^@/, '').toLowerCase() === username;
    var sameTitle = title && kxNormalizeText_(row.display_name).toLowerCase() === title.toLowerCase();
    if (sameChat || sameUsername || sameTitle) { existing = row; return true; }
    return false;
  });

  var now = kxNowIso_();
  if (existing) {
    kxUpdateRow_(KX.SHEETS.SUPPLIERS, existing._row, {
      display_name: title || existing.display_name,
      source_type: source.source_type || existing.source_type,
      telegram_chat_id: chatId || existing.telegram_chat_id,
      telegram_username: username || existing.telegram_username,
      active: true, updated_at: now
    });
    return existing.supplier_id;
  }

  var id = kxShortId_('SUP');
  kxAppend_(KX.SHEETS.SUPPLIERS, {
    supplier_id: id, display_name: title || 'منبع نامشخص',
    source_type: source.source_type || 'unknown', telegram_chat_id: chatId,
    telegram_username: username, aliases: '', default_location: '', active: true,
    created_at: now, updated_at: now, private_notes: source.hidden ? 'نام مبدأ توسط تلگرام مخفی شده است.' : ''
  });
  return id;
}

function kxCategoryFromLine_(line, fallback) {
  var text = kxNormalizeText_(line).toLowerCase();
  // Product-specific words must win over the generic word «ورق». In
  // particular, strip/flat-bar lists often contain ST37 and dimensions that
  // otherwise look exactly like sheet rows.
  if (/تسمه/.test(text)) return 'تسمه';
  if (/گالوانیزه/.test(text) && /رنگی/.test(text)) return 'ورق گالوانیزه رنگی';
  if (/میلگرد|آجدار|(?:^|\s|#)گرد(?:\s|$|a\s*[1234]|\d)/i.test(text)) return 'میلگرد';
  if ((!fallback || fallback === 'آهن‌آلات') &&
      /(?:^|[\s|_-])a\s*[234](?:$|[\s|_-])/i.test(text)) return 'میلگرد';
  if (/رنگی/.test(text)) return 'ورق رنگی';
  if (/گالوانیزه/.test(text)) return 'ورق گالوانیزه';
  if (/استیل/.test(text)) return 'ورق استیل';
  if (/اسید\s*شویی|اسیدشویی/.test(text)) return 'ورق اسیدشویی';
  if (/روغنی/.test(text)) return 'ورق روغنی';
  if (/کویل|رول|ورق/.test(text)) return 'ورق گرم و فولادی';
  if (/تیر\s*آهن|تیراهن/.test(text)) return 'تیرآهن';
  if (/پروفیل\s*(?:زد|z)|^زد\s/i.test(text)) return 'پروفیل Z';
  if (/پروفیل\s*صنعتی/.test(text)) return 'پروفیل صنعتی';
  if (/پروفیل|نبشی|ناودانی|کلاهی|ابرو/.test(text)) return 'پروفیل و مقاطع';
  if ((!fallback || fallback === 'آهن‌آلات') &&
      /^(?:st(?:w)?\s*-?\s*\d+|w\s*-?\s*\d+|304|410)$/i.test(text)) {
    return 'ورق گرم و فولادی';
  }
  // Many supplier posts contain only dimensions + steel grade, for example
  // "8_1200 st33". Treat these as sheet/coil rows unless a stronger heading
  // (such as industrial profile) is already active.
  if ((!fallback || fallback === 'آهن‌آلات') &&
      /\d+(?:[./]\d+)?\s*[*x×_]\s*\d+/i.test(text) &&
      /\b(?:st|stw|w)\s*-?\s*\d+\b/i.test(text)) return 'ورق گرم و فولادی';
  if ((!fallback || fallback === 'آهن‌آلات') &&
      /\d+(?:[./]\d+)?\s*میل/i.test(text) &&
      /\d+(?:[./]\d+)?\s*[*x×_]\s*\d+/i.test(text)) return 'ورق گرم و فولادی';
  return fallback || 'آهن‌آلات';
}

function kxCategoryEmoji_(category) {
  if (category === 'میلگرد') return '🔩';
  if (category === 'تیرآهن') return '🏗️';
  if (category === 'تسمه') return '➖';
  if (/پروفیل/.test(category)) return '▰';
  if (/استیل/.test(category)) return '✨';
  if (/رنگی|گالوانیزه|روغنی|اسیدشویی/.test(category)) return '🔷';
  if (/ورق/.test(category)) return '◼️';
  return '📦';
}

function kxHasProductKeyword_(line) {
  return /ورق|کویل|رول|تسمه|میلگرد|آجدار|(?:^|\s|#)گرد(?:\s|$)|تیر\s*آهن|تیراهن|پروفیل|نبشی|ناودانی|زد\s*\d|رنگی|گالوانیزه|روغنی|اسید\s*شویی|استیل/i.test(line);
}

function kxContainsSpecification_(line) {
  var text = kxNormalizeText_(line);
  return /\d/.test(text) && (
    kxHasProductKeyword_(text) ||
    /\d+(?:[./]\d+)?\s*[*x×_]\s*\d+/i.test(text) ||
    /ضخامت|عرض|طول|میل(?:\s|$|[()،,:])|\b(?:st|stw|w)\s*-?\s*\d+|\ba\s*[1234]\b|\b304\b|\b410\b|قطعات|سایز/i.test(text)
  );
}

function kxStripLinks_(line) {
  return kxString_(line)
    .replace(/\(?https?:\/\/[^\s)]+\)?/gi, ' ')
    .replace(/\(?www\.[^\s)]+\)?/gi, ' ')
    .replace(/(?:^|\s)@[A-Za-z0-9_]{4,}/g, ' ')
    .replace(/(?:telegram\.me|t\.me|rubika\.ir|eitaa\.com)\/[^\s)]+/gi, ' ');
}

function kxStripPrice_(line) {
  var text = kxString_(line);
  // Price arrows and call markers are unambiguous and can be removed safely.
  // Require meaningful text before the arrow so a decorative leading arrow
  // such as "⬅️ #پروفیل_صنعتی" is not mistaken for a price marker.
  text = text.replace(/(.+?)\s*(?:🔴\s*)?(?:⬅️?|➡️?|→|➜|=>)+[\s\S]*$/g, '$1');
  text = text.replace(/\s*(?:❇️?\s*)?(?:call|قیمت\s*تماس|تماس|📞)\s*$/gi, '');
  // Supplier lists often append prices without a currency, e.g.
  // "قیمت: 1.230.000", "نرخ ۱,۲۳۰,۰۰۰" or "فی 1230000".
  text = text.replace(
    /\s*(?:💰\s*)?(?:قیمت|نرخ|فی)\s*[:：=\-]?\s*(?:[\d۰-۹٠-٩][\d۰-۹٠-٩\s,،.\/٬٫_-]*|توافقی|(?:call|تماس))(?:\s*(?:تومان|ریال))?\s*$/gi,
    ''
  );
  if (/تومان|ریال/.test(text)) {
    text = text.replace(/\s*[:：]?\s*[\d\s,./٬٫]+\s*(?:تومان|ریال)[\s\S]*$/i, '');
  }
  return text;
}

function kxIsNoiseLine_(line) {
  var text = kxNormalizeText_(line).toLowerCase();
  if (!text) return true;
  if (/^[\-*_=–—.\s]+$/.test(text)) return true;
  if (/^(?:به نام خدا|بسم الله|﷽)$/.test(text)) return true;
  if (/^(?:لیست اعلامی|لیست قیمت|اعلام قیمت|قیمت میلگرد|قیمت تیرآهن|قیمت تیراهن)$/.test(text.replace(/[#📢🔵🔴]/g, '').trim())) return true;
  if (/با\s+گواهی|راز موفقیت|نوسان بازار|کامل ترین سبد|کامل‌ترین سبد|اطلاع از سایز|کارشناسان فروش|برای استعلام|برای تایید قیمت|برای تأیید قیمت|تماس حاصل|نوع تسویه|پول پیش|ارزش افزوده|هزینه پانچ|لینک کانال|روبیکا|ایتا|تلگرام|وبسایت|وب‌سایت|شماره تماس|همراه فروش|داخلی\s*[:：]?\s*\d|دفتر مرکزی|استخدام/.test(text)) return true;
  if (/^#?(?:ورق|میلگرد|تیرآهن|تیراهن|کویل)_?[آ-یa-z0-9_]*$/i.test(text) && text.length < 40) return false;
  if (/بازرگانی|شرکت توسعه تجارت|گروه صنعتی|آهن و فولاد احسان|اهن و فولاد احسان/.test(text) && !/فولاد مبارکه|ذوب آهن/.test(text)) return true;
  if (/^(?:📆|🏷)?\s*(?:شنبه|یکشنبه|دوشنبه|سه\s*شنبه|چهارشنبه|پنجشنبه|جمعه)\b/.test(text)) return true;
  if (/^⏱?\s*تاریخ\s*:/.test(text)) return true;
  if (/^(?:☎️?|📞|📱|🌐|🆔)/.test(text)) return true;
  if (/^(?:0|98)?9\d{9}$/.test(text.replace(/\D/g, ''))) return true;
  if (/^0\d[\d\-\s]{6,}$/.test(text)) return true;
  return false;
}

function kxCleanInventoryLine_(rawLine) {
  var line = kxNormalizeText_(rawLine)
    .replace(/#[\u200c\s]*/g, '')
    .replace(/([آ-یA-Za-z])_+(?=[آ-یA-Za-z])/g, '$1 ')
    .replace(/(?:👑|⭐️?|💋|🪄|🚩|🔥|🌎|🌼|🌳|🍂|😔|🔠|🅰️?)+/gu, ' ');
  line = kxStripLinks_(line);
  line = kxStripPrice_(line);
  line = line
    .replace(/\((?:\s*)\)/g, ' ')
    .replace(/[|]\s*-\s*$/g, '')
    .replace(/\s*[:：]\s*$/g, '')
    .replace(/ {2,}/g, ' ')
    .trim();
  line = kxCompactLine_(line);
  if (kxIsNoiseLine_(line)) return '';
  return line;
}

function kxExtractLocation_(line) {
  var text = kxNormalizeText_(line);
  var match = text.match(/(?:محل\s*بارگیری\s*[:：]?\s*)?(?:بارگیری\s*)?(انبار\s+[آ-یA-Za-z‌\s]+|کارخانه)/i);
  if (!match) return '';
  return kxCompactLine_(match[1]).replace(/\s+موجود.*$/, '').trim();
}

function kxKnownHeading_(line) {
  var text = kxNormalizeText_(line);
  if (text.length > 90) return false;
  return kxHasProductKeyword_(text) ||
    /فولاد مبارکه|ذوب آهن|ذوب‌آهن|ابرکوه|نیشابور|کرمانشاه|یزد|فایکو|آریان|آرین|خیام|پارسیان|اطلس|ماهان|هفت الماس|متفرقه|یکسر آرایش|دوسر آرایش/i.test(text) ||
    /^(?:st(?:w)?\s*-?\s*\d+|w\s*-?\s*\d+|a\s*36|304|410)$/i.test(text);
}

function kxIsStandaloneGrade_(line) {
  return /^(?:st(?:w)?\s*-?\s*\d+|w\s*-?\s*\d+|a\s*[1234]|304|410)$/i
    .test(kxNormalizeText_(line));
}

function kxIsStandaloneSheetHeading_(line, currentCategory) {
  var text = kxNormalizeText_(line);
  if (/^a\s*36$/i.test(text)) {
    return !currentCategory || currentCategory === 'آهن‌آلات' || /ورق/.test(currentCategory);
  }
  if (kxIsStandaloneGrade_(text)) {
    return !currentCategory || currentCategory === 'آهن‌آلات' || /ورق/.test(currentCategory);
  }
  return /^(?:ورق|رول|کویل|استیل)(?:\s|$)/i.test(text) &&
    /\b(?:st(?:w)?\s*-?\s*\d+|w\s*-?\s*\d+|a\s*36|304|410)\b/i.test(text) &&
    !/ضخامت|عرض|طول|\d+(?:[./]\d+)?\s*میل|[*x×_]/i.test(text);
}

function kxCleanHeading_(line, category) {
  var text = kxCleanInventoryLine_(line)
    .replace(/\bموجود(?:ی)?\b/g, ' ')
    .replace(/(?:در\s+)?انبار\s+[آ-ی‌\s]+$/g, ' ')
    .replace(/ {2,}/g, ' ')
    .trim();
  if (!text) return category;
  return kxTechnicalPersianDigits_(text);
}

function kxNormalizeSpecForPublic_(line) {
  var text = kxCleanInventoryLine_(line);
  text = text.replace(/(\d)\s*[_*x×]\s*(?=\d)/gi, '$1 × ');
  text = text.replace(/\s+_/g, ' ').replace(/_\s+/g, ' ');
  return kxTechnicalPersianDigits_(text).trim();
}

function kxExtractGrade_(line) {
  var match = kxNormalizeText_(line).match(/\b(?:st(?:w)?\s*-?\s*\d+|w\s*-?\s*\d+|a\s*(?:36|[1234])|304|410)\b/i);
  return match ? match[0].replace(/\s+/g, '').toUpperCase() : '';
}

function kxIsSheetCategory_(category) {
  return /ورق/.test(kxString_(category));
}

function kxIsThinSheetCategory_(category) {
  return /رنگی|گالوانیزه|روغنی|استیل/.test(kxString_(category));
}

/**
 * Normalize the common Iranian sheet-width notations to millimetres.
 * Accepted examples: 1, 100, 1000, 1.25, 125, 1250, 1.5, 150, 1500.
 * A sheet width above 2000 mm is rejected instead of being rendered as an
 * impossible value such as "15 متر".
 */
function kxNormalizeSheetWidthMm_(value) {
  var normalized = kxFormatDecimalAscii_(value);
  if (!/^\d+(?:\.\d+)?$/.test(normalized)) return '';
  var number = Number(normalized);
  if (!isFinite(number) || number <= 0) return '';

  if (number >= 0.95 && number <= 2) number = number * 1000;
  else if (number >= 95 && number <= 200) number = number * 10;
  else if (number > 200 && number <= 2000) number = number;
  else return '';

  if (number > 2000) return '';
  return String(Number(number.toFixed(3)));
}

/** Strip/flat-bar widths are conventionally written in centimetres. */
function kxNormalizeStripWidthCm_(value, line) {
  var normalized = kxFormatDecimalAscii_(value);
  if (!/^\d+(?:\.\d+)?$/.test(normalized)) return normalized;
  var number = Number(normalized);
  var text = kxNormalizeText_(line);
  var widthMatch = text.match(/عرض\s*[\d./]+\s*(میلی\s*متر|میلیمتر|میل|سانتی\s*متر|سانت|متر)?/i);
  var unit = widthMatch ? kxString_(widthMatch[1]).replace(/\s+/g, '') : '';

  if (/^متر$/.test(unit)) number = number * 100;
  else if (/^میلی?متر$|^میلیمتر$|^میل$/.test(unit)) number = number / 10;
  else if (number > 50) number = number / 10; // bare 150 means 150 mm = 15 cm

  return String(Number(number.toFixed(3)));
}

function kxNormalizeSheetThickness_(value, category, canonicalWidth) {
  var normalized = kxFormatDecimalAscii_(value);
  if (!/^\d+(?:\.\d+)?$/.test(normalized)) return normalized;
  var number = Number(normalized);
  // In thin-sheet lists, 30/50/125 are market shorthand for
  // 0.30/0.50/1.25 mm when paired with a valid sheet width.
  if (canonicalWidth && kxIsThinSheetCategory_(category) &&
      /^\d{2,3}$/.test(normalized) && number >= 20 && number <= 300) {
    number = number / 100;
  }
  return String(Number(number.toFixed(3)));
}

/**
 * Infer a three-part sheet dimension regardless of the two common orders:
 *   thickness × width × length  (0.5 × 1250 × 2500)
 *   length × width × thickness  (6000 × 1500 × 4)
 * The canonical sheet width is normally the middle value. A value above
 * 2000 mm is always length, never thickness.
 */
function kxInferSheetTriple_(first, second, third) {
  var parts = [first, second, third];
  var widths = parts.map(kxNormalizeSheetWidthMm_);
  var widthIndex = widths[1] ? 1 : (widths[0] ? 0 : (widths[2] ? 2 : -1));
  if (widthIndex < 0) return null;

  var remaining = [0, 1, 2].filter(function (index) { return index !== widthIndex; });
  var numbers = remaining.map(function (index) {
    return Number(kxFormatDecimalAscii_(parts[index]));
  });
  var lengthPosition = -1;

  if (numbers[0] > 2000 && numbers[1] <= 2000) lengthPosition = 0;
  else if (numbers[1] > 2000 && numbers[0] <= 2000) lengthPosition = 1;
  else if (numbers[0] > 200 && numbers[1] <= 200) lengthPosition = 0;
  else if (numbers[1] > 200 && numbers[0] <= 200) lengthPosition = 1;
  else if (widthIndex === 0) lengthPosition = 0;
  else lengthPosition = 1;

  var lengthIndex = remaining[lengthPosition];
  var thicknessIndex = remaining[lengthPosition === 0 ? 1 : 0];
  return {
    thickness: parts[thicknessIndex],
    width: parts[widthIndex],
    length: parts[lengthIndex]
  };
}

function kxExtractDimensions_(line, category) {
  var text = kxNormalizeText_(line);
  var thickness = '';
  var width = '';
  var length = '';
  var explicitThickness = false;
  var thicknessFromMill = false;
  var match = text.match(/ضخامت\s*([\d./]+)/i);
  if (match) { thickness = match[1]; explicitThickness = true; }
  if (!thickness) {
    match = text.match(/([\d./]+)\s*میل(?:\s|$|[()،,:])/i);
    if (match) {
      var beforeMill = text.slice(0, match.index);
      if (!/عرض\s*$/.test(beforeMill)) {
        thickness = match[1];
        thicknessFromMill = true;
      }
    }
  }
  match = text.match(/عرض\s*([\d./]+)/i);
  if (match) width = match[1];
  match = text.match(/طول\s*([\d./]+(?:\s*(?:و|،|,)\s*[\d./]+)?)/i);
  if (match) length = match[1];
  // Steel-market shorthand: "50 بلند" means 0.50 mm × 1250 mm;
  // "50 کوتاه" means the same thickness × 1000 mm.
  var marketSheet = text.match(/(?:^|\s)(\d{2,3})\s*(بلند|کوتاه)(?:\s|$)/i);
  if (marketSheet && kxIsSheetCategory_(category)) {
    if (!thickness) thickness = String(Number(marketSheet[1]) / 100);
    if (!width) width = marketSheet[2] === 'بلند' ? '1250' : '1000';
  }
  if (kxIsSheetCategory_(category) && !width) {
    if (/(?:^|\s)بلند(?:\s|$)/.test(text)) width = '1250';
    else if (/(?:^|\s)کوتاه(?:\s|$)/.test(text)) width = '1000';

    var meterWidth = text.match(/(?:^|\s)(?:عرض\s*)?([12](?:[./]\d+)?)\s*متر(?:\s|$)/i);
    if (!width && meterWidth) width = meterWidth[1];

    var standaloneWidth = text.match(/^\s*(?:عرض\s*)?([\d./]+)\s*(?:میلی\s*متر|میلیمتر|میل)?\s*$/i);
    if (!width && standaloneWidth && kxNormalizeSheetWidthMm_(standaloneWidth[1])) {
      width = standaloneWidth[1];
    }
  }
  var dimensions = text.match(/([\d./]+)\s*[*x×_]\s*([\d./]+)(?:\s*[*x×_]\s*([\d./]+))?/i);
  if (dimensions) {
    if (!thickness) {
      if (kxIsSheetCategory_(category) && dimensions[3]) {
        var inferredTriple = kxInferSheetTriple_(dimensions[1], dimensions[2], dimensions[3]);
        if (inferredTriple) {
          thickness = inferredTriple.thickness;
          if (!width) width = inferredTriple.width;
          if (!length) length = inferredTriple.length;
        }
      }
      if (!thickness && kxIsSheetCategory_(category)) {
        var firstAsWidth = kxNormalizeSheetWidthMm_(dimensions[1]);
        var secondAsWidth = kxNormalizeSheetWidthMm_(dimensions[2]);
        if (firstAsWidth && !secondAsWidth) {
          thickness = dimensions[2];
          if (!width) width = dimensions[1];
        } else {
          thickness = dimensions[1];
          if (!width) width = dimensions[2];
        }
      } else if (!thickness) {
        thickness = dimensions[1];
        if (!width) width = dimensions[2];
      }
      if (!length && dimensions[3]) length = dimensions[3];
    } else if (dimensions[3]) {
      if (kxNormalizeDigits_(dimensions[1]) === kxNormalizeDigits_(thickness)) {
        if (!width) width = dimensions[2];
        if (!length) length = dimensions[3];
      } else {
        if (!width) width = dimensions[2];
        if (!length) length = dimensions[1];
      }
    } else {
      var first = Number(kxNormalizeDigits_(dimensions[1]).replace('/', '.'));
      var second = Number(kxNormalizeDigits_(dimensions[2]).replace('/', '.'));
      if (!width) width = first > second ? dimensions[2] : dimensions[1];
      if (!length) length = first > second ? dimensions[1] : dimensions[2];
    }
  }

  if (category === 'تسمه') {
    if (width) width = kxNormalizeStripWidthCm_(width, text);
    return { thickness: kxFormatDecimalAscii_(thickness), width: width, length: length, width_unit: 'cm' };
  }

  if (kxIsSheetCategory_(category)) {
    // A lone "1250 میل" or "125 میل" is a width, not an impossible sheet
    // thickness. Explicit "ضخامت" always wins over this inference.
    if (!width && !explicitThickness && thicknessFromMill &&
        kxNormalizeSheetWidthMm_(thickness)) {
      width = thickness;
      thickness = '';
    }
    width = kxNormalizeSheetWidthMm_(width);
    thickness = kxNormalizeSheetThickness_(thickness, category, width);
    return { thickness: thickness, width: width, length: length, width_unit: 'mm' };
  }

  return { thickness: thickness, width: width, length: length, width_unit: '' };
}

function kxExtractColor_(line) {
  var text = kxNormalizeText_(line).replace(/[.،,:：]+$/g, '').trim();
  var emojiColors = [
    ['سفید', /🤍/, '🤍'],
    ['قرمز', /❤️|❤/, '❤️'],
    ['آبی', /💙/, '💙'],
    ['نارنجی', /🧡/, '🧡'],
    ['سبز', /💚/, '💚'],
    ['زرد', /💛/, '💛'],
    ['مشکی', /🖤/, '🖤'],
    ['بنفش', /💜/, '💜']
  ];
  for (var e = 0; e < emojiColors.length; e++) {
    if (emojiColors[e][1].test(text)) {
      return { name: emojiColors[e][0], emoji: emojiColors[e][2] };
    }
  }
  var colors = [
    ['آبی', /(?:^|\s)(?:آبی|ابی)(?:\s|$|🔵)/, '🔵'],
    ['قرمز', /(?:^|\s)قرمز(?:\s|$|🔴)/, '🔴'],
    ['نارنجی', /(?:^|\s)نارنجی(?:\s|$|🟠)/, '🟠'],
    ['سبز', /(?:^|\s)سبز(?:\s|$|🟢)/, '🟢'],
    ['زرد', /(?:^|\s)زرد(?:\s|$|🟡)/, '🟡'],
    ['سفید', /(?:^|\s)سفید(?:\s|$|⚪)/, '⚪'],
    ['مشکی', /(?:^|\s)(?:مشکی|سیاه)(?:\s|$|⚫)/, '⚫'],
    ['طوسی', /(?:^|\s)(?:طوسی|خاکستری)(?:\s|$)/, ''],
    ['کرم', /(?:^|\s)کرم(?:\s|$)/, ''],
    ['قهوه‌ای', /(?:^|\s)(?:قهوه‌ای|قهوه ای)(?:\s|$)/, ''],
    ['بنفش', /(?:^|\s)بنفش(?:\s|$|🟣)/, '🟣']
  ];
  for (var i = 0; i < colors.length; i++) {
    if (colors[i][1].test(text)) return { name: colors[i][0], emoji: colors[i][2] };
  }
  return null;
}

function kxParseInventoryText_(rawText, options) {
  options = options || {};
  var normalized = kxNormalizeText_(rawText);
  var rawLines = normalized.split('\n');
  var items = [];
  var locations = [];
  var currentCategory = 'آهن‌آلات';
  var currentTitle = '';
  var currentSheetDimensions = { thickness: '', width: '', length: '' };
  var warnings = [];

  rawLines.forEach(function (rawLine) {
    var location = kxExtractLocation_(rawLine);
    if (location) locations.push(kxPersianDigits_(location));

    var cleaned = kxCleanInventoryLine_(rawLine);
    if (!cleaned) return;
    var lineCategory = kxCategoryFromLine_(cleaned, currentCategory);
    var lineDimensions = kxExtractDimensions_(cleaned, lineCategory);
    if (kxIsSheetCategory_(lineCategory)) {
      if (lineDimensions.thickness && !lineDimensions.width && currentSheetDimensions.width) {
        lineDimensions.width = currentSheetDimensions.width;
        lineDimensions.width_unit = 'mm';
        lineDimensions.thickness = kxNormalizeSheetThickness_(
          lineDimensions.thickness, lineCategory, lineDimensions.width
        );
      }
      // Width-only headings such as «کوتاه»، «بلند»، «1250» or «1 متر»
      // establish context for the following thickness rows.
      if (lineDimensions.width && !lineDimensions.thickness) {
        currentSheetDimensions.width = lineDimensions.width;
        currentSheetDimensions.width_unit = 'mm';
      }
    }

    var detectedColor = kxExtractColor_(cleaned);
    if (detectedColor && /رنگی/.test(lineCategory)) {
      currentCategory = lineCategory;
      if (lineDimensions.thickness || lineDimensions.width) {
        currentSheetDimensions = lineDimensions;
      }
      var colorDimensions = (lineDimensions.thickness || lineDimensions.width) ?
        lineDimensions : currentSheetDimensions;
      if (!(colorDimensions.thickness || colorDimensions.width)) return;
      if (!currentTitle || kxCategoryFromLine_(currentTitle, 'آهن‌آلات') !== currentCategory) {
        currentTitle = currentCategory;
      }
      var colorText = 'رنگ: ' + detectedColor.name + (detectedColor.emoji ? ' ' + detectedColor.emoji : '');
      items.push({
        category: currentCategory,
        product_title: currentTitle || currentCategory,
        specification: colorText,
        grade: '',
        thickness: colorDimensions.thickness,
        width: colorDimensions.width,
        length: colorDimensions.length,
        width_unit: colorDimensions.width_unit || 'mm',
        unit: '',
        location: location || '',
        public_line: colorText
      });
      return;
    }

    // «تسمه نوردی درجه ۱» is a heading even though it contains a digit.
    if (lineCategory === 'تسمه' && /تسمه/.test(cleaned) &&
        !/عرض|ضخامت|طول|\d+(?:[./]\d+)?\s*میل|[*x×_]/i.test(cleaned)) {
      currentCategory = 'تسمه';
      currentTitle = kxCleanHeading_(cleaned, currentCategory);
      return;
    }

    // A standalone grade belongs to the active non-sheet product. Without
    // this guard, ST37 after a «تسمه» heading used to switch the post to ورق.
    if (kxIsStandaloneGrade_(cleaned) && currentCategory !== 'آهن‌آلات' &&
        !kxIsSheetCategory_(currentCategory)) {
      var contextualGrade = kxExtractGrade_(cleaned);
      if (contextualGrade && kxNormalizeText_(currentTitle).toUpperCase().indexOf(contextualGrade) === -1) {
        currentTitle = kxCompactLine_((currentTitle || currentCategory) + ' ' + contextualGrade);
      }
      return;
    }

    if (kxIsStandaloneSheetHeading_(cleaned, currentCategory)) {
      var grade = kxExtractGrade_(cleaned);
      var previousPrefix = /رول|کویل/i.test(currentTitle) ? 'رول' : 'ورق';
      currentCategory = /استیل/i.test(cleaned) ? 'ورق استیل' : 'ورق گرم و فولادی';
      currentTitle = /^(?:ورق|رول|کویل|استیل)(?:\s|$)/i.test(cleaned) ?
        kxCleanHeading_(cleaned, currentCategory) : previousPrefix + ' ' + grade;
      return;
    }

    if (!kxContainsSpecification_(cleaned)) {
      if (kxKnownHeading_(cleaned)) {
        currentCategory = lineCategory;
        currentTitle = kxCleanHeading_(cleaned, currentCategory);
      }
      return;
    }

    currentCategory = lineCategory;
    if (/رنگی/.test(currentCategory) && /رنگی/.test(cleaned)) {
      var coloredTitle = cleaned
        .replace(/(?:^|\s)\d{2,3}\s*(?:بلند|کوتاه)(?:\s|$)/i, ' ')
        .replace(/\s{2,}/g, ' ').trim();
      if (!/^ورق(?:\s|$)/.test(coloredTitle)) coloredTitle = 'ورق ' + coloredTitle;
      currentTitle = kxCleanHeading_(coloredTitle, currentCategory);
    }
    if (!currentTitle || kxCategoryFromLine_(currentTitle, 'آهن‌آلات') !== currentCategory) {
      // A specification line must not become the public post title. If no
      // compatible heading exists, use the concise product category.
      currentTitle = currentCategory;
    }

    var spec = kxNormalizeSpecForPublic_(cleaned);
    if (!spec) return;
    var dimensions = lineDimensions;
    if (/ورق/.test(currentCategory) && (dimensions.thickness || dimensions.width)) {
      currentSheetDimensions = dimensions;
    }
    var itemGrade = kxExtractGrade_(cleaned);
    var itemTitle = currentTitle || currentCategory;
    if (/ورق/.test(currentCategory) &&
        /^(?:ورق گرم و فولادی|آهن‌آلات)$/.test(itemTitle) && itemGrade) {
      itemTitle = 'ورق ' + itemGrade;
    }
    items.push({
      category: currentCategory,
      product_title: itemTitle,
      specification: spec,
      grade: itemGrade,
      thickness: dimensions.thickness,
      width: dimensions.width,
      length: dimensions.length,
      width_unit: dimensions.width_unit || '',
      unit: /تیر\s*آهن|تیراهن/.test(cleaned) ? 'شاخه' : (/میلگرد/.test(currentCategory) ? 'بندیل/شاخه' : ''),
      location: location || '',
      public_line: spec
    });
  });

  // Deduplicate exact public items while preserving order.
  var seen = {};
  items = items.filter(function (item) {
    var key = kxNormalizeText_(item.category + '|' + item.product_title + '|' +
      item.public_line + '|' + item.thickness + '|' + item.width + '|' + item.length).toLowerCase();
    if (seen[key]) return false;
    seen[key] = true;
    return true;
  });
  locations = kxUnique_(locations);
  if (!items.length) warnings.push('هیچ ردیف کالایی با اطمینان استخراج نشد؛ متن باید دستی ویرایش شود.');

  var ref = options.publicRef || kxMakePublicRef_();
  var output = {
    items: items,
    locations: locations,
    categories: kxUnique_(items.map(function (item) { return item.category; })),
    publicRef: ref,
    warnings: warnings
  };
  output.publicText = kxRenderParsedInventory_(output, options);
  return output;
}

function kxFormatDecimalAscii_(value) {
  var normalized = kxNormalizeDigits_(value).trim()
    .replace(/٫/g, '.').replace(/٬/g, '').replace(/,/g, '');
  if (/^\d+\/\d+$/.test(normalized)) normalized = normalized.replace('/', '.');
  if (/^\d+(?:\.\d+)?$/.test(normalized)) {
    var number = Number(normalized);
    if (isFinite(number)) return String(Number(number.toFixed(3)));
  }
  return normalized;
}

function kxWidthInMeters_(value) {
  var normalized = kxNormalizeSheetWidthMm_(value);
  if (!normalized) return '';
  var number = Number(normalized) / 1000;
  return String(Number(number.toFixed(3)));
}

function kxPublicCategoryUrl_(category) {
  var website = kxString_(kxGetSetting_('website', 'https://kavex.ir/'))
    .replace(/^https?:\/\//i, '').replace(/\/+$/, '');
  var path = '';
  if (/ورق|تسمه|استیل|گالوانیزه|روغنی|اسیدشویی/.test(category)) path = '/category/sheet';
  else if (category === 'میلگرد') path = '/category/rebar';
  else if (category === 'تیرآهن') path = '/category/beam';
  return website + path;
}

function kxPublicProductTitle_(category, title, items) {
  var value = kxNormalizeText_(title || '');
  var grades = kxUnique_((items || []).map(function (item) { return item.grade; }));
  var grade = grades.length === 1 ? grades[0] : '';
  var generic = !value || /^(?:آهن\s*آلات|آهن‌آلات|ورق گرم و فولادی)$/.test(value) || value === category;

  if (/ورق/.test(category)) {
    if (/^(?:st(?:w)?\d+|w\d+|304|410)$/i.test(value)) value = 'ورق ' + value;
    else if (generic) value = (grade ? 'ورق ' + grade : category.replace('گرم و فولادی', '').trim());
  } else if (category === 'میلگرد') {
    if (!/میلگرد/.test(value)) value = /آجدار/.test(value) ? 'میلگرد آجدار' : 'میلگرد';
  } else if (generic) {
    value = category;
  }

  // Public sheet titles follow the requested compact style: "رول st37".
  value = kxNormalizeDigits_(value).replace(/\b(STW?|W)(\d+)\b/g, function (_, prefix, digits) {
    return prefix.toLowerCase() + digits;
  });
  value = value.replace(/درجه\s*(\d+)/g, 'درجه $1');
  return value || category;
}

function kxPublicLocations_(items, fallbackLocations) {
  var values = [];
  (items || []).forEach(function (item) { if (item.location) values.push(item.location); });
  if (!values.length) values = fallbackLocations || [];
  return kxUnique_(values).map(function (location) {
    return kxNormalizeText_(location)
      .replace(/^(?:📍|📌)\s*/, '')
      .replace(/^محل\s*بارگیری\s*[:：]?\s*/, '')
      .trim();
  });
}

function kxRenderPublicGroup_(category, title, items, fallbackLocations) {
  var divider = '━━━━━━━━━━━━━━━━━━━━━';
  var lines = [
    '✅  ' + kxPublicProductTitle_(category, title, items) + ' 🔥 قیمت مناسب 🔥',
    ''
  ];

  if (category === 'تسمه') {
    var stripWidthOrder = [];
    var stripByWidth = {};
    items.forEach(function (item) {
      var stripWidth = kxFormatDecimalAscii_(item.width || '');
      var stripKey = stripWidth || '_unknown';
      if (!stripByWidth[stripKey]) { stripByWidth[stripKey] = []; stripWidthOrder.push(stripKey); }
      stripByWidth[stripKey].push(item);
    });

    stripWidthOrder.forEach(function (key, index) {
      if (index) lines.push('');
      lines.push(divider);
      lines.push(key === '_unknown' ? '📐 ابعاد موجود:' :
        '📐 عرض ' + key + ' سانتی‌متر | ضخامت‌های موجود:');
      lines.push(divider, '');
      var stripThicknesses = kxUnique_(stripByWidth[key].map(function (item) {
        return item.thickness ? kxFormatDecimalAscii_(item.thickness) + ' میل' : '';
      }));
      if (stripThicknesses.length) {
        stripThicknesses.forEach(function (thickness) { lines.push('▪️ ' + thickness); });
      } else {
        kxUnique_(stripByWidth[key].map(function (item) { return item.public_line; }))
          .forEach(function (value) { lines.push('▪️ ' + value); });
      }
    });
  } else if (/ورق/.test(category)) {
    var widthOrder = [];
    var byWidth = {};
    items.forEach(function (item) {
      var width = kxWidthInMeters_(item.width || '');
      var key = width || '_unknown';
      if (!byWidth[key]) { byWidth[key] = []; widthOrder.push(key); }
      byWidth[key].push(item);
    });

    widthOrder.forEach(function (key, index) {
      if (index) lines.push('');
      lines.push(divider);
      lines.push(key === '_unknown' ? '📐 ضخامت‌ها و ابعاد موجود:' :
        '📐 عرض ' + key + ' متر | ضخامت‌ موجود:');
      lines.push(divider, '');

      var thicknesses = kxUnique_(byWidth[key].map(function (item) {
        return item.thickness ? kxFormatDecimalAscii_(item.thickness) + ' میل' : '';
      }));
      if (thicknesses.length) {
        thicknesses.forEach(function (thickness) { lines.push('▪️ ' + thickness); });
      } else {
        kxUnique_(byWidth[key].map(function (item) { return item.public_line; }))
          .forEach(function (value) { lines.push('▪️ ' + value); });
      }

      var colors = kxUnique_(byWidth[key].map(function (item) {
        var match = kxString_(item.public_line).match(/^رنگ\s*[:：]\s*(.+)$/);
        return match ? match[1].trim() : '';
      }));
      if (colors.length) {
        lines.push('', '🎨 رنگ‌های موجود:');
        colors.forEach(function (color) { lines.push('▪️ ' + color); });
      }
    });
  } else {
    lines.push(divider, '📐 مشخصات موجود:', divider, '');
    kxUnique_(items.map(function (item) { return item.public_line; }))
      .forEach(function (value) { lines.push('▪️ ' + value); });
  }

  lines.push('', divider);
  var locations = kxPublicLocations_(items, fallbackLocations);
  if (locations.length) {
    lines.push('📌  ' + locations.join(' | '), divider);
  }
  lines.push(
    '☎️ ' + kxString_(kxGetSetting_('phone', '09132751779')),
    '',
    '🌐 ' + kxPublicCategoryUrl_(category),
    divider
  );
  return lines.join('\n').replace(/\n{3,}/g, '\n\n').trim();
}

function kxRenderParsedInventory_(parsed, options) {
  options = options || {};
  var items = parsed.items || [];
  if (!items.length) {
    return '⚠️ متن به‌صورت خودکار قابل تشخیص نبود و باید پیش از انتشار ویرایش شود.';
  }

  var groupOrder = [];
  var groups = {};
  items.forEach(function (item) {
    var title = item.product_title || item.category;
    var key = item.category + '|' + title;
    if (!groups[key]) {
      groups[key] = { category: item.category, title: title, items: [] };
      groupOrder.push(key);
    }
    groups[key].items.push(item);
  });

  return groupOrder.map(function (key) {
    var group = groups[key];
    return kxRenderPublicGroup_(group.category, group.title, group.items, parsed.locations || []);
  }).join('\n\n').trim();
}


/* ===== 04_Telegram.gs ===== */
/** Telegram Bot API adapter. */

function kxBotToken_() {
  var token = kxProps_().getProperty(KX.PROPS.BOT_TOKEN);
  kxAssert_(token, 'توکن ربات ثبت نشده است. از منوی کاوکس گزینه «۲) ثبت توکن و مدیر» را اجرا کنید.');
  return token;
}

function kxTelegramRequest_(method, payload) {
  var allowedMethods = {
    getMe: true, getUpdates: true, sendMessage: true, answerCallbackQuery: true,
    editMessageReplyMarkup: true, deleteMessage: true, getChatMember: true,
    getChat: true, getChatMemberCount: true,
    setMyCommands: true, getWebhookInfo: true, deleteWebhook: true
  };
  kxAssert_(Object.prototype.hasOwnProperty.call(allowedMethods, method), 'Telegram API method is not permitted.');
  var response;
  try {
    response = UrlFetchApp.fetch('https://api.telegram.org/bot' + kxBotToken_() + '/' + method, {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify(payload || {}),
      muteHttpExceptions: true,
      followRedirects: false,
      timeoutSeconds: 15
    });
  } catch (networkError) {
    // Fetch exceptions may include the URL (and therefore the bot token).
    throw new Error('ارتباط با تلگرام برقرار نشد؛ اتصال یا سهمیه اجرای اسکریپت را بررسی کنید.');
  }
  var code = response.getResponseCode();
  var body = response.getContentText();
  var parsed = kxParseJson_(body, null);
  if (code < 200 || code >= 300 || !parsed || !parsed.ok) {
    var description = parsed && parsed.description ? kxString_(parsed.description) : '';
    // With a one-minute poll interval the callback notification may expire
    // before it is fetched. The underlying authorized action must still run.
    if (method === 'answerCallbackQuery' && code === 400 &&
        /query is too old|query ID is invalid|QUERY_ID_INVALID/i.test(description)) {
      return false;
    }
    throw new Error('Telegram API ' + method + ' failed (HTTP ' + code + ').');
  }
  return parsed.result;
}

function kxSendTelegramText_(chatId, text, options) {
  options = options || {};
  var chunks = kxSplitTelegramText_(text, options.maxLength || KX.MAX_TELEGRAM_TEXT);
  var results = [];
  chunks.forEach(function (chunk, index) {
    var payload = {
      chat_id: chatId,
      text: chunk,
      disable_web_page_preview: true
    };
    if (options.parseMode) payload.parse_mode = options.parseMode;
    if (options.disableNotification !== undefined) payload.disable_notification = options.disableNotification;
    if (options.replyToMessageId && index === 0) payload.reply_parameters = { message_id: options.replyToMessageId };
    if (options.replyMarkup && index === chunks.length - 1) payload.reply_markup = options.replyMarkup;
    results.push(kxTelegramRequest_('sendMessage', payload));
  });
  return results;
}

function kxAnswerCallback_(callbackId, text, showAlert) {
  return kxTelegramRequest_('answerCallbackQuery', {
    callback_query_id: callbackId,
    text: kxString_(text).slice(0, 190),
    show_alert: !!showAlert
  });
}

function kxEditReplyMarkup_(chatId, messageId, replyMarkup) {
  return kxTelegramRequest_('editMessageReplyMarkup', {
    chat_id: chatId,
    message_id: messageId,
    reply_markup: replyMarkup || { inline_keyboard: [] }
  });
}

function kxDeleteTelegramMessage_(chatId, messageId) {
  return kxTelegramRequest_('deleteMessage', { chat_id: chatId, message_id: Number(messageId) });
}

function kxPublishTextToChannel_(text, options) {
  options = options || {};
  var destination = kxString_(kxGetSetting_('destination_channel', '@kavexir'));
  kxAssert_(destination, 'کانال مقصد در Settings ثبت نشده است.');
  var results = kxSendTelegramText_(destination, text, {
    disableNotification: !!options.disableNotification,
    maxLength: KX.MAX_TELEGRAM_TEXT
  });
  return results.map(function (message) { return message.message_id; });
}

function kxPreviewKeyboard_(inboxId) {
  return {
    inline_keyboard: [
      [
        { text: '✅ افزودن به گزارش ساعت ۹', callback_data: 'QUEUE:' + inboxId },
        { text: '🚀 انتشار فوری', callback_data: 'PUBLISH:' + inboxId }
      ],
      [
        { text: '📝 ویرایش متن', callback_data: 'EDIT:' + inboxId },
        { text: '🏷 اصلاح منبع', callback_data: 'SOURCE:' + inboxId }
      ],
      [
        { text: '🗑 رد کردن', callback_data: 'REJECT:' + inboxId }
      ]
    ]
  };
}

function kxMainKeyboard_() {
  return {
    keyboard: [
      [{ text: '📥 پیش‌نویس‌ها' }, { text: '📦 موجودی امروز' }],
      [{ text: '🏭 پیش‌نمایش ساعت ۸' }, { text: '🧪 وضعیت ربات' }]
    ],
    resize_keyboard: true,
    is_persistent: true
  };
}



/* ===== 05_Bot.gs ===== */
/** Private Telegram polling and owner-only review workflow. */

function kxWebhookOutput_(payload) {
  // Static denial only; saving code does not update archived/old deployments.
  return ContentService.createTextOutput(JSON.stringify(payload || { ok: false }))
    .setMimeType(ContentService.MimeType.JSON);
}

function doGet() {
  return kxWebhookOutput_({ ok: false, error: 'web_interface_disabled' });
}

function doPost() {
  return kxWebhookOutput_({ ok: false, error: 'web_interface_disabled' });
}

function kxIsValidTelegramUpdate_(update) {
  return !!update && typeof update === 'object' && /^\d+$/.test(kxString_(update.update_id));
}

function kxProcessTelegramUpdate_(update) {
  kxAssert_(kxIsValidTelegramUpdate_(update), 'Invalid Telegram update.');
  var context = kxTelegramContext_(update);
  // Ignore outsiders before allocating sheet rows or sending any response.
  if (!kxIsOwner_(context.userId) || !context.message || !context.chatId) return { unauthorized: true };
  var eventKey = 'TG:' + kxString_(update.update_id);
  if (!kxReserveEvent_(eventKey)) return { duplicate: true };
  try {
    var result = kxProcessUpdate_(update);
    kxFinishEvent_(eventKey, result);
    return result;
  } catch (err) {
    kxFailEvent_(eventKey, err);
    // Do not reveal internal errors or stored data through Telegram.
    try { kxSendTelegramText_(kxOwnerId_(), '❌ عملیات انجام نشد. جزئیات در شیت Events ثبت شده است.'); } catch (ignored) {}
    return { handled_error: true };
  }
}

/**
 * Private inbound path: Apps Script fetches Telegram updates. Telegram never
 * calls the script, therefore no public Web App deployment is required.
 */
function runKavexTelegramPoller() {
  try { return kxWithLock_(function () {
    kxAssert_(/^\d+$/.test(kxOwnerId_()), 'ابتدا توکن و شناسه مدیر را از منوی شیت ثبت کنید.');
    var startedAt = Date.now();
    var offset = Number(kxProps_().getProperty(KX.PROPS.TELEGRAM_OFFSET) || 0);
    var updates = kxTelegramRequest_('getUpdates', {
      offset: offset || undefined,
      limit: 20,
      timeout: 0,
      allowed_updates: ['message', 'edited_message', 'callback_query']
    }) || [];
    var processed = 0;
    for (var i = 0; i < updates.length; i++) {
      if (Date.now() - startedAt > 45000) break;
      var update = updates[i];
      if (!kxIsValidTelegramUpdate_(update)) continue;
      kxProcessTelegramUpdate_(update);
      kxProps_().setProperty(KX.PROPS.TELEGRAM_OFFSET, String(Number(update.update_id) + 1));
      processed++;
    }
    kxProps_().setProperty(KX.PROPS.LAST_POLL_AT, kxNowIso_());
    kxProps_().deleteProperty(KX.PROPS.LAST_POLL_ERROR);
    return { ok: true, processed: processed };
  }); } catch (err) {
    kxProps_().setProperty(KX.PROPS.LAST_POLL_ERROR, kxString_(err.message).slice(0, 300));
    throw err;
  }
}

function kxTelegramContext_(update) {
  var callback = update.callback_query || null;
  var message = callback ? callback.message :
    (update.message || update.edited_message || update.channel_post || update.edited_channel_post || null);
  var from = callback ? callback.from : (message ? message.from : null);
  return {
    update: update,
    callback: callback,
    message: message,
    from: from,
    userId: from ? kxString_(from.id) : '',
    senderName: from ? [from.first_name, from.last_name].filter(Boolean).join(' ') : '',
    chatId: message && message.chat ? kxString_(message.chat.id) : '',
    chatTitle: message && message.chat ? kxString_(message.chat.title || message.chat.username || message.chat.first_name) : '',
    chatType: message && message.chat ? kxString_(message.chat.type) : '',
    text: message ? kxString_(message.text || message.caption).trim() : ''
  };
}

function kxOwnerId_() {
  return kxString_(kxProps_().getProperty(KX.PROPS.OWNER_ID)).trim();
}

function kxIsOwner_(userId) {
  return !!kxOwnerId_() && kxString_(userId) === kxOwnerId_();
}

function kxIsOwnerPrivateChat_(ctx) {
  return !!ctx && kxIsOwner_(ctx.userId) &&
    ctx.chatType === 'private' && kxString_(ctx.chatId) === kxOwnerId_();
}

function kxInboxChatId_() {
  return kxString_(kxProps_().getProperty(KX.PROPS.INBOX_CHAT_ID));
}

/** Only a dedicated group containing the owner and this bot is eligible. */
function kxPrivateInboxProblem_(chatId) {
  var chat = kxTelegramRequest_('getChat', { chat_id: chatId });
  if (!chat || kxString_(chat.id) !== kxString_(chatId) ||
      ['group', 'supergroup'].indexOf(chat.type) === -1 || chat.username ||
      (chat.active_usernames && chat.active_usernames.length)) {
    return 'گروه ورودی باید خصوصی و بدون نام کاربری عمومی باشد.';
  }
  var memberCount = Number(kxTelegramRequest_('getChatMemberCount', { chat_id: chatId }));
  if (memberCount !== 2) return 'برای حفظ اطلاعات، گروه ورودی باید فقط دو عضو داشته باشد: شما و همین ربات.';
  return '';
}

function kxCanUseContext_(ctx) {
  if (!ctx || !kxIsOwner_(ctx.userId)) return false;
  if (kxIsOwnerPrivateChat_(ctx)) return true;
  return !!kxInboxChatId_() && ctx.chatId === kxInboxChatId_() &&
    ['group', 'supergroup'].indexOf(ctx.chatType) !== -1 && !kxPrivateInboxProblem_(ctx.chatId);
}

function kxStateKey_(userId) {
  return KX.PROPS.STATE_PREFIX + kxString_(userId);
}

function kxSetState_(userId, state) {
  state.expires_at = new Date(Date.now() + KX.STATE_TTL_MINUTES * 60000).toISOString();
  kxProps_().setProperty(kxStateKey_(userId), JSON.stringify(state));
}

function kxGetState_(userId) {
  var value = kxProps_().getProperty(kxStateKey_(userId));
  if (!value) return null;
  var state = kxParseJson_(value, null);
  var expiry = state && state.expires_at ? new Date(state.expires_at).getTime() : NaN;
  if (!state || !isFinite(expiry) || expiry < Date.now()) {
    kxClearState_(userId);
    return null;
  }
  return state;
}

function kxClearState_(userId) {
  kxProps_().deleteProperty(kxStateKey_(userId));
}

function kxCommand_(text) {
  var match = kxString_(text).match(/^\/([a-zA-Z_]+)(?:@\w+)?(?:\s+([\s\S]*))?$/);
  return match ? { name: match[1].toLowerCase(), args: kxString_(match[2]).trim() } : null;
}

function kxButtonCommand_(text) {
  var map = {
    '📥 پیش‌نویس‌ها': 'pending',
    '📦 موجودی امروز': 'today',
    '🏭 پیش‌نمایش ساعت ۸': 'morning',
    '🧪 وضعیت ربات': 'status'
  };
  return map[text] || '';
}

function kxProcessUpdate_(update) {
  var ctx = kxTelegramContext_(update);
  if (!ctx.message || !ctx.chatId) return { ignored: true };
  if (!kxIsOwner_(ctx.userId)) return { unauthorized: true };
  var command = kxCommand_(ctx.text);
  // Binding is the only command accepted in an as-yet-unbound group.
  if (!ctx.callback && command && command.name === 'bind_inbox') {
    return kxHandleCommand_(command, ctx);
  }
  if (!kxCanUseContext_(ctx)) {
    // Send setup hints only to the owner's DM, never to an arbitrary group.
    if (!ctx.callback && ['group', 'supergroup'].indexOf(ctx.chatType) !== -1) {
      var problem = ctx.chatId === kxInboxChatId_() ?
        'گروه متصل دیگر شرایط خصوصی را ندارد؛ گروه باید فقط شامل شما و ربات و بدون نام کاربری عمومی باشد.' :
        'این گروه هنوز متصل نیست. داخل گروه اختصاصیِ دو نفره خودتان و ربات، /bind_inbox را بفرستید.';
      try { kxSendTelegramText_(kxOwnerId_(), problem); } catch (ignored) {}
    }
    return { unauthorized_chat: true };
  }
  if (ctx.callback) return kxHandleCallback_(ctx);
  if (command && command.name === 'whoami') {
    kxSendTelegramText_(ctx.chatId, 'شناسه عددی شما: ' + (ctx.userId || 'نامشخص') + '\nشناسه این گفتگو: ' + ctx.chatId);
    return { whoami: true };
  }

  var mapped = kxButtonCommand_(ctx.text);
  if (mapped) command = { name: mapped, args: '' };
  if (command) return kxHandleCommand_(command, ctx);
  if (!ctx.text) return { ignored_non_text: true };
  var state = kxGetState_(ctx.userId);
  if (state) {
    if (kxString_(state.chat_id) !== ctx.chatId) {
      kxSendTelegramText_(ctx.chatId, 'یک ویرایش در گفتگوی دیگری باز است. همان‌جا ادامه دهید یا /cancel را بفرستید.');
      return { state_chat_mismatch: true };
    }
    return kxHandleStateMessage_(ctx, state);
  }
  return kxIngestMessage_(ctx);
}

function kxHandleCommand_(command, ctx) {
  if (command.name === 'start' || command.name === 'menu') {
    kxClearState_(ctx.userId);
    kxSendTelegramText_(ctx.chatId,
      'ربات مدیریت محتوای کانال کاوکس آماده است.\n\nپیام تأمین‌کننده را در چت خصوصی ربات یا گروه اختصاصی متصل Forward کنید. فقط پیام‌های خودتان پردازش می‌شوند.\nدریافت پیام تقریباً هر یک دقیقه انجام می‌شود.',
      { replyMarkup: kxMainKeyboard_() });
    return { menu: true };
  }
  if (command.name === 'cancel') {
    kxClearState_(ctx.userId);
    kxSendTelegramText_(ctx.chatId, 'عملیات جاری لغو شد.');
    return { cancelled: true };
  }
  if (command.name === 'bind_inbox') {
    kxAssert_(kxIsOwner_(ctx.userId), 'دسترسی ندارید.');
    kxAssert_(ctx.chatType === 'group' || ctx.chatType === 'supergroup', 'این دستور را داخل گروه خصوصی میانی اجرا کنید.');
    var problem = kxPrivateInboxProblem_(ctx.chatId);
    if (problem) {
      kxSendTelegramText_(kxOwnerId_(), problem);
      return { binding_refused: true };
    }
    var bot = kxTelegramRequest_('getMe', {});
    var botMember = kxTelegramRequest_('getChatMember', { chat_id: ctx.chatId, user_id: bot.id });
    if (botMember.status !== 'administrator') {
      kxSendTelegramText_(kxOwnerId_(), 'ربات را در گروه اختصاصی Admin کنید تا پیام‌های Forward شده را دریافت کند؛ سپس /bind_inbox را دوباره در همان گروه بفرستید.');
      return { bot_admin_required: true };
    }
    kxProps_().setProperty(KX.PROPS.INBOX_CHAT_ID, ctx.chatId);
    kxSetSetting_('inbox_chat_id', ctx.chatId, 'شناسه گروه خصوصی ورودی');
    kxSetSetting_('inbox_chat_title', ctx.chatTitle, 'نام گروه خصوصی ورودی');
    kxSendTelegramText_(ctx.chatId, '✅ این گروه خصوصی متصل شد.\nاز این پس پیام‌ها را همین‌جا Forward کنید؛ فقط پیام‌های خودتان پردازش می‌شوند. پاسخ معمولاً با اجرای بعدی زمان‌بند می‌رسد.');
    kxAudit_(ctx.userId, 'bind_inbox', 'Settings', 'inbox_chat_id', { chat_id: ctx.chatId, title: ctx.chatTitle });
    return { bound: true, chat_id: ctx.chatId };
  }
  if (command.name === 'pending') return kxSendPending_(ctx.chatId);
  if (command.name === 'today') return kxSendTodayInventory_(ctx.chatId);
  if (command.name === 'morning') {
    kxSendTelegramText_(ctx.chatId, 'پیش‌نمایش پیام ساعت ۸:\n\n' + kxBuildMorningPost_());
    return { morning_preview: true };
  }
  if (command.name === 'status') return kxSendBotStatus_(ctx.chatId);
  if (command.name === 'publish_morning') {
    var morningIds = kxPublishMorningPost_('manual:' + kxNowIso_());
    kxSendTelegramText_(ctx.chatId, '✅ پیام صبحگاهی منتشر شد. شناسه پیام: ' + morningIds.join(', '));
    return { published_morning: morningIds };
  }
  if (command.name === 'publish_digest') {
    var result = kxPublishDailyInventoryDigest_('manual:' + kxNowIso_());
    kxSendTelegramText_(ctx.chatId, result.skipped ? 'موجودی فعالی برای انتشار وجود ندارد.' : '✅ گزارش موجودی منتشر شد.');
    return result;
  }
  kxSendTelegramText_(ctx.chatId, 'دستور شناخته نشد. /menu را بزنید.');
  return { unknown_command: command.name };
}

function kxHandleStateMessage_(ctx, state) {
  kxAssert_(kxIsOwner_(ctx.userId) && kxString_(state.chat_id) === ctx.chatId, 'گفتگوی ویرایش معتبر نیست.');
  var inbox = kxFind_(KX.SHEETS.INBOX, 'inbox_id', state.inbox_id);
  kxAssert_(inbox, 'پیش‌نویس موردنظر پیدا نشد.');
  if (state.action === 'edit') {
    var edited = kxString_(ctx.text).trim();
    kxAssert_(edited.length >= 20, 'متن ویرایش‌شده خیلی کوتاه است.');
    kxUpdateRow_(KX.SHEETS.INBOX, inbox._row, {
      parsed_text: edited, status: 'edited', updated_at: kxNowIso_()
    });
    kxClearState_(ctx.userId);
    kxAudit_(ctx.userId, 'edit_draft', 'Inbox', inbox.inbox_id, { length: edited.length });
    return kxShowPreview_(ctx.chatId, kxFind_(KX.SHEETS.INBOX, 'inbox_id', inbox.inbox_id));
  }
  if (state.action === 'source') {
    var sourceName = kxNormalizeText_(ctx.text);
    kxAssert_(sourceName.length >= 2, 'نام منبع معتبر نیست.');
    var supplierId = kxUpsertSupplier_({ source_type: 'manual_name', chat_id: '', title: sourceName, username: '', hidden: false });
    kxUpdateRow_(KX.SHEETS.INBOX, inbox._row, {
      source_type: 'manual_name', source_title: sourceName, supplier_id: supplierId, updated_at: kxNowIso_()
    });
    kxClearState_(ctx.userId);
    kxAudit_(ctx.userId, 'set_source', 'Inbox', inbox.inbox_id, { supplier_id: supplierId, title: sourceName });
    return kxShowPreview_(ctx.chatId, kxFind_(KX.SHEETS.INBOX, 'inbox_id', inbox.inbox_id));
  }
  kxClearState_(ctx.userId);
  return { cleared_unknown_state: true };
}

function kxIngestMessage_(ctx) {
  kxAssert_(ctx.text, 'برای نسخه اول، پیام باید متن یا Caption داشته باشد.');
  var source = kxExtractSource_(ctx.message, ctx.text);
  var supplierId = kxUpsertSupplier_(source);
  var publicRef = kxMakePublicRef_();
  var parsed = kxParseInventoryText_(ctx.text, { publicRef: publicRef });
  var inboxId = kxShortId_('IN');
  var validUntil = kxEndOfTehranDay_(new Date()).toISOString();
  var status = parsed.items.length ? 'draft' : 'needs_review';
  kxAppend_(KX.SHEETS.INBOX, {
    inbox_id: inboxId,
    telegram_update_id: kxString_(ctx.update.update_id),
    received_at: kxNowIso_(), sender_user_id: ctx.userId, sender_name: ctx.senderName,
    inbox_chat_id: ctx.chatId, inbox_chat_title: ctx.chatTitle,
    source_type: source.source_type, source_chat_id: source.chat_id,
    source_title: source.title, source_username: source.username,
    source_message_id: source.message_id, supplier_id: supplierId,
    raw_text: ctx.text, detected_category: parsed.categories.join('، '),
    parsed_text: parsed.publicText, item_count: parsed.items.length,
    status: status, valid_until: validUntil, public_ref: publicRef,
    target_message_ids: '', review_message_id: '',
    error_message: parsed.warnings.join(' | '), updated_at: kxNowIso_()
  });
  kxAudit_(ctx.userId, 'ingest', 'Inbox', inboxId, {
    supplier_id: supplierId, source_title: source.title, items: parsed.items.length
  });
  return kxShowPreview_(ctx.chatId, kxFind_(KX.SHEETS.INBOX, 'inbox_id', inboxId));
}

function kxShowPreview_(chatId, inbox) {
  var sourceLabel = kxString_(inbox.source_title || 'نامشخص');
  var privateHeader = '🔒 پیش‌نمایش خصوصی — در کانال هنوز منتشر نشده\n' +
    'منبع ثبت‌شده: ' + sourceLabel + '\n' +
    'تعداد ردیف استخراج‌شده: ' + kxPersianDigits_(inbox.item_count || 0) + '\n' +
    'وضعیت: ' + inbox.status + '\n\n';
  var results = kxSendTelegramText_(chatId, privateHeader + kxString_(inbox.parsed_text), {
    replyMarkup: kxPreviewKeyboard_(inbox.inbox_id)
  });
  var reviewId = results.length ? results[results.length - 1].message_id : '';
  kxUpdateRow_(KX.SHEETS.INBOX, inbox._row, { review_message_id: reviewId, updated_at: kxNowIso_() });
  return { preview: true, inbox_id: inbox.inbox_id, review_message_id: reviewId };
}

function kxHandleCallback_(ctx) {
  if (!kxCanUseContext_(ctx)) {
    return { unauthorized_callback: true };
  }
  var parts = kxString_(ctx.callback.data).split(':');
  var action = parts.shift();
  var inboxId = parts.join(':');
  var inbox = kxFind_(KX.SHEETS.INBOX, 'inbox_id', inboxId);
  if (!inbox) {
    kxAnswerCallback_(ctx.callback.id, 'پیش‌نویس پیدا نشد.', true);
    return { missing_inbox: inboxId };
  }

  if (action === 'EDIT') {
    kxAnswerCallback_(ctx.callback.id, 'متن اصلاح‌شده را ارسال کنید.', false);
    kxSetState_(ctx.userId, { action: 'edit', inbox_id: inboxId, chat_id: ctx.chatId });
    kxSendTelegramText_(ctx.chatId, '📝 متن کامل اصلاح‌شده را در یک پیام بفرستید. برای لغو /cancel را بزنید.');
    return { awaiting_edit: inboxId };
  }
  if (action === 'SOURCE') {
    kxAnswerCallback_(ctx.callback.id, 'نام منبع را ارسال کنید.', false);
    kxSetState_(ctx.userId, { action: 'source', inbox_id: inboxId, chat_id: ctx.chatId });
    kxSendTelegramText_(ctx.chatId, '🏷 نام خصوصی تأمین‌کننده یا شرکت را بفرستید. این نام در کانال منتشر نمی‌شود.');
    return { awaiting_source: inboxId };
  }
  if (action === 'REJECT') {
    kxAnswerCallback_(ctx.callback.id, 'پیش‌نویس رد شد.', false);
    kxUpdateRow_(KX.SHEETS.INBOX, inbox._row, { status: 'rejected', updated_at: kxNowIso_() });
    kxAudit_(ctx.userId, 'reject', 'Inbox', inboxId, {});
    try { kxEditReplyMarkup_(ctx.chatId, ctx.callback.message.message_id, { inline_keyboard: [] }); } catch (ignored) {}
    kxSendTelegramText_(ctx.chatId, '🗑 پیش‌نویس ' + inbox.public_ref + ' رد شد.');
    return { rejected: inboxId };
  }
  if (action === 'QUEUE') {
    kxAnswerCallback_(ctx.callback.id, 'به گزارش ساعت ۹ افزوده می‌شود.', false);
    var queued = kxApproveInbox_(inbox, true, false, ctx.userId);
    try { kxEditReplyMarkup_(ctx.chatId, ctx.callback.message.message_id, { inline_keyboard: [] }); } catch (ignored2) {}
    kxSendTelegramText_(ctx.chatId, '✅ ' + inbox.public_ref + ' برای گزارش موجودی ساعت ۹ ثبت شد.');
    return queued;
  }
  if (action === 'PUBLISH') {
    kxAnswerCallback_(ctx.callback.id, 'در حال انتشار...', false);
    var published = kxApproveInbox_(inbox, false, true, ctx.userId);
    try { kxEditReplyMarkup_(ctx.chatId, ctx.callback.message.message_id, { inline_keyboard: [] }); } catch (ignored3) {}
    kxSendTelegramText_(ctx.chatId, '🚀 ' + inbox.public_ref + ' در کانال منتشر شد.');
    return published;
  }
  kxAnswerCallback_(ctx.callback.id, 'عملیات نامعتبر است.', true);
  return { unknown_action: action };
}

function kxApproveInbox_(inbox, includeInDigest, publishNow, actor) {
  kxAssert_(['rejected', 'expired'].indexOf(kxString_(inbox.status)) === -1, 'این پیش‌نویس قابل انتشار نیست.');
  var parseSource = inbox.status === 'edited' ? inbox.parsed_text : inbox.raw_text;
  var parsed = kxParseInventoryText_(parseSource, { publicRef: inbox.public_ref });
  if (includeInDigest || publishNow) {
    kxAssert_(parsed.items.length, 'برای انتشار حداقل یک ردیف کالا باید تشخیص داده شود؛ ابتدا متن را ویرایش کنید.');
  }
  var publishText = parsed.publicText || inbox.parsed_text;

  var existing = kxFilter_(KX.SHEETS.INVENTORY, function (row) { return kxString_(row.inbox_id) === kxString_(inbox.inbox_id); });
  if (!existing.length) {
    var inventoryRecords = parsed.items.map(function (item) {
      return {
        inventory_id: kxShortId_('INV'), inbox_id: inbox.inbox_id,
        supplier_id: inbox.supplier_id, received_at: inbox.received_at,
        category: item.category, product_title: item.product_title,
        specification: item.specification, grade: item.grade,
        thickness: item.thickness, width: item.width, length: item.length,
        unit: item.unit, location: item.location || parsed.locations.join('، '),
        public_line: item.public_line, status: 'active', valid_from: kxNowIso_(),
        valid_until: inbox.valid_until, include_in_digest: !!includeInDigest,
        public_ref: inbox.public_ref, source_message_id: inbox.source_message_id,
        published_at: '', channel_message_ids: '', updated_at: kxNowIso_()
      };
    });
    kxAppendMany_(KX.SHEETS.INVENTORY, inventoryRecords);
  } else {
    existing.forEach(function (row) {
      kxUpdateRow_(KX.SHEETS.INVENTORY, row._row, {
        status: 'active', include_in_digest: !!includeInDigest,
        valid_until: inbox.valid_until, updated_at: kxNowIso_()
      });
    });
  }

  var messageIds = [];
  var finalStatus = includeInDigest ? 'queued_for_digest' : 'approved';
  if (publishNow) {
    // Always publish the freshly parsed text. This upgrades older drafts to
    // the current formatter and runs price/privacy cleaning one last time.
    messageIds = kxPublishTextToChannel_(publishText, {});
    finalStatus = 'published';
    kxAppend_(KX.SHEETS.POSTS, {
      post_id: kxShortId_('POST'), inbox_id: inbox.inbox_id, post_type: 'inventory_immediate',
      schedule_key: '', scheduled_at: '', published_at: kxNowIso_(),
      destination_chat_id: kxGetSetting_('destination_channel', '@kavexir'),
      telegram_message_ids: kxJson_(messageIds), public_ref: inbox.public_ref,
      status: 'published', text: publishText, error_message: '',
      created_at: kxNowIso_(), updated_at: kxNowIso_()
    });
  }
  kxUpdateRow_(KX.SHEETS.INBOX, inbox._row, {
    status: finalStatus, parsed_text: publishText,
    target_message_ids: kxJson_(messageIds), updated_at: kxNowIso_()
  });
  kxAudit_(actor, publishNow ? 'publish_now' : 'queue_for_digest', 'Inbox', inbox.inbox_id, {
    item_count: parsed.items.length, message_ids: messageIds
  });
  return { ok: true, inbox_id: inbox.inbox_id, status: finalStatus, message_ids: messageIds };
}

function kxSendPending_(chatId) {
  var pending = kxFilter_(KX.SHEETS.INBOX, function (row) {
    return ['draft', 'needs_review', 'edited'].indexOf(kxString_(row.status)) !== -1;
  }).slice(-10).reverse();
  if (!pending.length) {
    kxSendTelegramText_(chatId, '✅ پیش‌نویس بررسی‌نشده‌ای ندارید.');
    return { count: 0 };
  }
  kxSendTelegramText_(chatId, '📥 پیش‌نویس‌های اخیر:');
  pending.forEach(function (row) { kxShowPreview_(chatId, row); });
  return { count: pending.length };
}

function kxSendTodayInventory_(chatId) {
  var text = kxBuildDailyInventoryDigest_();
  if (!text) kxSendTelegramText_(chatId, 'برای امروز موجودی فعال و تأییدشده‌ای ثبت نشده است.');
  else kxSendTelegramText_(chatId, 'پیش‌نمایش موجودی امروز:\n\n' + text);
  return { has_inventory: !!text };
}

function kxSendBotStatus_(chatId) {
  var inboxId = kxInboxChatId_() || 'ثبت نشده؛ چت خصوصی ربات فعال است';
  var activeCount = kxFilter_(KX.SHEETS.INVENTORY, function (row) {
    return kxString_(row.status) === 'active' && new Date(row.valid_until).getTime() >= Date.now();
  }).length;
  var text = '🧪 وضعیت ربات کانال کاوکس\n\n' +
    'نسخه: ' + KAVEX_CHANNEL_BOT_VERSION + '\n' +
    'روش اتصال: دریافت خصوصی، تقریباً هر یک دقیقه\n' +
    'کانال مقصد: ' + kxGetSetting_('destination_channel', '@kavexir') + '\n' +
    'گروه میانی: ' + inboxId + '\n' +
    'زمان پیام صبحگاهی: ' + kxGetSetting_('morning_time', '08:00') + '\n' +
    'زمان موجودی: ' + kxGetSetting_('inventory_time', '09:00') + '\n' +
    'موجودی فعال امروز: ' + kxPersianDigits_(activeCount);
  kxSendTelegramText_(chatId, text);
  return { active_inventory: activeCount };
}


/* ===== 06_Scheduler.gs ===== */
/** Scheduled morning post, daily inventory digest and expiry processing. */

function kxCatalogText_() {
  var rows = kxFilter_(KX.SHEETS.CATALOG, function (row) { return kxIsTrue_(row.active); });
  rows.sort(function (a, b) { return Number(a.display_order || 0) - Number(b.display_order || 0); });
  if (!rows.length) return 'برای استعلام محصولات موردنیاز با ما تماس بگیرید.';
  return rows.map(function (row) {
    var line = '🔹 ' + kxString_(row.title);
    if (row.specifications) line += '\n   ' + kxString_(row.specifications);
    return line;
  }).join('\n');
}

function kxRenderTemplateBody_(body, date) {
  var target = date || new Date();
  var rendered = kxString_(body);
  var replacements = {
    weekday: kxPersianWeekday_(target),
    date: kxJalaliDate_(target),
    jalali_date: kxJalaliDate_(target),
    jalali_long_date: kxJalaliLongDate_(target),
    phone: kxString_(kxGetSetting_('phone', '09132751779')),
    website: kxString_(kxGetSetting_('website', 'https://kavex.ir/')),
    thursday_cutoff: kxString_(kxGetSetting_('thursday_cutoff', '12:30'))
  };
  if (rendered.indexOf('{{catalog}}') !== -1) replacements.catalog = kxCatalogText_();
  Object.keys(replacements).forEach(function (key) {
    rendered = rendered.split('{{' + key + '}}').join(replacements[key]);
  });
  return rendered.trim();
}

function kxBuildMorningPost_(date) {
  var template = kxFind_(KX.SHEETS.TEMPLATES, 'template_key', 'MORNING');
  var body = template ? kxString_(template.body) :
    'بسم الله الرحمن الرحیم\n\nسلام صبح بخیر 🌹☀️\n\nامروز {{weekday}} {{jalali_long_date}}';
  return kxRenderTemplateBody_(body, date || new Date());
}

function kxActiveDigestInventory_() {
  var now = Date.now();
  return kxFilter_(KX.SHEETS.INVENTORY, function (row) {
    var valid = row.valid_until ? new Date(row.valid_until).getTime() >= now : true;
    return kxString_(row.status) === 'active' && kxIsTrue_(row.include_in_digest) && valid;
  });
}

function kxBuildDailyInventoryDigest_() {
  var rows = kxActiveDigestInventory_();
  if (!rows.length) return '';

  var sourceOrder = [];
  var bySource = {};
  rows.forEach(function (row) {
    var key = kxString_(row.inbox_id || row.public_ref || row.inventory_id);
    if (!bySource[key]) {
      bySource[key] = { items: [], locations: [], publicRef: row.public_ref };
      sourceOrder.push(key);
    }
    var source = bySource[key];
    source.items.push({
      category: kxString_(row.category || 'آهن‌آلات'),
      product_title: kxString_(row.product_title || row.category || 'آهن‌آلات'),
      specification: kxString_(row.specification),
      grade: kxString_(row.grade),
      thickness: kxString_(row.thickness),
      width: kxString_(row.width),
      length: kxString_(row.length),
      unit: kxString_(row.unit),
      location: kxString_(row.location),
      // Re-clean stored rows as well so older/manual Inventory entries cannot
      // reintroduce supplier prices into the scheduled public digest.
      public_line: kxNormalizeSpecForPublic_(kxString_(row.public_line || row.specification))
    });
    if (row.location) source.locations.push(kxString_(row.location));
  });

  return sourceOrder.map(function (sourceKey) {
    var source = bySource[sourceKey];
    source.locations = kxUnique_(source.locations);
    return kxRenderParsedInventory_(source, { digest: true });
  }).join('\n\n').trim();
}

function kxScheduleExists_(scheduleKey) {
  return !!kxFind_(KX.SHEETS.POSTS, 'schedule_key', scheduleKey);
}

function kxPublishTemplatePost_(template, scheduleKey, date) {
  if (scheduleKey && kxScheduleExists_(scheduleKey)) return [];
  var templateKey = kxString_(template && template.template_key).trim() || 'MORNING';
  var text = templateKey === 'MORNING' ? kxBuildMorningPost_(date || new Date()) :
    kxRenderTemplateBody_(template && template.body, date || new Date());
  if (!text) return [];
  var messageIds = kxPublishTextToChannel_(text, { disableNotification: false });
  kxAppend_(KX.SHEETS.POSTS, {
    post_id: kxShortId_('POST'), inbox_id: '',
    post_type: templateKey === 'MORNING' ? 'morning_greeting' : 'recurring_template',
    schedule_key: scheduleKey || '', scheduled_at: kxNowIso_(), published_at: kxNowIso_(),
    destination_chat_id: kxGetSetting_('destination_channel', '@kavexir'),
    telegram_message_ids: kxJson_(messageIds), public_ref: '', status: 'published',
    text: text, error_message: '', created_at: kxNowIso_(), updated_at: kxNowIso_()
  });
  kxAudit_('scheduler', templateKey === 'MORNING' ? 'publish_morning' : 'publish_recurring_template',
    'Posts', scheduleKey || '', { template_key: templateKey, message_ids: messageIds });
  return messageIds;
}

function kxPublishMorningPost_(scheduleKey) {
  var template = kxFind_(KX.SHEETS.TEMPLATES, 'template_key', 'MORNING') || {
    template_key: 'MORNING',
    body: 'بسم الله الرحمن الرحیم\n\nسلام صبح بخیر 🌹☀️\n\nامروز {{weekday}} {{jalali_long_date}}'
  };
  return kxPublishTemplatePost_(template, scheduleKey, new Date());
}

function kxPublishDailyInventoryDigest_(scheduleKey) {
  if (scheduleKey && kxScheduleExists_(scheduleKey)) return { duplicate: true };
  var text = kxBuildDailyInventoryDigest_();
  if (!text) {
    kxAppend_(KX.SHEETS.POSTS, {
      post_id: kxShortId_('POST'), inbox_id: '', post_type: 'daily_inventory',
      schedule_key: scheduleKey || '', scheduled_at: kxNowIso_(), published_at: '',
      destination_chat_id: kxGetSetting_('destination_channel', '@kavexir'),
      telegram_message_ids: '', public_ref: '', status: 'skipped_empty', text: '',
      error_message: '', created_at: kxNowIso_(), updated_at: kxNowIso_()
    });
    return { skipped: true };
  }

  var messageIds = kxPublishTextToChannel_(text, { disableNotification: false });
  var activeRows = kxActiveDigestInventory_();
  activeRows.forEach(function (row) {
    kxUpdateRow_(KX.SHEETS.INVENTORY, row._row, {
      published_at: kxNowIso_(), channel_message_ids: kxJson_(messageIds), updated_at: kxNowIso_()
    });
  });
  kxAppend_(KX.SHEETS.POSTS, {
    post_id: kxShortId_('POST'), inbox_id: kxJson_(kxUnique_(activeRows.map(function (r) { return r.inbox_id; }))),
    post_type: 'daily_inventory', schedule_key: scheduleKey || '',
    scheduled_at: kxNowIso_(), published_at: kxNowIso_(),
    destination_chat_id: kxGetSetting_('destination_channel', '@kavexir'),
    telegram_message_ids: kxJson_(messageIds), public_ref: '', status: 'published',
    text: text, error_message: '', created_at: kxNowIso_(), updated_at: kxNowIso_()
  });
  kxAudit_('scheduler', 'publish_digest', 'Posts', scheduleKey || '', {
    rows: activeRows.length, message_ids: messageIds
  });
  return { published: true, message_ids: messageIds, item_count: activeRows.length };
}

function kxExpireInventory_() {
  var now = Date.now();
  var expired = 0;
  kxRows_(KX.SHEETS.INVENTORY).forEach(function (row) {
    if (kxString_(row.status) !== 'active' || !row.valid_until) return;
    if (new Date(row.valid_until).getTime() < now) {
      kxUpdateRow_(KX.SHEETS.INVENTORY, row._row, { status: 'expired', updated_at: kxNowIso_() });
      expired++;
    }
  });
  return expired;
}

function kxTemplateRunsOnDate_(template, date) {
  var configured = kxString_(template && template.working_days).trim();
  if (!configured) configured = kxString_(kxGetSetting_('working_days', '0,1,2,3,4,6'));
  return kxIsWeekdayAllowed_(date || new Date(), configured);
}

function kxTemplateSendTime_(template) {
  var key = kxString_(template && template.template_key).trim();
  if (kxString_(template && template.send_time).trim()) return kxNormalizeClockTime_(template.send_time);
  if (key === 'MORNING') return kxNormalizeClockTime_(kxGetSetting_('morning_time', '08:00'));
  return '';
}

function kxTemplateScheduleKey_(template, date) {
  var key = kxString_(template && template.template_key).trim();
  if (key === 'MORNING') return kxTehranDateKey_(date || new Date()) + ':MORNING';
  return kxTehranDateKey_(date || new Date()) + ':TEMPLATE:' + key;
}

function kxSchedulableTemplates_(date) {
  var target = date || new Date();
  return kxRows_(KX.SHEETS.TEMPLATES).filter(function (template) {
    var key = kxString_(template.template_key).trim();
    return !!key && key !== 'INVENTORY_FOOTER' && kxIsTrue_(template.enabled) &&
      !!kxString_(template.body).trim() && !!kxTemplateSendTime_(template) &&
      kxTemplateRunsOnDate_(template, target);
  });
}

function kxSchedulerNow_(candidate) {
  // A time-driven Apps Script trigger calls its handler with an event object.
  // Only an actual Date is a valid test override; otherwise use the real time.
  if (Object.prototype.toString.call(candidate) === '[object Date]' && !isNaN(candidate.getTime())) {
    return candidate;
  }
  return new Date();
}

function runChannelScheduler(nowOverride) {
  return kxWithLock_(function () { return kxRunChannelScheduler_(nowOverride); });
}

function kxRunChannelScheduler_(nowOverride) {
  kxExpireInventory_();
  var now = kxSchedulerNow_(nowOverride);
  var policy = kxAutoPublishingPolicy_(now);
  if (!policy.allowed) return {
    working_day: false,
    automatic_publish: false,
    reason: policy.reason,
    holiday: policy.holiday || null
  };
  var dateKey = kxTehranDateKey_(now);
  var results = { automatic_publish: true, templates: {} };
  var inventoryTime = kxGetSetting_('inventory_time', '09:00');

  kxSchedulableTemplates_(now).forEach(function (template) {
    var sendTime = kxTemplateSendTime_(template);
    if (!kxIsInTimeWindow_(now, sendTime, 25)) return;
    var scheduleKey = kxTemplateScheduleKey_(template, now);
    if (kxScheduleExists_(scheduleKey)) return;
    var messageIds = kxPublishTemplatePost_(template, scheduleKey, now);
    if (kxString_(template.template_key) === 'MORNING') results.morning = messageIds;
    else results.templates[kxString_(template.template_key)] = messageIds;
  });

  if (kxIsInTimeWindow_(now, inventoryTime, 25)) {
    var inventoryKey = dateKey + ':INVENTORY';
    if (!kxScheduleExists_(inventoryKey)) results.inventory = kxPublishDailyInventoryDigest_(inventoryKey);
  }
  return results;
}


/* ===== 07_Setup.gs ===== */
/** Sheet menu, credentials and private Telegram polling. No deployment needed. */

function onOpen() {
  SpreadsheetApp.getUi().createMenu('کاوکس | ربات کانال')
    .addItem('۱) نصب ساختار شیت‌ها', 'installKavexChannelBot')
    .addItem('۲) ثبت توکن و مدیر', 'configureKavexBotCredentials')
    .addItem('۳) فعال‌سازی اتصال خصوصی تلگرام', 'activateKavexPrivateTelegram')
    .addItem('۴) فعال‌سازی انتشار زمان‌بندی‌شده کانال', 'installKavexScheduler')
    .addSeparator()
    .addItem('نسخه ۱.۲.۰ — وضعیت اتصال خصوصی', 'showKavexPrivatePollingInfo')
    .addItem('دریافت پیام‌های تلگرام همین حالا', 'pollKavexTelegramNow')
    .addItem('بررسی دسترسی کانال مقصد', 'testKavexDestinationAccess')
    .addItem('به‌روزرسانی منوی شیت', 'refreshKavexMenus')
    .addSeparator()
    .addItem('تنظیم اتصال سایت', 'configureKavexSiteRelay')
    .addItem('فعال‌سازی دریافت پیام‌های سایت', 'activateKavexSiteRelay')
    .addItem('دریافت پیام‌های سایت همین حالا', 'runKavexSiteRelay')
    .addItem('وضعیت اتصال سایت', 'showKavexSiteRelayInfo')
    .addItem('توقف دریافت پیام‌های سایت', 'stopKavexSiteRelay')
    .addSeparator()
    .addItem('توقف دریافت پیام‌های تلگرام', 'stopKavexPrivateTelegram')
    .addItem('توقف انتشار زمان‌بندی‌شده کانال', 'removeKavexScheduler')
    .addToUi();
}

function refreshKavexMenus() {
  onOpen();
}

function installKavexChannelBot() {
  var result = kxWithLock_(kxInstallSchema_);
  onOpen();
  SpreadsheetApp.getUi().alert(
    '✅ ساختار شیت‌ها آماده است.\n' +
    'در نصب اولیه ابتدا گزینه ۲ (توکن و مدیر)، سپس گزینه ۳ (اتصال خصوصی) را اجرا کنید.\n' +
    'برای نصب زمان‌بندی انتشار کانال، گزینه ۴ را اجرا کنید.\n' +
    'این پروژه باید از پروژه CRM جدا باشد.'
  );
  return result;
}

function configureKavexBotCredentials() {
  var ui = SpreadsheetApp.getUi();
  var tokenPrompt = ui.prompt(
    'توکن ربات کانال',
    'توکن ربات مخصوص کانال را از BotFather وارد کنید. توکن را داخل شیت یا متن کد ننویسید.',
    ui.ButtonSet.OK_CANCEL
  );
  if (tokenPrompt.getSelectedButton() !== ui.Button.OK) return { cancelled: true };
  var token = kxString_(tokenPrompt.getResponseText()).trim();
  kxAssert_(/^\d+:[A-Za-z0-9_-]{20,}$/.test(token), 'قالب توکن تلگرام معتبر نیست.');
  var ownerPrompt = ui.prompt(
    'شناسه عددی مدیر',
    'شناسه عددی اکانت Telegram خودتان را وارد کنید؛ نه شناسه ربات یا گروه. می‌توانید آن را از @userinfobot بگیرید.',
    ui.ButtonSet.OK_CANCEL
  );
  if (ownerPrompt.getSelectedButton() !== ui.Button.OK) return { cancelled: true };
  var ownerId = kxNormalizeDigits_(ownerPrompt.getResponseText()).trim();
  kxAssert_(/^[1-9]\d{4,15}$/.test(ownerId) && Number.isSafeInteger(Number(ownerId)), 'شناسه مدیر باید یک عدد مثبت معتبر باشد.');

  var result = kxWithLock_(function () {
    var props = kxProps_();
    var oldToken = props.getProperty(KX.PROPS.BOT_TOKEN);
    var oldOwner = kxOwnerId_() || kxString_(kxGetSetting_('owner_telegram_user_id', ''));
    props.setProperty(KX.PROPS.BOT_TOKEN, token);
    var bot;
    try { bot = kxTelegramRequest_('getMe', {}); }
    catch (err) {
      if (oldToken) props.setProperty(KX.PROPS.BOT_TOKEN, oldToken);
      else props.deleteProperty(KX.PROPS.BOT_TOKEN);
      throw err;
    }
    props.setProperty(KX.PROPS.OWNER_ID, ownerId);
    kxSetSetting_('owner_telegram_user_id', ownerId, 'شناسه نمایشی مدیر؛ کنترل دسترسی در Script Properties نگهداری می‌شود');
    if (oldToken !== token || oldOwner !== ownerId) {
      props.deleteProperty(KX.PROPS.TELEGRAM_OFFSET);
      props.deleteProperty(KX.PROPS.INBOX_CHAT_ID);
      props.deleteProperty(KX.PROPS.LAST_POLL_AT);
      props.deleteProperty(KX.PROPS.LAST_POLL_ERROR);
      if (oldOwner) kxClearState_(oldOwner);
    }
    return { bot_username: bot.username, owner_id: ownerId };
  });
  onOpen();
  ui.alert('✅ ربات @' + result.bot_username + ' و مدیر ثبت شدند.\n' +
    'اکنون گزینه ۳: فعال‌سازی اتصال خصوصی تلگرام را اجرا کنید.\n' +
    'در چت خصوصی ربات /start بفرستید. برای گروه، ربات را Admin کنید و /bind_inbox بفرستید.\n' +
    'Deploy یا Web App لازم نیست.');
  return result;
}

/** Pin the existing installation's owner once when explicitly activating. */
function kxEnsurePrivateCredentials_() {
  kxSpreadsheet_();
  kxBotToken_();
  if (!kxOwnerId_()) {
    var legacyOwner = kxNormalizeDigits_(kxGetSetting_('owner_telegram_user_id', '')).trim();
    kxAssert_(/^[1-9]\d{4,15}$/.test(legacyOwner) && Number.isSafeInteger(Number(legacyOwner)),
      'ابتدا گزینه ۲: ثبت توکن و مدیر را اجرا کنید.');
    kxProps_().setProperty(KX.PROPS.OWNER_ID, legacyOwner);
  }
  return kxTelegramRequest_('getMe', {});
}

function kxEnsureClockTrigger_(handler, minutes) {
  var matches = ScriptApp.getProjectTriggers().filter(function (trigger) {
    return trigger.getHandlerFunction() === handler;
  });
  if (!matches.length) {
    ScriptApp.newTrigger(handler).timeBased().everyMinutes(minutes).create();
  } else {
    // Keep a working trigger when repairing duplicate installations.
    matches.slice(1).forEach(function (trigger) { ScriptApp.deleteTrigger(trigger); });
  }
}

function installKavexTelegramPoller_() {
  kxEnsurePrivateCredentials_();
  // Preserve queued messages when switching away from webhooks.
  kxTelegramRequest_('deleteWebhook', { drop_pending_updates: false });
  kxEnsureClockTrigger_('runKavexTelegramPoller', 1);
  return { ok: true, mode: 'private_polling' };
}

function activateKavexPrivateTelegram() {
  var result = kxWithLock_(installKavexTelegramPoller_);
  onOpen();
  SpreadsheetApp.getUi().alert(
    '✅ دریافت خصوصی تلگرام فعال شد؛ نسخه ' + KAVEX_CHANNEL_BOT_VERSION + '\n\n' +
    'در چت خصوصی ربات /start بفرستید.\n' +
    'برای گروه: یک گروه خصوصی فقط با دو عضو (شما و ربات) داشته باشید، ربات را Admin کنید و داخل همان گروه /bind_inbox بفرستید.\n' +
    'پیام‌های جدید را پس از تأیید اتصال گروه Forward کنید.\n' +
    'پاسخ با اجرای بعدی زمان‌بند، معمولاً حدود یک دقیقه بعد می‌رسد.\n' +
    'برای آزمایش فوری، از منو «دریافت پیام‌های تلگرام همین حالا» را اجرا کنید.'
  );
  return result;
}

function pollKavexTelegramNow() {
  var result = runKavexTelegramPoller();
  SpreadsheetApp.getUi().alert('✅ دریافت پیام‌ها اجرا شد. تعداد رویدادهای دریافت‌شده: ' + result.processed +
    '\nاگر پاسخی دریافت نشد، گزینه «وضعیت اتصال خصوصی» را بررسی کنید. پیام‌های سایر کاربران نادیده گرفته می‌شوند.');
  return result;
}

function showKavexPrivatePollingInfo() {
  var webhook = kxTelegramRequest_('getWebhookInfo', {});
  var triggers = ScriptApp.getProjectTriggers();
  var hasPoller = triggers.some(function (trigger) { return trigger.getHandlerFunction() === 'runKavexTelegramPoller'; });
  var hasScheduler = triggers.some(function (trigger) { return trigger.getHandlerFunction() === 'runChannelScheduler'; });
  var lastPoll = kxProps_().getProperty(KX.PROPS.LAST_POLL_AT);
  var lastError = kxProps_().getProperty(KX.PROPS.LAST_POLL_ERROR);
  var text = 'نسخه: ' + KAVEX_CHANNEL_BOT_VERSION +
    '\nشناسه مدیر: ' + (kxOwnerId_() || 'ثبت نشده؛ گزینه ۳ را اجرا کنید') +
    '\nزمان‌بند دریافت: ' + (hasPoller ? 'نصب شده' : 'نصب نشده؛ گزینه ۳ را اجرا کنید') +
    '\nWebhook: ' + (webhook.url ? 'هنوز فعال است؛ گزینه ۳ را اجرا کنید' : 'غیرفعال؛ مناسب دریافت خصوصی') +
    '\nگروه متصل: ' + (kxInboxChatId_() || 'ثبت نشده؛ /bind_inbox را در گروه بفرستید') +
    '\nانتشار زمان‌بندی‌شده کانال: ' + (hasScheduler ? 'فعال' : 'نصب نشده') +
    '\nآخرین دریافت موفق: ' + (lastPoll ? Utilities.formatDate(new Date(lastPoll), KX.TIMEZONE, 'yyyy-MM-dd HH:mm:ss') : 'هنوز اجرا نشده');
  if (lastError) text += '\nآخرین خطای دریافت: ' + lastError;
  if (kxInboxChatId_()) {
    try {
      var groupProblem = kxPrivateInboxProblem_(kxInboxChatId_());
      text += '\nشرایط گروه: ' + (groupProblem || 'خصوصی و دو نفره');
    } catch (err) { text += '\nبررسی گروه موفق نبود؛ دسترسی ربات را بررسی کنید.'; }
  }
  SpreadsheetApp.getUi().alert(text);
  return { ok: !webhook.url && hasPoller && !!lastPoll && !lastError && !!kxOwnerId_(), mode: 'private_polling' };
}

// Compatibility entries for a sheet tab whose old menu has not refreshed yet.
function configureKavexWebAppUrl() {
  onOpen();
  SpreadsheetApp.getUi().alert('منو به‌روز شد. گزینه ۳: فعال‌سازی اتصال خصوصی تلگرام را اجرا کنید. Web App لازم نیست.');
}

function registerKavexWebhook() {
  return activateKavexPrivateTelegram();
}

function showKavexWebhookInfo() {
  return showKavexPrivatePollingInfo();
}

function deleteKavexWebhook() {
  return kxTelegramRequest_('deleteWebhook', { drop_pending_updates: false });
}

function testKavexDestinationAccess() {
  var destination = kxGetSetting_('destination_channel', '@kavexir');
  var bot = kxTelegramRequest_('getMe', {});
  var member = kxTelegramRequest_('getChatMember', { chat_id: destination, user_id: bot.id });
  var allowed = member.status === 'creator' || (member.status === 'administrator' && member.can_post_messages !== false);
  kxAssert_(allowed, 'ربات در کانال مقصد Admin نیست یا اجازه Post Messages ندارد.');
  SpreadsheetApp.getUi().alert('✅ ربات @' + bot.username + ' اجازه انتشار در ' + destination + ' را دارد. هیچ پیام آزمایشی منتشر نشد.');
  return member;
}

function installKavexScheduler() {
  kxWithLock_(function () {
    kxEnsurePrivateCredentials_();
    kxEnsureClockTrigger_('runChannelScheduler', 5);
  });
  onOpen();
  SpreadsheetApp.getUi().alert(
    '✅ زمان‌بندی انتشار کانال هر ۵ دقیقه نصب شد.\n' +
    'همه ردیف‌های فعال Templates در ساعت خودشان بررسی می‌شوند.\n' +
    'جمعه‌ها، تاریخ‌های فعال Holidays و پنجشنبه بعد از ۱۲:۳۰ انتشار خودکار متوقف است.\n' +
    'برای دریافت پیام‌های تلگرام، گزینه ۳ را هم فعال کنید.'
  );
  return { ok: true };
}

function kxRemoveTriggers_(handler) {
  var removed = 0;
  ScriptApp.getProjectTriggers().forEach(function (trigger) {
    if (trigger.getHandlerFunction() === handler) {
      ScriptApp.deleteTrigger(trigger);
      removed++;
    }
  });
  return { removed: removed };
}

function stopKavexPrivateTelegram() {
  var result = kxWithLock_(function () { return kxRemoveTriggers_('runKavexTelegramPoller'); });
  SpreadsheetApp.getUi().alert('دریافت پیام‌های تلگرام متوقف شد. تعداد زمان‌بندهای حذف‌شده: ' + result.removed);
  return result;
}

function removeKavexScheduler(showAlert) {
  var result = kxWithLock_(function () { return kxRemoveTriggers_('runChannelScheduler'); });
  if (showAlert !== false) SpreadsheetApp.getUi().alert('انتشار زمان‌بندی‌شده کانال متوقف شد. تعداد زمان‌بندهای حذف‌شده: ' + result.removed);
  return result;
}

function runKavexSchedulerFromMenu() {
  var result = runChannelScheduler();
  SpreadsheetApp.getUi().alert('اجرای زمان‌بندی انجام شد:\n' + kxJson_(result));
  return result;
}



/* ===== 08_SiteRelay.gs ===== */
/** Site-approved messages -> existing Telegram bot; private outbound polling. */
function kxSiteRelayConfig_() {
  var props = kxProps_();
  var url = kxString_(props.getProperty('KX_SITE_RELAY_URL')).replace(/\/+$/, '');
  var key = kxString_(props.getProperty('KX_SITE_RELAY_KEY'));
  var chat = kxString_(props.getProperty('KX_SITE_RELAY_CHAT_ID'));
  kxAssert_(/^https:\/\/[A-Za-z0-9.-]+(?::443)?$/.test(url), 'آدرس اصلی HTTPS سایت را بدون مسیر یا پارامتر وارد کنید.');
  kxAssert_(/^[a-f0-9]{64}$/.test(key), 'کلید اتصال سایت باید ۶۴ نویسه هگز باشد.');
  kxAssert_(/^@[A-Za-z0-9_]{4,}$/.test(chat) || /^-100\d+$/.test(chat), 'شناسه کانال معتبر نیست.');
  return { url: url, key: key, chat: chat };
}

function kxSiteRelayRequest_(action, payload) {
  var cfg = kxSiteRelayConfig_();
  var response;
  try {
    response = UrlFetchApp.fetch(cfg.url + '/api/messaging/market-relay/' + action + '/', {
      method: 'post', contentType: 'application/json',
      headers: { Authorization: 'Bearer ' + cfg.key },
      payload: JSON.stringify(payload || {}), muteHttpExceptions: true,
      followRedirects: false, validateHttpsCertificates: true, timeoutSeconds: 15
    });
  } catch (error) {
    // Never expose request exceptions; they may contain a credential or URL.
    throw new Error('ارتباط واسط با سایت برقرار نشد.');
  }
  var code = response.getResponseCode();
  var parsed = kxParseJson_(response.getContentText(), null);
  if (code !== 200 || !parsed || typeof parsed !== 'object') {
    var failure = new Error('پاسخ سایت معتبر نیست (HTTP ' + code + ').');
    failure.relayHttpCode = code;
    throw failure;
  }
  return parsed;
}

function kxSiteRelayAck_(pending) {
  var result;
  try {
    result = kxSiteRelayRequest_('ack', { id: pending.id, receipt: pending.receipt,
      status: pending.status, message_id: pending.message_id || '' });
  } catch (error) {
    if (error.relayHttpCode === 409) {
      // The operator may have resolved this attempt. Do not block later jobs
      // and never resend this one. The site keeps the uncertain state.
      kxProps_().deleteProperty('KX_SITE_RELAY_PENDING');
    }
    throw error;
  }
  kxAssert_(result.ok === true, 'ثبت رسید در سایت تأیید نشد.');
  kxProps_().deleteProperty('KX_SITE_RELAY_PENDING');
}

function runKavexSiteRelay() {
  try {
    return kxWithLock_(function () {
      var cfg = kxSiteRelayConfig_();
      kxBotToken_();
      var saved = kxProps_().getProperty('KX_SITE_RELAY_PENDING');
      if (saved) {
        var pending = kxParseJson_(saved, null);
        kxAssert_(pending && pending.id && pending.receipt, 'رسید محلی معتبر نیست؛ وضعیت کانال را بررسی کنید.');
        // A previous execution stopped at an unknown point in sendMessage.
        if (pending.status === 'sending') pending.status = 'unknown';
        kxSiteRelayAck_(pending);
      }
      var started = Date.now();
      var processed = 0;
      while (processed < 3 && Date.now() - started < 45000) {
        var claimed = kxSiteRelayRequest_('claim', {});
        if (claimed.job === null) break;
        var job = claimed.job;
        kxAssert_(job && job.id && job.receipt, 'پاسخ صف سایت معتبر نیست.');
        var checkpoint = { id: job.id, receipt: job.receipt, status: 'sending', message_id: '' };
        // Persist BEFORE a send, and retain it until the site acknowledges.
        kxProps_().setProperty('KX_SITE_RELAY_PENDING', JSON.stringify(checkpoint));
        if (kxString_(job.chat_id) !== cfg.chat || !job.text ||
            typeof job.text !== 'string' || job.text.length > 4000 ||
            !isFinite(Date.parse(job.expires_at)) || Date.parse(job.expires_at) <= Date.now() + 15000) {
          checkpoint.status = 'failed';
        } else {
          try {
            var message = kxTelegramRequest_('sendMessage', {
              chat_id: cfg.chat, text: job.text, disable_web_page_preview: true
            });
            kxAssert_(message && /^[1-9]\d*$/.test(kxString_(message.message_id)), 'شناسه ارسال معتبر نیست.');
            checkpoint.message_id = kxString_(message.message_id);
            checkpoint.status = 'sent';
          } catch (sendError) {
            checkpoint.status = /\(HTTP (?:400|401|403|404|429)\)/.test(kxString_(sendError.message)) ? 'failed' : 'unknown';
          }
        }
        kxProps_().setProperty('KX_SITE_RELAY_PENDING', JSON.stringify(checkpoint));
        kxSiteRelayAck_(checkpoint);
        processed++;
        if (processed < 3) Utilities.sleep(1100);
      }
      kxProps_().setProperty('KX_SITE_RELAY_LAST_POLL', kxNowIso_());
      kxProps_().deleteProperty('KX_SITE_RELAY_ERROR');
      return { processed: processed };
    });
  } catch (error) {
    kxProps_().setProperty('KX_SITE_RELAY_ERROR', 'دریافت یا ثبت نتیجه ناموفق بود؛ اتصال سایت و وضعیت صف را بررسی کنید.');
    throw new Error('واسط سایت کامل اجرا نشد؛ وضعیت اتصال سایت و صف پیام‌ها را بررسی کنید.');
  }
}

function configureKavexSiteRelay() {
  var ui = SpreadsheetApp.getUi();
  var inputs = [
    ['KX_SITE_RELAY_URL', 'آدرس اصلی سایت', 'مثال: https://kavehmetal.com — بدون /api یا مسیر دیگر'],
    ['KX_SITE_RELAY_KEY', 'کلید اتصال سایت', 'همان کلید ۶۴ نویسه‌ای ساخته‌شده در پنل کانال سایت را وارد کنید.'],
    ['KX_SITE_RELAY_CHAT_ID', 'شناسه کانال سایت', 'دقیقاً همان مقصد تنظیم‌شده در سایت؛ مثلاً @kavehmetal. ربات باید مدیر همین کانال باشد.']
  ];
  var values = {};
  for (var i = 0; i < inputs.length; i++) {
    var answer = ui.prompt(inputs[i][1], inputs[i][2], ui.ButtonSet.OK_CANCEL);
    if (answer.getSelectedButton() !== ui.Button.OK) return;
    values[inputs[i][0]] = kxString_(answer.getResponseText()).trim();
  }
  kxAssert_(/^https:\/\/[A-Za-z0-9.-]+(?::443)?\/?$/.test(values.KX_SITE_RELAY_URL), 'فقط آدرس اصلی HTTPS سایت مجاز است.');
  kxAssert_(/^[a-f0-9]{64}$/.test(values.KX_SITE_RELAY_KEY), 'کلید اتصال معتبر نیست.');
  kxAssert_(/^@[A-Za-z0-9_]{4,}$|^-100\d+$/.test(values.KX_SITE_RELAY_CHAT_ID), 'شناسه کانال معتبر نیست.');
  kxWithLock_(function () {
    if (kxProps_().getProperty('KX_SITE_RELAY_PENDING')) {
      kxAssert_(values.KX_SITE_RELAY_URL.replace(/\/+$/, '') === kxString_(kxProps_().getProperty('KX_SITE_RELAY_URL')).replace(/\/+$/, '') &&
        values.KX_SITE_RELAY_CHAT_ID === kxProps_().getProperty('KX_SITE_RELAY_CHAT_ID'),
        'رسید منتظر ثبت وجود دارد؛ تا ثبت رسید، سایت و مقصد را تغییر ندهید. تغییر کلید همان اتصال مجاز است.');
    }
    Object.keys(values).forEach(function (key) { kxProps_().setProperty(key, values[key]); });
  });
  ui.alert('تنظیمات سایت ذخیره شد. اکنون «فعال‌سازی دریافت پیام‌های سایت» را اجرا کنید.');
}

function activateKavexSiteRelay() {
  kxSiteRelayConfig_();
  kxBotToken_();
  kxWithLock_(function () { kxEnsureClockTrigger_('runKavexSiteRelay', 1); });
  SpreadsheetApp.getUi().alert('دریافت صف سایت تقریباً هر دقیقه فعال شد. در هر اجرا حداکثر ۳ پیام تأییدشده ارسال می‌شود. Web App یا تغییر Webhook لازم نیست.');
}

function stopKavexSiteRelay() {
  kxWithLock_(function () { kxRemoveTriggers_('runKavexSiteRelay'); });
  SpreadsheetApp.getUi().alert('دریافت پیام‌های سایت متوقف شد.');
}

function showKavexSiteRelayInfo() {
  var props = kxProps_();
  SpreadsheetApp.getUi().alert('آخرین دریافت موفق: ' + (props.getProperty('KX_SITE_RELAY_LAST_POLL') || 'هنوز اجرا نشده') +
    '\nرسید منتظر ثبت: ' + (props.getProperty('KX_SITE_RELAY_PENDING') ? 'بله؛ دریافت سایت را اجرا کنید' : 'خیر') +
    '\nوضعیت: ' + (props.getProperty('KX_SITE_RELAY_ERROR') || 'خطایی ثبت نشده'));
}
